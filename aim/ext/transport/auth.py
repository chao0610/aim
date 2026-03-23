"""Transport server auth: validates Bearer tokens and resolves user_id.

Supports two formats:
1. Bearer aim_tok_<hex>  — Personal API Tokens (validated via SHA-256 hash lookup)
2. Bearer <jwt>          — JWT access tokens (validated via decode + user lookup)

If AIM_SECRET_KEY is not set, auth is disabled and user_id will be None.
"""
import hashlib
import logging
import os

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def _get_structured_db():
    """Get the structured DB from the repo. Overridable for testing."""
    from aim.ext.transport.config import AIM_SERVER_MOUNTED_REPO_PATH
    from aim.sdk import Repo

    repo_path = os.environ.get(AIM_SERVER_MOUNTED_REPO_PATH)
    if repo_path:
        repo = Repo.from_path(repo_path)
    else:
        repo = Repo.default_repo()
    return repo.structured_db


def resolve_user_id_from_request(request: Request) -> int | None:
    """Extract user_id from the request Authorization header.

    Returns None if auth is not configured (AIM_SECRET_KEY not set).
    Raises HTTPException 401 if auth is configured but token is invalid.
    """
    from aim.web.configs import AIM_SECRET_KEY

    secret_key = os.environ.get(AIM_SECRET_KEY)
    if not secret_key:
        # AIM_SECRET_KEY is enforced at startup; this is a safety fallback
        raise HTTPException(status_code=500, detail='Server misconfigured: AIM_SECRET_KEY not set')

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing authentication token')

    token = auth_header[7:]
    db = _get_structured_db()
    session = db.get_session()

    from aim.storage.structured.sql_engine.models import AimUser, ApiToken

    # API token path
    if token.startswith('aim_tok_'):
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        api_token = session.query(ApiToken).filter(ApiToken.token_hash == token_hash).first()
        if not api_token:
            raise HTTPException(status_code=401, detail='Invalid API token')
        return api_token.user_id

    # JWT path
    try:
        from aim.web.api.auth.jwt_utils import decode_token

        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired token')

    if payload.get('type') != 'access':
        raise HTTPException(status_code=401, detail='Invalid token type')

    user = session.query(AimUser).filter(AimUser.id == payload['user_id']).first()
    if not user:
        raise HTTPException(status_code=401, detail='User not found')

    return user.id
