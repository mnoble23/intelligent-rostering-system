# intelligent-rostering-system
Full-stack web application for generating optimized staff rosters based on availability and workplace constraints using Python, PostgreSQL, and React.

## Tech Stack
- **Backend:** Python, FastAPI
- **Frontend:** React + TypeScript
- **Database:** PostgreSQL
- **Authentication:** JWT bearer tokens
- **Deployment:** Docker (local `docker-compose` supported)

## Project Overview
This system allows workplaces to:
- Create an initial manager account with first-run onboarding
- Add and manage staff users
- Submit weekly availability
- Generate rosters for one or more weeks
- Manually adjust assignments
- View shift coverage and understaffed time slots
- Configure workplace-level staffing constraints

## Project Status
Work in progress.

## Live Demo
- Frontend URL: `https://intelligent-rostering-system.vercel.app/`
- Backend URL: `https://intelligent-rostering-system.onrender.com`

### Demo Credentials
- Manager: `demo_manager` / `Manager123!`
- Staff: `demo_staff_1` / `Staff123!`

### Demo Notes
- Frontend may take 30-60 seconds to wake up on first load due to free-tier hosting.
- Demo data resets nightly at 05:00 Irish Time.
- `/admin/reset-demo` is protected and only works when the backend runs with `APP_ENV=demo`, a configured `DEMO_RESET_KEY`, and an `X-Reset-Key` request header.

### Quick Test Flow
1. Sign in as `demo_manager`.
2. Open **Roster Dashboard**.
3. Go to **Generate Roster** and generate for the selected week.
4. Open **Manage Shifts** and make one assignment change.
5. Sign out and verify the staff view with `demo_staff_1`.

## How To Run
Choose one of the two options below.

### 1. Clone Repo
```bash
git clone https://github.com/mnoble23/intelligent-rostering-system
cd intelligent-rostering-system
```

### Option A: Run with Docker (recommended)
```bash
docker compose up --build
```

Frontend: `http://localhost:3000`  
Backend: `http://127.0.0.1:8000`

To fully reset local Docker data:
```bash
docker compose down -v
docker compose up --build
```

### Option B: Run manually (without Docker)

#### 1. Configure backend env
Create `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg2://<username>:<password>@<host>:<port>/<database_name>
JWT_SECRET_KEY=change-me-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
DEFAULT_USER_PASSWORD=ChangeMe123!
```

Optional demo-only variables:

```env
APP_ENV=demo
DEMO_RESET_KEY=<secret-value>
DEMO_WORKPLACE_NAME=Demo Company
DEMO_MANAGER_PASSWORD=Manager123!
DEMO_STAFF_PASSWORD=Staff123!
```

#### 2. Start backend (FastAPI)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend: `http://127.0.0.1:8000`

#### 3. Start frontend (React)
In a second terminal:

```bash
cd frontend
npm install
npm start
```

Frontend: `http://localhost:3000`

### Use the app
- Open `http://localhost:3000`.
- If no users exist yet, run onboarding to create the first workplace + manager.
- Add staff users and their availability.
- Generate a roster from the UI.
- Review coverage and optionally adjust assignments manually.

### Troubleshooting (Docker)
- If ports `3000`, `8000`, or `5432` are already in use, stop conflicting processes/containers and rerun:

```bash
docker compose up --build
```

## Currently Implemented
- JWT login (`/auth/login`) and current-user endpoint (`/auth/me`)
- First-run onboarding flow (`/onboarding/status`, `/onboarding/create-workplace`)
- Role-based access (`manager`/`staff`) with protected routes
- Workplace isolation across users, availability, shifts, and assignments
- User CRUD (manager-controlled) with min/max hours and min/max shifts per week
- Availability submission (single and bulk) with overlap validation
- Weekly roster generation for up to 52 weeks in one request
- Manual assignment and unassignment endpoints
- Shift coverage endpoint for understaffing visibility
- Workplace constraints endpoints for staffing rules
- React frontend pages for dashboard, roster generation, assignment management, profile, and coverage
- Dockerized local stack for frontend, backend, and PostgreSQL
- Backend tests for route security and workplace isolation

## Next Steps
- Add DB-level uniqueness/index constraints for stronger tenant safety and performance
- Expand automated test coverage for scheduling edge cases and multi-week generation behavior
- Improve UX for availability entry (faster editing, fewer repetitive inputs)
- Add richer scheduler failure explanations when constraints cannot be satisfied
- Continue evolving fairness objectives (weekends/nights/load balancing)

## Roster Generation and Constraints
Current scheduler behavior:
- Generates weekly shifts within business hours (`06:00`-`22:00`)
- Builds assignable shifts from submitted availability
- Applies workplace-level constraints:
  - `min_staff_per_shift`
  - `min_managers_per_hour`
  - `max_consecutive_shifts`
  - `min_hours_between_shifts`
- Respects user-level limits:
  - `min_hours` / `max_hours`
  - `min_shifts_per_week` / `max_shifts_per_week`

## Potential Future Upgrades
- Configurable business operating hours from the UI
- Shift-length customization by workplace
- Shift swap workflows
- Break scheduling
- Holidays/time-off integration
- Skill-based coverage rules
- Preference-aware optimization
- Constraint-programming style optimization for better global fairness

## License
This project is licensed under the MIT License.
