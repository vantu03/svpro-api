from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text, func, Date
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class ApplicationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

class VehicleType(str, enum.Enum):
    motorbike = "motorbike"
    car = "car"

class ShipperApplication(Base):
    __tablename__ = "shipper_applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    full_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    identity_number = Column(String(20), nullable=False)

    identity_image_front = Column(String(1000), nullable=True)
    identity_image_back = Column(String(1000), nullable=True)
    portrait_image = Column(String(1000) ,nullable=True)

    address = Column(String(255), nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(10), nullable=True)

    vehicle_type = Column(Enum(VehicleType), nullable=False)
    license_plate = Column(String(20), nullable=False)

    note = Column(Text, nullable=True)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.pending)
    reject_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="shipper_applications")

    def __repr__(self):
        return f"<ShipperApplication(id={self.id}, user_id={self.user_id}, status={self.status})>"
