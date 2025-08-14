from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
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
def get_sender_info(
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    sender = (
        db.query(Sender)
        .filter(Sender.user_id == session.user_id, Sender.status == SenderStatus.active)
        .order_by(Sender.create_at.desc())  # fix: created_at
        .first()
    )
    return build_response(
        detail=response_json(True, message="", data=to_dict(sender) if sender else None))


@router.post("/register")
async def register_sender(
    payload: SenderRegisterRequest,
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    # Đã có sender
    if session.user.sender:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn đã có hồ sơ người gửi.")
        )

    # Tạo người gửi mới
    sender = Sender(
        user_id=session.user_id,
        full_name=normalize_name(payload.full_name),
        phone_number=normalize_phone(payload.phone_number),
        default_address=payload.default_address,
    )

    try:
        db.add(sender)
        db.commit()
        db.refresh(sender)
    except IntegrityError:
        db.rollback()
        # ví dụ: trùng phone (nếu bạn đặt unique)
        raise HTTPException(status_code=400, detail=response_json(False, "Số điện thoại đã được sử dụng."))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=response_json(False, "Không thể tạo hồ sơ người gửi."))

    # Thông báo đúng ngữ cảnh "người gửi"
    await notify_user(
        db,
        session.user_id,
        "Chào mừng bạn tham gia gửi đơn",
        "Hồ sơ người gửi đã được tạo thành công. Bạn có thể tạo đơn ngay.",
        "sound_success.wav",
    )

    return build_response(detail=response_json(True, "Đăng ký người gửi thành công.", data={"sender": to_dict(sender)}))


@router.get("/orders")
def list_orders(
    params: OrderListRequest = Depends(),
    db: Session = Depends(get_db),
    sender: Sender = Depends(require_sender),
):
    q = (
        db.query(Order)
        .options(joinedload(Order.shipper))
        .filter(Order.sender_id == sender.id)
        .order_by(Order.create_at.desc())
        .offset(params.offset)
        .limit(params.limit)
    )
    items = q.all()

    result = []
    for order in items:
        data = to_dict(order)
        if order.shipper:
            data["shipper"] = to_dict(order.shipper)
        else:
            data["shipper"] = None
        result.append(data)

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy danh sách đơn thành công!",
            data=result
        )
    )

@router.post("/order/create")
async def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    sender: Sender = Depends(require_sender),
):

    # Tạo đơn hàng mới
    order = Order(
        sender_id=sender.id,
        pickup_address=payload.pickup_address or sender.default_address,
        note=payload.note,
        receiver_name=normalize_name(payload.receiver_name),
        receiver_phone=normalize_phone(payload.receiver_phone),
        receiver_address=payload.receiver_address,
        item_value=payload.item_value,
        shipping_fee=payload.shipping_fee,
    )

    try:
        db.add(order)
        db.commit()
        db.refresh(order)
    except Exception as e:
        db.rollback()
        print (str(normalize_phone(payload.receiver_phone)) +" ---- "+ str(payload.receiver_phone))
        print(e)
        raise HTTPException(status_code=500, detail=response_json(False, "Lỗi tạo đơn hàng."))

    await notify_user(
        db,
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
    db: Session = Depends(get_db),
    sender: Sender = Depends(require_sender),
):
    # Lấy đơn
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.sender_id == sender.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail=response_json(False, "Không tìm thấy đơn hàng."))

    # Kiểm tra trạng thái cho phép hủy
    if order.status not in [OrderStatus.pending, OrderStatus.accepted_pending]:
        raise HTTPException(status_code=400, detail=response_json(False, "Không thể hủy đơn ở trạng thái hiện tại."))

    # Cập nhật trạng thái
    order.status = OrderStatus.cancelled
    db.commit()
    db.refresh(order)


    ws_users = get_ws_by_user(user_id=sender.user_id)
    for ws_user in ws_users:
        try:
            await ws_user.send("order_status_changed", {"order_id": order_id, "status": order.status.value})
        except Exception as e:
            print(f"[WS] Lỗi gửi socket: {e}")

    for ws in connected_sessions.values():
        try:
            if ws.subscribed_order_pending:
                await ws.send("order_removed", {"order_id": order_id})
        except Exception as e:
            print(f"[WS] Lỗi gửi tới session {ws.session_id}: {e}")

    # Nếu có shipper, thông báo cho shipper
    if order.shipper_id:
        await notify_user(
            db,
            order.shipper.user_id,
            "Đơn hàng đã bị hủy",
            f"Người gửi {order.sender.full_name} đã hủy đơn #{order.id}.",
            "sound_warning.wav"
        )

    return build_response(
        detail=response_json(True, "Hủy đơn thành công", data=to_dict(order))
    )