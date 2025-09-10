from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.app_version import PlatformEnum, AppVersion
from app.schemas.application import CheckUpdateRequest
from app.utils import build_response, response_json, is_outdated

router = APIRouter()

@router.post("/update/version")
def check_update(
    payload: CheckUpdateRequest,
    db: Session = Depends(get_db)
):
    platform = PlatformEnum(payload.os_name.lower())

    # Lấy bản version mới nhất từ DB theo platform
    record = (
        db.query(AppVersion)
        .filter(AppVersion.platform == platform)
        .order_by(AppVersion.created_at.desc())
        .first()
    )

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
                # Thêm log để debug / phân tích
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