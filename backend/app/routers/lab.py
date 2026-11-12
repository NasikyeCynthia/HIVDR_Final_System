from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..schemas.lab import CollectionRecord, DispatchRecord, ReceiptRecord, ResultRecord
from ..services.workflow_service import change_patient
from ..services import lab_service as lab

router = APIRouter(prefix='/api/lab', tags=['Laboratory'])


@router.get('/options')
def options(user=Depends(current_user)):
    return {'storage': lab.STORAGE, 'dbs_reasons': lab.DBS_REASONS, 'rejection_reasons': lab.REJECTION_REASONS,
            'deferral_reasons': lab.DEFERRAL_REASONS, 'dr_lab': lab.DR_LAB, 'separation_hours': lab.SEPARATION_HOURS,
            'tat_days': lab.DR_TAT_DAYS, 'sources': lab.SOURCES}


@router.put('/{patient_id}/collection')
def collection(patient_id: int, data: CollectionRecord, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), lab.record_collection)


@router.put('/{patient_id}/dispatch')
def dispatch(patient_id: int, data: DispatchRecord, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), lab.record_dispatch)


@router.put('/{patient_id}/receipt')
def receipt(patient_id: int, data: ReceiptRecord, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), lab.record_receipt)


@router.put('/{patient_id}/result')
def result(patient_id: int, data: ResultRecord, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), lab.record_result)


@router.post('/{patient_id}/repeat-request')
def request_repeat(patient_id: int, user=Depends(current_user)):
    return change_patient(patient_id, user, {}, lab.request_repeat_sample)
