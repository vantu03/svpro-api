
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.dependencies import get_db, require_session
from app.models.shipper_application import ShipperApplication, ApplicationStatus
from app.models.shippper import Shipper
from app.models.user_session import UserSession
from app.schemas.shipper import ShipperRegisterRequest
from app.services.notification_service import notify_user
from app.utils import response_json, build_response, to_dict

router = APIRouter()

@router.get("/info")
def get_shipper_info(
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session)
):
    user_id = session.user.id

    # Lấy thông tin Shipper (nếu đã được duyệt)
    shipper = (
        db.query(Shipper)
        .filter(Shipper.user_id == user_id, Shipper.is_active == True)
        .order_by(Shipper.create_at.desc())
        .first()
    )

    # Lấy thông tin đơn đăng ký gần nhất (nếu có)
    application = (
        db.query(ShipperApplication)
        .filter(ShipperApplication.user_id == user_id)
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

    # ✅ 1. Kiểm tra đã là Shipper hay chưa
    existing_shipper = db.query(Shipper).filter(
        Shipper.user_id == session.user.id,
        Shipper.is_active == True
    ).first()

    if existing_shipper:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn đã là Shipper.")
        )

    # ✅ 2. Kiểm tra đơn chờ duyệt
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
        full_name=payload.full_name,
        phone_number=payload.phone_number,
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

    await notify_user(db, session.user.id, "Đã gửi hồ sơ Shipper", "Bạn đã gửi hồ sơ đăng ký làm Shipper, hãy chờ để chúng tôi xét duyệt hồ sơ của bạn có đạt yêu cầu không nhé.")

    return build_response(
        detail=response_json(status=True,message= "Gửi hồ sơ thành công")
    )