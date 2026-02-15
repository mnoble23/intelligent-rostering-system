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

## Currently Implemented
- FastAPI backend initialised
- Modular backend folder structure
- Availability validation checks
- Endpoints to post availability entries (single and multiple)
- Implemented initial roster generation logic (very basic so far)
- Database now fully integrated
- Connected React frontend with backend

## Next Steps
- Add features to React app so that a user can submit availability and generate rosters
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
- Maximum hours of work for each user
- At least 1 manager on shift at any time

## License
This project is licensed under the MIT License.

