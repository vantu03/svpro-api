
from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), unique=True, nullable=False, index=True)
    password = Column(String(120), nullable=False)
    password_plaintext = Column(String(120), nullable=True)
    school = Column(String(20), nullable=True)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(2000), nullable=True)
    email = Column(String(120), unique=True, nullable=True)
    is_staff = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), server_default=func.now())
    updated_at = Column(DateTime, default=func.now(), server_default=func.now(), onupdate=func.now())

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    uploads = relationship("Upload", back_populates="user", cascade="all, delete-orphan")
    shipper_applications = relationship("ShipperApplication", back_populates="user", cascade="all, delete-orphan")
    shipper = relationship("Shipper", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    sender = relationship("Sender", back_populates="user", uselist=False, cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    post_comments = relationship("PostComment", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")


    def __repr__(self):
        return f"<User {self.id} {self.username}>"

