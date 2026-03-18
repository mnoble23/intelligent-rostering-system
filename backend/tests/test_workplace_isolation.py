import pathlib
import sys
from datetime import date, time

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from app.api import auth, availability, roster, users, workplace
from app.auth_utils import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.models.availability_db import AvailabilityDB
from app.models.shift_assignment_db import ShiftAssignmentDB
from app.models.shift_db import ShiftDB
from app.models.user_db import UserDB
from app.models.workplace_db import WorkplaceDB


def _build_test_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    app = FastAPI()
    app.include_router(users.router)
    app.include_router(availability.router)
    app.include_router(roster.router)
    app.include_router(auth.router)
    app.include_router(workplace.router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def _seed_two_workplaces(session: Session):
    workplace_a = WorkplaceDB(name="Workplace A")
    workplace_b = WorkplaceDB(name="Workplace B")
    session.add_all([workplace_a, workplace_b])
    session.flush()

    manager_a = UserDB(
        name="manager_a",
        role="manager",
        min_hours=0,
        max_hours=40,
        password_hash=hash_password("ManagerA123!"),
        is_active=True,
        workplace_id=workplace_a.id,
    )
    staff_a = UserDB(
        name="staff_a",
        role="staff",
        min_hours=0,
        max_hours=40,
        password_hash=hash_password("StaffA123!"),
        is_active=True,
        workplace_id=workplace_a.id,
    )
    manager_b = UserDB(
        name="manager_b",
        role="manager",
        min_hours=0,
        max_hours=40,
        password_hash=hash_password("ManagerB123!"),
        is_active=True,
        workplace_id=workplace_b.id,
    )
    staff_b = UserDB(
        name="staff_b",
        role="staff",
        min_hours=0,
        max_hours=40,
        password_hash=hash_password("StaffB123!"),
        is_active=True,
        workplace_id=workplace_b.id,
    )

    session.add_all([manager_a, staff_a, manager_b, staff_b])
    session.commit()

    return {
        "workplace_a": workplace_a,
        "workplace_b": workplace_b,
        "manager_a": manager_a,
        "staff_a": staff_a,
        "manager_b": manager_b,
        "staff_b": staff_b,
    }


def _login(client: TestClient, name: str, password: str) -> str:
    response = client.post("/auth/login", json={"name": name, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_users_endpoint_is_isolated_by_workplace():
    client, SessionLocal = _build_test_client()

    with SessionLocal() as session:
        seeded = _seed_two_workplaces(session)

    manager_a_token = _login(client, "manager_a", "ManagerA123!")

    list_response = client.get(
        "/users/",
        headers={"Authorization": f"Bearer {manager_a_token}"},
    )
    assert list_response.status_code == 200
    names = {user["name"] for user in list_response.json()}
    assert names == {"manager_a", "staff_a"}
    assert "manager_b" not in names

    delete_response = client.delete(
        f"/users/{seeded['staff_b'].id}",
        headers={"Authorization": f"Bearer {manager_a_token}"},
    )
    assert delete_response.status_code == 404


def test_availability_endpoint_blocks_cross_workplace_user_ids():
    client, SessionLocal = _build_test_client()

    with SessionLocal() as session:
        seeded = _seed_two_workplaces(session)

    manager_a_token = _login(client, "manager_a", "ManagerA123!")

    response = client.post(
        "/availability/",
        headers={"Authorization": f"Bearer {manager_a_token}"},
        json={
            "user_id": seeded["staff_b"].id,
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "12:00:00",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found in your workplace"


def test_availability_bulk_rejects_submission_when_user_cannot_reach_minimum_hours():
    client, SessionLocal = _build_test_client()

    with SessionLocal() as session:
        seeded = _seed_two_workplaces(session)
        seeded["workplace_a"].business_start_hour = 9
        seeded["workplace_a"].business_end_hour = 13
        seeded["workplace_a"].max_consecutive_shifts = 7
        seeded["workplace_a"].min_hours_between_shifts = 11
        seeded["staff_a"].min_hours = 10
        session.commit()

    manager_a_token = _login(client, "manager_a", "ManagerA123!")

    response = client.post(
        "/availability/bulk",
        headers={"Authorization": f"Bearer {manager_a_token}"},
        json={
            "availabilities": [
                {
                    "user_id": seeded["staff_a"].id,
                    "day_of_week": 0,
                    "start_time": "09:00:00",
                    "end_time": "13:00:00",
                }
            ]
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "min_hours_unreachable_on_submission"
    assert detail["context"]["user_id"] == seeded["staff_a"].id
    assert detail["context"]["user_name"] == "staff_a"
    assert detail["context"]["required_hours"] == 10.0
    assert detail["context"]["possible_hours"] == 4.0


def test_roster_endpoints_are_isolated_by_workplace():
    client, SessionLocal = _build_test_client()

    week_start = date(2026, 1, 5)

    with SessionLocal() as session:
        seeded = _seed_two_workplaces(session)

        shift_a = ShiftDB(
            workplace_id=seeded["workplace_a"].id,
            week_start_date=week_start,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(13, 0),
        )
        shift_b = ShiftDB(
            workplace_id=seeded["workplace_b"].id,
            week_start_date=week_start,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(14, 0),
        )
        session.add_all([shift_a, shift_b])
        session.flush()

        session.add_all(
            [
                ShiftAssignmentDB(
                    shift_id=shift_a.id,
                    user_id=seeded["staff_a"].id,
                    workplace_id=seeded["workplace_a"].id,
                ),
                ShiftAssignmentDB(
                    shift_id=shift_b.id,
                    user_id=seeded["staff_b"].id,
                    workplace_id=seeded["workplace_b"].id,
                ),
            ]
        )
        session.commit()

    manager_a_token = _login(client, "manager_a", "ManagerA123!")

    roster_response = client.get(
        "/roster/",
        params={"week_start_date": week_start.isoformat()},
        headers={"Authorization": f"Bearer {manager_a_token}"},
    )
    assert roster_response.status_code == 200
    roster_rows = roster_response.json()
    assert len(roster_rows) == 1
    assert roster_rows[0]["staff"] == [{"id": seeded["staff_a"].id, "name": "staff_a"}]

    cross_assign_response = client.post(
        "/roster/assign",
        headers={"Authorization": f"Bearer {manager_a_token}"},
        json={"shift_id": shift_b.id, "user_id": seeded["staff_a"].id},
    )
    assert cross_assign_response.status_code == 404
    assert cross_assign_response.json()["detail"] == "Shift not found"


def test_auth_rejects_token_with_mismatched_workplace_claim():
    client, SessionLocal = _build_test_client()

    with SessionLocal() as session:
        seeded = _seed_two_workplaces(session)

    bad_token = create_access_token(
        user_id=seeded["manager_a"].id,
        role="manager",
        workplace_id=seeded["workplace_b"].id,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {bad_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Token workplace mismatch"


def test_workplace_constraints_can_be_read_and_updated_by_manager():
    client, SessionLocal = _build_test_client()

    with SessionLocal() as session:
        _seed_two_workplaces(session)

    manager_a_token = _login(client, "manager_a", "ManagerA123!")

    get_response = client.get(
        "/workplace/constraints",
        headers={"Authorization": f"Bearer {manager_a_token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["min_staff_per_shift"] == 2
    assert get_response.json()["min_managers_per_hour"] == 1
    assert get_response.json()["max_consecutive_shifts"] == 7
    assert get_response.json()["min_hours_between_shifts"] == 11

    put_response = client.put(
        "/workplace/constraints",
        headers={"Authorization": f"Bearer {manager_a_token}"},
        json={
            "min_staff_per_shift": 3,
            "min_managers_per_hour": 1,
            "max_consecutive_shifts": 4,
            "min_hours_between_shifts": 12,
            "business_start_hour": 6,
            "business_end_hour": 22,
        },
    )
    assert put_response.status_code == 200
    assert put_response.json()["min_staff_per_shift"] == 3
    assert put_response.json()["min_managers_per_hour"] == 1
    assert put_response.json()["max_consecutive_shifts"] == 4
    assert put_response.json()["min_hours_between_shifts"] == 12


def test_workplace_constraints_reject_invalid_manager_requirements():
    client, SessionLocal = _build_test_client()

    with SessionLocal() as session:
        _seed_two_workplaces(session)

    manager_a_token = _login(client, "manager_a", "ManagerA123!")
    bad_update = client.put(
        "/workplace/constraints",
        headers={"Authorization": f"Bearer {manager_a_token}"},
        json={
            "min_staff_per_shift": 1,
            "min_managers_per_hour": 2,
            "max_consecutive_shifts": 5,
            "min_hours_between_shifts": 11,
            "business_start_hour": 6,
            "business_end_hour": 22,
        },
    )
    assert bad_update.status_code == 400
    assert bad_update.json()["detail"] == "min_managers_per_hour cannot exceed min_staff_per_shift"
