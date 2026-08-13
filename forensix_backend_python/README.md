ForensiX ZR Unit — Secure Crime Analysis System

A modern role-based crime analysis and incident management system designed for secure digital reporting, investigation tracking, evidence management, and officer collaboration.

ForensiX ZR Unit provides separate interfaces for citizens and authorized law enforcement personnel, enabling secure workflows for crime reporting, case conversion, investigation monitoring, and forensic evidence handling.

🚀 Features
🔐 Authentication & Security
JWT-based authentication
Role-based access control
Secure password hashing with bcrypt
Protected frontend routes
Officer code verification for authorized accounts
Secure case deletion with password confirmation
Activity logging for major actions
👥 User Roles
👤 Citizen
Submit crime reports
Upload evidence files
Track submitted reports
View alerts and notifications
Manage profile
🛡️ Officer/Admin
View and manage reports
Convert reports into investigation cases
Assign officers to cases
Manage evidence
View activity logs
Create notifications
Monitor dashboards and analytics
🧩 Core Modules
📊 Dashboard
Real-time statistics
Live activity feed
Crime category visualization
Investigation overview
📁 Reports Management
Real citizen reports
Status management
Report detail panel
Officer assignment workflow
Report-to-case conversion
Duplicate conversion prevention
🕵️ Case Management
Real backend-connected cases
Officer assignment
Case detail pages
Linked evidence display
Secure delete workflow
PKT timestamp formatting
🧾 Evidence Vault
Evidence upload system
Case-linked evidence
Report-linked evidence
File preview/open support
PDF/Image handling
🔔 Notifications
Role-targeted notifications
Citizen alerts
Officer announcements
Real-time notification display
📜 Activity Logs

Tracks:

Login actions
Report creation
Case creation
Evidence uploads
Status updates
Secure deletions
🛠️ Tech Stack
Frontend
HTML5
CSS3
Vanilla JavaScript (IIFE Architecture)
Font Awesome
Chart.js
Leaflet.js
Backend
FastAPI
SQLAlchemy
SQLite
JWT Authentication
Passlib (bcrypt)
🔒 Security Features
JWT Token Authentication
Role-Based Route Protection
Secure Password Verification
Protected API Endpoints
Backend Password Validation
Secure Case Delete Confirmation
Activity Logging System
📂 Project Structure
project/
│
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
│   │
│   ├── uploads/
│   ├── forensix.db
│   └── requirements.txt
│
└── README.md
⚙️ Installation
1️⃣ Clone Repository
git clone <your-repository-url>
cd project
🖥️ Backend Setup
Create Virtual Environment
python -m venv venv
Activate Environment
Windows
venv\Scripts\activate
Install Dependencies
pip install -r requirements.txt
Start Backend
uvicorn app.main:app --reload

Backend runs at:

http://127.0.0.1:8000

Swagger Docs:

http://127.0.0.1:8000/docs
🌐 Frontend Setup

Run frontend using VS Code Live Server or any static server.

Open:

frontend/index.html
🔑 Demo Accounts
👮 Officer
Username: officer
Password: officer123
🛡️ Admin
Username: admin
Password: admin123
👤 Citizen
Username: citizen
Password: citizen123
📸 Screenshots
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

🔄 Main Workflows
Report → Case Workflow
Citizen Report
      ↓
Officer Review
      ↓
Assign Officer
      ↓
Convert to Case
      ↓
Evidence Linking
      ↓
Investigation Tracking
📈 Highlights
Real backend-connected workflows
Professional role separation
Secure investigation handling
Real activity tracking
Dynamic report/case management
PKT time formatting support
Responsive professional UI
🚀 Future Enhancements
Real-time socket notifications
Advanced analytics dashboard
AI-assisted crime pattern analysis
GIS crime heatmaps
Role management system
Mobile responsive optimization
Cloud database deployment
👩‍💻 Author

Zainab
BS Artificial Intelligence Student
University of Management and Technology (UMT)

📄 License

This project is developed for educational and portfolio purposes.