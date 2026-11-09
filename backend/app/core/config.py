from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data'
DB = DATA_DIR / 'surveillance.sqlite3'
SCHEMA = ROOT / 'app' / 'models' / 'schema.sql'
FRONTEND_ORIGINS = set(os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000').split(','))
