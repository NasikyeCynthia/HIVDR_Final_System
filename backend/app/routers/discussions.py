from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..schemas.discussion import DiscussionRequest
from ..services.workflow_service import change_patient
from ..services.discussion_service import add_discussion
router = APIRouter(prefix='/api/discussions', tags=['Patient discussion'])

@router.post('/{patient_id}')
def add_entry(patient_id: int, data: DiscussionRequest, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), add_discussion)
