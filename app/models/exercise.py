from sqlalchemy import Column, Integer, String, DateTime, func, Text
from sqlalchemy.orm import relationship
from app.database import Base
class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    thumbnail_url = Column(String(2000), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    type_question = Column(Integer, default=1)
    shuffle_question = Column(Integer, default=1)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    exercise_questions = relationship(
        "ExerciseQuestion",
        back_populates="exercise",
        cascade="all, delete-orphan",
        overlaps="questions,exercises"
    )

    questions = relationship(
        "Question",
        secondary="exercise_questions",
        back_populates="exercises",
        overlaps="exercise_questions"
    )

    attempts = relationship("ExerciseAttempt", back_populates="exercise")
