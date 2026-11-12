"""Intensive adherence counselling (IAC) sessions with pill-count adherence scores."""
from datetime import date
from ..core.errors import DomainError
from ..core.database import now
from .audit_service import audit


def _check(user, p):
    from ..core.permissions import require
    require(user, 'record_iac', p)


def add_session(con, user, p, e, data):
    _check(user, p)
    day = data['session_date']
    if isinstance(day, str):
        day = date.fromisoformat(day)
    if day > date.today():
        raise ValueError('IAC session date cannot be in the future')
    pct = float(data['adherence_pct'])
    cur = con.execute('INSERT INTO iac_sessions(patient_id,session_date,adherence_pct,method,barriers,actor_id,created_at) VALUES(?,?,?,?,?,?,?)',
                      (p['id'], day.isoformat(), pct, data.get('method') or 'Pill count', data.get('barriers', ''), user['id'], now()))
    # Keep the profile's adherence field as the most recent recorded score.
    latest = con.execute('SELECT adherence_pct FROM iac_sessions WHERE patient_id=? ORDER BY session_date DESC,id DESC LIMIT 1', (p['id'],)).fetchone()
    con.execute('UPDATE patients SET adherence=? WHERE id=?', (min(latest[0], 100) if latest[0] is not None else None, p['id']))
    audit(con, user, 'IAC session recorded', p['id'], after={'id': cur.lastrowid, **{k: str(v) for k, v in data.items()}})


def delete_session(con, user, p, e, data):
    _check(user, p)
    row = con.execute('SELECT * FROM iac_sessions WHERE id=? AND patient_id=?', (data['session_id'], p['id'])).fetchone()
    if not row:
        raise DomainError('IAC session not found', 404)
    if e.get('referred_at'):
        raise DomainError('IAC sessions that supported a referral are locked; use the amendment workflow', 409)
    con.execute('DELETE FROM iac_sessions WHERE id=?', (row['id'],))
    audit(con, user, 'IAC session removed', p['id'], before=dict(row))
