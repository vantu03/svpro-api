from pydantic import BaseModel, Field
from typing import List, Optional

# Create
class CommentCreate(BaseModel):
    content: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Nội dung bình luận (1-300 ký tự)"
    )
    attachments: Optional[List[int]] = []

# Delete
class CommentDelete(BaseModel):
    id: int
