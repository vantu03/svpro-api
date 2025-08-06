from typing import Any
from urllib.request import Request

import httpx
from markupsafe import Markup
from sqladmin import ModelView, Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.dependencies import verify_token, get_db_context
from app.models.user import User
from app.models.user_session import UserSession
from app.models.shippper import Shipper
from app.models.shipper_application import ShipperApplication
from app.models.notification import Notification
from app.models.banner import Banner
from app.models.upload import Upload
from app.models.fcm_token import FCMToken
from app.services.notification_service import notify_user

settings = get_settings()

class AdminAuth(AuthenticationBackend):
    def __init__(self):
        super().__init__(secret_key=settings.SECRET_KEY)

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            return False

        # Gửi request tới /auth/login để lấy token
        async with httpx.AsyncClient(base_url=settings.BASE_URL) as client:
            response = await client.post("/auth/login", json={
                "username": username,
                "password": password,
                "device_info": "fast-admin web"
            })

        if response.status_code != 200:
            return False

        try:
            token = response.json().get("detail", {}).get("data", {}).get("token")
            if token:
                request.session.update({"token": token})
                return True
        except Exception as e:
            print(f"[Admin login failed] {e}")

        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False

        try:
            with get_db_context() as db:
                user_session = verify_token(token, db)
                return user_session.user.is_staff or user_session.user.is_superuser
        except:
            return False

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email]

class UserSessionAdmin(ModelView, model=UserSession):
    column_list = [UserSession.id, UserSession.user_id, UserSession.fcm_token, UserSession.created_at]

class ShipperAdmin(ModelView, model=Shipper):
    column_list = [Shipper.id, Shipper.user_id, Shipper.is_active, Shipper.application_id, Shipper.create_at]

class ShipperApplicationAdmin(ModelView, model=ShipperApplication):
    column_list = [ShipperApplication.id, Shipper.user_id, ShipperApplication.status, ShipperApplication.created_at]

    form_columns = ["phone_number", "full_name", "status", "reject_reason"]

    form_widget_args = {
        "full_name": {"readonly": True},
        "phone_number": {"readonly": True},
    }

    column_formatters_detail = {
        "portrait_image": lambda m, a: Markup(f'<a href="{m.portrait_image}" target="_blank"><img src="{m.portrait_image}" style="width: 200px;">'),
        "identity_image_front": lambda m, a: Markup(f'<a href="{m.identity_image_front}" target="_blank"><img src="{m.identity_image_front}" style="width: 200px;">'),
        "identity_image_back": lambda m, a: Markup(f'<a href="{m.identity_image_back}" target="_blank"><img src="{m.identity_image_back}" style="width: 200px;">'),
    }

    async def after_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        with get_db_context() as db:
            if model.status == 'approved' or model.status == 1:
                existing = db.query(Shipper).filter_by(user_id=model.user_id).first()
                if not existing:
                    new_shipper = Shipper(
                        user_id=model.user_id,
                        application_id=model.id,
                        is_active=True
                    )
                    db.add(new_shipper)
                    db.commit()
                    db.refresh(new_shipper)
                    await notify_user(
                        db,
                        model.user_id,
                        "Hồ sơ đăng ký Shipper đã được duyệt",
                        "Sau khi xem xét hồ sơ của bạn chúng tôi nhận thấy bạn đủ điều kiện làm shipper.\nHãy vào tiện ích shipper để bật thông báo khi có đơn nhé."
                    )

            if model.status == 'rejected':
                reason = model.reject_reason.strip() if model.reject_reason else None
                message = (
                    f"Bạn bị từ chối hồ sơ vì: {reason}"
                    if reason
                    else "Sau khi xem xét hồ sơ của bạn, chúng tôi nhận thấy nó chưa đáp ứng được các điều kiện cần thiết."
                )
                await notify_user(
                    db,
                    model.user_id,
                    "Cập nhật nội dung hồ sơ Shipper",
                    message
                )

class NotificationAdmin(ModelView, model=Notification):
    column_list = [Notification.id, Notification.user_id, Notification.title, Notification.content, Notification.is_read]

class BannerAdmin(ModelView, model=Banner):
    column_list = [Banner.id, "url", Banner.created_at, Banner.created_at]

    column_formatters = {
        "url": lambda m, a: Markup(f'<img src="{m.url}" style="width: 200px;">'),
    }

    column_formatters_detail = {
        "url": lambda m, a: Markup(f'<img src="{m.url}" style="width: 200px;">'),
    }


class UploadAdmin(ModelView, model=Upload):
    column_list = [Upload.id, Upload.url, Upload.file_name, Upload.uploaded_at]

    column_formatters = {
        "url": lambda m, a: Markup(f'<img src="{m.url}" style="width: 200px;">'),
    }

    column_formatters_detail = {
        "url": lambda m, a: Markup(f'<a href="{m.url}" target="_blank"><img src="{m.url}" style="width: 200px;"></a>'),
    }


class FCMTokenAdmin(ModelView, model=FCMToken):
    column_list = [FCMToken.id, FCMToken.session, FCMToken.token]


# Hàm khởi tạo admin
def setup_admin(app, engine):
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    admin = Admin(app, engine, authentication_backend=AdminAuth())
    admin.add_view(UserAdmin)
    admin.add_view(UserSessionAdmin)
    admin.add_view(ShipperAdmin)
    admin.add_view(ShipperApplicationAdmin)
    admin.add_view(NotificationAdmin)
    admin.add_view(BannerAdmin)
    admin.add_view(UploadAdmin)
    admin.add_view(FCMTokenAdmin)
