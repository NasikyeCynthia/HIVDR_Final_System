from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..schemas.decision import DecisionRequest, ImplementationRequest, FollowUpRequest
from ..services.workflow_service import change_patient
from ..services.decision_service import approve_decision, implement_decision, record_follow_up
router = APIRouter(prefix='/api/decisions', tags=['Clinical decisions'])

@router.post('/{patient_id}/approve')
def approve(patient_id: int, data: DecisionRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), approve_decision)

@router.post('/{patient_id}/implement')
def implement(patient_id: int, data: ImplementationRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), implement_decision)

@router.post('/{patient_id}/follow-up')
def follow_up(patient_id: int, data: FollowUpRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), record_follow_up)
