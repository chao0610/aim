import os
import time

import jwt

from aim.web.configs import (
    AIM_ACCESS_TOKEN_EXPIRE_HOURS,
    AIM_REFRESH_TOKEN_EXPIRE_DAYS,
    AIM_SECRET_KEY,
)

_ALGORITHM = 'HS256'


def _get_secret_key() -> str:
    key = os.environ.get(AIM_SECRET_KEY)
    if not key:
        raise ValueError(
            'AIM_SECRET_KEY environment variable is not set. '
            'Set it before starting the server.'
        )
    return key


def create_access_token(user_id: int, username: str) -> str:
    payload = {
        'user_id': user_id,
        'username': username,
        'type': 'access',
        'exp': time.time() + AIM_ACCESS_TOKEN_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=_ALGORITHM)


def create_refresh_token(user_id: int, username: str) -> str:
    payload = {
        'user_id': user_id,
        'username': username,
        'type': 'refresh',
        'exp': time.time() + AIM_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    }
    return jwt.encode(payload, _get_secret_key(), algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, _get_secret_key(), algorithms=[_ALGORITHM])
