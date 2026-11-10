import csv
import io
from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..core.database import connect
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..schemas.patient import ImportRequest
from ..services.import_service import import_rows
from ..services.audit_service import audit
router = APIRouter(prefix='/api/settings', tags=['Settings and audit'])

class DatasetSelection(BaseModel):
    source: Literal['original', 'synthetic']

def active_dataset(con):
    row = con.execute("SELECT value FROM settings WHERE key='active_dataset'").fetchone()
    return row['value'] if row and row['value'] in ('original', 'synthetic') else 'original'

@router.get('/dataset')
def get_dataset(user=Depends(current_user)):
    with connect() as con:
        return {'source': active_dataset(con)}

@router.put('/dataset')
def set_dataset(data: DatasetSelection, user=Depends(current_user)):
    if user['role'] != 'admin':
        raise DomainError('Administrator permission required', 403)
    with connect() as con:
        previous = active_dataset(con)
        con.execute("INSERT INTO settings(key,value) VALUES('active_dataset',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (data.source,))
        if previous != data.source:
            audit(con, user, 'active dataset changed', 'workspace', before={'source': previous}, after={'source': data.source})
        return {'source': data.source}

@router.get('/users')
def users(user=Depends(current_user)):
    with connect() as con:
        return [dict(row) for row in con.execute('SELECT id,username,name,role,facility,can_access_all FROM users') if user['role']=='admin' or bool(user.get('can_access_all')) or row['facility']==user['facility']]

@router.post('/import')
def import_csv(data: ImportRequest, user=Depends(current_user)):
    if user['role'] != 'admin':
        raise DomainError('Administrator permission required', 403)
    rows = list(csv.DictReader(io.StringIO(data.csv.lstrip('\ufeff'))))
    if not rows or len(rows)>50000:
        raise DomainError('Import 1–50,000 records')
    with connect() as con:
        return import_rows(con, rows, data.source, user)

@router.get('/audit')
def audit_history(user=Depends(current_user)):
    if user['role'] != 'admin':
        raise DomainError('Administrator permission required', 403)
    with connect() as con:
        return [dict(row) for row in con.execute('SELECT id,actor,role,action,entity,created_at FROM audit ORDER BY id DESC LIMIT 200')]
