from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import require_session, get_db
from app.models.upload import Upload, FileType
from app.models.user_session import UserSession
from app.utils import response_json, build_response, save_upload_file

router = APIRouter()

UPLOAD_FOLDER = "static/uploads"
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".pdf", ".doc", ".docx", ".txt", ".zip", ".rar"
}

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/zip",
    "application/x-rar-compressed"
}


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    result, error = await save_upload_file(
        file,
        UPLOAD_FOLDER,
        MAX_FILE_SIZE,
        {".jpg", ".jpeg", ".png", ".webp"},
        {"image/jpeg", "image/png", "image/webp"}
    )

    if error:
        raise HTTPException(status_code=400, detail=response_json(status=False, message=error))

    file_url = str(request.base_url) + f"static/uploads/{result['filename']}"

    upload = Upload(
        user_id=session.user.id,
        url=file_url,
        file_path=result["saved_path"],
        file_name=result["original_name"],
        file_type=file_type,
        mime_type=result["mime_type"],
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
                "mime_type": upload.mime_type,
                "size": upload.size
            }
        )
    )


@router.post("/")
async def upload_any_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    result, error = await save_upload_file(
        file,
        UPLOAD_FOLDER,
        MAX_FILE_SIZE,
        ALLOWED_EXTENSIONS,
        ALLOWED_MIME_TYPES
    )

    if error:
        raise HTTPException(status_code=400, detail=response_json(status=False, message=error))

    file_url = str(request.base_url) + f"static/uploads/{result['filename']}"

    upload = Upload(
        user_id=session.user.id,
        url=file_url,
        file_path=result["saved_path"],
        file_name=result["original_name"],
        file_type=file_type,
        mime_type=result["mime_type"],
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
                "mime_type": upload.mime_type,
                "size": upload.size
            }
        )
    )
