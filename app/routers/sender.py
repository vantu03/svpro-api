from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_db, require_session, require_sender
from app.models.order import Order, OrderStatus
from app.models.sender import Sender, SenderStatus
from app.models.user_session import UserSession
from app.schemas.order import OrderCreateRequest, OrderListRequest
from app.schemas.sender import SenderRegisterRequest
from app.services.notification_service import notify_user
from app.socket.ws_store import connected_sessions, get_ws_by_user
from app.utils import response_json, build_response, to_dict, normalize_name, normalize_phone

router = APIRouter()


@router.get("/")
async def get_sender_info(
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    result = await db.execute(
        select(Sender)
        .where(Sender.user_id == session.user_id, Sender.status == SenderStatus.active)
        .order_by(Sender.created_at.desc())
    )
    sender = result.scalar_one_or_none()
    return build_response(
        detail=response_json(True, message="", data=to_dict(sender) if sender else None)
    )


@router.post("/register")
async def register_sender(
    payload: SenderRegisterRequest,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    if session.user.sender:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn đã có hồ sơ người gửi."),
        )

    sender = Sender(
        user_id=session.user_id,
        full_name=normalize_name(payload.full_name),
        phone_number=normalize_phone(payload.phone_number),
        default_address=payload.default_address,
    )

    try:
        db.add(sender)
        await db.commit()
        await db.refresh(sender)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400, detail=response_json(False, "Số điện thoại đã được sử dụng.")
        )
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500, detail=response_json(False, "Không thể tạo hồ sơ người gửi.")
        )

    await notify_user(
        session.user_id,
        "Chào mừng bạn tham gia gửi đơn",
        "Hồ sơ người gửi đã được tạo thành công. Bạn có thể tạo đơn ngay.",
        "sound_success.wav",
    )

    return build_response(
        detail=response_json(True, "Đăng ký người gửi thành công.", data={"sender": to_dict(sender)})
    )


@router.get("/orders")
async def list_orders(
    payload: OrderListRequest = Depends(),
    db: AsyncSession = Depends(get_db),
    sender: Sender = Depends(require_sender),
):
    stmt = (
        select(Order)
        .options(joinedload(Order.shipper))
        .where(Order.sender_id == sender.id)
        .order_by(Order.created_at.desc())
        .offset(payload.offset)
        .limit(payload.limit)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    result_data = []
    for order in items:
        data = to_dict(order)
        data["shipper"] = to_dict(order.shipper) if order.shipper else None
        result_data.append(data)

    return build_response(
        detail=response_json(True, "Lấy danh sách đơn thành công!", result_data)
    )


@router.post("/order/create")
async def create_order(
    payload: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    sender: Sender = Depends(require_sender),
):
    order = Order(
        sender_id=sender.id,
        sender_name=sender.full_name,
        sender_phone=sender.phone_number,
        pickup_address=payload.pickup_address or sender.default_address,
        pickup_lat=payload.pickup_lat,
        pickup_lng=payload.pickup_lng,
        note=payload.note,
        receiver_name=normalize_name(payload.receiver_name),
        receiver_phone=normalize_phone(payload.receiver_phone),
        receiver_address=payload.receiver_address,
        receiver_lat=payload.receiver_lat,
        receiver_lng=payload.receiver_lng,
        item_value=payload.item_value,
        shipping_fee=payload.shipping_fee,
    )

    try:
        db.add(order)
        await db.commit()
        await db.refresh(order)
    except Exception as e:
        await db.rollback()
        print(e)
        raise HTTPException(
            status_code=500, detail=response_json(False, "Lỗi tạo đơn hàng.")
        )

    ws_users = get_ws_by_user(user_id=sender.user_id)
    for ws_user in ws_users:
        try:
            await ws_user.send("order_inserted", to_dict(order))
        except Exception as e:
            print(f"[WS] Lỗi gửi socket: {e}")

    await notify_user(
        sender.user_id,
        "Tạo đơn hàng thành công",
        f"Đơn #{order.id} đã được tạo, đang tìm shipper.",
        "sound_up1.wav",
    )

    return build_response(
        detail=response_json(True, "Tạo đơn hàng thành công.", data={"order": to_dict(order)})
    )


@router.post("/order/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    sender: Sender = Depends(require_sender),
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.sender_id == sender.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=404, detail=response_json(False, "Không tìm thấy đơn hàng.")
        )

    if order.status not in [OrderStatus.pending, OrderStatus.accepted_pending]:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Không thể hủy đơn ở trạng thái hiện tại."),
        )

    order.status = OrderStatus.cancelled
    await db.commit()
    await db.refresh(order)

    ws_users = get_ws_by_user(user_id=sender.user_id)
    for ws_user in ws_users:
        try:
            await ws_user.send(
                "order_status_changed", {"order_id": order_id, "status": order.status.value}
            )
        except Exception as e:
            print(f"[WS] Lỗi gửi socket: {e}")

    for ws in connected_sessions.values():
        try:
            if ws.subscribed_order_pending:
                await ws.send("order_removed", {"order_id": order_id})
        except Exception as e:
            print(f"[WS] Lỗi gửi tới session {ws.session_id}: {e}")

    if order.shipper_id:
        await notify_user(
            order.shipper.user_id,
            "Đơn hàng đã bị hủy",
            f"Người gửi {order.sender.full_name} đã hủy đơn #{order.id}.",
            "sound_warning.wav",
        )

    return build_response(
        detail=response_json(True, "Hủy đơn thành công", data=to_dict(order))
    )
