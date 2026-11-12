"""DR-test request, made by laboratory staff so that one named person is accountable for the
patient's sample and results. The gate is the guideline eligibility engine, not a points score.

Laboratory staff may request outside the automated rule, with a written indication (for example
from the clinician's request form), for indications
the record cannot show: e.g. an HIV-positive infant born to a mother failing treatment,
clinical failure (new WHO stage 3/4 event after 6 months of effective ART), or a request
from the switch committee (MoH Desktop Job Aid 2020, slides 159-160). Every override is audited.
"""
import json
from ..core.errors import DomainError
from ..core.database import now
from .audit_service import audit
from .eligibility_service import refresh


def refer_for_drt(con, user, p, e, data):
    pid = p['id']
    from ..core.permissions import require
    require(user, 'request_dr_test', p)
    if e.get('referred_at'):
        raise DomainError('This patient has already been referred for this episode', 409)
    basis = (data or {}).get('basis', 'guideline')
    reason = str((data or {}).get('reason', '')).strip()
    result = refresh(con, pid)
    if basis == 'guideline':
        if result['status'] != 'eligible':
            raise ValueError('Not eligible under the MoH criteria: ' + result['label'] + '. ' + result['next_step'])
        basis_text = 'MoH/WHO criteria met (' + result['rule_version'] + '): ' + str(result.get('pathway') or '')
        if reason:
            basis_text += ' — ' + reason
    else:
        require(user, 'refer_on_clinical_indication', p)
        if len(reason) < 15:
            raise ValueError('Give the indication for requesting outside the automated criteria (at least 15 characters)')
        basis_text = 'Outside automated criteria: ' + reason
    if data.get('weight_kg') is None or data.get('on_rifampicin') is None or not data.get('biorepository_consent'):
        raise ValueError('Complete the DR section of the request form: body weight, whether the patient is on rifampicin, '
                         'and biospecimen storage consent (accept or decline)')
    stamp = now()
    # The requesting laboratory officer becomes responsible for this patient's sample and results.
    con.execute('UPDATE episodes SET referred_at=?,referral_basis=?,lab_owner=?,weight_kg=?,on_rifampicin=?,biorepository_consent=? WHERE patient_id=?',
                (stamp, basis_text, user['id'], data['weight_kg'], int(bool(data['on_rifampicin'])), data['biorepository_consent'], pid))
    from .record_service import overlay_changes
    raw = {**json.loads(p.get('original_json') or '{}'), **json.loads(p.get('source_overrides_json') or '{}')}
    changes = {'Weight': str(data['weight_kg'])}
    if not str(raw.get('drIndication') or '').strip():
        changes['drIndication'] = result.get('indication', '')
    if changes:
        overlay_changes(con, pid, changes)
    audit(con, user, 'DRT referral', pid, after={'basis': basis, 'basis_text': basis_text,
                                                  'eligibility_status': result['status'], 'criteria': result['criteria']})
