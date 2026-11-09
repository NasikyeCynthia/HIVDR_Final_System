import math
from ..core.errors import DomainError
from ..core.database import now
from ..models.constants import CLINICAL_FIELDS
from .audit_service import audit
from .risk_service import score

def refer_for_drt(con, user, p, e, data):
    pid = p['id']
    if user['role'] not in ('nurse', 'counsellor', 'clinician'):
        raise DomainError('Clinical permission required', 403)
    if score(p)['category'] != 'High':
        raise ValueError('Referral flag awaits an unambiguous high-risk classification. Resolve the overall risk rule first.')
    con.execute('UPDATE episodes SET referred_at=COALESCE(referred_at,?) WHERE patient_id=?', (now(), pid))
    audit(con, user, 'DRT referral', pid)
