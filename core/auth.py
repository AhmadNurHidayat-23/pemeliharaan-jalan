import os
import re
import secrets
from dataclasses import dataclass
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from .db import connect
from .security import Problem, get_session, authenticate, new_session
auth = APIRouter()

@dataclass
class Context:
    db: object
    session: dict | None
    user: dict | None

async def context(request: Request):
    db = connect(request.app.state.folder)
    try:
        session = get_session(db, request.cookies.get('pemeliharaan_jalan_session'))
        user = {k: session[k] for k in ('id', 'username', 'name', 'role')} if session else None
        yield Context(db, session, user)
    finally:
        db.close()

def require(ctx, request, roles=('Admin', 'Petugas')):
    if not ctx.user:
        raise Problem('Silakan masuk terlebih dahulu.', 401)
    if ctx.user['role'] not in roles:
        raise Problem('Tindakan ini hanya untuk Admin.', 403)
    if request.method != 'GET':
        token = request.headers.get('X-CSRF-Token', '')
        if not re.fullmatch(r'[a-f0-9]{64}', token) or not secrets.compare_digest(ctx.session['csrf'], token):
            raise Problem('Sesi formulir tidak valid. Muat ulang halaman.', 403)
    return ctx.user

async def data(request):
    try:
        value = await request.json()
    except ValueError:
        raise Problem('Format data tidak valid.')
    if not isinstance(value, dict):
        raise Problem('Format data tidak valid.')
    return value

from fastapi import Depends

@auth.get('/api/session')
async def session(ctx=Depends(context)):
    return {'user': ctx.user, 'csrf': ctx.session['csrf'] if ctx.session else None,
            'configured': ctx.db.execute('SELECT id FROM users LIMIT 1').fetchone() is not None}

@auth.post('/api/login')
async def login(request: Request, ctx=Depends(context)):
    values = await data(request)
    id, key = authenticate(ctx.db, values.get('username', ''), values.get('password', ''))
    token, csrf = new_session(ctx.db, id, ctx.session, key)
    user = dict(ctx.db.execute('SELECT id,username,name,role FROM users WHERE id=?', (id,)).fetchone())
    response = JSONResponse({'user': user, 'csrf': csrf})
    response.set_cookie('pemeliharaan_jalan_session', token, max_age=28800, httponly=True, samesite='Strict', secure=os.getenv('SECURE_COOKIE') == '1')
    return response

@auth.post('/api/logout')
async def logout(request: Request, ctx=Depends(context)):
    require(ctx, request)
    with ctx.db:
        ctx.db.execute('DELETE FROM sessions WHERE token=?', (ctx.session['token'],))
    response = JSONResponse({'message': 'Anda telah keluar.'})
    response.delete_cookie('pemeliharaan_jalan_session', path='/')
    return response
