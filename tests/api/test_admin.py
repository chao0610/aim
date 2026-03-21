import os

os.environ['AIM_SECRET_KEY'] = 'test-key'

import bcrypt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from aim.storage.structured.sql_engine.models import AimUser, Base
from aim.web.api.auth.jwt_utils import create_access_token


@pytest.fixture
def db_session():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
    )

    @event.listens_for(engine, 'connect')
    def _set_sqlite_pragma(dbapi_conn, _rec):
        dbapi_conn.execute('PRAGMA journal_mode=WAL')

    connection = engine.connect()
    Base.metadata.create_all(bind=connection)
    session = sessionmaker(bind=connection)()
    yield session
    session.close()
    connection.close()


@pytest.fixture
def app(db_session):
    from aim.web.api.admin.views import admin_router
    from aim.web.api.auth import deps
    from aim.web.api.auth.deps import get_current_user

    deps._get_db_session = lambda: db_session
    app = FastAPI()
    app.include_router(
        admin_router,
        prefix='/api/admin',
        dependencies=[Depends(get_current_user)],
    )
    return app


@pytest.fixture
def admin_user(db_session):
    pw_hash = bcrypt.hashpw(b'adminpass', bcrypt.gensalt()).decode()
    user = AimUser(username='admin', password_hash=pw_hash, is_admin=True)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def regular_user(db_session):
    pw_hash = bcrypt.hashpw(b'pass', bcrypt.gensalt()).decode()
    user = AimUser(username='bob', password_hash=pw_hash, is_admin=False)
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_headers(admin_user):
    token = create_access_token(admin_user.id, admin_user.username)
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def bob_headers(regular_user):
    token = create_access_token(regular_user.id, regular_user.username)
    return {'Authorization': f'Bearer {token}'}


class TestAdminListUsers:
    def test_admin_can_list_users(self, app, admin_headers, admin_user):
        client = TestClient(app)
        resp = client.get('/api/admin/users', headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['username'] == 'admin'

    def test_non_admin_gets_403(self, app, bob_headers, regular_user):
        client = TestClient(app)
        resp = client.get('/api/admin/users', headers=bob_headers)
        assert resp.status_code == 403


class TestAdminCreateUser:
    def test_admin_can_create_user(self, app, admin_headers, db_session):
        client = TestClient(app)
        resp = client.post(
            '/api/admin/users',
            json={'username': 'alice', 'password': 'secret', 'is_admin': False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['username'] == 'alice'
        assert db_session.query(AimUser).filter(AimUser.username == 'alice').first() is not None

    def test_duplicate_username_returns_400(self, app, admin_headers, admin_user):
        client = TestClient(app)
        resp = client.post(
            '/api/admin/users',
            json={'username': 'admin', 'password': 'pass'},
            headers=admin_headers,
        )
        assert resp.status_code == 400

    def test_non_admin_cannot_create_user(self, app, bob_headers):
        client = TestClient(app)
        resp = client.post(
            '/api/admin/users',
            json={'username': 'newuser', 'password': 'pass'},
            headers=bob_headers,
        )
        assert resp.status_code == 403


class TestAdminResetPassword:
    def test_admin_can_reset_password(self, app, admin_headers, regular_user):
        client = TestClient(app)
        resp = client.put(
            f'/api/admin/users/{regular_user.id}/reset-password',
            json={'password': 'newpass123'},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] == 'OK'

    def test_reset_nonexistent_user_returns_404(self, app, admin_headers):
        client = TestClient(app)
        resp = client.put(
            '/api/admin/users/9999/reset-password',
            json={'password': 'newpass'},
            headers=admin_headers,
        )
        assert resp.status_code == 404
