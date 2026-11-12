# HIVDR Surveillance — v0.5

Workflow: dashboard → patient records (nurse/counsellor) → risk and DR-test eligibility (MoH/WHO) → laboratory (DR-test request, sample, result) → Stanford resistance interpretation → committee discussion and decision (clinician) → implementation and 6-monthly follow-up (nurse/counsellor). Everyone can view every page; each role edits only its own steps. See CHANGES_WORKFLOW_V5.md and backend/ml/RISK_SCORE.md.

React / JSX / HTML / CSS frontend; Python / FastAPI / SQLite backend.

Read **UPGRADE_V4.md** to apply the staged update while preserving your database and credentials. It also explains account/hospital setup, full record editing, archive/restore, clinician corrections and the trained model.

## Code organisation

| Folder | Responsibility |
| --- | --- |
| frontend/src/pages | Individual dashboard, patient, risk, lab, resistance, discussion, notifications and settings JSX pages |
| frontend/src/components | Forms, charts, tables and navigation |
| frontend/src/services | Calls to the Python API |
| backend/app/routers | Feature-specific API routes |
| backend/app/schemas | Request validation |
| backend/app/services | Record mapping, editing, lab, clinical, Stanford and ML logic |
| backend/app/models | SQL schema and source column catalogue |
| backend/app/core | Database, auth, configuration and additive migration |
| backend/ml | Reproducible training script, portable model and evaluation card |
| backend/tests | Service and HTTP workflow tests |

## Running the system (Windows)

You need Python 3.11+ and Node.js 18+ installed. Use two terminals.

**Terminal 1 — backend** (from the `Final_system` folder):

```bat
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Leave it running. On first start after this update it adds the new database columns and computes
eligibility, risk and ML estimates for every record (about 40 seconds for the full dataset).

**Terminal 2 — frontend**:

```bat
cd frontend
npm.cmd install
npm.cmd run dev
```

Open http://127.0.0.1:5173. Usernames: `admin`, `nurse`, `counsellor`, `lab`, `clinician`; the password
is in `backend/data/local_login.txt` (created on first start; existing installations keep their accounts).

Next time you only need: backend → `.venv\Scripts\activate` then the `uvicorn` line; frontend → `npm.cmd run dev`.

**Checks**: in the backend terminal `pip install -r requirements-dev.txt` then `python -m pytest tests`
(49 tests); in the frontend terminal `npm.cmd run build`.

## Fresh installation

From backend, create a virtual environment, install requirements.txt, and run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000. From frontend, run npm.cmd install and npm.cmd run dev. Open http://127.0.0.1:5173. Demo login details are generated in backend/data/local_login.txt on first start. Existing installations retain their accounts.

## Data integrity and roles

Source snapshots remain unchanged; corrections live in audited overlays. All source columns are exposed in organised sections, including genuine blanks. Clinical editing requires the corresponding staff role at that hospital. Administrator accounts manage staff and assignments. Archived records can be restored, and clinicians can reopen reviewed cases with a retained prior version. Data-source selection is in Settings.

No original patient CSV/database is included in this update. On existing installations, documented historical stages are recovered only where no active workflow will be overwritten. Genuine missing adherence remains missing; no synthetic clinical values are injected.

## Model

The included model runs using portable JSON parameters and the Python standard library. Read backend/ml/MODEL_CARD.md for the precisely defined panel outcome, facility-disjoint evaluation, performance and limitations. It remains separate from the rules-based score and clinician decision. Stanford uses the live Sierra API and requires an internet connection. Email/SMS delivery and prospective clinical model validation remain outside this version.

## Verification

From backend, install requirements-dev.txt and run python -m unittest discover -s tests -v. From frontend, run npm.cmd run build. Actual checks and limitations are in VALIDATION.md.
