from datetime import timedelta, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_session, require_shipper
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
def get_shipper(
    db: Session = Depends(get_db),
    shipper: Shipper = Depends(require_shipper)
):
    return build_response(
        detail=response_json(
            True,
            data= to_dict(shipper) if shipper else None,
        )
    )
@router.get("/info")
def get_shipper_info(
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session)
):

    # Lấy thông tin Shipper (nếu đã được duyệt)
    shipper = (
        db.query(Shipper)
        .filter(Shipper.user_id == session.user_id, Shipper.is_active == True)
        .order_by(Shipper.create_at.desc())
        .first()
    )

    # Lấy thông tin đơn đăng ký gần nhất (nếu có)
    application = (
        db.query(ShipperApplication)
        .filter(ShipperApplication.user_id == session.user_id)
        .order_by(ShipperApplication.created_at.desc())
        .first()
    )

    return build_response(
        detail=response_json(
            True,
            data= {
                "shipper": to_dict(shipper) if shipper else None,
                "application": to_dict(application) if application else None,
            }
        )
    )

@router.post("/register")
async def register_shipper(
    payload: ShipperRegisterRequest,
    db: Session = Depends(get_db),
    session = Depends(require_session)
):
    #1. Check shipper
    if session.user.shipper and session.user.shipper.is_active:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn đã là Shipper.")
        )

    #2. Kiểm tra đơn chờ duyệt
    existing_application = db.query(ShipperApplication).filter(
        ShipperApplication.user_id == session.user.id,
        ShipperApplication.status == ApplicationStatus.pending
    ).first()

    if existing_application:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn đã gửi đơn đăng ký và đang chờ duyệt")
        )

    # Tạo đơn mới
    application = ShipperApplication(
        user_id=session.user.id,
        full_name=normalize_name(payload.full_name),
        phone_number=normalize_phone(payload.phone_number),
        identity_number=payload.identity_number,
        identity_image_front=payload.identity_image_front,
        identity_image_back=payload.identity_image_back,
        portrait_image=payload.portrait_image,
        address=payload.address,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        vehicle_type=payload.vehicle_type,
        license_plate=payload.license_plate,
        note=payload.note,
        status=ApplicationStatus.pending
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    await notify_user(
        db,
        session.user.id,
     "Đã gửi hồ sơ Shipper",
      "Bạn đã gửi hồ sơ đăng ký làm Shipper, hãy chờ để chúng tôi xét duyệt hồ sơ của bạn có đạt yêu cầu không nhé.",
        'sound_warning.wav'
    )

    return build_response(
        detail=response_json(status=True,message= "Gửi hồ sơ thành công")
    )

@router.get("/orders")
def list_orders(
    payload: OrderListRequest = Depends(),
    db: Session = Depends(get_db),
    shipper: Shipper = Depends(require_shipper)
):
    now = datetime.now()
    min_time = now - timedelta(hours=2)
    max_time = now - timedelta(seconds=30)

    q = (
        db.query(Order)
        .filter(
            Order.status == OrderStatus.pending,
            Order.create_at >= min_time,
            Order.create_at <= max_time
        )
        .order_by(Order.create_at.desc())
        .offset(payload.offset)
        .limit(payload.limit)
    )
    items = q.all()

    result = []
    for order in items:
        data = to_dict(order)
        result.append(data)

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy danh sách đơn thành công!",
            data=result
        )
    )

@router.post("/orders/{order_id}/accept")
async def accept_order(
    order_id: int,
    db: Session = Depends(get_db),
    shipper: Shipper = Depends(require_shipper)
):

    # 2. Kiểm tra đơn tồn tại và đang ở trạng thái pending
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=404,
            detail=response_json(False, "Không tìm thấy đơn hàng")
        )

    if order.status != OrderStatus.pending:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Đơn hàng này không còn ở trạng thái chờ nhận")
        )

    # 3. Nhận đơn
    order.shipper_id = shipper.id
    order.status = OrderStatus.picking_up
    db.commit()
    db.refresh(order)

    # 4. Gửi thông báo cho người gửi
    await notify_user(
        db,
        order.sender.user_id,
        "Đơn hàng đã được nhận",
        f"Shipper {shipper.full_name} đã nhận đơn #{order.id} của bạn.",
        "sound_up1.wav"
    )

    for ws in connected_sessions.values():
        try:
            if ws.subscribed_order_pending:
                await ws.send("order_removed", {"order_id": order_id})
        except Exception as e:
            print(f"[WS] Lỗi gửi tới session {ws.session_id}: {e}")

    return build_response(
        detail=response_json(True, "Nhận đơn thành cônng", data={"order_id": order.id})
    )