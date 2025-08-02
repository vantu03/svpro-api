from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from app.models.shipper_application import VehicleType

class ShipperRegisterRequest(BaseModel):
    full_name: str
    phone_number: str
    identity_number: str
    identity_image_front: Optional[str]
    identity_image_back: Optional[str]
    portrait_image: Optional[str]
    address: str
    date_of_birth: Optional[date]
    gender: Optional[str]
    vehicle_type: VehicleType
    license_plate: str
    note: Optional[str] = None
