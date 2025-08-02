import asyncio
import firebase_admin
from firebase_admin import credentials, get_app
from app.config import get_settings
from firebase_admin.messaging import send_each_for_multicast, MulticastMessage, Notification

settings = get_settings()


def init_firebase():
    try:
        get_app()
    except ValueError:
        print("✅ Initializing Firebase...")
        cred = credentials.Certificate(settings.google_credentials)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized!")



async def send_fcm_to_many(tokens: list[str], title: str, body: str):
    if not tokens:
        print("⚠️ No tokens provided.")
        return

    message = MulticastMessage(
        notification=Notification(title=title, body=body),
        tokens=tokens,
    )

    try:
        response = await asyncio.to_thread(send_each_for_multicast, message)
        success_count = sum(1 for r in response if r.success)
        print(f"📤 Sent {success_count} / {len(tokens)} messages")

        for idx, resp in enumerate(response):
            if not resp.success:
                print(f"❌ Failed token: {tokens[idx]}, reason: {resp.exception}")
    except Exception as e:
        print(f"❌ FCM sending failed: {e}")

def chunked(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


async def send_fcm_large_list(tokens: list[str], title: str, body: str):
    for chunk in chunked(tokens, 500):
        await send_fcm_to_many(chunk, title, body)
