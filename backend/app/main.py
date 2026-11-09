from contextlib import asynccontextmanager
import sqlite3
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .core.bootstrap import initialize
from .core.config import FRONTEND_ORIGINS
from .core.errors import DomainError
from .routers import auth, patients, risk, lab, decisions, discussions, settings, notifications, integrations

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title='HIVDR Surveillance API', version='0.2.0', lifespan=lifespan)

@app.middleware('http')
async def protect_requests(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in FRONTEND_ORIGINS:
        return JSONResponse({'error': 'Origin not permitted'}, status_code=403)
    length = request.headers.get('content-length', '0')
    if length.isdigit() and int(length) > 42000000:
        return JSONResponse({'error': 'Request too large'}, status_code=413)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

@app.exception_handler(DomainError)
async def domain_error(request, error):
    return JSONResponse({'error': str(error)}, status_code=error.status_code)

@app.exception_handler(ValueError)
async def validation_error(request, error):
    return JSONResponse({'error': str(error)}, status_code=400)

@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error(request, error):
    return JSONResponse({'error': 'Duplicate record or invalid relationship. No changes were committed.'}, status_code=409)

for router in (auth, patients, risk, lab, decisions, discussions, settings, notifications, integrations):
    app.include_router(router.router)

@app.get('/api/health', tags=['Health'])
def health():
    return {'status': 'ok', 'version': '0.2.0'}
