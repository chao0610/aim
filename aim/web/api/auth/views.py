import bcrypt
from fastapi import HTTPException
from pydantic import BaseModel

from aim.storage.structured.sql_engine.models import AimUser
from aim.web.api.auth import deps as auth_deps
from aim.web.api.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
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
    token_type: str = 'bearer'


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


@auth_router.post('/login', response_model=TokenResponse)
async def login(body: LoginRequest):
    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.username == body.username).first()
    if not user:
        raise HTTPException(status_code=401, detail='Invalid username or password')

    if not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(status_code=401, detail='Invalid username or password')

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id, user.username),
    )


@auth_router.post('/refresh', response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')

    if payload.get('type') != 'refresh':
        raise HTTPException(status_code=401, detail='Invalid token type')

    return AccessTokenResponse(
        access_token=create_access_token(payload['user_id'], payload['username']),
    )
