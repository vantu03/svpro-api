from pydantic import BaseModel

# Base
class ViewBase(BaseModel):
    post_id: int
    user_id: int

# Create (add view)
class ViewCreate(ViewBase):
    pass