from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.models.order import Order
from app.dependencies import get_db, require_session
from app.models.user_session import UserSession
from app.schemas.order import OrderCreateRequest, OrderListRequest
from app.services.notification_service import notify_user
from app.utils import response_json, build_response, to_dict, normalize_name, normalize_phone

router = APIRouter()

@router.get("/")
def list_orders(
    params: OrderListRequest = Depends(),
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    if not session.user.sender:
        raise HTTPException(status_code=400, detail=response_json(False, "Bạn chưa có hồ sơ người gửi. Vui lòng đăng ký trước."))

    q = (
        db.query(Order)
        .options(joinedload(Order.shipper))
        .filter(Order.sender_id == session.user.sender.id)
        .order_by(Order.create_at.desc())
        .offset(params.offset)
        .limit(params.limit)
    )
    items = q.all()

    result = []
    for order in items:
        data = to_dict(order)
        if order.shipper:
            data["shipper"] = {
                "id": order.shipper.id,
                "full_name": order.shipper.full_name,
                "phone_number": order.shipper.phone_number,
                "avatar_url": order.shipper.avatar_url,
            }
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

@router.post("/create")
async def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    if not session.user.sender:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn chưa có hồ sơ người gửi. Vui lòng đăng ký trước.")
        )

    # Tạo đơn hàng mới
    order = Order(
        sender_id=session.user.sender.id,
        pickup_address=payload.pickup_address or session.user.sender.default_address,
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
        raise HTTPException(status_code=500, detail=response_json(False, "Lỗi tạo đơn hàng."))

    await notify_user(
        db,
        session.user_id,
        "Tạo đơn hàng thành công",
        f"Đơn #{order.id} đã được tạo, đang tìm shipper.",
        "sound_up1.wav",
    )

    return build_response(
        detail=response_json(True, "Tạo đơn hàng thành công.", data={"order": to_dict(order)})
    )
