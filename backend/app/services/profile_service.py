import math
import json
from ..core.errors import DomainError
from ..core.database import now
from ..models.constants import CLINICAL_FIELDS
from .audit_service import audit
from .risk_service import score

def update_profile(con, user, p, e, data):
    pid = p['id']
    expected=data.pop('expected_version',None)
    if expected is not None and expected!=p.get('data_version',0):raise DomainError('The profile changed. Reload before saving.',409)
    if user['role'] not in ('nurse', 'counsellor'):
        raise DomainError('Only nurses and counsellors can edit profiles', 403)
    if user['facility'] != p['facility']:
        raise DomainError('Edit patients at your assigned facility', 403)
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
    changed=con.execute('UPDATE patients SET ' + ','.join((k + '=?' for k in fields)) + ',assigned_to=COALESCE(assigned_to,?) WHERE id=? AND data_version=?', [updated.get(k) for k in fields] + [user['id'], pid,p.get('data_version',0)])
    if changed.rowcount!=1:raise DomainError('The profile changed. Reload before saving.',409)
    from .record_service import CORE
    overrides=json.loads(p.get('source_overrides_json') or '{}')
    for key,field in CORE.items():
        if field in data: overrides[key]='' if updated[field] is None else str(updated[field])
    con.execute('UPDATE patients SET source_overrides_json=?,data_version=data_version+1 WHERE id=?',(json.dumps(overrides),pid))
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
