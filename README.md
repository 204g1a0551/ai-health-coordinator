# AI Health Checkup & Appointment Coordinator

A modern healthcare web application featuring a clean two-column layout:
- **Left Column**: Healthcare Dashboard displaying patient profile, reported symptoms, suggested medical department, available doctors, available time slots, and appointment summary.
- **Right Column**: AI Chat Assistant communicating with a FastAPI backend to coordinate patient inquiries.

---

## Project Structure

```
ai-health-coordinator/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── chat.py          # Chat request/response schemas
│   │   │   └── dashboard.py     # Patient, symptom, doctor, slot schemas
│   │   ├── routers/
│   │   │   ├── chat.py          # POST /api/chat
│   │   │   └── dashboard.py     # GET /api/dashboard
│   │   ├── __init__.py
│   │   └── main.py              # FastAPI app with CORS middleware
│   ├── requirements.txt         # FastAPI, Uvicorn, Pydantic
│   └── run.py                   # Python server launcher
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── components/
│   │   │   │   ├── dashboard/   # Healthcare dashboard component
│   │   │   │   └── chat/        # AI chat assistant component
│   │   │   ├── models/          # TypeScript interfaces
│   │   │   ├── services/        # ChatService & DashboardService
│   │   │   ├── app.ts / app.html / app.css
│   │   │   └── app.config.ts    # provideHttpClient configuration
│   └── package.json
├── .gitignore
└── README.md
```

---

## Quick Start

### 1. Backend (FastAPI)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```
Backend runs on: `http://127.0.0.1:8000`  
API Docs (Swagger): `http://127.0.0.1:8000/docs`

### 2. Frontend (Angular)

```bash
cd frontend
npm install
npm start
```
Frontend runs on: `http://localhost:4200`
