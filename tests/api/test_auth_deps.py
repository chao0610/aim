import hashlib
import os
import time

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault('AIM_SECRET_KEY', 'test-secret-key')

from aim.storage.structured.sql_engine.models import AimUser, ApiToken, Base
from aim.web.api.auth.deps import get_current_user
from aim.web.api.auth import deps as deps_module


@pytest.fixture
def db_session():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def app_with_auth(db_session):
    """Create a minimal FastAPI app with auth dependency for testing."""
    # Override the DB session getter
    deps_module._get_db_session = lambda: db_session

    app = FastAPI()

    @app.get('/protected')
    async def protected(user: AimUser = Depends(get_current_user)):
        return {'user_id': user.id, 'username': user.username}

    return app


class TestGetCurrentUser:
    def test_no_auth_header_returns_401(self, app_with_auth):
        client = TestClient(app_with_auth)
        resp = client.get('/protected')
        assert resp.status_code == 401

    def test_valid_jwt_returns_user(self, app_with_auth, db_session):
        from aim.web.api.auth.jwt_utils import create_access_token

        user = AimUser(username='alice', password_hash='hash')
        db_session.add(user)
        db_session.commit()

        token = create_access_token(user_id=user.id, username='alice')
        client = TestClient(app_with_auth)
        resp = client.get('/protected', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        assert resp.json()['username'] == 'alice'

    def test_expired_jwt_returns_401(self, app_with_auth, db_session):
        import jwt as pyjwt

        user = AimUser(username='bob', password_hash='hash')
        db_session.add(user)
        db_session.commit()

        token = pyjwt.encode(
            {'user_id': user.id, 'username': 'bob', 'type': 'access', 'exp': time.time() - 10},
            'test-secret-key',
            algorithm='HS256',
        )
        client = TestClient(app_with_auth)
        resp = client.get('/protected', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 401

    def test_api_token_returns_user(self, app_with_auth, db_session):
        user = AimUser(username='carol', password_hash='hash')
        db_session.add(user)
        db_session.commit()

        raw_token = 'aim_tok_' + 'a' * 32
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        api_token = ApiToken(user_id=user.id, name='test', token_hash=token_hash)
        db_session.add(api_token)
        db_session.commit()

        client = TestClient(app_with_auth)
        resp = client.get('/protected', headers={'Authorization': f'Bearer {raw_token}'})
        assert resp.status_code == 200
        assert resp.json()['username'] == 'carol'

    def test_invalid_api_token_returns_401(self, app_with_auth):
        client = TestClient(app_with_auth)
        resp = client.get('/protected', headers={'Authorization': 'Bearer aim_tok_invalid'})
        assert resp.status_code == 401

    def test_refresh_token_rejected_as_access(self, app_with_auth, db_session):
        from aim.web.api.auth.jwt_utils import create_refresh_token

        user = AimUser(username='dave', password_hash='hash')
        db_session.add(user)
        db_session.commit()

        token = create_refresh_token(user_id=user.id, username='dave')
        client = TestClient(app_with_auth)
        resp = client.get('/protected', headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 401
