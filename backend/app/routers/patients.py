import json
from fastapi import APIRouter, Depends, Query
from ..core.database import connect, now
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..schemas.patient import PatientCreate, ProfileUpdate, AssignmentRequest, VLSampleCreate, VLResult
from ..services import vl_service
from ..services.patient_service import records, decorate
from ..services.profile_service import update_profile, assign_care_worker
from ..services.workflow_service import load_patient, change_patient
from ..services.audit_service import audit
from ..services.record_service import effective_record,sections,COLUMNS,section,sync_core,is_extra_vl_field,hidden_from_nurse
from ..services.mutation_inputs import suggested_mutations

router = APIRouter(prefix='/api/patients', tags=['Patients'])

@router.get('')
def list_patients(include_archived: bool=False, user=Depends(current_user)):
    # Rows are plain JSON values, so skip FastAPI's per-field encoder (≈3× faster for 40,000 records).
    from fastapi.responses import JSONResponse
    with connect() as con:
        return JSONResponse(records(con, user, include_archived, summary=True))

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
    from ..core.permissions import require
    require(user, 'register_patient')
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
    from ..core.permissions import any_facility
    facility = data.facility.strip() if data.facility.strip() and any_facility(user) else user['facility']
    raw={'Patient No.':external_id,'Facility':facility,**fields}
    with connect() as con:
        cur = con.execute('INSERT INTO patients(external_id,source,dataset_source,name,facility,assigned_to,original_json,created_at) VALUES(?,?,?,?,?,?,?,?)', (external_id, 'manual', data.dataset_source, data.name.strip() or 'Patient '+external_id, facility, user['id'], json.dumps(raw), now()))
        con.execute('INSERT INTO episodes(patient_id) VALUES(?)', (cur.lastrowid,))
        sync_core(con,cur.lastrowid,raw)
        from ..services.eligibility_service import refresh
        if data.vl_sample:
            p_row = dict(con.execute('SELECT * FROM patients WHERE id=?', (cur.lastrowid,)).fetchone())
            e_row = dict(con.execute('SELECT * FROM episodes WHERE patient_id=?', (cur.lastrowid,)).fetchone())
            vl_service.record_sample(con, user, p_row, e_row, data.vl_sample.model_dump())
        refresh(con,cur.lastrowid)
        audit(con, user, 'register', cur.lastrowid, after={'dataset_fields_provided':len(fields)})
        return {'id': cur.lastrowid}

@router.get('/{patient_id}')
def get_patient(patient_id: int, user=Depends(current_user)):
    with connect() as con:
        p, e = load_patient(con, user, patient_id)
        discussion = [dict(row) for row in con.execute('SELECT d.*,u.name AS author_name FROM discussions d JOIN users u ON d.author=u.id WHERE patient_id=? ORDER BY d.id', (patient_id,))]
        original = json.loads(p['original_json'])
        current_record = effective_record(p)
        patient = decorate({**p, **e, 'id': patient_id, 'suggested_mutations':e.get('mutations') or suggested_mutations(current_record)})
        review_history = [dict(r) for r in con.execute('SELECT r.*,u.name AS actor FROM episode_revisions r LEFT JOIN users u ON r.actor_id=u.id WHERE patient_id=? ORDER BY r.id DESC LIMIT 50',(patient_id,))]
        from ..services.suggestion_service import suggest
        from ..services.psychosocial_service import recommendations
        if not patient.get('suggestion'): patient['suggestion'] = suggest(p, e, current_record)
        patient['psychosocial_recommendations'] = recommendations(patient.get('psychosocial'), patient.get('age'))
        follow_ups = [dict(r) for r in con.execute('SELECT f.*,u.name AS actor FROM follow_ups f LEFT JOIN users u ON f.actor_id=u.id WHERE patient_id=? ORDER BY due_date',(patient_id,))]
        iac_sessions = [dict(r) for r in con.execute('SELECT s.*,u.name AS actor FROM iac_sessions s LEFT JOIN users u ON s.actor_id=u.id WHERE patient_id=? ORDER BY s.session_date,s.id',(patient_id,))]
        lab_history = [dict(r) for r in con.execute('SELECT a.id,a.created_at,a.snapshot_json,u.name AS actor FROM lab_attempts a LEFT JOIN users u ON a.actor_id=u.id WHERE patient_id=? ORDER BY a.id DESC',(patient_id,))]
        return {'patient': patient, 'original': original, 'current_record': current_record, 'record_sections': sections({**p,**e},user), 'review_history': review_history, 'discussion': discussion, 'lab_history': lab_history, 'iac_sessions': iac_sessions, 'follow_ups': follow_ups, 'vl_samples': vl_service.list_samples(con, patient_id), 'vl_indications': vl_service.INDICATIONS}

@router.patch('/{patient_id}/profile')
def save_profile(patient_id: int, data: ProfileUpdate, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(exclude_unset=True), update_profile)

@router.patch('/{patient_id}/assignment')
def save_assignment(patient_id: int, data: AssignmentRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), assign_care_worker)


@router.post('/{patient_id}/vl-samples')
def add_vl_sample(patient_id: int, data: VLSampleCreate, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), vl_service.record_sample)


@router.put('/{patient_id}/vl-samples/{sample_id}/result')
def add_vl_result(patient_id: int, sample_id: int, data: VLResult, user=Depends(current_user)):
    return change_patient(patient_id, user, {**data.model_dump(), 'sample_id': sample_id}, vl_service.record_result)
