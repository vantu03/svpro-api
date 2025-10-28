from sqlalchemy import Column, Integer, ForeignKey, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class ExerciseAttempt(Base):
    __tablename__ = "exercise_attempts"

    id = Column(Integer, primary_key=True, index=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    is_finished = Column(Boolean, default=False)

    exercise = relationship("Exercise", back_populates="attempts")
