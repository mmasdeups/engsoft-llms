import os
import json
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

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

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

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

@app.post("/api/assistants/{assistant_id}/context")
async def update_assistant_context(assistant_id: str, context: str):
    assistants = load_assistants()
    assistant = next((a for a in assistants if a["id"] == assistant_id), None)
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")
    assistant["knowledge"] = context
    save_assistants(assistants)
    return {"message": "Context updated"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
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
                    formatted_content = assistant["prompt_template"].replace("{context}", assistant.get("knowledge", "")).replace("{user_input}", last_msg["content"])
                    last_msg["content"] = formatted_content

        async def generate_chunks():
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
