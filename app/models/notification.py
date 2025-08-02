from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class NotificationTarget(str, enum.Enum):
    user = "user"
    shipper = "shipper"
    merchant = "merchant"
    admin = "admin"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target = Column(Enum(NotificationTarget), default=NotificationTarget.user)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="notifications")
