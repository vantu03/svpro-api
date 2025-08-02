from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class FileType(str, enum.Enum):
    portrait = "portrait"
    cmnd_front = "cmnd_front"
    cmnd_back = "cmnd_back"
    license = "license"
    other = "other"

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String(2000), nullable=False)
    file_path = Column(String(2000), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(Enum(FileType), default=FileType.other)
    mime_type = Column(String(50), nullable=True)
    size = Column(Integer, nullable=True)
    uploaded_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="uploads")
