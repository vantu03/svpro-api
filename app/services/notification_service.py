from datetime import datetime
from sqlalchemy.orm import Session
from app.models.notification import Notification, NotificationTarget
from app.models.user_session import UserSession
from app.services.firebase_service import send_fcm_large_list
from app.socket.ws_store import get_ws_by_user
from app.utils import to_dict
from sqlalchemy.orm import joinedload

async def notify_user(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    target: NotificationTarget = NotificationTarget.user,
):
    # 1. Lưu DB
    notification = Notification(
        user_id=user_id,
        title=title,
        content=content,
        is_read=False,
        target=target,
        created_at=datetime.now()
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # 2. Gửi FCM cho các phiên đang hoạt động
    active_sessions = db.query(UserSession).options(joinedload(UserSession.fcm_token)).filter(
        UserSession.user_id == user_id,
        UserSession.is_active == True
    ).all()

    tokens = [
        s.fcm_token.token
        for s in active_sessions
        if s.fcm_token and s.fcm_token.token
    ]

    if tokens:
        await send_fcm_large_list(tokens, title, content)

    # 3. Gửi WebSocket nếu đang online
    sessions = get_ws_by_user(user_id)
    if sessions:
        for session in sessions:
            if session.is_connected:
                await session.send("notification", to_dict(notification))
