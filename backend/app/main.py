from datetime import date, timedelta
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from app.api import admin, auth, availability, onboarding, roster, users, workplace
from app.auth_utils import hash_password
from app.db.base import Base
from app.db.session import engine
import app.models

Base.metadata.create_all(bind=engine)


def get_cors_origins() -> list[str]:
    # Comma-separated list, e.g. "https://demo.example.com,https://staging.example.com"
    raw = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    if not raw:
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    return origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


with engine.begin() as connection:
    inspector = inspect(connection)
    user_columns = {column["name"] for column in inspector.get_columns("user")}
    shift_columns = {column["name"] for column in inspector.get_columns("shift")}
    availability_columns = {column["name"] for column in inspector.get_columns("availability")}
    assignment_columns = {column["name"] for column in inspector.get_columns("shift_assignment")}
    workplace_columns = {column["name"] for column in inspector.get_columns("workplace")}

    if "min_hours" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN min_hours FLOAT NOT NULL DEFAULT 0')
        )
    if "max_hours" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN max_hours FLOAT NOT NULL DEFAULT 40')
        )
    if "min_shifts_per_week" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN min_shifts_per_week INTEGER')
        )
        connection.execute(
            text('UPDATE "user" SET min_shifts_per_week = 1 WHERE min_shifts_per_week IS NULL')
        )
        connection.execute(
            text('ALTER TABLE "user" ALTER COLUMN min_shifts_per_week SET DEFAULT 1')
        )
        connection.execute(
            text('ALTER TABLE "user" ALTER COLUMN min_shifts_per_week SET NOT NULL')
        )
    if "max_shifts_per_week" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN max_shifts_per_week INTEGER')
        )
        connection.execute(
            text('UPDATE "user" SET max_shifts_per_week = 7 WHERE max_shifts_per_week IS NULL')
        )
        connection.execute(
            text('ALTER TABLE "user" ALTER COLUMN max_shifts_per_week SET DEFAULT 7')
        )
        connection.execute(
            text('ALTER TABLE "user" ALTER COLUMN max_shifts_per_week SET NOT NULL')
        )
    if "role" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN role VARCHAR NOT NULL DEFAULT \'staff\'')
        )
    if "password_hash" not in user_columns:
        default_password = os.getenv("DEFAULT_USER_PASSWORD", "ChangeMe123!")
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN password_hash VARCHAR')
        )
        connection.execute(
            text('UPDATE "user" SET password_hash = :password_hash WHERE password_hash IS NULL OR password_hash = \'\''),
            {"password_hash": hash_password(default_password)},
        )
        connection.execute(
            text('ALTER TABLE "user" ALTER COLUMN password_hash SET NOT NULL')
        )
    if "is_active" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE')
        )
    if "workplace_id" not in user_columns:
        connection.execute(
            text('ALTER TABLE "user" ADD COLUMN workplace_id INTEGER')
        )

    if "min_staff_per_shift" not in workplace_columns:
        connection.execute(
            text('ALTER TABLE "workplace" ADD COLUMN min_staff_per_shift INTEGER')
        )
        connection.execute(
            text('UPDATE "workplace" SET min_staff_per_shift = 2 WHERE min_staff_per_shift IS NULL')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN min_staff_per_shift SET DEFAULT 2')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN min_staff_per_shift SET NOT NULL')
        )
    if "min_managers_per_hour" not in workplace_columns:
        connection.execute(
            text('ALTER TABLE "workplace" ADD COLUMN min_managers_per_hour INTEGER')
        )
        connection.execute(
            text('UPDATE "workplace" SET min_managers_per_hour = 1 WHERE min_managers_per_hour IS NULL')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN min_managers_per_hour SET DEFAULT 1')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN min_managers_per_hour SET NOT NULL')
        )
    if "max_consecutive_shifts" not in workplace_columns:
        connection.execute(
            text('ALTER TABLE "workplace" ADD COLUMN max_consecutive_shifts INTEGER')
        )
        connection.execute(
            text('UPDATE "workplace" SET max_consecutive_shifts = 5 WHERE max_consecutive_shifts IS NULL')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN max_consecutive_shifts SET DEFAULT 5')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN max_consecutive_shifts SET NOT NULL')
        )
    if "min_hours_between_shifts" not in workplace_columns:
        connection.execute(
            text('ALTER TABLE "workplace" ADD COLUMN min_hours_between_shifts INTEGER')
        )
        connection.execute(
            text('UPDATE "workplace" SET min_hours_between_shifts = 11 WHERE min_hours_between_shifts IS NULL')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN min_hours_between_shifts SET DEFAULT 11')
        )
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN min_hours_between_shifts SET NOT NULL')
        )
    if "min_hours_between_shifts" in workplace_columns:
        connection.execute(
            text('ALTER TABLE "workplace" ALTER COLUMN min_hours_between_shifts SET DEFAULT 11')
        )

    default_workplace_row = connection.execute(
        text('SELECT id FROM workplace ORDER BY id LIMIT 1')
    ).fetchone()
    default_workplace_id = default_workplace_row[0] if default_workplace_row else None

    users_without_workplace = connection.execute(
        text('SELECT COUNT(*) FROM "user" WHERE workplace_id IS NULL')
    ).scalar_one()
    if users_without_workplace > 0:
        if default_workplace_id is None:
            connection.execute(
                text('INSERT INTO workplace (name) VALUES (:name)'),
                {"name": "Default Workplace"},
            )
            default_workplace_id = connection.execute(
                text('SELECT id FROM workplace ORDER BY id LIMIT 1')
            ).scalar_one()
        connection.execute(
            text('UPDATE "user" SET workplace_id = :workplace_id WHERE workplace_id IS NULL'),
            {"workplace_id": default_workplace_id},
        )

    remaining_user_nulls = connection.execute(
        text('SELECT COUNT(*) FROM "user" WHERE workplace_id IS NULL')
    ).scalar_one()
    if remaining_user_nulls == 0:
        connection.execute(
            text('ALTER TABLE "user" ALTER COLUMN workplace_id SET NOT NULL')
        )

    if "workplace_id" not in availability_columns:
        connection.execute(
            text('ALTER TABLE "availability" ADD COLUMN workplace_id INTEGER')
        )

    connection.execute(
        text(
            'UPDATE "availability" a '
            'SET workplace_id = u.workplace_id '
            'FROM "user" u '
            'WHERE a.user_id = u.id AND a.workplace_id IS NULL'
        )
    )
    if default_workplace_id is not None:
        connection.execute(
            text('UPDATE "availability" SET workplace_id = :workplace_id WHERE workplace_id IS NULL'),
            {"workplace_id": default_workplace_id},
        )
    remaining_availability_nulls = connection.execute(
        text('SELECT COUNT(*) FROM "availability" WHERE workplace_id IS NULL')
    ).scalar_one()
    if remaining_availability_nulls == 0:
        connection.execute(
            text('ALTER TABLE "availability" ALTER COLUMN workplace_id SET NOT NULL')
        )

    if "workplace_id" not in shift_columns:
        connection.execute(
            text('ALTER TABLE "shift" ADD COLUMN workplace_id INTEGER')
        )

    connection.execute(
        text(
            'UPDATE "shift" s '
            'SET workplace_id = source.workplace_id '
            'FROM ('
            '  SELECT sa.shift_id AS shift_id, MIN(u.workplace_id) AS workplace_id '
            '  FROM shift_assignment sa '
            '  JOIN "user" u ON sa.user_id = u.id '
            '  GROUP BY sa.shift_id'
            ') AS source '
            'WHERE s.id = source.shift_id AND s.workplace_id IS NULL'
        )
    )
    if default_workplace_id is not None:
        connection.execute(
            text('UPDATE "shift" SET workplace_id = :workplace_id WHERE workplace_id IS NULL'),
            {"workplace_id": default_workplace_id},
        )

    if "week_start_date" not in shift_columns:
        connection.execute(
            text('ALTER TABLE "shift" ADD COLUMN week_start_date DATE')
        )
        current_week_start = date.today() - timedelta(days=date.today().weekday())
        connection.execute(
            text('UPDATE "shift" SET week_start_date = :week_start_date WHERE week_start_date IS NULL'),
            {"week_start_date": current_week_start.isoformat()},
        )
        connection.execute(
            text('ALTER TABLE "shift" ALTER COLUMN week_start_date SET NOT NULL')
        )

    remaining_shift_nulls = connection.execute(
        text('SELECT COUNT(*) FROM "shift" WHERE workplace_id IS NULL')
    ).scalar_one()
    if remaining_shift_nulls == 0:
        connection.execute(
            text('ALTER TABLE "shift" ALTER COLUMN workplace_id SET NOT NULL')
        )

    if "workplace_id" not in assignment_columns:
        connection.execute(
            text('ALTER TABLE "shift_assignment" ADD COLUMN workplace_id INTEGER')
        )

    connection.execute(
        text(
            'UPDATE "shift_assignment" sa '
            'SET workplace_id = s.workplace_id '
            'FROM "shift" s '
            'WHERE sa.shift_id = s.id AND sa.workplace_id IS NULL'
        )
    )
    connection.execute(
        text(
            'UPDATE "shift_assignment" sa '
            'SET workplace_id = u.workplace_id '
            'FROM "user" u '
            'WHERE sa.user_id = u.id AND sa.workplace_id IS NULL'
        )
    )
    if default_workplace_id is not None:
        connection.execute(
            text('UPDATE "shift_assignment" SET workplace_id = :workplace_id WHERE workplace_id IS NULL'),
            {"workplace_id": default_workplace_id},
        )
    remaining_assignment_nulls = connection.execute(
        text('SELECT COUNT(*) FROM "shift_assignment" WHERE workplace_id IS NULL')
    ).scalar_one()
    if remaining_assignment_nulls == 0:
        connection.execute(
            text('ALTER TABLE "shift_assignment" ALTER COLUMN workplace_id SET NOT NULL')
        )


app = FastAPI()
cors_origins = get_cors_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(onboarding.router)
app.include_router(users.router)
app.include_router(availability.router)
app.include_router(roster.router)
app.include_router(auth.router)
app.include_router(workplace.router)
app.include_router(admin.router)


@app.get("/")
def root():
    return {"message": "Rostering system backend running"}
