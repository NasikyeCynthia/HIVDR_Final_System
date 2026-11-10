from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..core.database import connect
from ..services.workflow_service import load_patient, change_patient
from ..services.risk_service import score
from ..services.referral_service import refer_for_drt
router = APIRouter(prefix='/api/risk', tags=['Risk assessment'])

@router.get('/rules')
def rules(user=Depends(current_user)):
    return {'notice': score({})['notice'], 'weights': {'high': 60, 'moderate': 30, 'low': 0}, 'overall_rule_ready': True}

@router.get('/{patient_id}')
def assess(patient_id: int, user=Depends(current_user)):
    with connect() as con:
        patient, _ = load_patient(con, user, patient_id)
        return score(patient)

@router.post('/{patient_id}/refer')
def refer(patient_id: int, user=Depends(current_user)):
    return change_patient(patient_id, user, {}, refer_for_drt)
