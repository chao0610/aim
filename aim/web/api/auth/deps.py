import hashlib

from fastapi import HTTPException, Request

from aim.storage.structured.sql_engine.models import AimUser, ApiToken
from aim.web.api.auth.jwt_utils import decode_token


def _get_db_session():
    """Get a DB session from the project repo. Overridable for testing."""
    from aim.web.api.utils import object_factory
    factory = object_factory()
    return factory.get_session()


async def get_current_user(request: Request) -> AimUser:
    """Extract and validate the current user from the Authorization header.

    Supports two formats:
    1. Bearer <jwt>          — web UI sessions
    2. Bearer aim_tok_<hex>  — Personal API Tokens
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing authentication token')

    token = auth_header[7:]  # strip 'Bearer '
    session = _get_db_session()

    # Personal API Token path
    if token.startswith('aim_tok_'):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        api_token = session.query(ApiToken).filter(ApiToken.token_hash == token_hash).first()
        if not api_token:
            raise HTTPException(status_code=401, detail='Invalid API token')
        user = session.query(AimUser).filter(AimUser.id == api_token.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail='Token user not found')
        return user

    # JWT path
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

    if payload.get('type') != 'access':
        raise HTTPException(status_code=401, detail='Invalid token type')

    user = session.query(AimUser).filter(AimUser.id == payload['user_id']).first()
    if not user:
        raise HTTPException(status_code=401, detail='User not found')

    return user
