import os

import bcrypt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

os.environ.setdefault('AIM_SECRET_KEY', 'test-secret-key')

from aim.storage.structured.sql_engine.models import AimUser, Base
from aim.web.api.auth import deps as auth_deps
from aim.web.api.auth.views import auth_router


@pytest.fixture
def db_session():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
    )

    # Force SQLAlchemy to reuse a single connection so the in-memory DB
    # is visible across the test thread and the ASGI server thread.
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
    auth_deps._get_db_session = lambda: db_session
    app = FastAPI()
    app.include_router(auth_router, prefix='/api/auth')
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def alice(db_session):
    pw_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode()
    user = AimUser(username='alice', password_hash=pw_hash)
    db_session.add(user)
    db_session.commit()
    return user


class TestLogin:
    def test_login_success(self, client, alice):
        resp = client.post('/api/auth/login', json={'username': 'alice', 'password': 'password123'})
        assert resp.status_code == 200
        data = resp.json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['token_type'] == 'bearer'

    def test_login_wrong_password(self, client, alice):
        resp = client.post('/api/auth/login', json={'username': 'alice', 'password': 'wrong'})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post('/api/auth/login', json={'username': 'nobody', 'password': 'x'})
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client, alice):
        login_resp = client.post('/api/auth/login', json={'username': 'alice', 'password': 'password123'})
        refresh_token = login_resp.json()['refresh_token']

        resp = client.post('/api/auth/refresh', json={'refresh_token': refresh_token})
        assert resp.status_code == 200
        assert 'access_token' in resp.json()

    def test_refresh_invalid_token(self, client):
        resp = client.post('/api/auth/refresh', json={'refresh_token': 'invalid'})
        assert resp.status_code == 401

    def test_refresh_with_access_token_rejected(self, client, alice):
        login_resp = client.post('/api/auth/login', json={'username': 'alice', 'password': 'password123'})
        access_token = login_resp.json()['access_token']

        resp = client.post('/api/auth/refresh', json={'refresh_token': access_token})
        assert resp.status_code == 401
