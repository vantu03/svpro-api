from typing import Any
from fastapi import Request
import httpx
from markupsafe import Markup
from sqladmin import ModelView, Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.database import async_session
from app.dependencies import verify_token
from app.models.feedback import Feedback
from app.models.order import Order
from app.models.post import Post
from app.models.post_attachment import PostAttachment
from app.models.post_comment import PostComment
from app.models.post_interacts import PostInteract
from app.models.post_view import PostView
from app.models.sender import Sender
from app.models.user import User
from app.models.user_session import UserSession
from app.models.shipper import Shipper
from app.models.shipper_application import ShipperApplication
from app.models.notification import Notification
from app.models.banner import Banner
from app.models.upload import Upload
from app.models.fcm_token import FCMToken
from app.models.app_version import AppVersion
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

        async with httpx.AsyncClient(base_url=settings.BASE_URL) as client:
            response = await client.post(
                "/auth/login",
                json={
                    "username": username,
                    "password": password,
                    "device_info": "fast-admin web",
                },
            )

        if response.status_code != 200:
            return False

        try:
            token = (
                response.json()
                .get("detail", {})
                .get("data", {})
                .get("token")
            )
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
            session = await verify_token(token)

            async with async_session() as db:
                result  = await db.execute(select(User).where(User.id == session.user_id))
                user = result.scalar_one_or_none()
                if user:
                    return user.is_staff or user.is_superuser

        except Exception as e:
            print(f"[Admin authenticate error] {e}")
            return False
        return False

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.full_name, User.email]
    form_excluded_columns = ["created_at", "updated_at"]


class UserSessionAdmin(ModelView, model=UserSession):
    column_list = [
        UserSession.id,
        UserSession.user_id,
        UserSession.fcm_token,
        UserSession.created_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]


class ShipperAdmin(ModelView, model=Shipper):
    column_list = [
        Shipper.id,
        Shipper.user_id,
        Shipper.is_active,
        Shipper.application_id,
        Shipper.created_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]


class ShipperApplicationAdmin(ModelView, model=ShipperApplication):
    column_list = [
        ShipperApplication.id,
        ShipperApplication.user_id,
        ShipperApplication.status,
        ShipperApplication.created_at,
    ]

    form_columns = ["phone_number", "full_name", "status", "reject_reason"]

    form_widget_args = {
        "full_name": {"readonly": True},
        "phone_number": {"readonly": True},
    }

    async def after_model_change(
        self, data: dict, model: Any, is_created: bool, request: Request
    ) -> None:
        async with async_session() as db:
            if model.status in ("approved", 1):
                result = await db.execute(
                    select(Shipper).where(Shipper.user_id == model.user_id)
                )
                existing = result.scalar_one_or_none()
                if not existing:
                    new_shipper = Shipper(
                        user_id=model.user_id,
                        application_id=model.id,
                        full_name=model.full_name,
                        phone_number=model.phone_number,
                        is_active=True,
                    )
                    db.add(new_shipper)
                    await db.commit()
                    await db.refresh(new_shipper)

                    await notify_user(
                        model.user_id,
                        "Chào mừng bạn tham gia shipper",
                        "Sau khi xem xét hồ sơ của bạn chúng tôi nhận thấy bạn đủ điều kiện làm shipper.\nHãy vào tiện ích shipper để bật thông báo khi có đơn nhé.",
                        "sound_warning.wav",
                    )

            if model.status == "rejected":
                reason = (model.reject_reason or "").strip()
                message = (
                    f"Bạn bị từ chối hồ sơ vì: {reason}"
                    if reason
                    else "Sau khi xem xét hồ sơ của bạn, chúng tôi nhận thấy hồ sơ chưa đạt yêu cầu."
                )
                await notify_user(
                    model.user_id,
                    "Cập nhật nội dung hồ sơ Shipper",
                    message,
                    "sound_warning.wav",
                )


class SenderAdmin(ModelView, model=Sender):
    column_list = [Sender.id, Sender.user_id, Sender.status, Sender.created_at]
    form_excluded_columns = ["created_at", "updated_at"]


class OrderAdmin(ModelView, model=Order):
    column_list = [
        Order.id,
        Order.sender_id,
        Order.receiver_name,
        Order.status,
        Order.created_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]


