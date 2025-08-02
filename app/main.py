from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.services.firebase_service import init_firebase
from app.routers import auth, user, common, shipper, upload, notification, websocket
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

init_firebase()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(shipper.router, prefix="/shipper", tags=["shipper"])
app.include_router(common.router, prefix="/common", tags=["common"])
app.include_router(upload.router, prefix="/upload", tags=["upload"])
app.include_router(notification.router, prefix="/notification", tags=["notification"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])

@app.get("/")
def read_root():
    return {"message": "Server is running"}