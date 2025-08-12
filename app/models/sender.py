from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class SenderStatus(str, enum.Enum):
    active = "active"
    suspended = "suspended"

class Sender(Base):
    __tablename__ = "senders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)

    # Thông tin tối thiểu để shipper liên hệ & lấy hàng
    full_name = Column(String(120), nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    default_address = Column(String(255), nullable=True)
    status = Column(Enum(SenderStatus), default=SenderStatus.active, nullable=False)

    create_at = Column(DateTime, server_default=func.now())
    update_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User")

    def __repr__(self):
        return f"<Sender(id={self.id}, name={self.name}, phone={self.phone}, status={self.status})>"
