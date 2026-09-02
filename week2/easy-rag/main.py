import os
import json
import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from openai import AsyncOpenAI
from collections_manager import create_collection, insert, query
from dotenv import load_dotenv
from markitdown import MarkItDown
import datetime

# Load environment variables
TOP_K = int(os.environ.get("TOP_K", "4"))
THRESHOLD = float(os.environ.get("THRESHOLD", "0.5"))
PERSIST_PATH = os.environ.get("PERSIST_PATH", "./collections-store")

# Load environment variables from .env
load_dotenv()

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY or OPENAI_API_KEY == "your-openai-api-key-here":
    print("Warning: OPENAI_API_KEY is not set to a valid API key.")

# Initialize the OpenAI-compatible Async client
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
)

app = FastAPI(title="EASY-CHATGPT")

# Ensure storage directories exist
static_dir = os.path.join(os.path.dirname(__file__), "static")
collections_store = os.path.join(os.path.dirname(__file__), "collections-store")
os.makedirs(static_dir, exist_ok=True)
os.makedirs(collections_store, exist_ok=True)

# Helper functions for assistants
ASSISTANTS_FILE = os.path.join(os.path.dirname(__file__), "assistants.json")

def load_assistants():
    if not os.path.exists(ASSISTANTS_FILE):
        return []
    with open(ASSISTANTS_FILE, "r") as f:
        return json.load(f)

def save_assistants(assistants):
    with open(ASSISTANTS_FILE, "w") as f:
        json.dump(assistants, f, indent=2)

class Assistant(BaseModel):
    id: Optional[str] = None
    name: str
    system_prompt: str
    prompt_template: str
    knowledge: str = ""

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    assistant_id: Optional[str] = None

@app.get("/api/assistants")
async def get_assistants():
    return load_assistants()

@app.post("/api/assistants")
async def create_assistant(assistant: Assistant):
    assistants = load_assistants()
    assistant.id = str(uuid.uuid4())
    assistants.append(assistant.dict())
    save_assistants(assistants)
    return assistant

# Create an ingestion endpoint
@app.post("/api/assistants/{assistant_id}/upload")
async def upload_document(assistant_id: str, file: UploadFile = File(...)):
    assistants = load_assistants()
    assistant = next((a for a in assistants if a["id"] == assistant_id), None)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # Save original file
    file_path = os.path.join(static_dir, f"{assistant_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Convert to markdown
    markitdown = MarkItDown()
    result = markitdown.convert(file_path)
    md_content = result.text_content
    
    md_file_path = file_path + ".md"
    with open(md_file_path, "w") as f:
        f.write(md_content)

    # Initialize collection (using persistent storage)
    col = create_collection(name=assistant_id,
                            description=f"Collection for assistant {assistant['name']}",
                            metric="cosine",
                            persist_path=collections_store)
    
    # Chunking (Simple strategy for now)
    chunks = [md_content[i:i+1000] for i in range(0, len(md_content), 1000)]
    
    success_count = 0
    for i, chunk in enumerate(chunks):
        res = insert(col, chunk, {
            "source": file.filename,  # Required by collections-manager
            "document_url": f"/static/{assistant_id}_{file.filename}",
            "title": file.filename,
            "markdown_url": f"/static/{assistant_id}_{file.filename}.md",
            "chunk_number": i,
            "chunking_strategy": "fixed-1000",
            "ingestion_date": datetime.datetime.now().isoformat()
        })
        if res.get("ok"):
            success_count += 1
        else:
            print(f"Failed to insert chunk {i}: {res}")
        
    return {"message": "Document ingested", "chunks": len(chunks), "successes": success_count}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    provenance = []
    try:
        api_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        if request.assistant_id:
            assistants = load_assistants()
            assistant = next((a for a in assistants if a["id"] == request.assistant_id), None)
            if assistant:
                # Prepend system_prompt
                api_messages.insert(0, {"role": "system", "content": assistant["system_prompt"]})
                
                # Replace placeholders in last user message with template
                last_msg = api_messages[-1]
                if last_msg["role"] == "user":
                    user_query = last_msg["content"]
                    
                    # RAG lookup
                    col = create_collection(name=request.assistant_id,
                                            description=f"Collection for assistant {assistant['name']}",
                                            metric="cosine",
                                            persist_path=collections_store)
                    hits = query(col, user_query, top_k=TOP_K, threshold=THRESHOLD)
                    
                    if not hits:
                        # Refusal
                        answer = "I'm sorry, I don't have enough information in my knowledge base to answer that."
                        # Send back the refusal without calling the model
                        async def generate_refusal():
                            yield f"data: {json.dumps({'text': answer})}\n\n"
                            yield "data: [DONE]\n\n"
                        return StreamingResponse(generate_refusal(), media_type="text/event-stream")

                    # Format context
                    context_text = "\n\n".join([f"[{h['metadata']['title']} · chunk {h['metadata']['chunk_number']} · similarity {h['similarity']:.3f}]\n{h['chunk']}" for h in hits])
                    formatted_content = assistant["prompt_template"].replace("{context}", context_text).replace("{user_input}", user_query)
                    last_msg["content"] = formatted_content
                    
                    # Store provenance for later use in streaming
                    provenance = [{"source": h['metadata']['title'], "url": h['metadata']['document_url'], "chunk": h['metadata']['chunk_number'], "similarity": h['similarity']} for h in hits]

        async def generate_chunks():
            # Send provenance to UI
            if provenance:
                yield f"data: {json.dumps({'provenance': provenance})}\n\n"
            
            # Send the final prompt being used to the frontend first
            yield f"data: {json.dumps({'sent_prompt': api_messages})}\n\n"

            response_stream = await client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                stream=True,
                stream_options={"include_usage": True}
            )

            async for chunk in response_stream:
                try:
                    if hasattr(chunk, "choices") and chunk.choices and chunk.choices[0].delta.content:
                        yield f"data: {json.dumps({'text': chunk.choices[0].delta.content})}\n\n"
                    
                    if hasattr(chunk, "usage") and chunk.usage:
                        yield f"data: {json.dumps({'usage': {
                            'prompt_tokens': getattr(chunk.usage, 'prompt_tokens', 0),
                            'completion_tokens': getattr(chunk.usage, 'completion_tokens', 0),
                            'total_tokens': getattr(chunk.usage, 'total_tokens', 0)
                        }})}\n\n"
                except Exception as e:
                    print(f"Error processing chunk: {e}")
            
            yield "data: [DONE]\n\n"
            
        return StreamingResponse(generate_chunks(), media_type="text/event-stream",
                                 headers={
                                     "Cache-Control": "no-cache",
                                     "X-Accel-Buffering": "no",
                                     "Connection": "keep-alive"
                                 })

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount the static directory to serve CSS and JS
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve the main HTML file at the root route
@app.get("/")
async def read_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Frontend index.html not found"}
