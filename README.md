# intelligent-rostering-system
Full-stack web application for generating optimised staff rosters based on availability and constraints using Python, PostgreSQL, and React.

## Tech Stack
- **Backend:** Python, FastAPI 
- **Frontend:** React
- **Database:** PostgreSQL 
- **Authentication:** JWT 
- **Deployment:** Docker (local docker-compose setup available)

## Project Overview
This system will allow staff to submit their availability and will generate rosters based on these availabilities and some other constraints to optimise the rosters.
Key features include:
- User availability submission
- Manual shift management
- Automatic roster generation
- Scheduling logic based on additional constraints
- Web-based dashboard for roster visualisation

## Project Status
Work in progress.

## How To Run

Choose one of the two options below.

### 1. Clone Repo
```bash
git clone https://github.com/mnoble23/intelligent-rostering-syst
cd intelligent-rostering-system
```

### Option A: Run with Docker (recommended)
```bash
docker compose up --build
```

Frontend runs at: `http://localhost:3000`  
Backend runs at: `http://127.0.0.1:8000`

To reset local docker data:
```bash
docker compose down -v
docker compose up --build
```

### Option B: Run manually (without Docker)

#### 1. Configure Backend with Database
Create a `.env` file inside `backend/` and add your database connection string:

```env
DATABASE_URL=postgresql+psycopg2://<username>:<password>@<host>:<port>/<database_name>
```

#### 2. Backend Setup (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate 
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at: `http://127.0.0.1:8000`

#### 3. Start the Frontend (React)
In a second terminal:
```bash
cd frontend
npm install
npm start
```

Frontend runs at: `http://localhost:3000`

### Use the app
- Open `http://localhost:3000`
- Create a new workplace or sign in if already created
- Submit user availability
- Generate a roster from the UI
- View roster 

## Currently Implemented
- FastAPI backend initialised
- Modular backend folder structure
- Availability validation checks
- Endpoints to post availability entries (single and multiple)
- Implemented initial roster generation logic (very basic so far)
- Database now fully integrated
- Connected React frontend with backend
- Added features to React app so that a user can submit availability, generate rosters, manually manage shifts and more
- Simplistic but nice react app design for easy navigation and use
- Rosters can be generated for multiple weeks

## Next Steps
- Live demo with demo credentials
- Add DB-level uniqueness/index constraints for tenant safety and performance
- Add more cross-workplace regression tests around manager edge cases
- Small improvements needed to make things like submitting availability less tedious
- Subheadings for each page to separate things like roster generation and deletion from things like viewing 'My Profile' and 'My Roster' pages

## Roster Generation Info
**Current Version**
- Creates a weekly roster adhering to user availability
- No overlapping shifts for a user and only one shift per day
- Ensures a minimum 2 staff working at a time with at least 1 manager at any time
- Shifts can be 4, 6 or 9 hours long
- Business hours from 06:00 - 22:00

**Future Upgrades:**
- Maximum working days in a row
- Include a minimum rest period between shifts
- Add unit tests to ensure the roster is not violating any of the constraints

## Frontend Info and Plans
**Currently Implemented:** 
- Roster dashboard table to view full roster for the week
- Page for user submission of their name, availability, min and max hours, role
- Generate Roster button
- My Roster page to show a user their roster for the week
- Shift coverage page to see what times are understaffed
- Login + JWT auth with role-based access (manager/staff)
- First-run workplace onboarding flow for initial manager creation
- My profile page added for a user to look at their info such as submitted availability and assigned shifts and min and max hours per week
- React app has been updated with much nicer design and easier to navigate
- Manual shift management page can be used to manage shifts by selecting the employee and day to edit it

**Planned Improvements:**
- Small improvements needed to make things like submitting availability less tedious
- Subheadings for each page to separate things like roster generation and deletion from things like viewing 'My Profile' and 'My Roster' pages

## Potential Future Upgrades
- Allow for specific business operation times to be picked
- Allow minimum and maximum number of staff per shift to be picked (with specific choices for given times on given days)
- Scheduling breaks for each member of staff
- Specific shift lengths for a business could be input rather than just the 4, 6 or 9 hour blocks
- Allow for holidays to be put in so a user will not be included for that time period
- Better fairness objective with night/weekends/unpopular shifts/number of extra hours
- Skill based coverage
- Let users rank preferred times
- When roster generation fails, return exact reasons it has failed
- A lot of these changes may require a change in roster generation approach, it is currently using a greedy heuristics type of model but may need to be changed to a constraint programming type of model with scoring and penalties
- Shift swap feature

## License
This project is licensed under the MIT License.
