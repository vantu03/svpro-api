from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    prompt: str
    images: Optional[List[str]] = []
    files: Optional[List[str]] = []