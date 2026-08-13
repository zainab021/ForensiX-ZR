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
- SQLite
- JWT Authentication
- Passlib bcrypt

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
│   ├── uploads/
│   ├── forensix.db
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
uvicorn app.main:app --reload

 Backend runs at:

http://127.0.0.1:8000

Swagger Docs:

http://127.0.0.1:8000/docs
Frontend Setup

Open the frontend with VS Code Live Server:

frontend/index.html
Demo Accounts
Officer
Username: officer
Password: officer123
Admin
Username: admin
Password: admin123
Citizen
Username: citizen
Password: citizen123
Screenshots
Authorized Dashboard

Add screenshot here

Reports Management

Add screenshot here

Case Details

Add screenshot here

Evidence Vault

Add screenshot here

Citizen Dashboard

Add screenshot here

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

# 👩‍💻 Team
**ForensiX ZR Unit Development Team**
- Zainab
- Raiha

## License
This project is developed for educational and portfolio purposes.
