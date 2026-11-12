import json
from ..models.constants import PROFILE_FIELDS
from .import_service import present
from .eligibility_service import STATUS_LABELS

def allowed(user, p):
    # Every signed-in user can view every facility's records (read-only).
    # Editing is limited to the user's own facility and role (core/permissions.py).
    return True

def records(con, user, include_archived=False, summary=False):
    pcols='id,external_id,source,dataset_source,name,facility,age,sex,regimen,treatment_line,viral_load,adherence,assigned_to,created_at,archived_at,archive_reason'
    ecols='repeat_reason,mutations,risk_ml,ttf,officer_name,officer_phone,risk_category,risk_flagged,eligibility_status,referral_basis,referred_at,sample_at,sample_type,dbs_reason,centrifuged_at,tubes,whole_blood_ml,storage_temp,workflow_collection,dispatched_at,received_at,plasma_volume_ml,cphl_outcome,cphl_reason,dr_lab,dr_referred_at,tested_at,attempt_no,lab_owner,status,failure_reason,report_at,amplified,repeat_requested_at,reviewed_at,reviewer,decision,discussion_status,decision_at,decision_notes,recommended_regimen,implemented_at,implementation_notes'
    sql='SELECT '+','.join('p.'+k for k in pcols.split(','))+','+','.join('e.'+k for k in ecols.split(','))+',u.name AS owner_name,lab.name AS lab_owner_name,clinician.name AS reviewer_name FROM patients p LEFT JOIN users u ON p.assigned_to=u.id JOIN episodes e ON e.patient_id=p.id LEFT JOIN users lab ON lab.id=e.lab_owner LEFT JOIN users clinician ON clinician.id=e.reviewer'
    args=()
    rows=[decorate(dict(r)) for r in con.execute(sql,args).fetchall() if include_archived or not dict(r).get('archived_at')]
    if summary:
        omit={'psychosocial','interpretation','approval_blockers','decision_notes','recommended_regimen','implementation_notes',
              'centrifuged_at','tubes','whole_blood_ml','storage_temp','workflow_collection','plasma_volume_ml','cphl_reason','dr_referred_at','tested_at','dispatched_at','referral_basis',
              'eligibility_status','risk_category','risk_flagged'}
        for row in rows:
            for key in omit:row.pop(key,None)
            row['eligibility']={'status':row['eligibility']['status']}
            row['risk']={'category':row['risk']['category'],'flagged':row['risk']['flagged'],'total':row['risk'].get('total'),'ml':row.pop('risk_ml',None)}
            row['lab']={'stage':row['lab']['stage'],'flag_count':sum(f['level']=='error' for f in row['lab']['flags'])}
    return rows


def decorate(p):
    p.pop('original_json', None)
    p.pop('source_overrides_json', None)
    p['psychosocial'] = json.loads(p.get('psychosocial_json') or '{}')
    p.pop('psychosocial_json', None)
    p['interpretation'] = json.loads(p.get('interpretation_json') or 'null')
    p.pop('interpretation_json', None)
    from .lab_service import assess as lab_assess
    p['lab'] = lab_assess(p)
    p['approval_blockers'] = []
    p['ttf'] = json.loads(p['ttf']) if isinstance(p.get('ttf'), str) and p['ttf'] else None
    risk = json.loads(p.pop('risk_json', None) or 'null')
    p['risk'] = risk or {'category': p.get('risk_category') or 'Not assessed', 'flagged': bool(p.get('risk_flagged'))}
    p['suggestion'] = json.loads(p.pop('suggestion_json', None) or 'null')
    full = json.loads(p.pop('eligibility_json', None) or 'null')
    status = p.get('eligibility_status') or (full or {}).get('status') or 'insufficient_data'
    p['eligibility'] = full or {'status': status}
    p['eligibility'].setdefault('label', STATUS_LABELS.get(status, status))
    p['eligibility']['eligible'] = status == 'eligible'
    p['missing_pre'] = [f for f in PROFILE_FIELDS if not present(p.get(f))]
    if not p['psychosocial'].get('assessed'): p['missing_pre'].append('psychosocial assessment')
    p['missing_post'] = [] if not p.get('decision') else [f for f in ('decision_notes', 'recommended_regimen', 'implementation_notes') if not present(p.get(f))]
    p['pre_complete'] = not p['missing_pre']
    if p['missing_pre']: p['approval_blockers'].append('Complete profile: '+', '.join(p['missing_pre']))
    if p.get('status') != 'Usable result': p['approval_blockers'].append('A usable laboratory result is required')
    if not p.get('discussion_status'):
        from .discussion_status import classify_discussion
        p['discussion_status'] = classify_discussion(None, p.get('decision'), p.get('amplified'))
    p['post_complete'] = bool(p.get('decision')) and (not p['missing_post'])
    return p
