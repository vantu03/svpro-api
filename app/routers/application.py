from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.dependencies import get_db
from app.models.app_version import PlatformEnum, AppVersion
from app.schemas.application import CheckUpdateRequest
from app.utils import build_response, response_json, is_outdated

router = APIRouter()

@router.post("/update/version")
async def check_update(
    payload: CheckUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    platform = PlatformEnum(payload.os_name.lower())

    result = await db.execute(
        select(AppVersion)
        .where(AppVersion.platform == platform)
        .order_by(AppVersion.created_at.desc())
    )
    record = result.scalars().first()

    if not record:
        return build_response(
            status_code=404,
            detail=response_json(False, "Không tìm thấy dữ liệu update", None)
        )

    need_update = is_outdated(payload.app_version, record.latest_version)

    return build_response(
        status_code=200,
        detail=response_json(
            status=True,
            message="Thông tin cập nhật",
            data={
                "update": need_update,
                "force": record.force if need_update else False,
                "latest_version": record.latest_version,
                "latest_build": record.latest_build,
                "title": record.title,
                "content": record.content,
                "confirm_text": record.confirm_text,
                "url": record.url,
                "client_info": {
                    "app_version": payload.app_version,
                    "build_number": payload.build_number,
                    "os_name": payload.os_name,
                    "os_version": payload.os_version,
                    "device_name": payload.device_name,
                    "device_model": payload.device_model,
                }
            }
        )
    )
