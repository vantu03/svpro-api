from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.banner import Banner
from app.utils import response_json, build_response

router = APIRouter()

@router.get("/banners")
def get_banners(db: Session = Depends(get_db)):
    banners = db.query(Banner).order_by(Banner.created_at.desc()).all()
    return build_response(
        status_code=200,
        detail=response_json(status=True, message="Danh sách banner", data=banners)
    )

@router.get("/update/version")
def get_app_version():
    return build_response(
        status_code=200,
        detail=response_json(
            status=True,
            message="Thông tin cập nhật",
            data={
                "latest_version": "1.0.8",
                "force": False,
                "title": "Có bản cập nhật mới",
                "content": "Phiên bản 1.0.8 đã có. Vui lòng cập nhật để có trải nghiệm tốt nhất.",
                "confirm_text": "Cập nhật",
                "urls": {
                    "android": "https://play.google.com/store/apps/details?id=com.vantu.svpro",
                    "ios": "https://apps.apple.com/vn/app/svpro/id6749335407?l=vi",
                    "web": "https://svpro.vn/"
                }
            }
        )
    )