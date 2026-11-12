from fastapi import APIRouter, Depends
from ..core.database import connect
from ..core.dependencies import current_user
from ..services.patient_service import records
from ..services.notification_service import notifications
router = APIRouter(prefix='/api/notifications', tags=['Notifications'])
@router.get('')
def list_notifications(user=Depends(current_user)):
    with connect() as con:
        due = {r[0]: r[1] for r in con.execute('SELECT patient_id,min(due_date) FROM follow_ups WHERE assessed_on IS NULL GROUP BY patient_id')}
        result = notifications(records(con, user), due)
        if user['role'] == 'nurse':
            result = [
                {**item, 'reasons': [reason for reason in item['reasons'] if reason.startswith(('Missing profile: ', 'Approved decision', '6-monthly', 'High risk'))]}
                for item in result
            ]
            result = [item for item in result if item['reasons']]
        return result
