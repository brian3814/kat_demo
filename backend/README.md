# ADK Chat Service

FastAPI backend for Google ADK (Agent Development Kit) chat integration with MCP (Model Context Protocol) extensibility.

## Overview

This backend service provides a streaming chat API that:
- Accepts POST requests with chat messages
- Connects to Google's Gemini models using the ADK
- Streams responses back in real-time as NDJSON
- Provides extensibility for future MCP tools integration
- Is designed to be consumed by Omniverse Kit extensions

## Architecture

```
Omniverse Extension (Client)
    ↓ HTTP/JSON
FastAPI Backend (this service)
    ↓ Google ADK
Gemini LLM
    ↓ (Phase 2)
MCP Tools (extensible)
```

## Features

✅ **FastAPI Backend**: Modern, async Python framework with automatic API docs
✅ **Google ADK Integration**: Streaming chat with Gemini models
✅ **NDJSON Streaming**: Newline-delimited JSON for progressive rendering
✅ **CORS Support**: Configured for local Omniverse extension communication
✅ **MCP Ready**: Plugin architecture for Phase 2 tool integration
✅ **Structured Logging**: JSON logs with request tracking
✅ **Type Safety**: Pydantic models for request/response validation

## Setup

### Prerequisites

- Python 3.10 or higher
- Google API key for ADK (get from [Google AI Studio](https://aistudio.google.com/))

### Installation

1. **Navigate to backend directory**:
   ```bash
   cd d:\code\omniverse_learn\demo\backend
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment**:
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure environment**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your Google API key:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```

## Running the Server

### Development Mode

```bash
python run_server.py
```

The server will start at `http://localhost:8000` with hot reload enabled.

### Direct uvicorn

```bash
uvicorn adk_chat_service.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production Mode

For production, disable reload and use multiple workers:

```bash
uvicorn adk_chat_service.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## API Endpoints

### POST /api/v1/chat/stream

Stream chat responses from Google ADK.

**Request Body**:
```json
{
  "message": "Hello, how are you?",
  "conversation_id": "optional-uuid",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

**Response**: Streaming NDJSON
```
{"chunk_id": "uuid-1", "content": "Hello", "done": false, "metadata": null}
{"chunk_id": "uuid-2", "content": "! I'm", "done": false, "metadata": null}
{"chunk_id": "uuid-3", "content": " doing well", "done": false, "metadata": null}
{"chunk_id": "uuid-4", "content": "", "done": true, "metadata": {"total_chunks": 3}}
```

**cURL Example**:
```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a joke"}'
```

**Python Example**:
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/chat/stream",
    json={"message": "Hello!"},
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

### GET /api/v1/health

Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "adk_ready": true,
  "timestamp": "2025-12-15T10:30:00Z"
}
```

### GET /

Root endpoint with service information.

### GET /ping

Simple connectivity check.

## Omniverse Extension Integration

Use this client pattern in your Omniverse extension:

```python
import aiohttp
import json

class ADKChatClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None

    async def stream_chat(self, message: str):
        """Stream chat responses from backend."""
        if not self.session:
            self.session = aiohttp.ClientSession()

        async with self.session.post(
            f"{self.base_url}/api/v1/chat/stream",
            json={"message": message}
        ) as response:
            async for line in response.content:
                if line:
                    chunk = json.loads(line.decode('utf-8'))
                    if not chunk.get("done"):
                        yield chunk["content"]

    async def close(self):
        """Cleanup session."""
        if self.session:
            await self.session.close()

# Usage
client = ADKChatClient()
async for text in client.stream_chat("Hello!"):
    print(text, end='', flush=True)
await client.close()
```

## Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | (required) | Google API key for ADK |
| `MODEL_NAME` | `gemini-2.0-flash-exp` | Gemini model to use |
| `TEMPERATURE` | `0.7` | Model temperature (0.0-2.0) |
| `MAX_TOKENS` | `2048` | Max tokens in response |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `CORS_ORIGINS` | `["http://localhost:*"]` | Allowed CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENABLE_TOOLS` | `false` | Enable MCP tools (Phase 2) |

## Project Structure

```
backend/
├── adk_chat_service/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings
│   ├── models.py                  # Pydantic models
│   ├── routes/
│   │   └── chat.py               # Chat endpoints
│   ├── services/
│   │   ├── adk_client.py         # Google ADK wrapper
│   │   └── stream_handler.py     # Stream utilities
│   ├── middleware/
│   │   └── cors.py               # CORS config
│   ├── tools/                     # MCP tools (Phase 2)
│   │   ├── base.py
│   │   └── registry.py
│   └── utils/
│       ├── exceptions.py
│       └── logger.py
├── tests/                         # Test suite
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── run_server.py
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black adk_chat_service/

# Lint
ruff check adk_chat_service/

# Type checking
mypy adk_chat_service/
```

## Phase 2: MCP Tools Integration

The backend is designed for extensibility with MCP (Model Context Protocol) tools. In Phase 2:

1. **Install MCP SDK**: `pip install mcp`
2. **Implement Tools**: Create tool plugins in `tools/builtin/`
3. **Register with ADK**: Tools automatically registered with agent
4. **Function Calling**: LLM can invoke tools during conversation

### Example Tool

```python
from adk_chat_service.tools.base import BaseTool

class FileReadTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read contents of a file",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        )

    async def execute(self, path: str) -> str:
        with open(path, 'r') as f:
            return f.read()
```

## Troubleshooting

### Server won't start

- Check `.env` file exists and has `GOOGLE_API_KEY`
- Verify port 8000 is not in use
- Check Python version: `python --version` (need 3.10+)

### API key errors

- Verify API key is valid at [Google AI Studio](https://aistudio.google.com/)
- Check key has proper permissions for Gemini API

### Streaming not working

- Ensure client is reading response incrementally
- Check CORS settings if calling from browser
- Verify `Content-Type: application/json` header

### Import errors

- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

## Security

⚠️ **Important Security Notes**:

1. **Never commit `.env` file** - Contains API keys
2. **Restrict CORS in production** - Current config allows localhost
3. **Use HTTPS in production** - Don't send API keys over HTTP
4. **Rate limiting** - Add rate limiting for production
5. **Input validation** - All inputs validated with Pydantic

## License

Part of the Omniverse demo project.

## Support

For issues or questions:
1. Check API documentation at `/docs`
2. Review logs for error details
3. Verify configuration in `.env`
4. Check Google ADK documentation

## Links

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
