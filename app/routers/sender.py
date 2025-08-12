from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.dependencies import get_db, require_session
from app.models.sender import Sender, SenderStatus
from app.models.user_session import UserSession
from app.schemas.sender import SenderRegisterRequest
from app.services.notification_service import notify_user
from app.utils import response_json, build_response, to_dict, normalize_name, normalize_phone

router = APIRouter()

@router.get("/info")
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
    return build_response(detail=response_json(True, data={"sender": to_dict(sender) if sender else None}))


@router.post("/register")
async def register_sender(
    payload: SenderRegisterRequest,
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    # Đã có sender active?
    existing_sender = db.query(Sender).filter(
        Sender.user_id == session.user_id,
        Sender.status == SenderStatus.active
    ).first()
    if existing_sender:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn đã có hồ sơ người gửi đang hoạt động.")
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
