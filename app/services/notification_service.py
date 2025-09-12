from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.database import async_session
from app.models.notification import Notification, NotificationTarget
from app.models.user_session import UserSession
from app.services.firebase_service import send_notification
from app.socket.ws_store import get_ws_by_user
from app.utils import to_dict, build_navigate_payload


async def notify_user(
    user_id: int,
    title: str,
    content: str,
    sound: str = None,
    target: NotificationTarget = NotificationTarget.user,
):
    async with async_session() as db:
        # 1. Lưu thông báo vào DB
        notification = Notification(
            user_id=user_id,
            title=title,
            content=content,
            is_read=False,
            target=target,
            created_at=datetime.now(),
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        # 2. Lấy các phiên đang active
        result = await db.execute(
            select(UserSession)
            .options(joinedload(UserSession.fcm_token))
            .where(
                UserSession.user_id == user_id,
                UserSession.is_active.is_(True),
            )
        )
        active_sessions = result.scalars().all()

        tokens = [
            s.fcm_token.token
            for s in active_sessions
            if s.fcm_token and s.fcm_token.token
        ]
        print(f"[FCM] Sending {len(tokens)} tokens: {title} - {content}")

        payload_str = build_navigate_payload("/home", {"tab": "notifications"})

        if tokens:
            # gửi push FCM
            await send_notification(
                tokens,
                title,
                content,
                data={"payload": payload_str},
                sound=sound,
            )

        # 3. Gửi WebSocket cho user nếu đang online
        ws_users = get_ws_by_user(user_id=user_id)
        print(f"[notify_user] Sockets: {len(ws_users)}")
        for ws_user in ws_users:
            try:
                await ws_user.send("notification", to_dict(notification))
            except Exception as e:
                print(f"[WS] Lỗi gửi socket: {e}")
