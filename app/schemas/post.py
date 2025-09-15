from pydantic import BaseModel, Field
from typing import List, Optional

# Create
class PostCreate(BaseModel):
    attachments: Optional[List[int]] = []
    content: Optional[str] = Field(
        None,
        min_length=1,
        max_length=500,
        description="Nội dung bài viết (1-500 ký tự, có thể để trống)"
    )

# Delete
class PostDelete(BaseModel):
    id: int
