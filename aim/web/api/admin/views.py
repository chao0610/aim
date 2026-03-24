import bcrypt

from fastapi import Depends, HTTPException
from pydantic import BaseModel

from aim.storage.structured.sql_engine.models import AimUser
from aim.web.api.auth import deps as auth_deps
from aim.web.api.auth.deps import require_admin
from aim.web.api.utils import APIRouter

admin_router = APIRouter()


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False
    role: str = 'editor'


class ResetPasswordRequest(BaseModel):
    password: str


class UpdateRoleRequest(BaseModel):
    role: str


@admin_router.get('/users')
async def list_users(admin: AimUser = Depends(require_admin)):
    session = auth_deps._get_db_session()
    users = session.query(AimUser).all()
    return [
        {
            'id': u.id,
            'username': u.username,
            'is_admin': u.is_admin,
            'role': getattr(u, 'role', 'editor'),
            'created_at': str(u.created_at),
        }
        for u in users
    ]


@admin_router.post('/users')
async def create_user(body: CreateUserRequest, admin: AimUser = Depends(require_admin)):
    session = auth_deps._get_db_session()
    existing = session.query(AimUser).filter(AimUser.username == body.username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f'User "{body.username}" already exists')

    if body.role not in ('viewer', 'editor', 'admin'):
        raise HTTPException(status_code=400, detail='Invalid role. Must be viewer, editor, or admin')

    pw_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    user = AimUser(
        username=body.username,
        password_hash=pw_hash,
        is_admin=body.is_admin or body.role == 'admin',
        role=body.role,
    )
    session.add(user)
    session.commit()
    return {'id': user.id, 'username': user.username, 'role': user.role, 'status': 'OK'}


@admin_router.put('/users/{user_id}/reset-password')
async def reset_user_password(
    user_id: int, body: ResetPasswordRequest, admin: AimUser = Depends(require_admin)
):
    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')
    user.password_hash = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    session.commit()
    return {'username': user.username, 'status': 'OK'}


@admin_router.put('/users/{user_id}/role')
async def update_user_role(
    user_id: int, body: UpdateRoleRequest, admin: AimUser = Depends(require_admin)
):
    if body.role not in ('viewer', 'editor', 'admin'):
        raise HTTPException(status_code=400, detail='Invalid role. Must be viewer, editor, or admin')

    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    user.role = body.role
    user.is_admin = (body.role == 'admin')
    session.commit()
    return {'username': user.username, 'role': user.role, 'status': 'OK'}


@admin_router.delete('/users/{user_id}')
async def delete_user(user_id: int, admin: AimUser = Depends(require_admin)):
    session = auth_deps._get_db_session()
    user = session.query(AimUser).filter(AimUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail='Cannot delete yourself')

    # Delete user's API tokens first
    from aim.storage.structured.sql_engine.models import ApiToken
    session.query(ApiToken).filter(ApiToken.user_id == user.id).delete()
    session.delete(user)
    session.commit()
    return {'username': user.username, 'status': 'deleted'}
