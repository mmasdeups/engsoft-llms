import os
import json # New import
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse # Modified import
from pydantic import BaseModel
from typing import List, Union, Dict, Any
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

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, Any]]]

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        api_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        async def generate_chunks():
            full_content = ""
            final_usage = None
            
            response_stream = await client.chat.completions.create(
                model=MODEL,
                messages=api_messages,
                stream=True, # New: Enable streaming
                stream_options={"include_usage": True} # New: Include usage in final chunk
            )

            async for chunk in response_stream:
                try:
                    # Guard every attribute access
                    if hasattr(chunk, "choices") and chunk.choices and chunk.choices[0].delta.content:
                        fragment = chunk.choices[0].delta.content
                        full_content += fragment
                        yield f"data: {json.dumps({'text': fragment})}\n\n"
                    
                    if hasattr(chunk, "usage") and chunk.usage:
                        final_usage = {
                            "prompt_tokens": getattr(chunk.usage, "prompt_tokens", 0),
                            "completion_tokens": getattr(chunk.usage, "completion_tokens", 0),
                            "total_tokens": getattr(chunk.usage, "total_tokens", 0)
                        }
                except Exception as e:
                    # Wrap per-chunk processing so one bad chunk can't kill the whole stream
                    print(f"Error processing chunk: {e}")
            
            # Send the final token usage
            if final_usage:
                yield f"data: {json.dumps({'usage': final_usage})}\n\n"
            
            yield "data: [DONE]\n\n" # Signal end of stream
            
        return StreamingResponse(generate_chunks(), media_type="text/event-stream",
                                 headers={
                                     "Cache-Control": "no-cache",
                                     "X-Accel-Buffering": "no",
                                     "Connection": "keep-alive"
                                 }) # New: Return StreamingResponse with anti-buffering headers

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Ensure static directory exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Mount the static directory to serve CSS and JS
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Serve the main HTML file at the root route
@app.get("/")
async def read_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Frontend index.html not found"}
