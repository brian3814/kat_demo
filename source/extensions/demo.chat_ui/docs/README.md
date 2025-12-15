# Chat UI Extension

A chat interface extension for NVIDIA Omniverse Kit that connects to a FastAPI backend for LLM interactions with streaming support.

## Features

- **Streaming Chat Interface**: Real-time streaming of LLM responses
- **Clean UI**: Message bubbles for user and assistant messages
- **Status Indicator**: Visual feedback for connection and processing states
- **Conversation History**: Maintains context across multiple messages
- **Backend Health Check**: Automatic verification of backend availability on startup

## Architecture

### Components

1. **backend_client.py**: Async HTTP client using aiohttp for streaming NDJSON responses
2. **message_widget.py**: UI components for displaying messages and status
3. **chat_window.py**: Main chat window with input field and message history
4. **extension.py**: Extension entry point and lifecycle management

### Backend Communication

- **Endpoint**: `POST /api/v1/chat/stream`
- **Format**: NDJSON (Newline-Delimited JSON)
- **Request**:
  ```json
  {
    "message": "User message",
    "temperature": 0.7,
    "max_tokens": 2048,
    "conversation_history": []
  }
  ```
- **Response Stream**:
  ```json
  {"content": "chunk", "done": false, "chunk_id": 0}
  {"content": "next", "done": false, "chunk_id": 1}
  {"content": "", "done": true, "chunk_id": 2}
  ```

## Installation

### Prerequisites

1. NVIDIA Omniverse Kit installed
2. FastAPI backend running at `http://localhost:8000`

### Setup

1. Copy the extension to your Omniverse extensions directory:
   ```
   source/extensions/demo.chat_ui/
   ```

2. Enable the extension in Omniverse:
   - Open Extension Manager (Window > Extensions)
   - Search for "Chat UI"
   - Click Enable

3. Or add to your `.kit` file:
   ```toml
   [dependencies]
   "demo.chat_ui" = {}
   ```

## Usage

### Opening the Chat Window

- **Menu**: Window > LLM Chat
- The chat window will open automatically when the extension starts

### Sending Messages

1. Type your message in the input field at the bottom
2. Click "Send" or press the Send button
3. Watch the response stream in real-time

### Status Indicator

- **Green (Ready)**: Connected to backend and ready to chat
- **Orange (Thinking)**: Processing request
- **Red (Error)**: Backend unavailable or error occurred

## Configuration

Edit settings in [extension.toml](../config/extension.toml):

```toml
[settings]
exts."demo.chat_ui".backend_url = "http://localhost:8000"
exts."demo.chat_ui".api_endpoint = "/api/v1/chat/stream"
exts."demo.chat_ui".default_temperature = 0.7
exts."demo.chat_ui".default_max_tokens = 2048
```

## Backend Setup

Ensure the FastAPI backend is running:

```bash
cd backend
uv pip install -e .
python run_server.py
```

The backend should be accessible at `http://localhost:8000`.

## Troubleshooting

### Extension Not Loading

1. Check Extension Manager for error messages
2. Verify Python dependencies are installed
3. Check Omniverse console for stack traces

### Backend Connection Issues

1. Verify backend is running: `curl http://localhost:8000/health`
2. Check firewall settings for localhost communication
3. Review CORS configuration in backend [config.py](../../../backend/adk_chat_service/config.py)

### UI Not Updating

1. Check Omniverse console for asyncio errors
2. Verify aiohttp is installed in Omniverse Python environment
3. Try restarting the extension

### Streaming Not Working

1. Verify backend sends proper NDJSON format
2. Check backend logs for streaming errors
3. Test endpoint directly: `curl -X POST http://localhost:8000/api/v1/chat/stream -H "Content-Type: application/json" -d '{"message":"test"}'`

## Development

### File Structure

```
demo.chat_ui/
├── config/
│   └── extension.toml          # Extension configuration
├── demo/
│   └── chat_ui/
│       ├── __init__.py         # Package init
│       ├── extension.py        # Extension entry point
│       ├── chat_window.py      # Main UI window
│       ├── backend_client.py   # HTTP client
│       └── message_widget.py   # Message UI components
├── data/
│   └── icons/                  # Extension icons
└── docs/
    └── README.md               # This file
```

### Adding Features

1. **Custom Styling**: Edit message_widget.py to customize colors and layouts
2. **Additional Parameters**: Extend backend_client.py to support more model parameters
3. **Message Types**: Add new message types in message_widget.py
4. **UI Enhancements**: Modify chat_window.py to add new controls

## API Reference

### BackendClient

```python
class BackendClient:
    async def stream_chat(message: str, temperature: float, max_tokens: int, conversation_history: list) -> AsyncGenerator
    async def send_chat(message: str, temperature: float, max_tokens: int, conversation_history: list) -> dict
    async def health_check() -> bool
    async def close()
```

### MessageWidget

```python
class MessageWidget:
    def __init__(message_type: Literal["user", "assistant"], initial_content: str)
    def build() -> ui.Frame
    def append_content(content: str)
    def set_content(content: str)
```

### ChatWindow

```python
class ChatWindow(ui.Window):
    def __init__(title: str, width: int, height: int)
    async def check_backend_health() -> bool
    def clear_chat()
    def destroy()
```

## License

Internal demo extension for Omniverse learning project.

## Support

For issues or questions, check:
- Backend logs: `backend/logs/`
- Omniverse console: Window > Console
- Extension logs: Check Extension Manager
