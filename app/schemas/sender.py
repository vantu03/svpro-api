
from pydantic import BaseModel, Field

class SenderRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=5, max_length=50, description="Tên đầy đủ")
    phone_number: str = Field(..., min_length=10, max_length=12, description="Số điện thoại")
    default_address: str = Field(..., min_length=5, max_length=255, description="Địa chỉ mặc định")
