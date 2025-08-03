import firebase_admin
from firebase_admin import credentials, messaging
import asyncio
from typing import List

from app.config import get_settings

settings = get_settings()

def initialize_firebase():
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(settings.google_credentials)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized!")

async def send_fcm_multicast_each(
    tokens: List[str],
    title: str,
    body: str,
    data: dict = None
):
    if not tokens:
        return {"success_count": 0, "failure_count": 0, "failed_tokens": []}

    message = messaging.MulticastMessage(
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
        tokens=tokens,
    )

    def _send_each():
        return messaging.send_each_for_multicast(message)

    try:
        response = await asyncio.to_thread(_send_each)
        print(f"📤 Gửi thành công {response.success_count}/{len(tokens)} tokens")
        failed = [tokens[i] for i, resp in enumerate(response.responses) if not resp.success]
        for i, resp in enumerate(response.responses):
            if not resp.success:
                print(f"❌ Token lỗi[{i}]: {tokens[i]}, lỗi: {resp.exception}")
        return {
            "success_count": response.success_count,
            "failure_count": response.failure_count,
            "failed_tokens": failed,
        }

    except Exception as e:
        print(f"❌ Lỗi khi gửi FCM: {e}")
        return {"success_count": 0, "failure_count": len(tokens), "error": str(e)}
