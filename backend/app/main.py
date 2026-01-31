from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Rostering system backend running"}

@app.get("/users")
def get_users():
    return [
        {
            "id": 1,
            "name": "Alice",
            "role": "Sales Associate"
        },
        {
            "id": 2,
            "name": "Bob",
            "role": "Manager"
        }
    ]