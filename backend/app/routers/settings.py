import csv
import io
from fastapi import APIRouter, Depends
from ..core.database import connect
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..schemas.patient import ImportRequest
from ..services.import_service import import_rows
router = APIRouter(prefix='/api/settings', tags=['Settings and audit'])

@router.get('/users')
def users(user=Depends(current_user)):
    with connect() as con:
        return [dict(row) for row in con.execute('SELECT id,name,role,facility FROM users') if user['role']=='admin' or row['facility']==user['facility']]

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
