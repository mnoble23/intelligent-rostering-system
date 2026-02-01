from fastapi import FastAPI
from app.api import users, availability, roster

app = FastAPI()

app.include_router(users.router)
app.include_router(availability.router)
app.include_router(roster.router)

@app.get("/")
def root():
    return {"message": "Rostering system backend running"}
