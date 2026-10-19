# CRM Autopilot

An AI agent system that automates sales operations work using CRM data and deterministic execution tools.

Sales managers can describe an operational business task in plain English (e.g., *"Find open opportunities worth more than ₹10 lakh with no activity in the last 7 days and create follow-up tasks"*). The system parses intent, generates a dry-run preview, waits for human approval, and executes verified, idempotent actions without duplicate side effects.

---

## Features
- **Deterministic CRM Tools & Storage**: Full SQLAlchemy ORM models for Accounts, Contacts, Opportunities, Activities, and Tasks with PostgreSQL/Supabase and SQLite support.
- **RESTful CRUD Endpoints**: High-performance FastAPI endpoints for `/contacts`, `/deals`, and `/tasks` with JWT authentication.
- **AI Autopilot Engine**:
  - **Natural Language Intent Parsing**: Powered by Gemini API structured outputs (`gemini-2.5-flash`) with an offline deterministic fallback.
  - **Safe Dry-Run Preview**: Matches qualifying opportunities and drafts proposed tasks without performing any writes.
  - **Human-in-the-Loop Approval Gate**: Requires explicit approval before any database state modifications.
  - **Idempotency & Duplicate Prevention**: Automatically skips duplicate pending tasks.
  - **Audit Verification**: Validates persisted database state and returns a comprehensive execution report.

---

## API Endpoints

### 1. Autopilot AI Workflow
- `POST /autopilot/seed`: Seeds sample accounts, contacts, opportunities, and activities.
- `POST /autopilot/preview`: Submits a plain English prompt and returns matched records & proposed actions.
- `POST /autopilot/execute`: Approves (`approved=true`) or rejects (`approved=false`) the drafted preview plan.

### 2. Core CRM CRUD
- `/contacts`: List (with pagination), get by ID, create, update, and delete.
- `/deals`: List (with pagination), get by ID, create, update, and delete.
- `/tasks`: Workflow task submission and status checks.
- `GET /health`: Health status.

---

## Quick Start (Local)

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs` to test via Swagger UI.

---

## Testing

```powershell
python -m pytest -v
```
All 10 unit and integration tests verify CRUD operations, authentication, LLM parsing, dry-run previews, approval gating, and duplicate prevention.
