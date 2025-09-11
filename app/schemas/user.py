
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=4, max_length=20)
    password: str = Field(..., min_length=2)
    fcm_token: Optional[str] = None
    device_info: Optional[str] = 'app mobile'
    school: Optional[str] = None

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=5, max_length=20)
    password: str = Field(..., min_length=2)
    full_name: Optional[str] = Field(None, min_length=4, max_length=50)
    email: Optional[EmailStr] = None


class FcmTokenRequest(BaseModel):
    fcm_token: str
    platform: Optional[str] = None