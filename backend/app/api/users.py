from fastapi import APIRouter

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/")
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
