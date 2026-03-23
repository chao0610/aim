import hashlib
import os
from datetime import datetime

import bcrypt
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel

from aim.storage.structured.sql_engine.models import AimUser, ApiToken
from aim.web.api.auth import deps as auth_deps
from aim.web.api.auth.deps import get_current_user
from aim.web.api.utils import APIRouter

settings_router = APIRouter()


class CreateTokenRequest(BaseModel):
    name: str


class TokenOut(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        orm_mode = True


class TokenCreatedOut(BaseModel):
    id: int
    name: str
    token: str
    created_at: datetime


@settings_router.get('/tokens')
async def list_tokens(user: AimUser = Depends(get_current_user)):
    session = auth_deps._get_db_session()
    tokens = session.query(ApiToken).filter(ApiToken.user_id == user.id).all()
    return [
        TokenOut(id=t.id, name=t.name, created_at=t.created_at)
        for t in tokens
    ]


@settings_router.post('/tokens', status_code=201)
async def create_token(body: CreateTokenRequest, user: AimUser = Depends(get_current_user)):
    raw_token = 'aim_tok_' + os.urandom(16).hex()
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    session = auth_deps._get_db_session()
    api_token = ApiToken(user_id=user.id, name=body.name, token_hash=token_hash)
    session.add(api_token)
    session.commit()
    session.refresh(api_token)

    return TokenCreatedOut(
        id=api_token.id,
        name=api_token.name,
        token=raw_token,
        created_at=api_token.created_at,
    )


@settings_router.delete('/tokens/{token_id}', status_code=204)
async def delete_token(token_id: int, user: AimUser = Depends(get_current_user)):
    session = auth_deps._get_db_session()
    api_token = (
        session.query(ApiToken)
        .filter(ApiToken.id == token_id, ApiToken.user_id == user.id)
        .first()
    )
    if not api_token:
        raise HTTPException(status_code=404, detail='Token not found')

    session.delete(api_token)
    session.commit()
    return Response(status_code=204)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@settings_router.post('/change-password')
async def change_password(body: ChangePasswordRequest, user: AimUser = Depends(get_current_user)):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail='Password must be at least 8 characters')

    session = auth_deps._get_db_session()
    db_user = session.query(AimUser).filter(AimUser.id == user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail='User not found')

    if not bcrypt.checkpw(body.current_password.encode(), db_user.password_hash.encode()):
        raise HTTPException(status_code=400, detail='Current password is incorrect')

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt()).decode()
    db_user.password_hash = new_hash
    session.commit()

    return {'status': 'OK'}
