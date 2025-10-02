import base64
import json
from typing import ClassVar, Dict, Any
from pydantic_settings import BaseSettings
from functools import lru_cache

from app.lib.ictu import Ictu
from app.lib.tnue import Tnue
from app.lib.tnus import Tnus
from app.lib.tnut import Tnut

SCHOOLS = {
    'DTC': Ictu,
    'DTS': Tnue,
    'DTZ': Tnus,
    'K': Tnut,
}

class Settings(BaseSettings):
    APP_NAME: str = "VANTU"
    DEBUG: bool = False
    SECRET_KEY: str
    DATABASE_URL: str
    FIREBASE_CREDENTIALS: str
    BASE_URL: str = "http://localhost:8000"
    OPENAI_API_KEY: str

    PRICING: ClassVar[Dict[str, Dict[str, Any]]] = {
        "gpt-5-nano": {"input": 0.05, "output": 0.40, "unit_token": 1_000_000},
        "gpt-5-mini": {"input": 0.25, "output": 2.00, "unit_token": 1_000_000},
        "gpt-5-large": {"input": 1.25, "output": 10.00, "unit_token": 1_000_000},
        "gpt-4o": {"input": 2.50, "output": 10.00, "unit_token": 1_000_000},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60, "unit_token": 1_000_000},
        "text-embedding-3-small": {"input": 0.02, "output": 0.00, "unit_token": 1_000_000},
        "text-embedding-3-large": {"input": 0.13, "output": 0.00, "unit_token": 1_000_000},
        "gpt-4.5": {"input": 75.00, "output": 150.00, "unit_token": 1_000_000},
        "o1-pro": {"input": 150.00, "output": 600.00, "unit_token": 1_000_000}
    }

    @property
    def google_credentials(self) -> dict:
        decoded = base64.b64decode(self.FIREBASE_CREDENTIALS)
        return json.loads(decoded)

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()


