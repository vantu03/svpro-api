from pydantic import BaseModel, Field
from typing import Optional

class OrderCreateRequest(BaseModel):
    pickup_address: Optional[str] = Field(None, max_length=255, description="Địa chỉ lấy hàng (nếu bỏ trống sẽ dùng địa chỉ mặc định của người gửi)")
    item_value: int = Field(..., ge=0, description="Giá trị hàng hóa (VNĐ)")
    shipping_fee: Optional[int] = Field(None, ge=0, description="Phí ship (VNĐ), có thể để trống để shipper đề xuất")

    receiver_name: str = Field(..., max_length=120, description="Tên người nhận")
    receiver_phone: str = Field(..., max_length=20, description="Số điện thoại người nhận")
    receiver_address: str = Field(..., max_length=255, description="Địa chỉ người nhận")

    note: Optional[str] = Field(None, max_length=500, description="Ghi chú cho shipper hoặc người nhận")

class OrderListRequest(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)