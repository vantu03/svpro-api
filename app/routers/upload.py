from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db, require_user
from app.models.upload import Upload, FileType
from app.models.user import User
from app.utils import response_json, build_response, save_upload_file

router = APIRouter()

UPLOAD_FOLDER = "static/uploads"
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".pdf", ".doc", ".docx", ".txt", ".zip", ".rar"
}

@router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_user),
):
    result, error = await save_upload_file(
        file,
        UPLOAD_FOLDER,
        MAX_FILE_SIZE,
        ALLOWED_EXTENSIONS
    )

    if error:
        raise HTTPException(status_code=400, detail=response_json(status=False, message=error))

    file_url = str(request.base_url) + f"static/uploads/{result['filename']}"

    upload = Upload(
        user_id=user.id,
        url=file_url,
        file_path=result["saved_path"],
        file_name=result["original_name"],
        file_type=file_type,
        size=result["size"]
    )

    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    return build_response(
        detail=response_json(
            status=True,
            data={
                "id": upload.id,
                "url": upload.url,
                "file_type": upload.file_type,
                "size": upload.size
            }
        )
    )
