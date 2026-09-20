# 🩺 AI Health Checkup & Appointment Coordinator
### Autonomous Healthcare Multi-Agent System & Grounded Clinical Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Angular](https://img.shields.io/badge/Angular-17+-DD0031?style=for-the-badge&logo=angular&logoColor=white)](https://angular.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Redis](https://img.shields.io/badge/Redis-Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io)

An enterprise-grade, context-aware Healthcare AI platform built with **FastAPI**, **LangGraph Multi-Agent Workflows**, **Retrieval-Augmented Generation (RAG)**, and **Angular 17+**. The platform dynamically coordinates appointments, extracts clinical entities from handwritten prescriptions, analyzes complex corporate insurance policies, evaluates multi-page laboratory reports against biological reference ranges, and discovers nearby pharmacies in real time.

---

## 🌟 Key Features

### 1. 🤖 Supervisor Multi-Agent Orchestrator (LangGraph)
- **Central Supervisor**: Coordinates intent extraction, domain validation, and context routing across specialized sub-agents.
- **Symptom & Triage Agent**: Extracts clinical symptoms, duration, and urgency indicators; intercepts emergency red flags (cardiac arrest, stroke, acute trauma) with immediate hospital emergency contacts.
- **Doctor & Slot Agent**: Filters Bengaluru medical practitioners by specialty, hospital network, distance, and real-time consultation slots.
- **Prescription & Document Agent**: Parses unstructured prescriptions, extracting medicines, dosages, frequencies, and doctor signatures.
- **Medicine Intelligence Agent**: Searches pharmacology references for indications, interactions, dosage guidelines, and precautions.
- **Pharmacy Discovery Agent**: Ranks verified pharmacies in Bengaluru by geospatial proximity to the patient.
- **Insurance Policy Agent**: Analyzes corporate insurance policies across 8 dimensions (OPD caps, inpatient clauses, exclusions, claim deadlines) and compares medical bills against policy coverage.
- **Lab Report Analyzer Agent**: Automatically parses 16+ laboratory parameters (CBC, metabolic, lipid, thyroid), checks observed values against biological reference ranges, and enforces strict non-diagnostic clinical safety guardrails.

### 2. 📑 Grounded Document RAG Engine
- Multi-page PDF extraction using `pypdf`, chunking, embeddings, and vector similarity search.
- **Strict Anti-Hallucination Mandate**: Returns *"I couldn’t find this information in the uploaded document"* when information is not present.
- Every response provides verifiable document names and page numbers (e.g., `Page 1`, `Page 3`).

### 3. 🎨 Dynamic Canvas Dashboard (Turn-by-Turn UI)
- The left column operates as a **single active dynamic canvas**, controlled in real time by the AI chat on the right:
  - `SHOW_WELCOME`
  - `SHOW_PATIENT_INFO`
  - `SHOW_SYMPTOMS`
  - `SHOW_DEPARTMENT`
  - `SHOW_DOCTORS`
  - `SHOW_SLOTS`
  - `SHOW_NEARBY_DOCTORS`
  - `SHOW_DOCUMENT_UPLOAD`
  - `SHOW_DOCUMENT_SUMMARY`
  - `SHOW_MEDICINES`
  - `SHOW_MEDICINE_INFO`
  - `SHOW_PHARMACIES`
  - `SHOW_POLICY`
  - `SHOW_COVERAGE_ANALYSIS`
  - `SHOW_DOCUMENT_EVIDENCE`
  - `SHOW_LAB_REPORT`
  - `SHOW_LAB_RESULTS`
  - `SHOW_LAB_EVIDENCE`
  - `SHOW_APPOINTMENT`

---

## 🏗️ System Architecture

