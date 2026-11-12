"""Committee decision (clinician), implementation (assigned nurse/counsellor) and the
6-monthly cohort follow-up, following the MoH HIVDR database workflow (Participants'
Manual §7.3.2–7.3.4): decision → 'Switched pending action' → start on regimen (start date,
previous regimen stop date; 'maintained' is confirmed as seen) → assessment every 6 months."""
import json
from datetime import date
from ..core.errors import DomainError
from ..core.database import now
from ..core.permissions import require
from .audit_service import audit
from .patient_service import decorate

FOLLOW_UP_MONTHS = 6
CARE_STATUS = ('Alive and on treatment', 'Lost to follow up/Dropped out of care (90  days)', 'Lost (<90 days)',
               'Transferred out', 'Stopped', 'Died')


def add_months(day, months):
    m = day.month - 1 + months
    y, m = day.year + m // 12, m % 12 + 1
    from calendar import monthrange
    return date(y, m, min(day.day, monthrange(y, m)[1]))


def _raw(p):
    return {**json.loads(p.get('original_json') or '{}'), **json.loads(p.get('source_overrides_json') or '{}')}


def approve_decision(con, user, p, e, data):
    require(user, 'review_and_decide', p)
    pid = p['id']
    view = decorate({**p, **e})
    if not view['pre_complete']:
        raise ValueError('Complete the patient profile before a decision can be approved: ' + ', '.join(view['missing_pre']))
    if e['status'] != 'Usable result':
        raise ValueError('A usable laboratory result is required')
    if e['decision']:
        raise ValueError('A decision is already approved for this episode; use the amendment workflow to change it.')
    from .suggestion_service import suggest
    suggestion = suggest(p, e, _raw(p))
    followed = bool(suggestion and suggestion.get('action') == data['decision'])
    if suggestion and suggestion.get('action') and not followed and len(str(data.get('decision_notes', '')).strip()) < 20:
        raise ValueError('The decision differs from the suggested action: explain the clinical reasoning (at least 20 characters).')
    stamp = now()
    con.execute("""UPDATE episodes SET reviewed_at=COALESCE(reviewed_at,?),reviewer=?,decision=?,discussion_status='Done',decision_at=?,
                   decision_notes=?,recommended_regimen=?,suggestion_json=? WHERE patient_id=?""",
                (stamp, user['id'], data['decision'], stamp, data['decision_notes'], data['recommended_regimen'],
                 json.dumps({**(suggestion or {}), 'followed': followed}), pid))
    audit(con, user, 'clinical decision approved', pid, e, {**data, 'suggested': (suggestion or {}).get('action'), 'followed': followed})
    from .record_service import overlay_changes
    overlay_changes(con, pid, {'Decision Date': stamp[:10], 'decision Category': data['decision'], 'Decision': data['decision_notes'],
                               'Assigned ART by switch committee': data['recommended_regimen']})


def implement_decision(con, user, p, e, data):
    require(user, 'implement_decision', p)
    pid = p['id']
    if p.get('assigned_to') not in (None, user['id']):
        raise DomainError('Only the nurse/counsellor assigned to this patient can record implementation', 403)
    if not e['decision']:
        raise ValueError('There is no approved decision to implement')
    if e.get('implemented_at'):
        raise ValueError('Implementation is already recorded')
    notes = str(data.get('implementation_notes', '')).strip()
    if not notes:
        raise ValueError('Describe how implementation was confirmed')
    start = data.get('start_date')
    start = date.fromisoformat(str(start)) if start else None
    if start and start > date.today():
        raise ValueError('Start date cannot be in the future')
    regimen = str(data.get('started_regimen') or '').strip()
    stop = data.get('previous_stop_date')
    stop = date.fromisoformat(str(stop)) if stop else None
    if e['decision'] in ('Switched', 'Substituted'):
        if not (start and regimen):
            raise ValueError('Record the date the patient started the new regimen and the regimen started')
        if stop and start and stop > start:
            raise ValueError('The previous regimen stop date cannot be after the new start date')
    else:
        start = start or date.today()
        regimen = regimen or (p.get('regimen') or '')
    con.execute('UPDATE episodes SET implemented_at=?,implementation_notes=?,start_date=?,started_regimen=?,previous_stop_date=? WHERE patient_id=?',
                (now(), notes, start.isoformat(), regimen, stop.isoformat() if stop else None, pid))
    if not con.execute('SELECT 1 FROM follow_ups WHERE patient_id=? AND assessed_on IS NULL', (pid,)).fetchone():
        con.execute('INSERT INTO follow_ups(patient_id,due_date,created_at) VALUES(?,?,?)', (pid, add_months(start, FOLLOW_UP_MONTHS).isoformat(), now()))
    if e['decision'] in ('Switched', 'Substituted') and regimen:
        con.execute('UPDATE patients SET regimen=? WHERE id=?', (regimen, pid))
    if p.get('assigned_to') is None:
        con.execute('UPDATE patients SET assigned_to=? WHERE id=?', (user['id'], pid))
    audit(con, user, 'decision implemented', pid, e, {k: str(v) for k, v in data.items()})
    from .record_service import overlay_changes
    overlay_changes(con, pid, {'ART started by patient': regimen, 'ART start date': start.isoformat()})


def record_follow_up(con, user, p, e, data):
    require(user, 'record_follow_up', p)
    pid = p['id']
    due = con.execute('SELECT * FROM follow_ups WHERE patient_id=? AND assessed_on IS NULL ORDER BY due_date LIMIT 1', (pid,)).fetchone()
    if not due:
        raise ValueError('No follow-up assessment is due; implementation must be recorded first')
    care = data.get('care_status')
    if care not in CARE_STATUS:
        raise ValueError('Choose the care status')
    vl, vl_date = data.get('vl_copies'), data.get('vl_date')
    if care == CARE_STATUS[0] and (vl is None or not vl_date):
        raise ValueError('Record the most recent viral load and its date')
    if vl_date and date.fromisoformat(str(vl_date)) > date.today():
        raise ValueError('Viral load date cannot be in the future')
    con.execute('UPDATE follow_ups SET assessed_on=?,vl_copies=?,vl_date=?,regimen=?,care_status=?,psychosocial=?,clinical_status=?,notes=?,actor_id=? WHERE id=?',
                (date.today().isoformat(), vl, str(vl_date) if vl_date else None, data.get('regimen') or p.get('regimen'), care,
                 data.get('psychosocial', ''), data.get('clinical_status', ''), data.get('notes', ''), user['id'], due['id']))
    done = con.execute('SELECT count(*) FROM follow_ups WHERE patient_id=? AND assessed_on IS NOT NULL', (pid,)).fetchone()[0]
    from .record_service import overlay_changes
    if vl is not None and done in (1, 2):
        label = 'VL 6 Months Post Decision' if done == 1 else 'VL 12 Months Post Decision'
        overlay_changes(con, pid, {label: str(vl), label + ': Date': str(vl_date)})
    if care == CARE_STATUS[0]:
        con.execute('INSERT INTO follow_ups(patient_id,due_date,created_at) VALUES(?,?,?)',
                    (pid, add_months(date.fromisoformat(due['due_date']), FOLLOW_UP_MONTHS).isoformat(), now()))
    overlay_changes(con, pid, {'Care Status': care})
    audit(con, user, 'follow-up assessment', pid, after={k: str(v) for k, v in data.items()})
