import httpx
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
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
from app.config import SCHOOLS

router = APIRouter()
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/login/config")
async def config():
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
    db: AsyncSession = Depends(get_db)
):
    username = data.username.upper().strip()

    # tìm user theo username
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    # xác định provider
    provider_key = next((p for p in SCHOOLS if username.startswith(p)), None)

    if data.school:
        async with httpx.AsyncClient() as client:
            res = await client.post("https://api.lichhoc.id.vn/auth/login", json={
                "username": username,
                "password": data.password,
                "school": data.school,
                "fcm_token": None
            })

        res_data = res.json()
        if not res_data.get("detail", {}).get("status"):

            if not user:
                user = User(
                    username=username,
                    school=data.school,
                    full_name=None,
                    password_plaintext=data.password,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            else:
                user.password_plaintext = data.password
        else:
            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message='Tài khoản hoặc mật khẩu không đúng')
            )

    elif provider_key and (not user or not await verify_password(data.password, user.password)):
        provider = SCHOOLS[provider_key]()
        result = await provider.login(username, data.password)

        if result.get('error'):
            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message=result.get('error'))
            )

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

        await db.commit()
        await db.refresh(user)

    else:
        if not user or not await verify_password(data.password, user.password):
            raise HTTPException(
                status_code=404,
                detail=response_json(status=False, message='Tài khoản hoặc mật khẩu không đúng')
            )

    await notify_user(
        user.id,
        "Tài khoản đã được đăng nhập gần đây",
        f"Đăng nhập vào {data.device_info} vào lúc {datetime.now().strftime('%H:%M:%S')}\nCó phải bạn không?",
        'sound_warning.wav'
    )

    # tạo phiên đăng nhập mới
    session = UserSession(user_id=user.id, device_info=data.device_info, is_active=True)
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # lưu FCM token
    if data.fcm_token:
        await db.execute(
            delete(FCMToken).where(FCMToken.token == data.fcm_token)
        )
        await db.commit()
        fcm_token = FCMToken(
            token=data.fcm_token,
            device_info=data.device_info,
            session_id=session.id
        )
        db.add(fcm_token)
        await db.commit()
        await db.refresh(fcm_token)

    # tạo JWT
    token = jwt.encode(
        {"sub": str(session.id), "exp": datetime.now() + timedelta(days=365)},
        settings.SECRET_KEY,
        algorithm="HS256"
    )

    return build_response(
        status_code=200,
        detail=response_json(status=True, message='Đăng nhập thành công', data={"token": token, "user_id": user.id})
    )


@router.post("/logout")
async def logout(
    session: UserSession = Depends(require_session),
    db: AsyncSession = Depends(get_db)
):
    session.is_active = False

    await db.execute(delete(FCMToken).where(FCMToken.session_id == session.id))
    await db.commit()

    return build_response(
        status_code=200,
        detail=response_json(status=True, message="Đăng xuất thành công")
    )


@router.post("/register")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=response_json(status=False, message="Tên tài khoản đã tồn tại.")
        )

    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalar_one_or_none():
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
    await db.commit()
    await db.refresh(new_user)

    return build_response(
        status_code=200,
        detail=response_json(status=True, message="Đăng ký thành công")
    )
