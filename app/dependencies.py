from app.database import SessionLocal
from typing import Generator, Any
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models.user_session import UserSession
from app.models.user import User
from app.socket.ws_store import connected_sessions
from app.utils import response_json

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

settings = get_settings()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(token: str, db: Session):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        session_id: str = payload.get("sub")
        if session_id:
            user_session = db.query(UserSession).filter(
                UserSession.id == session_id,
                UserSession.is_active == True
            ).first()
            if user_session:
                return user_session
            else:
                ws_session = connected_sessions.get(session_id)
                if ws_session:
                    ws_session.send('auth_failed', {})
                raise HTTPException(
                    status_code=401,
                    detail=response_json(status=False, message="Phiên đăng nhập đã hết hạn.")
                )
    except JWTError:
        pass
    raise HTTPException(
        status_code=401,
        detail=response_json(status=False, message="Token không hợp lệ hoặc hết hạn.")
    )

def require_session(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> type[UserSession]:
    return verify_token(token, db)

def require_user(session: UserSession = Depends(require_session)) -> type[User]:
    return session.user
