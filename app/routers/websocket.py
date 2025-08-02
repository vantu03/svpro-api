
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.socket.ws_session import WebSocketSession

router = APIRouter()

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    session = WebSocketSession(websocket)
    try:
        await session.listen_message()
    except WebSocketDisconnect:
        await session.close(reason="Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await session.close(reason="Unexpected error")