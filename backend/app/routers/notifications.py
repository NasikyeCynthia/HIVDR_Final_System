from fastapi import APIRouter, Depends
from ..core.database import connect
from ..core.dependencies import current_user
from ..services.patient_service import records
from ..services.notification_service import notifications
router = APIRouter(prefix='/api/notifications', tags=['Notifications'])
@router.get('')
def list_notifications(user=Depends(current_user)):
    with connect() as con:
        result = notifications(records(con, user))
        if user['role'] == 'nurse':
            result = [
                {**item, 'reasons': [reason for reason in item['reasons'] if reason.startswith('Missing profile: ')]}
                for item in result
            ]
            result = [item for item in result if item['reasons']]
        return result