```
                               ┌─────────────────────────┐
                               │       User Client       │
                               │  (Angular 17+ / RxJS)   │
                               └────────────┬────────────┘
                                            │ HTTP / JSON
                                            ▼
                               ┌─────────────────────────┐
                               │     FastAPI Gateway     │
                               │ (Auth, JWT, Triage NLU) │
                               └────────────┬────────────┘
                                            │ State Graph
                                            ▼
                       ┌─────────────────────────────────────────┐
                       │        LangGraph Supervisor Node        │
                       └────┬──────┬──────┬──────┬─────────┬─────┘
                            │      │      │      │         │
      ┌─────────────────────┘      │      │      │         └──────────────────────┐
      ▼                            ▼      ▼      ▼                                ▼
┌──────────────┐            ┌──────────┐ ┌──────────────┐                  ┌──────────────┐
│Document Agent│            │ Doctor / │ │  Insurance   │                  │  Lab Report  │
│  & Rx Parser │            │Slot Agent│ │ Policy Agent │                  │Analyzer Agent│
└──────┬───────┘            └────┬─────┘ └──────┬───────┘                  └──────┬───────┘
       │                         │              │                                 │
       ▼                         ▼              ▼                                 ▼
┌──────────────┐            ┌──────────┐ ┌──────────────┐                  ┌──────────────┐
│  Medicine &  │            │Geospatial│ │  Vector DB   │                  │  Biological  │
│Pharmacy Agent│            │ Providers│ │ (Policy RAG) │                  │Interval Eval │
└──────┬───────┘            └────┬─────┘ └──────┬───────┘                  └──────┬───────┘
       │                         │              │                                 │
       └─────────────────────────┴──────┬───────┴─────────────────────────────────┘
                                        │ Unified Actions
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │              UI Action Node             │
                       │    (Payload Validation & Sanitization)  │
                       └────────────────┬────────────────────────┘
                                        │ Dynamic UI Action
                                        ▼
                       ┌─────────────────────────────────────────┐
                       │      Left Dynamic Canvas Dashboard      │
                       └─────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Frontend** | Angular 17+, TypeScript, RxJS, HTML5/CSS3 | Standalone Components, Signals, Reactive Forms, CSS Grid |
| **Backend** | Python 3.9+, FastAPI, Pydantic v2, Uvicorn | Asynchronous REST APIs, CORS Middleware, Swagger OpenAPI |
| **AI & Orchestration** | LangGraph, LangChain, Google Gemini API | Multi-Agent Supervisor Pattern, Cyclic State Graphs |
| **Document Intelligence** | PyPDF, Sentence Embeddings, In-Memory Vector Store | Extraction, Semantic Chunking, Grounded RAG |
| **State & Storage** | SQLite / PostgreSQL, Redis / Fakeredis | Multi-turn Session Memory, Entity Cache, Persistence |
| **Security & Safety** | Bcrypt, Python-Jose JWT, Red-Flag Interceptor | Password hashing, token authentication, clinical guardrails |

---

## 🚀 Getting Started

### Prerequisites
- **Node.js** (v18.x or v20.x) & **npm**
- **Python** (v3.9 or v3.11)
- **Git**

---

### 1. Clone the Repository
```bash
git clone https://github.com/204g1a0551/ai-health-coordinator.git
cd ai-health-coordinator
```

---

### 2. Backend Setup (FastAPI + LangGraph)

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Set your Gemini API key in a .env file or environment
export GEMINI_API_KEY="your-google-gemini-api-key"
export USE_LOCAL_NLU=1  # Set to 1 for deterministic local NLU fallback

# Start the backend server
python run.py
```
- **Backend API**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

### 3. Frontend Setup (Angular 17+)

```bash
cd ../frontend

# Install node dependencies
npm install

# Start development server
npm start
```
- **Frontend Application**: `http://localhost:4200`

---

## 🧪 Comprehensive Verification Suite

Run the backend verification suite to validate all multi-agent routes, document RAG, and lab report extraction:

```bash
PYTHONPATH=backend USE_LOCAL_NLU=1 python -c "
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Test Lab Report Intelligence
res = client.post('/api/chat', json={'message': 'Show my latest lab report', 'session_id': 'test'})
assert res.json().get('action') == 'SHOW_LAB_REPORT'

res = client.post('/api/chat', json={'message': 'Which values are outside the reference range?', 'session_id': 'test'})
assert res.json().get('action') == 'SHOW_LAB_RESULTS'

res = client.post('/api/chat', json={'message': 'What does page 3 say?', 'session_id': 'test'})
assert res.json().get('action') == 'SHOW_LAB_EVIDENCE'

print('All verification tests passed successfully!')
"
```

---

## 🛡️ Clinical Guardrails & Medical Safety

1. **Non-Diagnostic Policy**: The system strictly coordinates consultations, extracts structured text, and compares observations against explicitly stated ranges. It **never** generates independent medical diagnoses.
2. **Emergency Red-Flag Interceptor**: Symptoms indicating acute medical crises (e.g. chest pain, cardiac arrest, stroke) immediately trigger emergency routing with 24x7 emergency contacts for top Bengaluru hospitals (Manipal, Apollo, Fortis).
3. **Document Grounding**: Never fabricates medication details or policy terms. Every answer cites source documents and specific page numbers.

---

## 📄 License
This project is licensed under the MIT License.
