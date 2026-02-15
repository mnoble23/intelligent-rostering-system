from fastapi import FastAPI
from app.api import users, availability, roster
from app.db.base import Base
from app.db.session import engine
import app.models
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(availability.router)
app.include_router(roster.router)

@app.get("/")
def root():
    return {"message": "Rostering system backend running"}
