from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Rostering system backend running"}

