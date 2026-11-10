import json
import secrets
from fastapi import APIRouter,Depends
from ..core.database import connect,now
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..core.security import password_hash
from ..schemas.operations import RecordFieldsUpdate,ArchiveRequest,AccountCreate,AmendmentRequest
from ..services.workflow_service import load_patient,change_patient
from ..services.record_service import update_fields,effective_record
from ..services.audit_service import audit
from ..services.ml_service import predict,status
router=APIRouter(prefix='/api/operations',tags=['Records, accounts and model'])

@router.patch('/patients/{patient_id}/fields')
def fields(patient_id:int,data:RecordFieldsUpdate,user=Depends(current_user)):
    return change_patient(patient_id,user,data.model_dump(),update_fields)

@router.post('/patients/{patient_id}/archive')
def archive(patient_id:int,data:ArchiveRequest,user=Depends(current_user)):
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        if user['role'] not in ('admin','nurse','counsellor') or (user['role']!='admin' and p['facility']!=user['facility']):raise DomainError('Patient registry permission required',403)
        con.execute('UPDATE patients SET archived_at=?,archive_reason=? WHERE id=?',(now() if data.archived else None,data.reason,patient_id))
        audit(con,user,'record archived' if data.archived else 'record restored',patient_id,after={'reason':data.reason})
    return {'ok':True}

@router.post('/accounts')
def account(data:AccountCreate,user=Depends(current_user)):
    if user['role']!='admin':raise DomainError('Administrator permission required',403)
    if not data.name.strip() or not data.facility.strip():raise DomainError('Name and facility are required')
    password=secrets.token_urlsafe(15);salt=secrets.token_hex(16)
    with connect() as con:
        cur=con.execute('INSERT INTO users(username,name,role,facility,salt,password_hash,can_access_all) VALUES(?,?,?,?,?,?,0)',(data.username,data.name.strip(),data.role,data.facility.strip(),salt,password_hash(password,salt)))
        audit(con,user,'staff account created',cur.lastrowid,after={'username':data.username,'role':data.role,'facility':data.facility})
    return {'username':data.username,'password':password,'message':'Generated password is shown once. Store and share with the intended staff member securely.'}

@router.get('/model')
def model_status(user=Depends(current_user)):return status()

@router.get('/patients/{patient_id}/prediction')
def prediction(patient_id:int,user=Depends(current_user)):
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        return predict(effective_record(p),p)

@router.post('/patients/{patient_id}/amend')
def amend(patient_id:int,data:AmendmentRequest,user=Depends(current_user)):
    with connect() as con:
        p,e=load_patient(con,user,patient_id)
        if user['role']!='clinician' or user['facility']!=p['facility']:raise DomainError('Clinician at this facility required',403)
        if p.get('archived_at'):raise DomainError('Restore the record before amendment',409)
        if not e['decision'] and not e['reviewed_at']:raise DomainError('This record is already open for review')
        con.execute('INSERT INTO episode_revisions(patient_id,actor_id,reason,snapshot_json,created_at) VALUES(?,?,?,?,?)',(patient_id,user['id'],data.reason,json.dumps(e),now()))
        con.execute("UPDATE episodes SET reviewed_at=NULL,reviewer=NULL,review_notes='',decision=NULL,decision_at=NULL,decision_notes='',recommended_regimen='',implemented_at=NULL,implementation_notes='' WHERE patient_id=?",(patient_id,))
        overrides=json.loads(p.get('source_overrides_json') or '{}')
        from ..services.record_service import DECISION
        overrides.update({key:'' for key in DECISION})
        con.execute('UPDATE patients SET source_overrides_json=?,data_version=data_version+1 WHERE id=?',(json.dumps(overrides),patient_id))
        audit(con,user,'clinical amendment opened',patient_id,after={'reason':data.reason})
    return {'ok':True}
