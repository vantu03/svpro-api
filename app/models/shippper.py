from sqlalchemy import Column, Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Shipper(Base):
    __tablename__ = "shippers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    application_id = Column(Integer, ForeignKey("shipper_applications.id"))
    create_at = Column(DateTime, default=func.now)
    is_active = Column(Boolean, default=True)

    user = relationship("User")
    application = relationship("ShipperApplication")
