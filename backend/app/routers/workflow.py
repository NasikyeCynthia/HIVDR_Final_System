import json
from fastapi import APIRouter, Depends
from ..core.database import connect, now
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..schemas.workflow import PsychosocialUpdate, InterpretationRequest, UserUpdate, LabAssignmentRequest, ReviewRequest
from ..services.workflow_service import load_patient
from ..services.audit_service import audit
from ..services import stanford_service
router = APIRouter(prefix='/api/workflow',tags=['Review and accountability'])

@router.post('/patients/{patient_id}/retry-interpretation')
def retry_interpretation(patient_id:int,user=Depends(current_user)):
    if user['role'] not in ('lab','clinician'):raise DomainError('Only laboratory staff or clinicians can request analysis of the saved laboratory result.',403)
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        from ..core.permissions import any_facility
        if not any_facility(user) and user['facility']!=p['facility']:raise DomainError('Cross-facility access is read-only.',403)
        if p.get('archived_at') or e.get('decision'):raise DomainError('This record is locked.',409)
        if e['status']!='Usable result':raise DomainError('A usable laboratory result is required.')
        from ..services.auto_interpretation import enqueue
        job=enqueue(con,user,patient_id)
    from ..services.auto_interpretation import schedule
    schedule(patient_id)
    return {'ok':True,'job_id':job}

@router.post('/patients/{patient_id}/review')
def mark_reviewed(patient_id:int,data:ReviewRequest,user=Depends(current_user)):
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        from ..core.permissions import require
        require(user,'review_and_decide',p)
        if e['status']!='Usable result': raise DomainError('A usable laboratory result is required')
        if e['decision']: raise DomainError('This episode already has a final decision')
        con.execute('UPDATE episodes SET reviewed_at=COALESCE(reviewed_at,?),reviewer=?,review_notes=? WHERE patient_id=?',(now(),user['id'],data.notes,patient_id))
        audit(con,user,'clinical review recorded',patient_id,after=data.model_dump())
    return {'ok':True}

@router.patch('/patients/{patient_id}/lab-assignment')
def assign_lab(patient_id:int,data:LabAssignmentRequest,user=Depends(current_user)):
    if user['role']!='admin': raise DomainError('Administrator permission required',403)
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        staff=con.execute('SELECT * FROM users WHERE id=?',(data.lab_owner,)).fetchone()
        if not staff or staff['role']!='lab' or staff['facility']!=p['facility']:
            raise DomainError('Choose a laboratory officer at this patient facility')
        con.execute('UPDATE episodes SET lab_owner=? WHERE patient_id=?',(staff['id'],patient_id))
        audit(con,user,'laboratory assignment',patient_id,{'lab_owner':e['lab_owner']},data.model_dump())
    return {'ok':True}

@router.put('/patients/{patient_id}/psychosocial')
def psychosocial(patient_id:int,data:PsychosocialUpdate,user=Depends(current_user)):
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        from ..core.permissions import require
        require(user,'record_psychosocial',p)
        from ..core.config import ALL_FACILITIES
        if not ALL_FACILITIES and p['assigned_to'] not in (None,user['id']):
            raise DomainError('Only the assigned nurse/counsellor can update this assessment',403)
        from ..services.psychosocial_service import FACTORS
        unknown=[f for f in data.factors if f not in FACTORS]
        if unknown: raise DomainError('Choose factors from the MoH psychosocial list: '+', '.join(unknown))
        con.execute('UPDATE patients SET psychosocial_json=?,assigned_to=? WHERE id=?',(data.model_dump_json(),user['id'],patient_id))
        if data.assessed:
            from ..services.record_service import overlay_changes
            overlay_changes(con,patient_id,{'PSS:'+f:('Yes' if f in data.factors else 'No') for f in FACTORS})
        audit(con,user,'psychosocial assessment',patient_id,after=data.model_dump())
    return {'ok':True}

@router.post('/patients/{patient_id}/interpret')
def interpret(patient_id:int,data:InterpretationRequest,user=Depends(current_user)):
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        from ..core.permissions import require
        require(user,'interpret_resistance',p)
        if e['status']!='Usable result': raise DomainError('A usable laboratory result is required')
        version=e['version']
        if e['decision']: raise DomainError('Approved interpretation is locked. Start an amendment workflow.',409)
    result=stanford_service.analyze(data.kind,data.text)
    with connect() as con:
        p,current=load_patient(con,user,patient_id)
        require(user,'interpret_resistance',p)
        if current['version']!=version or current['status']!='Usable result':
            raise DomainError('Lab result changed during analysis. Please rerun.',409)
        if current['decision']: raise DomainError('Approved interpretation is locked. Start an amendment workflow.',409)
        from ..services.suggestion_service import suggest
        from ..services.record_service import effective_record
        draft=suggest(p,{**current,'interpretation_json':json.dumps(result)},effective_record(p))
        con.execute('UPDATE episodes SET interpretation_json=?,interpreted_at=?,suggestion_json=?,version=version+1 WHERE patient_id=?',(json.dumps(result),now(),json.dumps(draft),patient_id))
        con.execute("UPDATE interpretation_jobs SET status='superseded',message='Replaced by a laboratory interpretation.',finished_at=? WHERE patient_id=? AND status IN ('pending','running')",(now(),patient_id))
        audit(con,user,'Stanford interpretation',patient_id,after={'kind':data.kind,'version':result.get('version')})
    return result

@router.patch('/users/{user_id}')
def update_user(user_id:int,data:UserUpdate,user=Depends(current_user)):
    if user['role']!='admin': raise DomainError('Administrator permission required',403)
    with connect() as con:
        old=con.execute('SELECT id,name,facility,can_access_all FROM users WHERE id=?',(user_id,)).fetchone()
        if not old: raise DomainError('User not found',404)
        con.execute('UPDATE users SET name=?,facility=?,can_access_all=? WHERE id=?',(data.name.strip(),data.facility.strip(),int(data.can_access_all),user_id))
        con.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
        audit(con,user,'account scope updated',user_id,dict(old),data.model_dump())
    return {'ok':True,'message':'Updated user must sign in again.'}

@router.post('/map-original-history')
def map_original_history(user=Depends(current_user)):
    if user['role']!='admin': raise DomainError('Administrator permission required',403)
    from ..services.history_service import map_history
    with connect() as con:
        rows=con.execute("SELECT id,original_json FROM patients WHERE source='original'").fetchall()
        count=sum(map_history(con,r['id'],json.loads(r['original_json'])) for r in rows)
        audit(con,user,'historical workflow mapping','original',after={'mapped':count})
    return {'mapped':count}
