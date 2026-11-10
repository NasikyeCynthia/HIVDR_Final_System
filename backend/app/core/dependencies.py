import time
from fastapi import Cookie
from .database import connect
from .errors import DomainError

def current_user(session: str | None = Cookie(default=None)):
    if not session:
        raise DomainError('Please sign in', 401)
    with connect() as con:
        row = con.execute('SELECT u.id,u.username,u.name,u.role,u.facility,u.can_access_all FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?', (session, time.time())).fetchone()
    if row is None:
        raise DomainError('Your session has expired. Please sign in again.', 401)
    return dict(row)
