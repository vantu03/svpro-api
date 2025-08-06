from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class UserSession(Base):
    
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(ForeignKey("users.id"), nullable=False)
    device_info = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    expired_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="sessions")
    fcm_token = relationship("FCMToken", back_populates="session", uselist=False, cascade="all, delete-orphan")
