
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class LoginRequest(BaseModel):
    username: str
    password: str
    fcm_token: Optional[str] = None
    device_info: Optional[str] = None

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=20)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None