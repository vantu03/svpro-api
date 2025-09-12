
from app.dependencies import verify_token
from app.models.user_session import UserSession
from app.services.notification_service import notify_user
from app.socket.ws_store import add_session, get_ws_by_user, connected_sessions


class WebsocketController:
    def __init__(self, session):
        self.session = session

    async def process_message(self, msg):
        cmd = msg.get("cmd")

        payload = msg.get("payload")
        if not self.session.is_auth:
            if cmd == "auth":
                token = payload.get("token", "")
                if not token:
                    await self.session.send('logout', {})
                    await self.session.close()
                    return

                try:
                    user_session: UserSession = await verify_token(token)
                    if not user_session:

                        # Gán thông tin user/session vào WebSocketSession
                        self.session.user_id = user_session.user_id
                        self.session.session_id = user_session.id
                        self.session.is_auth = True
                        add_session(self.session)
                        await self.session.send('auth_done', {})

                        print(f"[WS] size: {len(connected_sessions)}")
                except Exception as e:
                    await self.session.send('logout', {})
                    await self.session.send('auth_failed', {"reason": "expired"})
                    await self.session.close()
        else:
            if cmd == "logout_all":
                ws_users = get_ws_by_user(user_id=self.session.user_id)
                if ws_users is not None:
                    for ws_user in ws_users:
                        try:
                            await ws_user.send('logout', {})
                            await ws_user.close()
                        except Exception as e:
                            print(f"[WS] Lỗi gửi socket: {e}")

            elif cmd == "ping":
                await self.session.send('pong', {})

            elif cmd == "add_test_notification":
                await notify_user(
                    self.session.db,
                    user_id=self.session.user_id,
                    title="📢 Thông báo test",
                    content=f"Đây là thông báo thử nghiệm",
                    sound='sound_warning.wav'
                )
            elif cmd == "subscribe_order_pending":
                self.session.subscribed_order_pending = True
                await self.session.send("subscribed", {"topic": "order_pending"})

            elif cmd == "unsubscribe_order_pending":
                self.session.subscribed_order_pending = False
                await self.session.send("unsubscribed", {"topic": "order_pending"})

            elif cmd == "location":
                lat = payload.get("latitude")
                lng = payload.get("longitude")
                timestamp = payload.get("timestamp")

                self.session.last_location = {
                    "lat": lat,
                    "lng": lng,
                    "timestamp": timestamp,
                }

                ws_users = get_ws_by_user(user_id=self.session.user_id)
                if ws_users:
                    for ws_user in ws_users:
                        if ws_user != self.session:
                            await ws_user.send("location_update", {
                                "user_id": self.session.user_id,
                                "lat": lat,
                                "lng": lng,
                                "timestamp": timestamp,
                            })

    async def cleanup(self):
        pass