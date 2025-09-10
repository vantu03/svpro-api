import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func, Enum
from app.database import Base

class PlatformEnum(str, enum.Enum):
    android = "android"
    ios = "ios"
    windows = "windows"
    macos = "macos"
    linux = "linux"
    web = "web"

class AppVersion(Base):
    __tablename__ = "app_versions"

    id = Column(Integer, primary_key=True, index=True)
    platform = Column(Enum(PlatformEnum), nullable=False, index=True)
    latest_version = Column(String(50), nullable=False)
    latest_build = Column(String(50), nullable=False)
    force = Column(Boolean, default=False)
    url = Column(String(2000), nullable=False)
    title = Column(String(255), default="Cập nhật ứng dụng")
    content = Column(String(255), default="Ứng dụng đã có bản cập nhật mới.")
    confirm_text = Column(String(255), default="Cập nhật ngay")
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(), onupdate=func.now())
