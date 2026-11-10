import math
from ..core.errors import DomainError
from ..core.database import now
from ..models.constants import CLINICAL_FIELDS
from .audit_service import audit
from .risk_service import score

def add_discussion(con, user, p, e, data):
    pid = p['id']
    if user['role'] not in ('counsellor', 'clinician'):
        raise DomainError('Clinical discussion permission required', 403)
    body = str(data.get('body', '')).strip()
    if not body or len(body) > 5000:
        raise ValueError('Discussion entry must be 1–5,000 characters')
    con.execute('INSERT INTO discussions(patient_id,author,body,created_at) VALUES(?,?,?,?)', (pid, user['id'], body, now()))
    audit(con, user, 'discussion entry', pid)
