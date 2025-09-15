from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    views = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="posts")
    post_attachments = relationship("PostAttachment", back_populates="post", cascade="all, delete-orphan")
    post_comments = relationship("PostComment", back_populates="post", cascade="all, delete-orphan")