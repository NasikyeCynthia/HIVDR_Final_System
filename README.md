# HIVDR Surveillance System

**Frontend: React + JSX + HTML + CSS + Vite. Backend: Python + FastAPI + SQLite.**

This version separates the interface, API routes, validation schemas, data model and business logic. The previous prototype is left unchanged. This package is a new project; it does not automatically migrate changes made in the old prototype database.

## Where everything is

| Folder / file | Purpose |
| --- | --- |
| `frontend/` | React application; run with npm |
| `frontend/index.html` | HTML entry point containing the React root |
| `frontend/src/main.jsx` | Starts React |
| `frontend/src/App.jsx` | Connects URL routes to page components |
| `frontend/src/pages/` | Separate JSX files for each page |
| `frontend/src/components/` | Reusable navigation, charts, tables and patient forms |
| `frontend/src/services/` | JavaScript API calls to the Python backend |
| `frontend/src/contexts/` | Authentication and workspace state |
| `frontend/src/styles/global.css` | Interface styling |
| `backend/app/main.py` | FastAPI application entry point |
| `backend/app/routers/` | Python API endpoints grouped by feature |
| `backend/app/schemas/` | Pydantic request validation |
| `backend/app/models/schema.sql` | Database tables and relationships; SQL schema, not ORM classes |
| `backend/app/services/` | Risk scoring, import, permissions and workflow logic |
| `backend/app/core/` | Database connection, configuration, authentication and initialization |
| `backend/data/` | Synthetic sample and local runtime database |
| `backend/tests/` | Service tests and optional HTTP integration tests |

## Pages and URLs

| Page | React file | URL |
| --- | --- | --- |
| Login | `frontend/src/pages/LoginPage.jsx` | Shown before authentication |
| Dashboard | `frontend/src/pages/DashboardPage.jsx` | `/dashboard` |
| Patient records | `frontend/src/pages/PatientRecordsPage.jsx` | `/patients` |
| Individual patient and forms | `frontend/src/pages/PatientDetailPage.jsx` | `/patients/:patientId` |
| Risk assessment | `frontend/src/pages/RiskAssessmentPage.jsx` | `/risk-assessment` |
| Lab results | `frontend/src/pages/LabResultsPage.jsx` | `/lab-results` |
| Resistance classification | `frontend/src/pages/ResistanceClassificationPage.jsx` | `/resistance-classification` |
| Discussion | `frontend/src/pages/DiscussionPage.jsx` | `/discussion` |
| Notifications | `frontend/src/pages/NotificationsPage.jsx` | `/notifications` |
| Settings | `frontend/src/pages/SettingsPage.jsx` | `/settings` |

The individual patient page has Overview, Profile, Risk assessment, Laboratory, Discussion, Decision and Source record tabs. Each functional form lives in its own component file, rather than one large page script.

## Start the backend — terminal 1

Requirements: Python 3.11+ and internet access to install packages. From the extracted project folder:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

These commands use the virtual environment directly, so PowerShell activation permissions are not needed. If `python` is unavailable, use `py` for the environment creation command.

- API health: http://127.0.0.1:8000/api/health
- Interactive API documentation: http://127.0.0.1:8000/docs
- Generated database: `backend/data/surveillance.sqlite3`
- First-run demo password: `backend/data/local_login.txt`
- Demo usernames: `admin`, `nurse`, `counsellor`, `lab`, `clinician`

The backend generates a random local demo password on first startup and hashes stored passwords. This is prototype account provisioning, not a finished account-management interface.

## Start the frontend — terminal 2

Requirements: Node.js 20.19+ (your Node 22 installation is suitable) and npm. Open another terminal from the extracted project folder:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173**. Keep both terminals running. Vite forwards `/api` requests to FastAPI on port 8000, keeping the session cookie on the same browser origin. Do not open `index.html` directly.

## What is connected

| Feature | Status |
| --- | --- |
| Login and role/facility permissions | Implemented in FastAPI |
| Dashboard charts and clickable patient lists | Implemented in React |
| Patient registration, search, assignment and profile updates | Implemented |
| 60/30/0 factor scoring | Implemented with unchanged weights |
| Overall risk category and automatic referral | Blocked pending clarification of overlapping ranges |
| Laboratory entry, DBS reason, unsuccessful-test reason | Implemented |
| Repeat-sample request | Implemented; additional test-attempt entry is pending |
| Patient discussion | Implemented |
| Clinician-approved decision and implementation tracking | Implemented |
| Original/synthetic CSV import with source-column preservation | Implemented |
| Administrator audit history | Implemented |
| Stanford mutation interpretation | Not connected; integration boundary is `stanford_service.py` |
| Machine-learning prediction | Not connected; integration boundary is `ml_service.py` |
| External notifications, account administration, deployment | Pending |

## Data and scoring details

The package includes **499 rows from your synthetic CSV**, including all 120 columns. It does not contain the full original clinical dataset. Initial demo assignments and laboratory/decision milestones are fictional overlays so the workflow can be demonstrated; the source snapshot shows actual values from the synthetic CSV. Additional imported rows do not receive invented workflow milestones. Historical laboratory/decision fields remain visible in source snapshots until a dedicated migration is implemented.

Import your full original or synthetic CSV through Settings as `admin`. The importer recognizes the original headers, including `Patient No.`, `VL Leading to DR` and `Treatment Line at Sample collection`. Adherence is read from `Adherence (%)` or `Simulated Adherence (%)`; absent adherence stays missing. Original files are never overwritten. Duplicate source + Patient No. entries are skipped. Confirm the stable person identifier before treating imported record counts as unique patients.

Your factor scores remain high 60, moderate 30, low 0. Your stated overall ranges were high >60, moderate 31–59 and low ≥30. These overlap, and totals are multiples of 30. All complete assessments therefore show **Rule unresolved** while retaining their calculated total. Missing inputs show **Incomplete**. No alternative overall thresholds are substituted.

## Verification and limitations

The source was checked for Python syntax, JSX syntax and local import resolution. Five service tests exercise scoring boundaries, role/facility access, lab-to-decision workflow, import rollback and invalid inputs. FastAPI HTTP tests are included and require development dependencies. React/Vite and FastAPI runtime execution could not be verified here because package downloads were unavailable. Run the installation and checks below on your PC before relying on this version.

Backend, from `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend, from `frontend`:

```powershell
npm run build
```

This remains a local prototype. It uses SQLite rather than PostgreSQL. It supports one current episode per patient, has no finalized cohort/date filters or complete MOH job-card validation, and does not automatically generate treatment recommendations. Clinical decisions and lab results are locked after approval; amendment/history workflows are pending. Production identity, HTTPS, managed storage, backup and deployment configuration are not included.
