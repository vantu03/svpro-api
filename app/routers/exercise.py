from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import asc, desc
from sqlalchemy.orm import joinedload

from app.dependencies import get_db, require_user
from app.models.exercise import Exercise
from app.models.exercise_attempt import ExerciseAttempt
from app.models.exercise_question import ExerciseQuestion
from app.models.question import Question
from app.utils import response_json, build_response

router = APIRouter()


# ==============================================================
# 📘 LẤY DANH SÁCH BÀI TẬP
# ==============================================================

@router.get("/")
async def get_exercises(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    search: str | None = Query(None, description="Tìm kiếm theo tiêu đề"),
    sort: str | None = Query(None, description="Sắp xếp (az, za, newest, oldest)"),
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user),
):
    stmt = select(Exercise)

    if search:
        stmt = stmt.where(Exercise.title.ilike(f"%{search}%"))

    if sort == "az":
        stmt = stmt.order_by(asc(Exercise.title))
    elif sort == "za":
        stmt = stmt.order_by(desc(Exercise.title))
    elif sort == "newest":
        stmt = stmt.order_by(desc(Exercise.id))
    elif sort == "oldest":
        stmt = stmt.order_by(asc(Exercise.id))
    else:
        stmt = stmt.order_by(desc(Exercise.created_at))

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    exercises = result.scalars().unique().all()

    data = [
        {
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "thumbnail_url": e.thumbnail_url,
            "duration_minutes": e.duration_minutes,
            "shuffle_question": e.shuffle_question,
            "type_question": e.type_question,
            "created_at": e.created_at.isoformat() if e.created_at else None,
            "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        }
        for e in exercises
    ]

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy danh sách bài tập thành công!",
            data=data,
        )
    )


# ==============================================================
# 📗 LẤY CHI TIẾT BÀI TẬP
# ==============================================================

@router.get("/{exercise_id}")
async def get_exercise_detail(
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user),
):
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()

    if not exercise:
        return build_response(detail=response_json(False, "Không tìm thấy bài tập."))

    data = {
        "id": exercise.id,
        "title": exercise.title,
        "description": exercise.description,
        "thumbnail_url": exercise.thumbnail_url,
        "duration_minutes": exercise.duration_minutes,
        "shuffle_question": exercise.shuffle_question,
        "type_question": exercise.type_question,
        "created_at": exercise.created_at.isoformat() if exercise.created_at else None,
    }

    return build_response(
        detail=response_json(
            status=True,
            message="Lấy chi tiết bài tập thành công!",
            data=data,
        )
    )


# ==============================================================
# 🚀 BẮT ĐẦU LÀM BÀI (LẤY DANH SÁCH CÂU HỎI)
# ==============================================================

@router.post("/{exercise_id}/start")
async def start_exercise(
    exercise_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_user),
):
    # 1️⃣ Lấy bài tập
    result = await db.execute(select(Exercise).where(Exercise.id == exercise_id))
    exercise = result.scalar_one_or_none()

    if not exercise:
        return build_response(detail=response_json(False, "Không tìm thấy bài tập."))

    # 2️⃣ Kiểm tra bài làm đang mở
    attempt_result = await db.execute(
        select(ExerciseAttempt)
        .where(ExerciseAttempt.exercise_id == exercise.id)
        .where(ExerciseAttempt.user_id == user.id)
        .where(ExerciseAttempt.is_finished == False)
    )
    attempt = attempt_result.scalar_one_or_none()

    if not attempt:
        attempt = ExerciseAttempt(exercise_id=exercise.id, user_id=user.id)
        db.add(attempt)
        await db.commit()
        await db.refresh(attempt)

    # 3️⃣ Lấy danh sách câu hỏi và options
    question_result = await db.execute(
        select(ExerciseQuestion)
        .options(joinedload(ExerciseQuestion.question).joinedload(Question.options))
        .where(ExerciseQuestion.exercise_id == exercise.id)
    )
    exercise_questions = question_result.scalars().unique().all()

    questions_list = [eq.question for eq in exercise_questions if eq.question]

    # 5️⃣ Chuẩn bị dữ liệu câu hỏi
    questions_data = []
    for q in questions_list:
        # Lấy danh sách options

        options_data = [
            {
                "id": opt.id,
                "text": opt.text,
                "meta_data": opt.meta_data,
            }
            for opt in q.options
        ]

        questions_data.append({
            "id": q.id,
            "text": q.text,
            "type": q.type,
            "feedback": q.feedback,
            "options": options_data,
            "correct_answers": q.correct_answers,
        })

    # 6️⃣ Trả dữ liệu ra client
    data = {
        "attempt_id": attempt.id,
        "started_at": attempt.started_at.isoformat() if attempt.started_at else None,
        "finished_at": attempt.finished_at.isoformat() if attempt.finished_at else None,
        "is_finished": attempt.is_finished,
        "exercise": {
            "id": exercise.id,
            "title": exercise.title,
            "description": exercise.description,
            "duration_minutes": exercise.duration_minutes,
            "shuffle_question": exercise.shuffle_question,
            "type_question": exercise.type_question,
            "questions": questions_data,
        },
    }

    return build_response(
        detail=response_json(
            status=True,
            message="Bắt đầu làm bài thành công!",
            data=data,
        )
    )
