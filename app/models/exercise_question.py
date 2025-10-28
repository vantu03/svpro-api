from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ExerciseQuestion(Base):
    __tablename__ = "exercise_questions"

    id = Column(Integer, primary_key=True, index=True)

    exercise_id = Column(
        Integer,
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id = Column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    exercise = relationship(
        "Exercise",
        back_populates="exercise_questions",
        overlaps="exercises,questions"
    )

    question = relationship(
        "Question",
        back_populates="exercise_questions",
        overlaps="exercises,questions"
    )


