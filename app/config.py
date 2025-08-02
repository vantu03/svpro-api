import base64
import json

from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "VANTU"
    DEBUG: bool = False
    SECRET_KEY: str
    DATABASE_URL: str
    FIREBASE_CREDENTIALS: str

    @property
    def google_credentials(self) -> dict:
        decoded = base64.b64decode(self.FIREBASE_CREDENTIALS)
        return json.loads(decoded)

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
