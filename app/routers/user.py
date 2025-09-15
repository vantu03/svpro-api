from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_user
from app.config import SCHOOLS
from app.models.user import User
from app.utils import response_json, build_response
from fastapi import APIRouter, HTTPException, Depends

router = APIRouter()


@router.get("/")
async def get_current_user(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    return build_response(
        status_code=200,
        detail=response_json(
            status=True,
            message="Lấy thông tin người dùng thành công",
            data={
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email,
                "avatar_url": user.avatar_url,
            },
        ),
    )


@router.get("/schedule")
async def get_user_schedule(
    user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    provider_key = next((p for p in SCHOOLS if user.username.startswith(p)), None)

    if provider_key:
        provider = SCHOOLS[provider_key]()
        result = await provider.login(user.username, user.password)

        if result.get("error"):
            raise HTTPException(
                status_code=500,
                detail=response_json(status=False, message=result.get("error")),
            )

        schedule = await provider.get_schedule()
        return build_response(
            status_code=200,
            detail=response_json(
                status=True,
                message="Lấy dữ liệu lịch học thành công",
                data=schedule,
            ),
        )

    raise HTTPException(
        status_code=404,
        detail=response_json(status=False, message="Không có lịch"),
    )
