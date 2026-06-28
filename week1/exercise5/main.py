import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
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
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # Format the messages array for the OpenAI client
        api_messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        # Call the OpenAI-compatible endpoint
        response = await client.chat.completions.create(
            model=MODEL,
            messages=api_messages
        )
        
        # Parse the assistant message and token usage
        choice = response.choices[0]
        assistant_message = {
            "role": choice.message.role,
            "content": choice.message.content or ""
        }
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0
        }
        
        return {
            "message": assistant_message,
            "usage": usage
        }
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
