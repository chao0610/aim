import os

import bcrypt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault('AIM_SECRET_KEY', 'test-secret-key')

from aim.storage.structured.sql_engine.models import AimUser, Base, Experiment, Run
from aim.web.api.auth import deps as deps_module
from aim.web.api.auth.deps import get_current_user
from aim.web.api.utils import object_factory
from aim.web.api.visibility import visibility_router


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
def app(db_session):
    orig_get_db_session = deps_module._get_db_session
    deps_module._get_db_session = lambda: db_session

    class FakeFactory:
        def get_session(self):
            return db_session

    app = FastAPI()
    app.include_router(visibility_router, prefix='', dependencies=[Depends(get_current_user)])
    app.dependency_overrides[object_factory] = lambda: FakeFactory()
    yield app
    deps_module._get_db_session = orig_get_db_session


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


def auth_headers(user):
    from aim.web.api.auth.jwt_utils import create_access_token
    token = create_access_token(user.id, user.username)
    return {'Authorization': f'Bearer {token}'}


class TestRunVisibility:
    def test_owner_can_set_public(self, app, db_session, alice):
        run = Run('run1')
        run.user_id = alice.id
        db_session.add(run)
        db_session.commit()

        client = TestClient(app)
        resp = client.put('/runs/run1/visibility', json={'is_public': True}, headers=auth_headers(alice))
        assert resp.status_code == 200
        assert resp.json()['is_public'] is True

        db_session.refresh(run)
        assert run.is_public is True

    def test_non_owner_gets_403(self, app, db_session, alice, bob):
        run = Run('run2')
        run.user_id = alice.id
        db_session.add(run)
        db_session.commit()

        client = TestClient(app)
        resp = client.put('/runs/run2/visibility', json={'is_public': True}, headers=auth_headers(bob))
        assert resp.status_code == 403


class TestExperimentVisibility:
    def test_owner_can_set_public(self, app, db_session, alice):
        exp = Experiment('exp1')
        exp.user_id = alice.id
        db_session.add(exp)
        db_session.commit()

        client = TestClient(app)
        resp = client.put(f'/experiments/{exp.uuid}/visibility', json={'is_public': True}, headers=auth_headers(alice))
        assert resp.status_code == 200
        assert resp.json()['is_public'] is True

    def test_non_owner_gets_403(self, app, db_session, alice, bob):
        exp = Experiment('exp2')
        exp.user_id = alice.id
        db_session.add(exp)
        db_session.commit()

        client = TestClient(app)
        resp = client.put(f'/experiments/{exp.uuid}/visibility', json={'is_public': True}, headers=auth_headers(bob))
        assert resp.status_code == 403
