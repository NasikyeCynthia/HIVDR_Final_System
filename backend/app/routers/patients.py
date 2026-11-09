import json
from fastapi import APIRouter, Depends
from ..core.database import connect, now
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..schemas.patient import PatientCreate, ProfileUpdate, AssignmentRequest
from ..services.patient_service import records, decorate
from ..services.profile_service import update_profile, assign_care_worker
from ..services.workflow_service import load_patient, change_patient
from ..services.audit_service import audit

router = APIRouter(prefix='/api/patients', tags=['Patients'])

@router.get('')
def list_patients(user=Depends(current_user)):
    with connect() as con:
        return records(con, user)

@router.post('')
def create_patient(data: PatientCreate, user=Depends(current_user)):
    if user['role'] not in ('nurse', 'counsellor'):
        raise DomainError('Only nurses and counsellors can register patients', 403)
    external_id = data.external_id.strip()
    if not external_id:
        raise DomainError('Patient ID is required')
    with connect() as con:
        cur = con.execute('INSERT INTO patients(external_id,source,name,facility,assigned_to,original_json,created_at) VALUES(?,?,?,?,?,?,?)', (external_id, 'manual', data.name.strip() or 'Patient '+external_id, user['facility'], user['id'], '{}', now()))
        con.execute('INSERT INTO episodes(patient_id) VALUES(?)', (cur.lastrowid,))
        audit(con, user, 'register', cur.lastrowid)
        return {'id': cur.lastrowid}

@router.get('/{patient_id}')
def get_patient(patient_id: int, user=Depends(current_user)):
    with connect() as con:
        p, e = load_patient(con, user, patient_id)
        discussion = [dict(row) for row in con.execute('SELECT d.*,u.name AS author_name FROM discussions d JOIN users u ON d.author=u.id WHERE patient_id=? ORDER BY d.id', (patient_id,))]
        return {'patient': decorate({**p, **e, 'id': patient_id}), 'original': json.loads(p['original_json']), 'discussion': discussion}

@router.patch('/{patient_id}/profile')
def save_profile(patient_id: int, data: ProfileUpdate, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(exclude_unset=True), update_profile)

@router.patch('/{patient_id}/assignment')
def save_assignment(patient_id: int, data: AssignmentRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), assign_care_worker)
