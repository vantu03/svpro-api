
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.admin import setup_admin
from app.services.firebase_service import initialize_firebase
from app.database import engine, Base

from dotenv import load_dotenv

from app.routers import (
    auth,
    user,
    common,
    shipper,
    upload,
    notification,
    websocket,
    sender,
    application,
    post,
    feedback,
)
load_dotenv()
app = FastAPI()

# Khởi tạo database
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(shipper.router, prefix="/shipper", tags=["shipper"])
app.include_router(sender.router, prefix="/sender", tags=["sender"])
app.include_router(common.router, prefix="/common", tags=["common"])
app.include_router(application.router, prefix="/application", tags=["application"])
app.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(notification.router, prefix="/notification", tags=["notification"])
app.include_router(post.router, prefix="/post", tags=["post"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

setup_admin(app, engine)

initialize_firebase()

@app.get("/")
def read_root():
    return {"message": "Server is running"}
