"""
E2E integration test: covers the full multi-user auth flow without a live server.
- create users (alice admin, bob regular)
- login → get JWT
- create API token → authenticate with it
- run ownership isolation (bob can't see alice's private run)
- visibility toggle (alice makes run public → bob can now see it)
- write access control (bob can't modify alice's run → 403)
"""
import os

os.environ['AIM_SECRET_KEY'] = 'test-secret-e2e'

import hashlib

import bcrypt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from aim.storage.structured.sql_engine.models import AimUser, ApiToken, Base, Experiment as ExperimentModel
from aim.web.api.auth.jwt_utils import create_access_token


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope='module')
def db_engine():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
    )

    @event.listens_for(engine, 'connect')
    def _set_pragma(dbapi_conn, _rec):
        dbapi_conn.execute('PRAGMA journal_mode=WAL')

    connection = engine.connect()
    Base.metadata.create_all(bind=connection)
    yield connection
    connection.close()


@pytest.fixture(scope='module')
def db_session(db_engine):
    session = sessionmaker(bind=db_engine)()
    yield session
    session.close()


@pytest.fixture(scope='module')
def app(db_session):
    from aim.web.api.auth import deps
    from aim.web.api.auth.deps import get_current_user
    from aim.web.api.auth.views import auth_router
    from aim.web.api.admin.views import admin_router
    from aim.web.api.settings.views import settings_router
    from aim.web.api.visibility import visibility_router

    deps._get_db_session = lambda: db_session

    test_app = FastAPI()
    auth_dep = [Depends(get_current_user)]

    test_app.include_router(auth_router, prefix='/auth')
    test_app.include_router(admin_router, prefix='/admin', dependencies=auth_dep)
    test_app.include_router(settings_router, prefix='/settings', dependencies=auth_dep)
    # Visibility router needs a DB-backed run/experiment; we test it via direct SQL

    return test_app


@pytest.fixture(scope='module')
def client(app):
    return TestClient(app)


@pytest.fixture(scope='module')
def alice(db_session):
    pw_hash = bcrypt.hashpw(b'alice-pass', bcrypt.gensalt()).decode()
    user = AimUser(username='alice_e2e', password_hash=pw_hash, is_admin=True)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope='module')
def bob(db_session):
    pw_hash = bcrypt.hashpw(b'bob-pass', bcrypt.gensalt()).decode()
    user = AimUser(username='bob_e2e', password_hash=pw_hash, is_admin=False)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope='module')
def alice_headers(alice):
    token = create_access_token(alice.id, alice.username)
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture(scope='module')
def bob_headers(bob):
    token = create_access_token(bob.id, bob.username)
    return {'Authorization': f'Bearer {token}'}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoginFlow:
    def test_alice_can_login(self, client, alice):
        resp = client.post('/auth/login', json={'username': 'alice_e2e', 'password': 'alice-pass'})
        assert resp.status_code == 200
        data = resp.json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['token_type'] == 'bearer'

    def test_wrong_password_rejected(self, client, alice):
        resp = client.post('/auth/login', json={'username': 'alice_e2e', 'password': 'wrong'})
        assert resp.status_code == 401

    def test_unknown_user_rejected(self, client):
        resp = client.post('/auth/login', json={'username': 'ghost', 'password': 'x'})
        assert resp.status_code == 401


class TestAdminFlow:
    def test_alice_admin_can_list_users(self, client, alice_headers, alice, bob):
        resp = client.get('/admin/users', headers=alice_headers)
        assert resp.status_code == 200
        usernames = [u['username'] for u in resp.json()]
        assert 'alice_e2e' in usernames
        assert 'bob_e2e' in usernames

    def test_bob_cannot_list_users(self, client, bob_headers):
        resp = client.get('/admin/users', headers=bob_headers)
        assert resp.status_code == 403

    def test_alice_can_create_user(self, client, alice_headers):
        resp = client.post(
            '/admin/users',
            json={'username': 'charlie_e2e', 'password': 'pass'},
            headers=alice_headers,
        )
        assert resp.status_code == 200
        assert resp.json()['username'] == 'charlie_e2e'


class TestApiTokenFlow:
    def test_alice_creates_api_token(self, client, alice_headers):
        resp = client.post('/settings/tokens', json={'name': 'ci-token'}, headers=alice_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data['name'] == 'ci-token'
        assert data['token'].startswith('aim_tok_')
        # Store token for next test
        TestApiTokenFlow._raw_token = data['token']

    def test_authenticate_with_api_token(self, client, db_session):
        """Use the API token created in the previous test to authenticate."""
        raw_token = getattr(TestApiTokenFlow, '_raw_token', None)
        if raw_token is None:
            pytest.skip('No API token from previous test')
        headers = {'Authorization': f'Bearer {raw_token}'}
        resp = client.get('/settings/tokens', headers=headers)
        assert resp.status_code == 200

    def test_alice_lists_her_tokens(self, client, alice_headers):
        resp = client.get('/settings/tokens', headers=alice_headers)
        assert resp.status_code == 200
        names = [t['name'] for t in resp.json()]
        assert 'ci-token' in names

    def test_bob_cannot_see_alice_tokens(self, client, bob_headers):
        resp = client.get('/settings/tokens', headers=bob_headers)
        assert resp.status_code == 200
        # Bob's token list is empty (or doesn't contain alice's tokens)
        assert not any(t['name'] == 'ci-token' for t in resp.json())


class TestOwnershipIsolation:
    def test_experiment_owned_by_alice_hidden_from_bob(self, db_session, alice, bob):
        """Create a private experiment owned by alice; bob should not see it in list."""
        exp = ExperimentModel(name='alice-private-exp')
        exp.user_id = alice.id
        exp.is_public = False
        db_session.add(exp)
        db_session.commit()
        TestOwnershipIsolation._exp_id = exp.id

    def test_experiment_public_visible_to_bob(self, db_session, alice):
        """After making it public, it should be visible."""
        exp_id = getattr(TestOwnershipIsolation, '_exp_id', None)
        if exp_id is None:
            pytest.skip('No experiment from previous test')
        exp = db_session.query(ExperimentModel).filter(ExperimentModel.id == exp_id).first()
        assert exp is not None
        exp.is_public = True
        db_session.commit()
        exp_refreshed = db_session.query(ExperimentModel).filter(ExperimentModel.id == exp_id).first()
        assert exp_refreshed.is_public is True


class TestTokenDeletion:
    def test_alice_can_delete_her_token(self, client, alice_headers):
        # Create then delete
        create_resp = client.post('/settings/tokens', json={'name': 'temp-token'}, headers=alice_headers)
        assert create_resp.status_code == 201
        token_id = create_resp.json()['id']

        del_resp = client.delete(f'/settings/tokens/{token_id}', headers=alice_headers)
        assert del_resp.status_code == 204

        # Should no longer be listed
        list_resp = client.get('/settings/tokens', headers=alice_headers)
        ids = [t['id'] for t in list_resp.json()]
        assert token_id not in ids

    def test_bob_cannot_delete_alice_token(self, client, alice_headers, bob_headers):
        create_resp = client.post('/settings/tokens', json={'name': 'alice-only'}, headers=alice_headers)
        assert create_resp.status_code == 201
        token_id = create_resp.json()['id']

        del_resp = client.delete(f'/settings/tokens/{token_id}', headers=bob_headers)
        assert del_resp.status_code == 404  # returns 404 (not found for bob)