class NotificationAdmin(ModelView, model=Notification):
    column_list = [
        Notification.id,
        Notification.user_id,
        Notification.title,
        Notification.content,
        Notification.is_read,
    ]
    form_excluded_columns = ["created_at", "updated_at"]


class BannerAdmin(ModelView, model=Banner):
    column_list = [Banner.id, "url", Banner.created_at, Banner.created_at]
    form_excluded_columns = ["created_at", "updated_at"]

    column_formatters = {
        "url": lambda m, a: Markup(
            f'<img src="{m.url}" style="width: 200px;">'
        ),
    }
    column_formatters_detail = {
        "url": lambda m, a: Markup(
            f'<img src="{m.url}" style="width: 200px;">'
        ),
    }


class UploadAdmin(ModelView, model=Upload):
    column_list = [Upload.id, Upload.url, Upload.file_name, Upload.created_at]
    form_excluded_columns = ["created_at", "updated_at"]

    column_formatters = {
        "url": lambda m, a: Markup(
            f'<img src="{m.url}" style="width: 200px;">'
        ),
    }
    column_formatters_detail = {
        "url": lambda m, a: Markup(
            f'<a href="{m.url}" target="_blank"><img src="{m.url}" style="width: 200px;"></a>'
        ),
    }


class FCMTokenAdmin(ModelView, model=FCMToken):
    column_list = [FCMToken.id, FCMToken.session, FCMToken.token]
    form_excluded_columns = ["created_at", "updated_at"]


class AppVersionAdmin(ModelView, model=AppVersion):
    column_list = [
        AppVersion.id,
        AppVersion.platform,
        AppVersion.latest_version,
        AppVersion.title,
        AppVersion.created_at,
        AppVersion.updated_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]

class PostAdmin(ModelView, model=Post):
    column_list = [
        Post.id,
        Post.user_id,
        Post.content,
        Post.is_deleted,
        Post.created_at,
        Post.updated_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]

class PostCommentAdmin(ModelView, model=PostComment):
    column_list = [
        PostComment.id,
        PostComment.post_id,
        PostComment.user_id,
        PostComment.content,
        PostComment.is_deleted,
        PostComment.created_at,
        PostComment.updated_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]

class PostAttachmentAdmin(ModelView, model=PostAttachment):
    column_list = [
        PostAttachment.id,
        PostAttachment.post_id,
        PostAttachment.type,
        PostAttachment.url,
        PostAttachment.created_at,
        PostAttachment.updated_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]

    # Hiển thị preview nếu url là ảnh
    column_formatters = {
        "url": lambda m, a: Markup(f'<img src="{m.url}" style="max-width:200px;">') if m.url else ""
    }
    column_formatters_detail = {
        "url": lambda m, a: Markup(f'<a href="{m.url}" target="_blank"><img src="{m.url}" style="max-width:400px;"></a>') if m.url else ""
    }

class PostInteractAdmin(ModelView, model=PostInteract):
    column_list = [
        PostInteract.id,
        PostInteract.post_id,
        PostInteract.user_id,
        PostInteract.created_at,
        PostInteract.updated_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]

class PostViewAdmin(ModelView, model=PostView):
    column_list = [
        PostView.id,
        PostView.post_id,
        PostView.user_id,
        PostView.created_at,
        PostView.updated_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]

class FeedbackAdmin(ModelView, model=Feedback):
    column_list = [
        Feedback.id,
        Feedback.title,
        Feedback.content,
        Feedback.created_at,
        Feedback.updated_at,
    ]
    form_excluded_columns = ["created_at", "updated_at"]

def setup_admin(app, engine):
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuth(),
        session_maker=async_session,
    )
    admin.add_view(UserAdmin)
    admin.add_view(UserSessionAdmin)
    admin.add_view(ShipperAdmin)
    admin.add_view(SenderAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(ShipperApplicationAdmin)
    admin.add_view(NotificationAdmin)
    admin.add_view(BannerAdmin)
    admin.add_view(UploadAdmin)
    admin.add_view(FCMTokenAdmin)
    admin.add_view(AppVersionAdmin)
    admin.add_view(PostAdmin)
    admin.add_view(PostCommentAdmin)
    admin.add_view(PostAttachmentAdmin)
    admin.add_view(PostInteractAdmin)
    admin.add_view(PostViewAdmin)
    admin.add_view(FeedbackAdmin)

