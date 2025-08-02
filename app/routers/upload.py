from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from uuid import uuid4
import os
import aiofiles
from app.dependencies import require_session, get_db
from app.models.upload import Upload, FileType
from app.models.user_session import UserSession
from app.utils import response_json, build_response

router = APIRouter()

UPLOAD_FOLDER = "static/uploads"
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

@router.post("/image")
async def upload_file(
    file: UploadFile = File(...),
    file_type: FileType = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    session: UserSession = Depends(require_session),
):
    ext = os.path.splitext(file.filename)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS or file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=response_json(status=False, message="Invalid image type"),
        )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=response_json(status=False, message=f"File exceeds {MAX_FILE_SIZE_MB}MB limit"),
        )

    filename = f"{uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_FOLDER, filename)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Ghi file bất đồng bộ
    async with aiofiles.open(saved_path, "wb") as out_file:
        await out_file.write(content)

    file_url = str(request.base_url) + f"static/uploads/{filename}"

    upload = Upload(
        user_id=session.user.id,
        url=file_url,
        file_path=saved_path,
        file_name=file.filename,
        file_type=file_type,
        mime_type=file.content_type,
        size=len(content)
    )

    db.add(upload)
    db.commit()
    db.refresh(upload)

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