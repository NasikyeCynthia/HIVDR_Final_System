import hmac
import secrets
import time
from threading import Lock
from fastapi import APIRouter, Depends, Request, Response, Cookie
from ..core.database import connect
from ..core.dependencies import current_user
from ..core.errors import DomainError
from ..core.security import password_hash
from ..schemas.auth import LoginRequest
from ..services.audit_service import audit

router = APIRouter(prefix='/api/auth', tags=['Authentication'])
attempts = {}
lock = Lock()

@router.post('/login')
def login(data: LoginRequest, request: Request, response: Response):
    ip = request.client.host if request.client else 'local'
    with lock:
        recent = [stamp for stamp in attempts.get(ip, []) if time.time() - stamp < 60]
        attempts[ip] = recent + [time.time()]
    if len(recent) >= 15:
        raise DomainError('Too many sign-in attempts. Try again in one minute.', 429)
    with connect() as con:
        user = con.execute('SELECT * FROM users WHERE username=?', (data.username,)).fetchone()
        if user is None or not hmac.compare_digest(user['password_hash'], password_hash(data.password, user['salt'])):
            raise DomainError('Incorrect username or password', 401)
        token = secrets.token_urlsafe(32)
        con.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        con.execute('INSERT INTO sessions VALUES(?,?,?)', (token, user['id'], time.time()+28800))
        audit(con, user, 'login', 'session')
    response.set_cookie('session', token, httponly=True, samesite='strict', max_age=28800)
    return {'ok': True}

@router.get('/me')
def me(user=Depends(current_user)):
    return user

@router.post('/logout')
def logout(response: Response, session: str | None = Cookie(default=None), user=Depends(current_user)):
    with connect() as con:
        con.execute('DELETE FROM sessions WHERE token=?', (session,))
        audit(con, user, 'logout', 'session')
    response.delete_cookie('session')
    return {'ok': True}
