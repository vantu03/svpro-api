from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.dependencies import get_db, require_session, require_shipper, require_user
from app.models.user import User
from app.models.order import Order, OrderStatus
from app.models.shipper_application import ShipperApplication, ApplicationStatus
from app.models.shipper import Shipper
from app.models.user_session import UserSession
from app.schemas.order import OrderListRequest
from app.schemas.shipper import ShipperRegisterRequest
from app.services.notification_service import notify_user
from app.socket.ws_store import connected_sessions
from app.utils import response_json, build_response, to_dict, normalize_phone, normalize_name

router = APIRouter()


@router.get("/")
async def get_shipper(
    db: AsyncSession = Depends(get_db),
    shipper: Shipper = Depends(require_shipper),
):
    return build_response(
        detail=response_json(
            True,
            data=to_dict(shipper) if shipper else None,
        )
    )


@router.get("/info")
async def get_shipper_info(
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    result = await db.execute(
        select(Shipper)
        .where(Shipper.user_id == session.user_id, Shipper.is_active == True)
        .order_by(Shipper.created_at.desc())
    )
    shipper = result.scalar_one_or_none()

    result = await db.execute(
        select(ShipperApplication)
        .where(ShipperApplication.user_id == session.user_id)
        .order_by(ShipperApplication.created_at.desc())
    )
    application = result.scalar_one_or_none()

    return build_response(
        detail=response_json(
            True,
            data={
                "shipper": to_dict(shipper) if shipper else None,
                "application": to_dict(application) if application else None,
            },
        )
    )

@router.post("/register")
async def register_shipper(
    payload: ShipperRegisterRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    # Tự kiểm tra xem user đã có shipper chưa
    result = await db.execute(
        select(Shipper)
        .where(Shipper.user_id == user.id, Shipper.is_active == True)
        .order_by(Shipper.created_at.desc())
    )
    shipper = result.scalar_one_or_none()

    if shipper and shipper.is_active:
        raise HTTPException(
            status_code=400, detail=response_json(False, "Bạn đã là Shipper.")
        )

    # Kiểm tra đơn ứng tuyển đang chờ
    result = await db.execute(
        select(ShipperApplication).where(
            ShipperApplication.user_id == user.id,
            ShipperApplication.status == ApplicationStatus.pending,
        )
    )
    existing_application = result.scalar_one_or_none()

    if existing_application:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn đã gửi đơn đăng ký và đang chờ duyệt"),
        )

    # ✅ Tạo hồ sơ mới
    application = ShipperApplication(
        user_id=user.id,
        full_name=normalize_name(payload.full_name),
        phone_number=normalize_phone(payload.phone_number),
        address=payload.address,
        status=ApplicationStatus.pending,
    )

    db.add(application)
    await db.commit()
    await db.refresh(application)

    await notify_user(
        user.id,
        "Đã gửi hồ sơ Shipper",
        "Bạn đã gửi hồ sơ đăng ký làm Shipper, hãy chờ để chúng tôi xét duyệt.",
        "sound_warning.wav",
    )

    return build_response(
        detail=response_json(status=True, message="Gửi hồ sơ thành công")
    )


@router.get("/orders")
async def list_orders(
    payload: OrderListRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    shipper: Shipper = Depends(require_shipper),
):
    now = datetime.now()
    min_time = now - timedelta(hours=2)
    max_time = now - timedelta(seconds=30)

    stmt = (
        select(Order)
        .where(
            Order.status == OrderStatus.pending,
            Order.created_at >= min_time,
            Order.created_at <= max_time,
        )
        .order_by(Order.created_at.desc())
        .offset(payload.offset)
        .limit(payload.limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy danh sách đơn thành công!",
            data=[to_dict(order) for order in items],
        )
    )


@router.post("/orders/{order_id}/accept")
async def accept_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    shipper: Shipper = Depends(require_shipper),
):
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404, detail=response_json(False, "Không tìm thấy đơn hàng")
        )

    if order.status != OrderStatus.pending:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Đơn hàng này không còn ở trạng thái chờ nhận"),
        )

    order.shipper_id = shipper.id
    order.status = OrderStatus.picking_up
    await db.commit()
    await db.refresh(order)

    await notify_user(
        db,
        order.sender.user_id,
        "Đơn hàng đã được nhận",
        f"Shipper {shipper.full_name} đã nhận đơn #{order.id} của bạn.",
        "sound_up1.wav",
    )

    for ws in connected_sessions.values():
        try:
            if ws.subscribed_order_pending:
                await ws.send("order_removed", {"order_id": order_id})
        except Exception as e:
            print(f"[WS] Lỗi gửi tới session {ws.session_id}: {e}")

    return build_response(
        detail=response_json(True, "Nhận đơn thành công", data={"order_id": order.id})
    )
