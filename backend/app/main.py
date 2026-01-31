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
        {"user_id": 1, "day": "Monday", "available_hours": ["09:00-12:00", "14:00-18:00"]},
        {"user_id": 2, "day": "Monday", "available_hours": ["08:00-16:00"]},
        {"user_id": 1, "day": "Tuesday", "available_hours": ["09:00-12:00"]}
    ]
