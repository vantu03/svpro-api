import json

import firebase_admin
from firebase_admin import credentials, messaging
import asyncio
from typing import List, Optional

from app.config import get_settings

settings = get_settings()

def initialize_firebase():
    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(settings.google_credentials)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized!")

async def send_notification(
    tokens: List[str],
    title: str,
    content: str,
    data: dict,
    *,
    sound: Optional[str] = None,                 # "default" or filename (Android/iOS)
    media: Optional[dict] = None,                # {"type": "image|video|audio", "url": "https://..."}
    actions: Optional[List[dict]] = None,        # [{id, title, reply: bool, icon?, intent? (android), url? (web)}]
    link: Optional[str] = None,                  # URL to open on click (Web). Mobile handles deeplink natively
    badge: Optional[int] = None,                 # iOS badge
    priority: str = "high",                     # "high" | "normal" (Android)
    category: Optional[str] = None,              # iOS UNNotificationCategory identifier
    overrides: Optional[dict] = None             # {"android": {...}, "ios": {...}, "web": {...}}
) -> dict:

    overrides = overrides or {}

    # Cross-platform meta for client capabilities and behavior fallbacks
    meta = {
        "sound": sound,
        "link": link or "",
        "actions": actions or [],
        "media": media or {},
        "category": category or "",
        "capabilities": {
            "android": {"reply": True, "actions": True, "image": True, "video": False, "audio": False},
            "ios":     {"reply": True, "actions": True, "image": True, "video": True,  "audio": True},
            "web":     {"reply": True, "actions": True, "image": True, "video": True,  "audio": True},
        },
    }

    # Android config
    android_notif_kwargs = {"title": title, "body": content}
    if media and media.get("type") == "image" and isinstance(media.get("url"), str) and media.get("url").strip():
        android_notif_kwargs["image"] = media["url"]
    if isinstance(sound, str) and sound.strip():
        android_notif_kwargs["sound"] = sound.split(".")[0].strip()

    android_cfg = messaging.AndroidConfig(
        priority=priority if priority in ("high", "normal") else "high",
        notification=messaging.AndroidNotification(**android_notif_kwargs)
    )

    if "android" in overrides and isinstance(overrides.get("android"), dict):
        o = overrides["android"]
        for k in ("channel_id", "click_action", "ticker", "visibility"):
            v = o.get(k)
            if isinstance(v, str) and v.strip():
                setattr(android_cfg.notification, k, v)

    # iOS / APNs config
    aps_kwargs = {}
    if badge is not None:
        aps_kwargs["badge"] = int(badge)
    if isinstance(sound, str) and sound.strip():
        aps_kwargs["sound"] = sound
    if isinstance(category, str) and category.strip():
        aps_kwargs["category"] = category
    if media and isinstance(media.get("url"), str) and media.get("url").strip():
        aps_kwargs["mutable_content"] = True  # enable NSE when media exists

    apns_payload = messaging.APNSPayload(aps=messaging.Aps(**aps_kwargs) if aps_kwargs else messaging.Aps())
    apns_fcm_opts = messaging.APNSFCMOptions(
        image=media["url"] if media and media.get("type") == "image" and isinstance(media.get("url"), str) and media.get("url").strip() else None
    )
    apns_cfg = messaging.APNSConfig(payload=apns_payload, fcm_options=apns_fcm_opts)

    if "ios" in overrides and isinstance(overrides.get("ios"), dict):
        o = overrides["ios"]
        thread_id = o.get("thread_id")
        if isinstance(thread_id, str) and thread_id.strip():
            apns_cfg.payload.aps.thread_id = thread_id

    # Web Push config
    webpush_notif_kwargs = {"title": title, "body": content}
    if media and media.get("type") == "image" and isinstance(media.get("url"), str) and media.get("url").strip():
        webpush_notif_kwargs["image"] = media["url"]
    if "web" in overrides and isinstance(overrides.get("web"), dict):
        icon = overrides["web"].get("icon")
        if isinstance(icon, str) and icon.strip():
            webpush_notif_kwargs["icon"] = icon

    webpush_cfg_kwargs = {"notification": messaging.WebpushNotification(**webpush_notif_kwargs)}
    if isinstance(link, str) and link.strip():
        webpush_cfg_kwargs["fcm_options"] = messaging.WebpushFCMOptions(link=link)
    webpush_cfg = messaging.WebpushConfig(**webpush_cfg_kwargs)

    # Data payload (FCM data requires string values). Do not overwrite user-supplied keys; add __meta
    merged_data = {}
    for k, v in data.items():
        merged_data[k] = str(v)
    merged_data["__meta"] = json.dumps(meta, ensure_ascii=False)

    # Build message. FCM will route per-token platform; unused platform configs are ignored.
    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=content),
        data=merged_data,
        android=android_cfg,
        apns=apns_cfg,
        webpush=webpush_cfg,
    )

    # Send concurrently via a thread (messaging calls are blocking)
    try:
        resp = await asyncio.to_thread(messaging.send_each_for_multicast, message)
        failed = [tokens[i] for i, r in enumerate(resp.responses) if not r.success]
        for i, r in enumerate(resp.responses):
            if not r.success:
                print(f"Token lỗi[{i}]: {tokens[i]}, lỗi: {r.exception}")
        print(f"Gửi thành công {resp.success_count}/{len(tokens)} tokens")
        return {"success_count": resp.success_count, "failure_count": resp.failure_count, "failed_tokens": failed}
    except Exception as e:
        print(f"Lỗi khi gửi FCM: {e}")
        return {"success_count": 0, "failure_count": len(tokens), "error": str(e)}
