# ForensiX ZR Unit — Secure Crime Analysis System

A modern role-based crime analysis and incident management system designed for secure digital reporting, investigation tracking, evidence management, and officer collaboration.

## Features

### Authentication & Security
- JWT-based authentication
- Role-based access control
- Secure password hashing with bcrypt
- Protected frontend routes
- Officer code verification
- Secure case deletion with password confirmation
- Activity logging for major actions

### User Roles

#### Citizen
- Submit crime reports
- Upload evidence files
- Track submitted reports
- View alerts and notifications
- Manage profile

#### Officer/Admin
- View and manage reports
- Convert reports into investigation cases
- Assign officers to cases
- Manage evidence
- View activity logs
- Create notifications
- Monitor dashboards and analytics

## Tech Stack

### Frontend
- HTML5
- CSS3
- Vanilla JavaScript
- Font Awesome
- Chart.js
- Leaflet.js

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL (SQLite fallback for local dev)
- Alembic migrations
- JWT Authentication
- Passlib bcrypt
- Pytest

## Project Structure

```bash
project/
├── frontend/
│   ├── authorized/
│   ├── unauthorized/
│   ├── css/
│   ├── js/
│   └── index.html
│
├── forensix_backend_python/
│   ├── app/
│   │   ├── models/
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── utils/
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── uploads/
│   └── requirements.txt
│
└── README.md
```
## Installation
## Backend Setup
cd forensix_backend_python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then edit values, see Environment Variables below
uvicorn app.main:app --reload

 Backend runs at:

http://127.0.0.1:8000

Swagger Docs:

http://127.0.0.1:8000/docs

Running Tests

cd forensix_backend_python
pip install -r requirements.txt
pytest

Running with Docker (backend + PostgreSQL + frontend)

docker compose up --build

This starts a PostgreSQL container, the FastAPI backend (migrated automatically via `Base.metadata.create_all`, or run `alembic upgrade head` inside the backend container for a migration-driven schema), and an nginx-served frontend at http://localhost:5500.

Frontend Setup

Open the frontend with VS Code Live Server:

frontend/index.html

Update `frontend/js/config.js` if your backend isn't running at `http://127.0.0.1:8000`.

Demo Accounts

When `SEED_DEMO_USERS=true` (the default for local dev), these accounts are auto-created on backend startup:

Officer
Username: officer
Password: officer123
Admin
Username: admin
Password: admin123
Citizen
Username: citizen
Password: citizen123

Set `SEED_DEMO_USERS=false` before deploying to production.
Screenshots

Screenshots are not yet included in this README — add them under a `screenshots/` folder and link them here once captured from a running instance.

## Environment Variables

Copy `forensix_backend_python/.env.example` to `forensix_backend_python/.env` and configure:

| Variable | Purpose | Production value |
|---|---|---|
| `SECRET_KEY` | JWT signing secret | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` — never reuse the example value |
| `DATABASE_URL` | Database connection string | `postgresql://user:pass@host:5432/forensix_db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime | Tune to your session policy |
| `VALID_OFFICER_CODES` | Comma-separated valid officer/admin registration codes | Your real internal codes |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | Your real frontend domain(s), no trailing slash |
| `ALLOWED_HOSTS` | Comma-separated allowed `Host` header values | Your real backend domain(s), not `*` |
| `SEED_DEMO_USERS` | Auto-create demo admin/officer/citizen accounts on startup | `false` |

The frontend's backend URL is set separately in `frontend/js/config.js` (`window.FORENSIX_API_BASE`) — update it to point at your deployed backend.

## Production Checklist

- [ ] Set a real, randomly generated `SECRET_KEY`
- [ ] Point `DATABASE_URL` at a PostgreSQL instance and run `alembic upgrade head`
- [ ] Set `SEED_DEMO_USERS=false` (demo accounts use known weak passwords)
- [ ] Set `CORS_ORIGINS` and `ALLOWED_HOSTS` to your real domain(s)
- [ ] Update `frontend/js/config.js` to point at the deployed backend URL
- [ ] Run the backend test suite (`pytest`) before deploying

## 🔄 Main Workflow
Citizen Report → Officer Review → Assign Officer → Convert to Case → Evidence Linking → Investigation Tracking

## Highlights
Real backend-connected workflows
Professional role separation
Secure investigation handling
Real activity tracking
Dynamic report and case management
PKT timestamp formatting
Professional dashboard interface

## Future Enhancements
Real-time socket notifications
Advanced analytics dashboard
AI-assisted crime pattern analysis
GIS crime heatmaps
Role management system
Cloud database deployment

## Author
Zainab
BS Artificial Intelligence Student
University of Management and Technology

## License
This project is developed for educational and portfolio purposes.
