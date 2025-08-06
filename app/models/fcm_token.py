from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class FCMToken(Base):

    __tablename__ = "fcm_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(512), nullable=False, unique=True)
    device_info = Column(String(255), nullable=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("UserSession", back_populates="fcm_token")
