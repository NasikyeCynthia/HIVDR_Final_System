# Backend — Python / FastAPI

Start: `python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000` after installing `requirements.txt` in a virtual environment. Full Windows instructions are in the root README.

| Python module | Responsibility / API prefix |
| --- | --- |
| `app/main.py` | Application, startup and error handlers |
| `app/routers/auth.py` | Login, logout, current user — `/api/auth` |
| `app/routers/patients.py` | Registration, profiles, care-worker assignment — `/api/patients` |
| `app/routers/risk.py` | Factor scoring and referral gate — `/api/risk` |
| `app/routers/lab.py` | Lab entry and repeat request — `/api/lab` |
| `app/routers/decisions.py` | Clinician approval and implementation — `/api/decisions` |
| `app/routers/discussions.py` | Patient discussion — `/api/discussions` |
| `app/routers/notifications.py` | Outstanding work — `/api/notifications` |
| `app/routers/settings.py` | CSV import, user listing and audit — `/api/settings` |
| `app/routers/integrations.py` | Explicit ML and Stanford connection status — `/api/integrations` |

Routers validate requests with `app/schemas/`, then call `app/services/`. Services make role checks and transactional changes through `app/core/database.py`. The database schema is in `app/models/schema.sql`. A user being allowed to view a record does not grant permission to edit it.

`app/services/ml_service.py` is the place for future model inference. `app/services/stanford_service.py` is the place for future Stanford mutation interpretation. The Stanford service now calls the official Sierra GraphQL API with sequence or mutation input. The ML service remains unconnected. Additional review, assignment and account-scope endpoints are in app/routers/workflow.py.

SQLite stores the current episode, patient source snapshots, discussion and audit events. Runtime database files, credentials and virtual environments are excluded from the distributable and Git.

## v0.4 record operations and model

app/routers/operations.py exposes full record corrections, archive/restore, clinician amendments, staff account creation and model inference. app/services/record_service.py maps the source catalogue into sections and preserves original values behind overlays. app/services/ml_service.py performs dependency-free inference using ml/artifacts/model.json. Read ml/MODEL_CARD.md before interpreting the estimate.
