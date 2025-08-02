from sqlalchemy.orm import Session
from app.dependencies import get_db, require_session
from app.lib.ictu import Ictu
from app.models.user_session import UserSession
from app.utils import response_json, build_response
from fastapi import APIRouter, HTTPException, Depends
router = APIRouter()

@router.get("/")
def get_current_user(
    session: UserSession = Depends(require_session),
    db: Session = Depends(get_db)
):
    user = session.user
    return build_response(
        status_code=200,
        detail=response_json(
            status=True,
            message="Lấy thông tin người dùng thành công",
            data={
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "email": user.email
            }
        )
    )
@router.get("/schedule")
async def get_current_user(
    session: UserSession = Depends(require_session),
    db: Session = Depends(get_db)
):
    user = session.user

    if user.username.startswith('dtc'):
        browser = Ictu()
        res = await browser.login(user.username, user.password)

        if res != '':
            raise HTTPException(
                status_code=500,
                detail=response_json(status=False, message=res)
            )

        result = await browser.get_schedule()
        return build_response(
            status_code=200,
            detail=response_json(
                status=True,
                message='Lấy dữ liệu lịch học thành công',
                data=result
            )
        )

    else:
        raise HTTPException(
            status_code=404,
            detail=response_json(status=False, message='Không có lịch')
        )