import math
from ..core.errors import DomainError
from ..core.database import now
from ..models.constants import CLINICAL_FIELDS
from .audit_service import audit
from .risk_service import score

def approve_decision(con, user, p, e, data):
    pid = p['id']
    if user['role'] != 'clinician':
        raise DomainError('Clinician permission required', 403)
    if e['status'] != 'Usable result':
        raise ValueError('A usable laboratory result is required')
    if data.get('decision') not in ('Maintained', 'Switched', 'Substituted'):
        raise ValueError('Choose a decision')
    if not str(data.get('decision_notes', '')).strip() or not str(data.get('recommended_regimen', '')).strip():
        raise ValueError('Record the rationale and intended regimen')
    if e['decision']:
        raise ValueError('Decision already approved for this episode; amendment workflow is pending.')
    stamp = now()
    con.execute('UPDATE episodes SET reviewed_at=?,reviewer=?,decision=?,decision_at=?,decision_notes=?,recommended_regimen=? WHERE patient_id=?', (stamp, user['id'], data['decision'], stamp, data['decision_notes'], data['recommended_regimen'], pid))
    audit(con, user, 'clinical decision approved', pid, e, data)

def implement_decision(con, user, p, e, data):
    pid = p['id']
    if user['role'] not in ('nurse', 'counsellor', 'clinician'):
        raise DomainError('Clinical permission required', 403)
    if user['role'] != 'clinician' and p['assigned_to'] != user['id']:
        raise DomainError('Assigned care worker permission required', 403)
    if not e['decision'] or not str(data.get('implementation_notes', '')).strip():
        raise ValueError('An approved decision and implementation notes are required')
    con.execute('UPDATE episodes SET implemented_at=?,implementation_notes=? WHERE patient_id=?', (now(), data['implementation_notes'], pid))
    audit(con, user, 'decision implemented', pid, e, data)
