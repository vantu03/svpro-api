from pydantic import BaseModel, Field
class FeedbackCreateRequest(BaseModel):
    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Tiêu đề góp ý (ví dụ: Ứng dụng bị lỗi khi mở quiz)"
    )
    content: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Nội dung góp ý chi tiết hoặc mô tả lỗi"
    )
