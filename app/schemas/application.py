from pydantic import BaseModel
from typing import Optional

class CheckUpdateRequest(BaseModel):
    app_version: str
    build_number: str
    os_name: str
    os_version: Optional[str] = None
    device_name: Optional[str] = None
    device_model: Optional[str] = None