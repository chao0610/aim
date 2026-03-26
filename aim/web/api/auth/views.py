import hashlib
import hmac
import os
import time

import bcrypt
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from aim.storage.structured.sql_engine.models import AimUser
from aim.web.api.auth import deps as auth_deps
from aim.web.api.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from aim.web.configs import AIM_SSO_SECRET_KEY, AIM_SSO_TOKEN_EXPIRE_SECONDS
from aim.web.api.utils import APIRouter

auth_router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'Bearer'


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


@auth_router.post('/login', response_model=TokenResponse)
async def login(body: LoginRequest):
    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.username == body.username).first()
    if not user:
        raise HTTPException(status_code=401, detail='Invalid username or password')

    if not user.password_hash or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail='Invalid username or password')

    role = getattr(user, 'role', 'editor')
    return TokenResponse(
        access_token=create_access_token(user.id, user.username, role),
        refresh_token=create_refresh_token(user.id, user.username),
    )


@auth_router.get('/refresh')
async def refresh_get():
    """Old frontend sends GET /refresh; return 401 so the client redirects to /sign-in."""
    raise HTTPException(status_code=401, detail='Token expired or missing')


@auth_router.post('/refresh', response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')

    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail='Invalid token type')

    # Look up current role from DB
    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.id == payload['user_id']).first()
    role = getattr(user, 'role', 'editor') if user else 'editor'

    return AccessTokenResponse(
        access_token=create_access_token(payload['user_id'], payload['username'], role),
    )


def _get_sso_secret() -> str:
    key = os.environ.get(AIM_SSO_SECRET_KEY, '')
    if not key:
        raise HTTPException(status_code=500, detail='AIM_SSO_SECRET_KEY not configured')
    return key


@auth_router.get('/sso/callback')
async def sso_callback(email: str, ts: str, sig: str):
    """SSO callback: validate HMAC signature, find/create user, issue JWT, redirect."""
    # Validate signature
    secret = _get_sso_secret()
    message = f'{email}:{ts}'
    expected_sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail='Invalid SSO signature')

    # Validate timestamp (within AIM_SSO_TOKEN_EXPIRE_SECONDS)
    try:
        ts_float = float(ts)
    except ValueError:
        raise HTTPException(status_code=400, detail='Invalid timestamp')

    if abs(time.time() - ts_float) > AIM_SSO_TOKEN_EXPIRE_SECONDS:
        raise HTTPException(status_code=401, detail='SSO token expired')

    # Find or create user
    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.username == email).first()
    if not user:
        user = AimUser(username=email, password_hash='', role=AimUser.ROLE_VIEWER)
        session.add(user)
        session.commit()

    # Issue JWT tokens
    role = getattr(user, 'role', 'viewer')
    access_token = create_access_token(user.id, user.username, role)
    refresh_token = create_refresh_token(user.id, user.username)

    # Redirect to frontend SSO callback page with tokens in query params
    base_path = os.environ.get('__AIM_UI_BASE_PATH__', '')
    redirect_url = (
        f'{base_path}/sso/callback'
        f'?access_token={access_token}'
        f'&refresh_token={refresh_token}'
        f'&token_type=Bearer'
    )
    return RedirectResponse(url=redirect_url, status_code=302)
