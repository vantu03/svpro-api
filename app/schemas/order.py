from pydantic import BaseModel, Field
from typing import Optional

class OrderCreateRequest(BaseModel):
    pickup_address: Optional[str] = Field(
        None,
        min_length=5,
        max_length=255,
        description="Địa chỉ lấy hàng (nếu bỏ trống sẽ dùng địa chỉ mặc định của người gửi)"
    )
    pickup_lat: float = Field(..., description="Vĩ độ điểm lấy hàng")
    pickup_lng: float = Field(..., description="Kinh độ điểm lấy hàng")
    item_value: int = Field(
        ...,
        ge=0,
        le=10_000_000,
        description="Giá trị hàng hóa (VNĐ)"
    )
    shipping_fee: Optional[int] = Field(
        None,
        ge=0,
        le=10_000_000,
        description="Phí ship (VNĐ), có thể để trống để shipper đề xuất"
    )

    receiver_name: str = Field(..., min_length=5, max_length=50, description="Tên người nhận")
    receiver_phone: str = Field(..., min_length=10, max_length=12, description="Số điện thoại người nhận")
    receiver_lat: Optional[float] = Field(None, description="Vĩ độ điểm giao (có thể bỏ trống)")
    receiver_lng: Optional[float] = Field(None, description="Kinh độ điểm giao (có thể bỏ trống)")

    receiver_address: str = Field(..., min_length=5, max_length=255, description="Địa chỉ người nhận")

    note: Optional[str] = Field(None, max_length=500, description="Ghi chú cho shipper hoặc người nhận")

class OrderListRequest(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)