from fastapi import APIRouter, Depends
from ..core.database import connect
from ..core.dependencies import current_user
from ..services.patient_service import records
from ..services.notification_service import notifications
router = APIRouter(prefix='/api/notifications', tags=['Notifications'])
@router.get('')
def list_notifications(user=Depends(current_user)):
    with connect() as con:
        return notifications(records(con, user))
