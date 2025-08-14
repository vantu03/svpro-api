from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_session
from app.models.notification import Notification
from app.models.user_session import UserSession
from app.schemas.notification import NotificationListRequest, NotificationUpdateRequest
from app.socket.ws_store import get_ws_by_user
from app.utils import response_json, build_response, to_dict

router = APIRouter()

@router.get("/")
def get_notifications(
    data: NotificationListRequest = Depends(),
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    # Tạo câu query cơ bản
    q = db.query(Notification).filter(Notification.user_id == session.user.id)

    # Lọc theo status nếu có
    if data.status:
        if data.status == "unread":
            q = q.filter(Notification.is_read == False)
        elif data.status == "read":
            q = q.filter(Notification.is_read == True)

    # Sắp xếp và phân trang
    notifications = (
        q.order_by(Notification.created_at.desc())
        .offset(data.offset)
        .limit(data.limit)
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


@router.post("/read")
async def mark_notification_read(
    payload: NotificationUpdateRequest,
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    notification = db.query(Notification).filter(
        Notification.id == payload.id,
        Notification.user_id == session.user.id,
    ).first()

    if not notification:
        return build_response(
            detail=response_json(
                status=False,
                message="Không tìm thấy thông báo hoặc không có quyền truy cập.",
            )
        )

    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)


    unread_count = (
        db.query(Notification)
        .filter(Notification.user_id == session.user.id, Notification.is_read == False)
        .count()
    )

    ws_users = get_ws_by_user(user_id=session.user_id)
    for ws_user in ws_users:
        try:
            await ws_user.send('notification_read', {
                "id": notification.id,
                "unread_count": unread_count,
            },)
        except Exception as e:
            print(f"[WS] Lỗi gửi socket: {e}")

    return build_response(
        detail=response_json(
            status=True,
            message="Đã đánh dấu thông báo là đã đọc.",
            data={},
        )
    )


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    count = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.user_id == session.user.id,
            Notification.is_read == False
        )
        .scalar()
    )

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy số lượng thông báo chưa đọc thành công!",
            data={
                "unread_count": count,
                "has_unread": count > 0,
            }
        )
    )