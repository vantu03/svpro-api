from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "VANTU"
    DEBUG: bool = False
    SECRET_KEY: str
    DATABASE_URL: str

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()
