from sqlalchemy import Column, Integer, Boolean, DateTime, func, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class Shipper(Base):
    __tablename__ = "shippers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    application_id = Column(Integer, ForeignKey("shipper_applications.id"))

    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    avatar_url = Column(String(1000), nullable=True)

    create_at = Column(DateTime, server_default=func.now())
    is_active = Column(Boolean, default=True)

    user = relationship("User")
    application = relationship("ShipperApplication")
    orders = relationship("Order", back_populates="shipper")
