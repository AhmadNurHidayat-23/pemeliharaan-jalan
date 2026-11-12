from pathlib import Path
import os
import sqlite3
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException
from core.db import initialize
from core.auth import auth
from core.security import Problem
from core.limit import BodyLimit
from .routes import api

def create_app(config=None):
    config = config or {}
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.folder = Path(config.get('INSTANCE_DIR') or os.getenv('APP_INSTANCE', './instance')).resolve()
    root = Path(__file__).parent
    initialize(app.state.folder, (root / 'schema.sql').read_text())
    templates = Jinja2Templates(directory=str(root / 'templates'))
    app.add_middleware(BodyLimit)

    @app.middleware('http')
    async def headers(request: Request, call_next):
        if request.method in ('POST', 'PUT', 'DELETE'):
            expected = request.url.scheme + '://' + request.headers.get('host', request.url.netloc)
            if request.headers.get('Origin') and request.headers['Origin'] != expected:
                return JSONResponse({'error': 'Asal permintaan tidak diizinkan.'}, 403)
            if not request.headers.get('Content-Type', '').startswith('application/json'):
                return JSONResponse({'error': 'Format permintaan tidak valid.'}, 415)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'"
        return response

    @app.get('/')
    async def index(request: Request):
        return templates.TemplateResponse(request=request, name='index.html', context={})

    @app.exception_handler(Problem)
    async def problem(_request: Request, error: Problem):
        return JSONResponse({'error': str(error)}, error.status)

    @app.exception_handler(sqlite3.IntegrityError)
    async def integrity(_request: Request, _error):
        return JSONResponse({'error': 'Data sudah digunakan atau masih memiliki relasi yang harus dipertahankan.'}, 409)

    @app.exception_handler(RequestValidationError)
    async def validation(_request: Request, _error):
        return JSONResponse({'error': 'ID atau format permintaan tidak valid.'}, 400)

    @app.exception_handler(HTTPException)
    async def http_error(_request: Request, error: HTTPException):
        return JSONResponse({'error': 'Alamat atau format permintaan tidak valid.'}, error.status_code)

    app.include_router(auth)
    app.include_router(api)
    app.mount('/static', StaticFiles(directory=str(root / 'static')), name='static')
    return app
