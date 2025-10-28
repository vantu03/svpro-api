from pydantic import BaseModel, Field

class ShipperRegisterRequest(BaseModel):
    full_name: str = Field(
        ...,
        min_length=5,
        max_length=50,
        description="Họ và tên"
    )
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=12,
        description="Số điện thoại"
    )
    address: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Địa chỉ liên hệ"
    )
