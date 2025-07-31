from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, user, common

app = FastAPI()

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
app.include_router(common.router, prefix="/common", tags=["common"])

@app.get("/")
def read_root():
    return {"message": "Server is running"}