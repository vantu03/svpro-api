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