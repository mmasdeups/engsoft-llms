# EASY-CHATGPT (Streaming) — Docker

A FastAPI app that proxies a chat frontend to an LLM over the OpenAI-compatible API,
streaming the reply token by token. Runs in Docker via `docker compose up`.

## Setup

1. Copy `.env.example` to `.env` and fill in your values:
OPENAI_BASE_URL=http://host.docker.internal:11434/v1

OPENAI_API_KEY=ollama

MODEL=llama3.1:8b

   **Important:** to reach Ollama running on your host machine from inside the
   container, use `http://host.docker.internal:11434/v1` — NOT `localhost` or
   `127.0.0.1`, which refer to the container itself, not your host.

2. Make sure Ollama is running on the host with the model pulled
   (e.g. `ollama pull llama3.1:8b`).

3. Build and run:

```bash
   docker compose up --build
```

## Access

Open http://localhost:6662 in your browser.
