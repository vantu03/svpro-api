import enum
from sqlalchemy import Column, Integer, Text, JSON, Enum, DateTime, func, String
from sqlalchemy.orm import relationship
from app.database import Base

class QuestionType(str, enum.Enum):
    radio = "radio"
    checkbox = "checkbox"
    text = "text"
    number = "number"
    essay = "essay"

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    type = Column(Enum(QuestionType), default=QuestionType.radio)
    feedback = Column(String(2000), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    correct_answers = Column(JSON, nullable=True)
    options = relationship(
        "Option",
        back_populates="question",
        cascade="all, delete-orphan"
    )

    exercise_questions = relationship(
        "ExerciseQuestion",
        back_populates="question",
        cascade="all, delete-orphan",
        overlaps="exercises"
    )

    exercises = relationship(
        "Exercise",
        secondary="exercise_questions",
        back_populates="questions",
        overlaps="exercise_questions"
    )
