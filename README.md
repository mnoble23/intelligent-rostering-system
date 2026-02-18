# intelligent-rostering-system
Full-stack web application for generating optimised staff rosters based on availability and constraints using Python, PostgreSQL, and React.

## Tech Stack
- **Backend:** Python, FastAPI 
- **Frontend:** React
- **Database:** PostgreSQL 
- **Authentication:** JWT (planned)
- **Deployment:** Docker (planned)

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

### 1. Clone Repo
```bash
git clone https://github.com/mnoble23/intelligent-rostering-syst
cd intelligent-rostering-system
```

### 2. Configure Backend with Database
Create a `.env` file inside `backend/` and add your database connection string:

```env
DATABASE_URL=postgresql+psycopg2://<username>:<password>@<host>:<port>/<database_name>
```

### 3. Backend Setup (FastAPI)
```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate 
pip install -r requirements.txt
pip install python-dotenv
uvicorn app.main:app --reload
```

Backend runs at: `http://127.0.0.1:8000`

### 4. Start the Frontend (React)
In a second terminal:
```bash
cd frontend
npm install
npm start
```

Frontend runs at: `http://localhost:3000`

### 5. Use the app
- Open `http://localhost:3000`
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
- Added features to React app so that a user can submit availability and generate rosters

## Next Steps
- Continue with the planned improvements to the frontend which can be seen below
- Once frontend partially implemented, improve roster generation logic to adhere to all constraints (will be easier with better roster visualisation through frontend)
- Also must change logic to ensure that roster generation is never duplicating shifts or any other issues

## Roster Generation Info
**Constraints for initial version:**
- Will be a weekly roster
- Adhere to user availability
- No overlapping shifts for a user
- Minimum 2 staff working at a time
- Shifts between 4 - 9 hours long (currently only does it in 4 hour blocks)
- Business hours from 06:00 - 22:00

**Future Upgrades:**
- Fair distribution of shifts between users
- Maximum and minimum hours of work for each user
- At least 1 manager on shift at any time

## Frontend Info and Plans
**Currently Implemented:** 
- Simple roster table view of staffed shifts
- Page for user submission and their availability
- Generate Roster button
- Manual shift management
- My Roster page to show a user their roster for the week
- Changed roster table to a nicer design which is easier to read
- Shift coverage page to see what times are understaffed
- Manager and staff roles to determine what access they have in the app (at this point, you can just pick staff or manager without authentication)

**Planned Improvements:**
- Improve manual shift management to allow staff to have a custom shift start and end time
- Profile page showing availability and shifts for a user
- Upgrade user and availability submission form to update a user availability if already in the system
- React app design also needs to be much improved to be more user friendly and nicer on the eye

## Potential Future Upgrades
- Role based access control
- Allow for specific business operation times to be picked
- Allow minimum and maximum number of staff per shift to be picked (with specific choices for given times on given days)
- Scheduling breaks for each member of staff
- Specific shift lengths for a business could be input rather than just the 4 or 9 hour blocks

## License
This project is licensed under the MIT License.

