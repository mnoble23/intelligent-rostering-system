from fastapi import FastAPI
from sqlalchemy import inspect, text
from app.api import users, availability, roster
from app.db.base import Base
from app.db.session import engine
import app.models
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

with engine.begin() as connection:
    inspector = inspect(connection)
    user_columns = {column["name"] for column in inspector.get_columns("user")}

    if "min_hours" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN min_hours FLOAT NOT NULL DEFAULT 0')
        )
    if "max_hours" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN max_hours FLOAT NOT NULL DEFAULT 40')
        )

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
