import bcrypt

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from aim.storage.structured.sql_engine.models import AimUser
from aim.web.api.auth import deps as auth_deps
from aim.web.api.auth.deps import get_current_user
from aim.web.api.utils import APIRouter

admin_router = APIRouter()


def _require_admin(current_user: AimUser = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail='Admin access required')
    return current_user


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class ResetPasswordRequest(BaseModel):
    password: str


@admin_router.get('/users')
async def list_users(admin: AimUser = Depends(_require_admin)):
    session = auth_deps._get_db_session()
    users = session.query(AimUser).all()
    return [
        {'id': u.id, 'username': u.username, 'is_admin': u.is_admin, 'created_at': str(u.created_at)}
        for u in users
    ]


@admin_router.post('/users')
async def create_user(body: CreateUserRequest, admin: AimUser = Depends(_require_admin)):
    session = auth_deps._get_db_session()
    existing = session.query(AimUser).filter(AimUser.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f'User "{body.username}" already exists')
    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = AimUser(username=body.username, password_hash=pw_hash, is_admin=body.is_admin)
    session.add(user)
    session.commit()
    return {'id': user.id, 'username': user.username, 'status': 'OK'}


@admin_router.put('/users/{user_id}/reset-password')
async def reset_user_password(
    user_id: int, body: ResetPasswordRequest, admin: AimUser = Depends(_require_admin)
):
    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    session.commit()
    return {'username': user.username, 'status': 'OK'}
