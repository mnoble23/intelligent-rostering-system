from fastapi import APIRouter

router = APIRouter(
    prefix="/roster",
    tags=["Roster"]
)

@router.get("/")
def get_roster():
    return [
        {
            "user_id": 1,
            "week": "2026-02-03",
            "shifts": [
                {"day": "Monday", "hours": ["09:00-12:00", "14:00-18:00"]}
            ]
        }
    ]
