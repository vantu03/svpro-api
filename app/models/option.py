import enum
from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean, DateTime, func, JSON, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from app.database import Base

class Option(Base):
    __tablename__ = "question_options"

    id = Column(Integer, nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))

    text = Column(Text, nullable=False)
    meta_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    question = relationship("Question", back_populates="options")

    __table_args__ = (
        PrimaryKeyConstraint("id", "question_id"),
    )
