"""WebSocket endpoint for Kit tool connection."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.kit_connection import get_kit_manager
from ..utils.logger import get_logger

logger = get_logger()

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/tools")
async def websocket_tools_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for Kit tool connection.

    Kit connects to this endpoint to:
    1. Register available tools
    2. Receive tool call requests
    3. Send tool results back

    Protocol: JSON-RPC 2.0
    """
    kit_manager = get_kit_manager()

    # Accept connection
    await websocket.accept()
    logger.info("WebSocket connection accepted", client=websocket.client)

    # Register connection
    await kit_manager.register_connection(websocket)

    try:
        # Message loop
        while True:
            message = await websocket.receive_text()
            await kit_manager.handle_message(message)

    except WebSocketDisconnect:
        logger.info("Kit disconnected normally")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        await kit_manager.unregister_connection()
