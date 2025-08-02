from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class Banner(Base):

    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1000), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
