import json
from fastapi import APIRouter, Depends, Query
from ..core.database import connect, now
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..schemas.patient import PatientCreate, ProfileUpdate, AssignmentRequest
from ..services.patient_service import records, decorate
from ..services.profile_service import update_profile, assign_care_worker
from ..services.workflow_service import load_patient, change_patient
from ..services.audit_service import audit
from ..services.record_service import effective_record,sections,COLUMNS,section,sync_core,is_extra_vl_field,hidden_from_nurse
from ..services.mutation_inputs import suggested_mutations

router = APIRouter(prefix='/api/patients', tags=['Patients'])

@router.get('')
def list_patients(include_archived: bool=False, user=Depends(current_user)):
    with connect() as con:
        return records(con, user, include_archived, summary=True)

@router.get('/columns')
def patient_columns(user=Depends(current_user)):
    columns = [key for key in COLUMNS if user['role'] != 'nurse' or not hidden_from_nurse(key)]
    return {'columns': columns}

@router.get('/table')
def patient_table(ids: list[int]=Query(...), fields: list[str]=Query(default=[]), user=Depends(current_user)):
    if not ids or len(ids)>25:
        raise DomainError('Select between 1 and 25 patient rows',400)
    selected=list(dict.fromkeys(field for field in fields if field in COLUMNS and (user['role'] != 'nurse' or not hidden_from_nurse(field))))
    placeholders=','.join('?' for _ in ids)
    sql=f'SELECT id,facility,original_json,source_overrides_json FROM patients WHERE id IN ({placeholders})'
    args=list(ids)
    if user['role'] not in ('admin', 'nurse') and not user.get('can_access_all'):
        sql+=' AND facility=?';args.append(user['facility'])
    with connect() as con:
        rows=con.execute(sql,args).fetchall()
        if len(rows)!=len(set(ids)):
            raise DomainError('Patient not found or access denied',404)
        result=[]
        for row in rows:
            raw={**json.loads(row['original_json'] or '{}'),**json.loads(row['source_overrides_json'] or '{}')}
            result.append({'id':row['id'],'fields':{key:raw.get(key,'') for key in selected}})
        return result

@router.post('')
def create_patient(data: PatientCreate, user=Depends(current_user)):
    if user['role'] not in ('nurse', 'counsellor'):
        raise DomainError('Only nurses and counsellors can register patients', 403)
    external_id = data.external_id.strip()
    if not external_id:
        raise DomainError('Patient ID is required')
    if len(data.fields)>len(COLUMNS):
        raise DomainError('Too many dataset fields were submitted',400)
    fields={}
    protected={'Identity and provenance','Laboratory','Discussion and committee decision'}
    for key,value in data.fields.items():
        if key not in COLUMNS and not is_extra_vl_field(key):
            raise DomainError('Unknown dataset field: '+key,400)
        if section(key) in protected and value.strip():
            raise DomainError('Laboratory results and committee decisions must be entered through their role-specific workflows',403)
        if len(value)>20000:
            raise DomainError('Dataset field is too long: '+key,400)
        fields[key]=value.strip()
    raw={'Patient No.':external_id,'Facility':user['facility'],**fields}
    with connect() as con:
        cur = con.execute('INSERT INTO patients(external_id,source,dataset_source,name,facility,assigned_to,original_json,created_at) VALUES(?,?,?,?,?,?,?,?)', (external_id, 'manual', data.dataset_source, data.name.strip() or 'Patient '+external_id, user['facility'], user['id'], json.dumps(raw), now()))
        con.execute('INSERT INTO episodes(patient_id) VALUES(?)', (cur.lastrowid,))
        sync_core(con,cur.lastrowid,raw)
        audit(con, user, 'register', cur.lastrowid, after={'dataset_fields_provided':len(fields)})
        return {'id': cur.lastrowid}

@router.get('/{patient_id}')
def get_patient(patient_id: int, user=Depends(current_user)):
    with connect() as con:
        p, e = load_patient(con, user, patient_id)
        discussion = [dict(row) for row in con.execute('SELECT d.*,u.name AS author_name FROM discussions d JOIN users u ON d.author=u.id WHERE patient_id=? ORDER BY d.id', (patient_id,))]
        original = json.loads(p['original_json'])
        current_record = effective_record(p)
        patient = decorate({**p, **e, 'id': patient_id, 'suggested_mutations':suggested_mutations(current_record)})
        review_history = [dict(r) for r in con.execute('SELECT r.*,u.name AS actor FROM episode_revisions r LEFT JOIN users u ON r.actor_id=u.id WHERE patient_id=? ORDER BY r.id DESC LIMIT 50',(patient_id,))]
        lab_history = [dict(r) for r in con.execute('SELECT a.id,a.created_at,a.snapshot_json,u.name AS actor FROM lab_attempts a LEFT JOIN users u ON a.actor_id=u.id WHERE patient_id=? ORDER BY a.id DESC',(patient_id,))]
        if user['role'] == 'nurse':
            hidden_patient_fields = {'sample_type','dbs_reason','lab_owner','status','failure_reason','report_at','amplified','mutations','repeat_requested_at','reviewed_at','reviewer','review_notes','decision','decision_at','decision_notes','recommended_regimen','implemented_at','implementation_notes','missing_post','post_complete','suggested_mutations'}
            patient = {key:value for key,value in patient.items() if key not in hidden_patient_fields}
            original = {key:value for key,value in original.items() if not hidden_from_nurse(key)}
            current_record = {key:value for key,value in current_record.items() if not hidden_from_nurse(key)}
            discussion = []
            review_history = []
            lab_history = []
        return {'patient': patient, 'original': original, 'current_record': current_record, 'record_sections': sections({**p,**e},user), 'review_history': review_history, 'discussion': discussion, 'lab_history': lab_history}

@router.patch('/{patient_id}/profile')
def save_profile(patient_id: int, data: ProfileUpdate, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(exclude_unset=True), update_profile)

@router.patch('/{patient_id}/assignment')
def save_assignment(patient_id: int, data: AssignmentRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), assign_care_worker)
