import json
from ..models.constants import PROFILE_FIELDS
from .import_service import present
from .risk_service import score

def allowed(user, p):
    return user['role'] in ('admin', 'nurse') or bool(user.get('can_access_all')) or user['facility'] == p['facility']

def records(con, user, include_archived=False, summary=False):
    pcols='id,external_id,source,dataset_source,name,facility,age,sex,regimen,treatment_line,viral_load,adherence,assigned_to,created_at,archived_at,archive_reason'
    ecols='referred_at,sample_at,sample_type,dbs_reason,lab_owner,status,failure_reason,report_at,amplified,repeat_requested_at,reviewed_at,reviewer,decision,discussion_status,decision_at,decision_notes,recommended_regimen,implemented_at,implementation_notes'
    sql='SELECT '+','.join('p.'+k for k in pcols.split(','))+','+','.join('e.'+k for k in ecols.split(','))+',u.name AS owner_name,lab.name AS lab_owner_name,clinician.name AS reviewer_name FROM patients p LEFT JOIN users u ON p.assigned_to=u.id JOIN episodes e ON e.patient_id=p.id LEFT JOIN users lab ON lab.id=e.lab_owner LEFT JOIN users clinician ON clinician.id=e.reviewer'
    if user['role'] not in ('admin', 'nurse') and not user.get('can_access_all'):
        sql+=' WHERE p.facility=?';args=(user['facility'],)
    else:args=()
    rows=[decorate(dict(r)) for r in con.execute(sql,args).fetchall() if include_archived or not dict(r).get('archived_at')]
    if summary:
        omit={'psychosocial','interpretation','approval_blockers','decision_notes','recommended_regimen','implementation_notes'}
        for row in rows:
            for key in omit:row.pop(key,None)
            row['risk']={key:row['risk'][key] for key in ('total','known_total','complete','category','eligible')}
    return rows


def decorate(p):
    p.pop('original_json', None)
    p.pop('source_overrides_json', None)
    p['psychosocial'] = json.loads(p.get('psychosocial_json') or '{}')
    p.pop('psychosocial_json', None)
    p['interpretation'] = json.loads(p.get('interpretation_json') or 'null')
    p.pop('interpretation_json', None)
    p['approval_blockers'] = []
    p['risk'] = score(p)
    p['missing_pre'] = [f for f in PROFILE_FIELDS if not present(p.get(f))]
    p['missing_post'] = [] if not p.get('decision') else [f for f in ('decision_notes', 'recommended_regimen', 'implementation_notes') if not present(p.get(f))]
    p['pre_complete'] = not p['missing_pre']
    if p['missing_pre']: p['approval_blockers'].append('Complete profile: '+', '.join(p['missing_pre']))
    if p.get('status') != 'Usable result': p['approval_blockers'].append('A usable laboratory result is required')
    if not p.get('discussion_status'):
        from .discussion_status import classify_discussion
        p['discussion_status'] = classify_discussion(None, p.get('decision'), p.get('amplified'))
    p['post_complete'] = bool(p.get('decision')) and (not p['missing_post'])
    return p
