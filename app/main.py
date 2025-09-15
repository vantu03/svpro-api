from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.admin import setup_admin
from app.services.firebase_service import initialize_firebase
from app.routers import (
    auth, user, common, shipper, upload,
    notification, websocket, sender, conversations, application, post
)
from app.database import Base, engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init Firebase
    initialize_firebase()

    # Init database
    async with engine.begin() as conn:
        print("Loaded tables:", Base.metadata.tables.keys())
        await conn.run_sync(Base.metadata.create_all)

    yield

app = FastAPI(lifespan=lifespan)

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
app.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(notification.router, prefix="/notification", tags=["notification"])
app.include_router(post.router, prefix="/post", tags=["post"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

# Admin setup
setup_admin(app, engine)

@app.get("/")
def read_root():
    return {"message": "Server is running"}
