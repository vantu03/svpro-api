from fastapi import APIRouter, Depends
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.dependencies import get_db, require_user
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationListRequest, NotificationUpdateRequest
from app.socket.ws_store import get_ws_by_user
from app.utils import response_json, build_response, to_dict

router = APIRouter()


@router.get("/")
async def get_notifications(
    data: NotificationListRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    stmt = select(Notification).where(Notification.user_id == user.id)

    # filter theo status
    if data.status == "unread":
        stmt = stmt.where(Notification.is_read == False)
    elif data.status == "read":
        stmt = stmt.where(Notification.is_read == True)

    stmt = stmt.order_by(Notification.created_at.desc()).offset(data.offset).limit(data.limit)

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy danh sách thông báo thành công!",
            data=[to_dict(n) for n in notifications],
        )
    )


@router.post("/read")
async def mark_notification_read(
    payload: NotificationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == payload.id,
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        return build_response(
            detail=response_json(
                status=False,
                message="Không tìm thấy thông báo hoặc không có quyền truy cập.",
            )
        )

    if not notification.is_read:
        notification.is_read = True
        await db.commit()
        await db.refresh(notification)

    # đếm lại số unread
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    unread_count = result.scalar() or 0

    ws_users = get_ws_by_user(user_id=user.id)
    for ws_user in ws_users:
        try:
            await ws_user.send(
                "notification_read",
                {"id": notification.id, "unread_count": unread_count},
            )
        except Exception as e:
            print(f"[WS] Lỗi gửi socket: {e}")

    return build_response(
        detail=response_json(
            status=True,
            message="Đã đánh dấu thông báo là đã đọc.",
            data={},
        )
    )


@router.post("/read/all")
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()

    ws_users = get_ws_by_user(user_id=user.id)
    for ws_user in ws_users:
        try:
            await ws_user.send("notification_read_all", {})
        except Exception as e:
            print(f"[WS] Lỗi gửi socket: {e}")

    return build_response(
        detail=response_json(
            status=True,
            message="Đã đánh dấu tất cả thông báo là đã đọc.",
            data={},
        )
    )


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    result = await db.execute(
        select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    count = result.scalar() or 0

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy số lượng thông báo chưa đọc thành công!",
            data={"unread_count": count, "has_unread": count > 0},
        )
    )
