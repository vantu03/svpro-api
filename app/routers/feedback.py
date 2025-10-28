from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_user
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackCreateRequest
from app.utils import build_response, response_json

router = APIRouter()

@router.post("/create")
async def create_feedback(
    payload: FeedbackCreateRequest,
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db)
):
    feedback = Feedback(
        user_id=user.id,
        title=payload.title,
        content=payload.content,
    )

    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return build_response(
        status_code=201,
        detail=response_json(
            True,
            "Gửi góp ý thành công! Cảm ơn bạn đã phản hồi",
            {
                "id": feedback.id,
                "created_at": feedback.created_at,
            }
        )
    )
