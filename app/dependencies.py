from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.config import get_settings
from app.database import get_db, async_session
from app.models.sender import SenderStatus, Sender
from app.models.shipper import Shipper
from app.models.user_session import UserSession
from app.models.user import User
from app.socket.ws_store import connected_sessions
from app.utils import response_json

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
settings = get_settings()


async def verify_token(token: str):
    try:

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        session_id: str = payload.get("sub")
        if session_id:
            async with async_session() as db:
                result = await db.execute(
                    select(UserSession).where(
                        UserSession.id == session_id,
                        UserSession.is_active == True
                    )
                )
                user_session = result.scalar_one_or_none()
                if user_session:
                    return user_session
                else:
                    ws_session = connected_sessions.get(session_id)
                    if ws_session:
                        ws_session.send('logout', {})
                        ws_session.send('auth_failed', {})
                    raise HTTPException(
                        status_code=401,
                        detail=response_json(False, "Phiên đăng nhập đã hết hạn.")
                    )
    except JWTError as e:
        print(e)
        pass
    raise HTTPException(
        status_code=401,
        detail=response_json(status=False, message="Token không hợp lệ hoặc hết hạn.")
    )


async def require_session(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserSession:
    return await verify_token(token)


async def require_user(session: UserSession = Depends(require_session), db: AsyncSession = Depends(get_db)) -> User:
    result = await db.execute(select(User).where(User.id == session.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def require_shipper(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> Shipper:
    result = await db.execute(
        select(Shipper)
        .where(Shipper.user_id == user.id, Shipper.is_active == True)
        .order_by(Shipper.created_at.desc())
    )
    shipper = result.scalar_one_or_none()

    if not shipper:
        raise HTTPException(
            status_code=403,
            detail=response_json(False, "Bạn chưa phải là shipper hoặc tài khoản chưa được duyệt."),
        )

    return shipper

async def require_sender(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
) -> Sender:
    result = await db.execute(
        select(Sender)
        .where(Sender.user_id == user.id, Sender.status == SenderStatus.active)
        .order_by(Sender.created_at.desc())
    )
    sender = result.scalar_one_or_none()

    if not sender:
        raise HTTPException(
            status_code=400,
            detail=response_json(False, "Bạn chưa có hồ sơ người gửi. Vui lòng đăng ký trước."),
        )

    return sender