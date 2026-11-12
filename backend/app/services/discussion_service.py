import math
from ..core.errors import DomainError
from ..core.database import now
from ..models.constants import CLINICAL_FIELDS
from .audit_service import audit

def add_discussion(con, user, p, e, data):
    pid = p['id']
    from ..core.permissions import require
    require(user, 'discuss', p)
    body = str(data.get('body', '')).strip()
    if not body or len(body) > 5000:
        raise ValueError('Discussion entry must be 1–5,000 characters')
    con.execute('INSERT INTO discussions(patient_id,author,body,created_at) VALUES(?,?,?,?)', (pid, user['id'], body, now()))
    audit(con, user, 'discussion entry', pid)
