from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.dependencies import get_db
from app.models.banner import Banner
from app.schemas.conversation import ChatRequest
from app.utils import response_json, build_response
from openai import AsyncOpenAI

router = APIRouter()

@router.get("/banners")
async def get_banners(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Banner).order_by(Banner.created_at.desc()))
    banners = result.scalars().all()
    return build_response(
        status_code=200,
        detail=response_json(status=True, message="Danh sách banner", data=banners)
    )
@router.get("/utilities")
async def get_utilities(db: AsyncSession = Depends(get_db)):
    return build_response(
        status_code=200,
        detail=response_json(status=True, message="URL tiện ích", data={
            "url": "https://react-simple-quiz-delta.vercel.app/"
        })
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

        return build_response(
            status_code=200,
            detail=response_json(
                status=True,
                message=response.output_text,
                data=None
            )
        )

    except Exception as e:
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
