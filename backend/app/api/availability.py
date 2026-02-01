from fastapi import APIRouter
from app.models.availability import Availability

router = APIRouter(
    prefix="/availability",
    tags=["Availability"]
)


@router.get("/")
def get_availability():
    return [
        {"user_id": 1, "day_of_week": 0, "start_time": "09:00", "end_time": "12:00"},
        {"user_id": 2, "day_of_week": 0, "start_time": "08:00", "end_time": "16:00"}
    ]


@router.post("/")
def create_availability(availability: Availability):
    return {
        "message": "Availability received",
        "availability": availability
    }
