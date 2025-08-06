
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from app.dependencies import get_db, require_session
from app.models.user import User
from app.models.user_session import UserSession
from app.models.fcm_token import FCMToken
from app.schemas.user import LoginRequest, RegisterRequest
from app.services.notification_service import notify_user
from app.utils import response_json, md5_hash, verify_password, build_response
from app.config import get_settings
from app.lib.ictu import Ictu

router = APIRouter()
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
@router.post("/login")
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    username = data.username.lower()
    pwd_md5 = md5_hash(data.password)
    user = db.query(User).filter(User.username == username).first()

    # Nếu là tài khoản sinh viên và chưa có user trong hệ thống → đăng nhập từ ICTU
    if username.startswith('dtc') and not user:
        browser = Ictu()
        result = await browser.login(username, pwd_md5)
        if result:
            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message=result)
            )
        user = User(username=username, password=pwd_md5)
        db.add(user)
        db.commit()
        db.refresh(user)

    else:
        if not user or not verify_password(data.password, user.password):
            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message='Tài khoản hoặc mật khẩu không đúng')
            )

    await notify_user(db, user.id, "Tài khoản đã được đăng nhập gần đây", f"Đăng nhập vào {data.device_info} vào lúc {datetime.now().strftime('%H:%M:%S')}\nCó phải bạn không?")

    # Tạo phiên đăng nhập mới
    session = UserSession(user_id=user.id, device_info=data.device_info)
    db.add(session)
    db.commit()
    db.refresh(session)

    # Lưu FCM nếu có
    if data.fcm_token:
        db.query(FCMToken).filter(FCMToken.token == data.fcm_token).delete()

        fcm_token = FCMToken(
            token=data.fcm_token,
            device_info=data.device_info,
            session_id=session.id
        )
        db.add(fcm_token)
        db.commit()
        db.refresh(fcm_token)

    # Tạo JWT token
    token = jwt.encode(
        {"sub": str(session.id), "exp": datetime.now() + timedelta(days=365)},
        settings.SECRET_KEY,
        algorithm="HS256"
    )

    return build_response(
        status_code=200,
        detail=response_json(status=True,message='Đăng nhập thành công',data={"token": token})
    )

@router.post("/logout")
def logout(
    session: UserSession = Depends(require_session),
    db: Session = Depends(get_db)
):
    session.is_active = False
    db.query(FCMToken).filter(FCMToken.session_id == session.id).delete()

    db.commit()

    return build_response(
        status_code=200,
        detail=response_json(status=True, message="Đăng xuất thành công")
    )


@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    # Check username đã tồn tại chưa
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(
            status_code=400,
            detail=response_json(status=False, message="Tên tài khoản đã tồn tại.")
        )

    # Check email đã tồn tại chưa (nếu có)
    if data.email and db.query(User).filter(User.email == data.email).first():
        raise HTTPException(
            status_code=400,
            detail=response_json(status=False, message="Email đã được sử dụng.")
        )

    hashed_password = pwd_context.hash(data.password)

    new_user = User(
        username=data.username,
        password=hashed_password,
        full_name=data.full_name,
        email=str(data.email) if data.email else None
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return build_response(
        status_code=200,
        detail=response_json(status=True, message="Đăng ký thành công")
    )
