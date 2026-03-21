import os

os.environ.setdefault('AIM_SECRET_KEY', 'test-secret-key')

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import bcrypt

from aim.storage.structured.sql_engine.models import AimUser, ApiToken, Base


@pytest.fixture
def db_session():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
    )

    connection = engine.connect()

    @event.listens_for(engine, 'connect')
    def _set_sqlite_pragma(dbapi_conn, _rec):
        dbapi_conn.execute('PRAGMA journal_mode=WAL')

    Base.metadata.create_all(bind=connection)
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    connection.close()


@pytest.fixture
def app(db_session):
    from aim.web.api.auth import deps
    from aim.web.api.auth.deps import get_current_user
    from aim.web.api.settings.views import settings_router

    deps._get_db_session = lambda: db_session

    app = FastAPI()
    app.include_router(settings_router, prefix='/api/settings', dependencies=[Depends(get_current_user)])
    return app


@pytest.fixture
def alice(db_session):
    pw_hash = bcrypt.hashpw(b'pass', bcrypt.gensalt()).decode()
    user = AimUser(username='alice', password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def bob(db_session):
    pw_hash = bcrypt.hashpw(b'pass', bcrypt.gensalt()).decode()
    user = AimUser(username='bob', password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def auth_headers(alice):
    from aim.web.api.auth.jwt_utils import create_access_token

    token = create_access_token(alice.id, 'alice')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def bob_auth_headers(bob):
    from aim.web.api.auth.jwt_utils import create_access_token

    token = create_access_token(bob.id, 'bob')
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def client(app):
    return TestClient(app)


class TestListTokens:
    def test_empty_list(self, client, auth_headers):
        resp = client.get('/api/settings/tokens', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_own_tokens(self, client, auth_headers, alice, db_session):
        import hashlib

        token_hash = hashlib.sha256(b'aim_tok_abc123').hexdigest()
        t = ApiToken(user_id=alice.id, name='my-token', token_hash=token_hash)
        db_session.add(t)
        db_session.commit()

        resp = client.get('/api/settings/tokens', headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['name'] == 'my-token'
        assert data[0]['id'] == t.id
        assert 'created_at' in data[0]
        # Raw token should NOT be in the response
        assert 'token' not in data[0]
        assert 'token_hash' not in data[0]

    def test_list_does_not_return_other_users_tokens(self, client, auth_headers, bob, db_session):
        import hashlib

        token_hash = hashlib.sha256(b'aim_tok_bob1').hexdigest()
        t = ApiToken(user_id=bob.id, name='bob-token', token_hash=token_hash)
        db_session.add(t)
        db_session.commit()

        resp = client.get('/api/settings/tokens', headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unauthenticated(self, client):
        resp = client.get('/api/settings/tokens')
        assert resp.status_code == 401


class TestCreateToken:
    def test_create_token(self, client, auth_headers):
        resp = client.post('/api/settings/tokens', json={'name': 'ci-token'}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == 'ci-token'
        assert data['token'].startswith('aim_tok_')
        assert len(data['token']) == 8 + 32  # 'aim_tok_' + 16 hex bytes
        assert 'id' in data
        assert 'created_at' in data

    def test_created_token_appears_in_list(self, client, auth_headers):
        resp = client.post('/api/settings/tokens', json={'name': 'deploy'}, headers=auth_headers)
        assert resp.status_code == 201

        resp = client.get('/api/settings/tokens', headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]['name'] == 'deploy'

    def test_create_multiple_tokens(self, client, auth_headers):
        client.post('/api/settings/tokens', json={'name': 'tok1'}, headers=auth_headers)
        client.post('/api/settings/tokens', json={'name': 'tok2'}, headers=auth_headers)

        resp = client.get('/api/settings/tokens', headers=auth_headers)
        assert len(resp.json()) == 2

    def test_unauthenticated(self, client):
        resp = client.post('/api/settings/tokens', json={'name': 'ci-token'})
        assert resp.status_code == 401


class TestDeleteToken:
    def test_delete_own_token(self, client, auth_headers):
        resp = client.post('/api/settings/tokens', json={'name': 'temp'}, headers=auth_headers)
        token_id = resp.json()['id']

        resp = client.delete(f'/api/settings/tokens/{token_id}', headers=auth_headers)
        assert resp.status_code == 204

        resp = client.get('/api/settings/tokens', headers=auth_headers)
        assert resp.json() == []

    def test_delete_nonexistent_token(self, client, auth_headers):
        resp = client.delete('/api/settings/tokens/9999', headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_other_users_token(self, client, auth_headers, bob_auth_headers):
        # Bob creates a token
        resp = client.post('/api/settings/tokens', json={'name': 'bob-tok'}, headers=bob_auth_headers)
        token_id = resp.json()['id']

        # Alice tries to delete it
        resp = client.delete(f'/api/settings/tokens/{token_id}', headers=auth_headers)
        assert resp.status_code == 404

        # Bob's token should still exist
        resp = client.get('/api/settings/tokens', headers=bob_auth_headers)
        assert len(resp.json()) == 1

    def test_unauthenticated(self, client):
        resp = client.delete('/api/settings/tokens/1')
        assert resp.status_code == 401
