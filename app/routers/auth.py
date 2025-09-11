import httpx
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
from app.utils import response_json, verify_password, build_response
from app.config import get_settings
from app.lib.ictu import Ictu
from app.lib.tnue import Tnue

PROVIDERS = {
    'DTC': Ictu,  # ICTU
    'DTS': Tnue,  # TNUE
}

router = APIRouter()
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/login/config")
def config():
    return build_response(
        status_code=200,
        detail=response_json(
            status=True,
            message='Lấy cấu hình đăng nhập thành công',
            data={
              "login_url": "https://sv.pro.vn/login.html",
              "success_url": "https://api.sv.pro.vn/auth/login/success",
              "method": "webview",
            }
        )
    )

@router.post("/login")
async def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    username = data.username.upper().strip()
    user = db.query(User).filter(User.username == username).first()

    # Xác định provider theo prefix
    provider_key = next((p for p in PROVIDERS if username.startswith(p)), None)

    if data.school:

        async with httpx.AsyncClient() as client:
            res = await client.post("https://api.lichhoc.id.vn/auth/login", json={
                "username": username,
                "password": data.password,
                "school": data.school,
                "fcm_token": None
            })

        data = res.json()
        if not data.get("detail", {}).get("status"):

            if not user:
                user = User(
                    username=username,
                    full_name=None,
                    password_plaintext=data.password,
                )
                db.add(user)

                db.commit()
                db.refresh(user)
            else:
                user.password_plaintext = data.password
        else:

            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message='Tài khoản hoặc mật khẩu không đúng')
            )

    elif provider_key and (not user or not verify_password(data.password, user.password)):
        provider = PROVIDERS[provider_key]()
        result = await provider.login(username, data.password)

        if result.get('error'):
            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message=result.get('error'))
            )

        # Upsert user + lưu MD5 (giữ nguyên convention hiện tại)
        if not user:
            user = User(
                username=username,
                full_name=result.get('full_name'),
                password=result.get('password')
            )
            db.add(user)
        else:
            user.password = result.get('password')
            if not user.full_name and result.get('full_name'):
                user.full_name = result['full_name']

        db.commit()
        db.refresh(user)

    else:
        # Tài khoản không phải mã sinh viên (hoặc đã có user và verify pass OK) → kiểm tra local
        if not user or not verify_password(data.password, user.password):
            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message='Tài khoản hoặc mật khẩu không đúng')
            )

    await notify_user(
        db,
        user.id,
        "Tài khoản đã được đăng nhập gần đây",
       f"Đăng nhập vào {data.device_info} vào lúc {datetime.now().strftime('%H:%M:%S')}\nCó phải bạn không?",
       'sound_warning.wav'
    )

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
