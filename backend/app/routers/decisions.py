from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..schemas.decision import DecisionRequest, ImplementationRequest
from ..services.workflow_service import change_patient
from ..services.decision_service import approve_decision, implement_decision
router = APIRouter(prefix='/api/decisions', tags=['Clinical decisions'])

@router.post('/{patient_id}/approve')
def approve(patient_id: int, data: DecisionRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), approve_decision)

@router.post('/{patient_id}/implement')
def implement(patient_id: int, data: ImplementationRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), implement_decision)
