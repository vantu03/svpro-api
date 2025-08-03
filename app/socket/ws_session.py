import json
from starlette.websockets import WebSocket

from app.database import SessionLocal
from app.socket.ws_controller import WebsocketController
from app.socket.ws_store import remove_session


class WebSocketSession:

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.controller: WebsocketController = WebsocketController(self)
        self.user_id: int | None = None
        self.session_id: int | None = None
        self.is_connected = False
        self.is_auth = False
        self.db = SessionLocal()

    async def listen_message(self):
        self.is_connected = True
        await self.send('auth', {})
        while self.is_connected:
            raw = await self.websocket.receive_text()
            try:
                message = json.loads(raw)
                await self.controller.process_message(message)
            except json.JSONDecodeError:
                await self.close()

    async def close(self, code: int = 1000, reason: str = "Normal Closure"):
        self.is_connected = False
        remove_session(self)
        try:
            await self.websocket.close(code=code, reason=reason)
        except RuntimeError as e:
            print(f"[!] WebSocket already closed: {e}")
        await self.controller.cleanup()
        self.db.close()

    async def send(self, cmd: str, payload: dict):
        try:
            await self.websocket.send_json({
                "cmd": cmd,
                "payload": payload
            })
        except RuntimeError as e:
            if "close message has been sent" in str(e):
                print(f"[!] Gửi thất bại, WebSocket đã đóng (user_id={self.user_id})")
            else:
                raise
        except Exception as e:
            print(f"[!] Gửi thất bại do lỗi khác: {e}")
