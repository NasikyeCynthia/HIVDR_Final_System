from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data'
DB = DATA_DIR / 'surveillance.sqlite3'
SCHEMA = ROOT / 'app' / 'models' / 'schema.sql'
# Demo with one account per role: role limits still apply, but every account may work on every
# facility's records. Set HIVDR_ALL_FACILITIES=0 to restrict edits to each user's own facility.
ALL_FACILITIES = os.getenv('HIVDR_ALL_FACILITIES', '1') != '0'
FRONTEND_ORIGINS = set(os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000').split(','))
