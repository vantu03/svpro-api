from typing import Literal, Optional
from pydantic import BaseModel, Field

class NotificationListRequest(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)
    status: Optional[Literal["unread", "read"]] = None

class NotificationUpdateRequest(BaseModel):
    id: int
