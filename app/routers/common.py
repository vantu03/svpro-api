from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.models.banner import Banner
from app.schemas.conversation import ChatRequest
from app.utils import response_json, build_response
from openai import AsyncOpenAI

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

@router.post("/r")
async def chat_ai(payload: ChatRequest):
    client = AsyncOpenAI()

    try:
        # Chuẩn bị nội dung input
        content = [{"type": "input_text", "text": payload.prompt}]

        # Thêm ảnh
        for img in payload.images:
            content.append({"type": "input_image", "image_url": img})

        # Thêm file
        for f in payload.files:
            content.append({"type": "input_file", "file_id": f})

        # Gọi ChatGPT (phải await)
        response = await client.responses.create(
            model="gpt-4o",
            input=[{"role": "user", "content": content}]
        )

        # Thành công → message = output_text
        return build_response(
            status_code=200,
            detail=response_json(
                status=True,
                message=response.output_text,
                data=None
            )
        )

    except Exception as e:
        # Thất bại → message = lỗi
        return build_response(
            status_code=500,
            detail=response_json(
                status=False,
                message=f"Lỗi: {str(e)}",
                data=None
            )
        )
    
@router.get("/f")
async def list_files():
    client = AsyncOpenAI()
    try:
        files = await client.files.list()
        return build_response(
            status_code=200,
            detail=response_json(
                status=True,
                message="successs",
                data=[{
                    "id": f.id,
                    "filename": f.filename,
                    "purpose": f.purpose,
                    "size": f.bytes,
                    "created_at": f.created_at
                } for f in files.data]
            )
        )
    except Exception as e:
        return build_response(
            status_code=500,
            detail=response_json(status=False, message=f"Lỗi: {str(e)}", data=None)
        )
