from ..models.constants import PROFILE_FIELDS
from .import_service import present
from .risk_service import score

def allowed(user, p):
    return user['role'] == 'admin' or user['facility'] == p['facility']

def records(con, user):
    sql = 'SELECT p.*,u.name AS owner_name,e.*,p.id AS id FROM patients p LEFT JOIN users u ON p.assigned_to=u.id JOIN episodes e ON e.patient_id=p.id'
    return [decorate(dict(r)) for r in con.execute(sql).fetchall() if allowed(user, r)]

def decorate(p):
    p.pop('original_json', None)
    p['risk'] = score(p)
    p['missing_pre'] = [f for f in PROFILE_FIELDS if not present(p.get(f))]
    p['missing_post'] = [] if not p.get('reviewed_at') else [f for f in ('decision', 'decision_notes', 'recommended_regimen', 'implementation_notes') if not present(p.get(f))]
    p['pre_complete'] = not p['missing_pre']
    p['post_complete'] = bool(p.get('reviewed_at')) and (not p['missing_post'])
    return p
