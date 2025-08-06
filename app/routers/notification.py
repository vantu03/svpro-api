from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_session
from app.models.notification import Notification
from app.models.user_session import UserSession
from app.utils import response_json, build_response, to_dict

router = APIRouter()

@router.get("/")
def get_notifications(
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    # Lấy danh sách thông báo cho người dùng hiện tại theo phân trang
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == session.user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Chuyển kết quả thành list dict
    result = [to_dict(n) for n in notifications]

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy danh sách thông báo thành công!",
            data=result
        )
    )
