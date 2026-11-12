"""Viral load samples: a sample is recorded when blood is taken, and its result is added when it
comes back. The indication follows the MoH/CPHL viral load request form. Results are written into the
patient's viral load history (viral_load_test_N, dated by the sample date), so the eligibility rules,
the risk score and the time-to-failure measure all use them."""
import json
import re
from datetime import date
from ..core.database import now
from ..core.permissions import require
from .audit_service import audit
from .eligibility_service import parse_vl, vl_timeline

INDICATIONS = ('6 months after ART initiation', '12 months after ART initiation', 'Routine', 'Repeat (after IAC)',
               'Suspected treatment failure', 'ANC / PMTCT', 'Special')
RESULT_STATES = ('Resulted', 'Failed / invalid')


def _day(value, label):
    try:
        day = date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValueError(f'{label}: enter a valid date')
    if day > date.today():
        raise ValueError(f'{label} cannot be in the future')
    return day


def list_samples(con, pid):
    return [dict(r) for r in con.execute(
        'SELECT s.*,a.name AS collected_by_name,b.name AS resulted_by_name FROM vl_samples s '
        'LEFT JOIN users a ON s.collected_by=a.id LEFT JOIN users b ON s.resulted_by=b.id '
        'WHERE patient_id=? ORDER BY collected_on DESC,id DESC', (pid,))]


def record_sample(con, user, p, e, data):
    require(user, 'edit_patient_record', p)
    collected = _day(data.get('collected_on'), 'Sample date')
    indication = data.get('indication')
    if indication not in INDICATIONS:
        raise ValueError('Choose the indication for viral load testing')
    if con.execute("SELECT 1 FROM vl_samples WHERE patient_id=? AND collected_on=? AND status='Pending'", (p['id'], collected.isoformat())).fetchone():
        raise ValueError('A viral load sample from this date is already waiting for its result')
    cur = con.execute('INSERT INTO vl_samples(patient_id,collected_on,indication,status,collected_by,created_at) VALUES(?,?,?,?,?,?)',
                      (p['id'], collected.isoformat(), indication, 'Pending', user['id'], now()))
    audit(con, user, 'viral load sample taken', p['id'], after={'sample_id': cur.lastrowid, **{k: str(v) for k, v in data.items()}})
    if data.get('result'):
        record_result(con, user, p, e, {'sample_id': cur.lastrowid, 'result': data['result'], 'result_date': data.get('result_date') or collected.isoformat()})


def record_result(con, user, p, e, data):
    if user['role'] not in ('nurse', 'counsellor', 'lab'):
        require(user, 'edit_patient_record', p)
    sample = con.execute('SELECT * FROM vl_samples WHERE id=? AND patient_id=?', (data.get('sample_id'), p['id'])).fetchone()
    if not sample:
        raise ValueError('Viral load sample not found')
    correcting = sample['status'] != 'Pending'
    reason = str(data.get('correction_reason') or '').strip()
    if correcting and len(reason) < 10:
        raise ValueError('This sample already has a result: explain the correction (at least 10 characters)')
    released = _day(data.get('result_date'), 'Result date')
    if released < date.fromisoformat(sample['collected_on']):
        raise ValueError('The result date cannot be before the sample date')
    text = str(data.get('result') or '').strip()
    failed = bool(data.get('failed'))
    if not failed:
        if not parse_vl(text):
            raise ValueError('Enter the result as copies/mL (e.g. 25000, <20 or "Target not detected"), or mark the test as failed')
    status = 'Failed / invalid' if failed else 'Resulted'
    con.execute('UPDATE vl_samples SET result=?,result_date=?,status=?,failure_reason=?,resulted_by=?,resulted_at=? WHERE id=?',
                ('' if failed else text, released.isoformat(), status, str(data.get('failure_reason') or '') if failed else '',
                 user['id'], now(), sample['id']))
    # write into the dated viral load history used by the clinical rules
    from .record_service import overlay_changes
    raw = {**json.loads(p.get('original_json') or '{}'), **json.loads(p.get('source_overrides_json') or '{}')}
    key = sample['history_key']
    if not key:
        n = 1 + max([int(k.rsplit('_', 1)[1]) for k in raw if re.fullmatch(r'viral_load_test_\d+', k)] or [0])
        key = f'viral_load_test_{n}'
        con.execute('UPDATE vl_samples SET history_key=? WHERE id=?', (key, sample['id']))
    overlay_changes(con, p['id'], {key: '' if failed else text, key + '_date': '' if failed else sample['collected_on']})
    # the profile viral load is the most recent dated result
    raw.update({key: '' if failed else text, key + '_date': '' if failed else sample['collected_on']})
    latest = [o for o in vl_timeline(raw) if o['kind'] == 'pre']
    if latest:
        con.execute('UPDATE patients SET viral_load=? WHERE id=?', (latest[-1]['copies'], p['id']))
    audit(con, user, 'viral load result corrected' if correcting else 'viral load result recorded', p['id'],
          before=dict(sample), after={k: str(v) for k, v in data.items()})
