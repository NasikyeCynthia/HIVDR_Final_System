import math
from ..core.errors import DomainError
from ..core.database import now
from ..models.constants import CLINICAL_FIELDS
from .audit_service import audit
from .risk_service import score

def update_profile(con, user, p, e, data):
    pid = p['id']
    if user['role'] not in ('nurse', 'counsellor'):
        raise DomainError('Only nurses and counsellors can edit profiles', 403)
    if p['assigned_to'] not in (None, user['id']):
        raise DomainError('This patient is assigned to another care worker', 403)
    if set(data) - CLINICAL_FIELDS:
        raise ValueError('Profile contains fields outside your permission')
    updated = {**p, **data}
    for key in ('age', 'viral_load', 'adherence'):
        v = updated.get(key)
        updated[key] = None if v in ('', None) else float(v)
        if updated[key] is not None and (not math.isfinite(updated[key]) or updated[key] < 0):
            raise ValueError(key + ' must be a nonnegative number')
    if updated['adherence'] is not None and updated['adherence'] > 100:
        raise ValueError('Adherence must be 0–100')
    if updated['age'] is not None and updated['age'] > 120:
        raise ValueError('Age must be 0–120')
    updated['treatment_line'] = None if updated.get('treatment_line') in ('', None) else int(updated['treatment_line'])
    if updated['treatment_line'] not in (None, 1, 2, 3):
        raise ValueError('Treatment line must be 1, 2 or 3')
    fields = sorted(CLINICAL_FIELDS)
    con.execute('UPDATE patients SET ' + ','.join((k + '=?' for k in fields)) + ',assigned_to=? WHERE id=?', [updated.get(k) for k in fields] + [user['id'], pid])
    audit(con, user, 'profile update', pid, {k: p[k] for k in fields}, {k: updated[k] for k in fields})

def assign_care_worker(con, user, p, e, data):
    pid = p['id']
    if user['role'] != 'admin':
        raise DomainError('Administrator permission required', 403)
    owner = con.execute('SELECT * FROM users WHERE id=?', (data.get('assigned_to'),)).fetchone()
    if not owner or owner['role'] not in ('nurse', 'counsellor') or owner['facility'] != p['facility']:
        raise ValueError('Choose a nurse/counsellor at the patient facility')
    con.execute('UPDATE patients SET assigned_to=? WHERE id=?', (owner['id'], pid))
    audit(con, user, 'assignment', pid, {'assigned_to': p['assigned_to']}, {'assigned_to': owner['id']})
