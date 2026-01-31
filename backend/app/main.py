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

@app.get("/availability")
def get_availability():
    return [
        {"user_id": 1, "day": "Monday", "available": True},
        {"user_id": 2, "day": "Monday", "available": False},
        {"user_id": 1, "day": "Tuesday", "available": True}
    ]
