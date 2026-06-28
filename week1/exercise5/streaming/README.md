# FastAPI Application with Docker

This application containerizes a FastAPI app that interacts with an LLM via an OpenAI-compatible API.

## Setup

1.  **Create a `.env` file** in the same directory as this README:
    ```
    # Example .env file
    OPENAI_API_BASE="http://host.docker.internal:11434/v1"
    OPENAI_API_KEY="ollama"
    # Add any other environment variables your app needs
    ```
    
    **Important:** When connecting to Ollama running on your host machine, use `http://host.docker.internal:11434/v1` for the `OPENAI_API_BASE`. Do NOT use `localhost` or `127.0.0.1` as these will refer to the container's loopback interface, not your host machine.

2.  **Build and run the application**:
    ```bash
    docker compose up --build
    ```

## Access the application

Once the application is running, you can access it at: http://localhost:6662
