import math
from ..core.errors import DomainError
from ..core.database import now
from ..models.constants import CLINICAL_FIELDS
from .audit_service import audit
from .risk_service import score

def update_lab_result(con, user, p, e, data):
    pid = p['id']
    if user['role'] != 'lab':
        raise DomainError('Laboratory permission required', 403)
    kind = data.get('sample_type')
    status = data.get('status')
    if kind not in ('Plasma', 'DBS') or status not in ('Pending', 'Usable result', 'Unamplified', 'Sequencing failed'):
        raise ValueError('Choose a sample type and laboratory status')
    if kind == 'DBS' and (not str(data.get('dbs_reason', '')).strip()):
        raise ValueError('A reason for DBS is required')
    if status in ('Unamplified', 'Sequencing failed') and (not str(data.get('failure_reason', '')).strip()):
        raise ValueError('An unsuccessful-test reason is required')
    if e['reviewed_at']:
        raise ValueError('This episode has been reviewed. Create a new test episode before replacing its result (not yet available in this version).')
    stamp = now()
    report = stamp if status != 'Pending' else None
    con.execute('UPDATE episodes SET sample_type=?,dbs_reason=?,sample_at=COALESCE(sample_at,?),lab_owner=?,status=?,failure_reason=?,report_at=?,amplified=?,mutations=?,version=version+1 WHERE patient_id=?', (kind, data.get('dbs_reason', ''), stamp, user['id'], status, data.get('failure_reason', ''), report, 0 if status == 'Unamplified' else 1 if status in ('Usable result', 'Sequencing failed') else None, str(data.get('mutations', '')), pid))
    audit(con, user, 'laboratory update', pid, e, data)

def request_repeat_sample(con, user, p, e, data):
    pid = p['id']
    if user['role'] != 'lab':
        raise DomainError('Laboratory permission required', 403)
    if e['status'] not in ('Unamplified', 'Sequencing failed'):
        raise ValueError('Repeat request requires an unsuccessful test')
    con.execute('UPDATE episodes SET repeat_requested_at=? WHERE patient_id=?', (now(), pid))
    audit(con, user, 'repeat sample requested', pid)
