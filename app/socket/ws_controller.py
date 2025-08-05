from app.dependencies import verify_token
from app.services.notification_service import notify_user
from app.socket.ws_store import add_session, get_ws_by_user, connected_sessions


class WebsocketController:
    def __init__(self, session):
        self.session = session

    async def process_message(self, msg):
        cmd = msg.get("cmd")

        print(cmd)
        payload = msg.get("payload")
        print(payload)
        if not self.session.is_auth:
            if cmd == "auth":
                token = payload.get("token", "")
                if not token:
                    await self.session.send('logout', {})
                    await self.session.close()
                    return

                try:
                    user_session = verify_token(token, self.session.db)
                    user = user_session.user

                    # Gán thông tin user/session vào WebSocketSession
                    self.session.user_id = user.id
                    self.session.session_id = user_session.id
                    self.session.is_auth = True
                    add_session(self.session)
                    await self.session.send('auth_done', {})

                    print(f"[WS] size: {len(connected_sessions)}")
                except Exception as e:
                    print('Loi xac thuc '+ str(e))
                    await self.session.send('auth_failed', {})
                    await self.session.close()
        else:
            if cmd == "logout_all":
                wss = get_ws_by_user(user_id=self.session.user_id)
                if wss is not None:
                    for ws in wss:
                        await ws.send('logout', {})
                        ws.close()

            elif cmd == "ping":
                await self.session.send('pong', {})

            elif cmd == "add_test_notification":
                await notify_user(
                    self.session.db,
                    user_id=self.session.user_id,
                    title="📢 Thông báo test",
                    content=f"Đây là thông báo thử nghiệm"
                )

    async def cleanup(self):
        pass