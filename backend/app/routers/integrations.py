from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..services import ml_service, stanford_service
router = APIRouter(prefix='/api/integrations', tags=['Integration readiness'])
@router.get('/status')
def integration_status(user=Depends(current_user)):
    return {'stanford': stanford_service.status(), 'machine_learning': ml_service.status()}

@router.get('/stanford/check')
def check_stanford(user=Depends(current_user)):
    return stanford_service.check_connection()
