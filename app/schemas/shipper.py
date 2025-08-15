from pydantic import BaseModel, Field
from datetime import date
from app.models.shipper_application import VehicleType

class ShipperRegisterRequest(BaseModel):
    full_name: str = Field(
        ...,
        min_length=5,
        max_length=50,
        description="Họ và tên"
    )
    phone_number: str = Field(
        ...,
        min_length=9,
        max_length=20,
        description="Số điện thoại"
    )
    identity_number: str = Field(
        ...,
        min_length=9,
        max_length=20,
        description="Số CMND/CCCD"
    )
    identity_image_front: str = Field(
        ...,
        description="Ảnh mặt trước CMND/CCCD"
    )
    identity_image_back: str = Field(
        ...,
        description="Ảnh mặt sau CMND/CCCD"
    )
    portrait_image: str = Field(
        ...,
        description="Ảnh chân dung"
    )
    address: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Địa chỉ liên hệ"
    )
    date_of_birth: date = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Ngày sinh"
    )
    gender: str = Field(
        ...,
        max_length=20,
        description="Giới tính"
    )
    vehicle_type: VehicleType = Field(
        ...,
        description="Loại phương tiện"
    )
    license_plate: str = Field(
        ...,
        min_length=5,
        max_length=20,
        description="Biển số xe"
    )
    note: str = Field(
        None,
        max_length=500,
        description="Ghi chú thêm"
    )
