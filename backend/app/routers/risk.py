"""DR-testing eligibility (MoH criteria), IAC sessions and referral.

Kept at /api/risk for compatibility; /api/eligibility is the same router.
"""
from fastapi import APIRouter, Depends
from ..core.dependencies import current_user
from ..core.database import connect
from ..schemas.eligibility import IACSessionCreate, ReferralRequest
from ..services.workflow_service import load_patient, change_patient
from ..services import eligibility_service as rules_engine
from ..services.referral_service import refer_for_drt
from ..services.iac_service import add_session, delete_session

router = APIRouter(prefix='/api/eligibility', tags=['DR testing eligibility'])


@router.get('/rules')
def rules(user=Depends(current_user)):
    e = rules_engine
    return {'version': e.RULE_VERSION, 'sources': e.SOURCES, 'statuses': e.STATUS_LABELS,
            'thresholds': {'nonsuppressed_at': e.NONSUPPRESSED_AT, 'min_repeat_interval_days': e.MIN_REPEAT_INTERVAL_DAYS,
                           'min_art_days': e.MIN_ART_DAYS, 'good_adherence': e.GOOD_ADHERENCE, 'fair_adherence': e.FAIR_ADHERENCE,
                           'required_good_iac': e.REQUIRED_GOOD_IAC, 'child_age_limit': e.CHILD_AGE_LIMIT}}


@router.get('/{patient_id}')
def assess(patient_id: int, user=Depends(current_user)):
    with connect() as con:
        load_patient(con, user, patient_id)
        result = rules_engine.refresh(con, patient_id)
        result['sessions'] = rules_engine.load_sessions(con, patient_id)
        return result


@router.post('/{patient_id}/iac')
def record_iac(patient_id: int, data: IACSessionCreate, user=Depends(current_user)):
    return change_patient(patient_id, user, data.model_dump(), add_session)


@router.delete('/{patient_id}/iac/{session_id}')
def remove_iac(patient_id: int, session_id: int, user=Depends(current_user)):
    return change_patient(patient_id, user, {'session_id': session_id}, delete_session)


@router.post('/{patient_id}/refer')
def refer(patient_id: int, data: ReferralRequest | None = None, user=Depends(current_user)):
    return change_patient(patient_id, user, (data.model_dump() if data else {}), refer_for_drt)


legacy = APIRouter(prefix='/api/risk', tags=['DR testing eligibility (legacy path)'])
for route in router.routes:
    legacy.add_api_route(route.path.replace('/api/eligibility', ''), route.endpoint, methods=list(route.methods), include_in_schema=False)
