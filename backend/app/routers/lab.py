from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..schemas.lab import LabUpdate
from ..services.workflow_service import change_patient
from ..services.lab_service import update_lab_result, request_repeat_sample
router = APIRouter(prefix='/api/lab', tags=['Laboratory'])

@router.put('/{patient_id}')
def save_result(patient_id: int, data: LabUpdate, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), update_lab_result)

@router.post('/{patient_id}/repeat-request')
def request_repeat(patient_id: int, user=Depends(current_user)):
    return change_patient(patient_id, user, {}, request_repeat_sample)
