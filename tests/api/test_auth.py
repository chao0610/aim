import importlib.util

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

try:
    from aim.storage.structured.sql_engine.models import AimUser, ApiToken, Base
except ImportError:
    # Fallback: load models module directly to avoid aim/__init__.py triggering Cython imports
    _spec = importlib.util.spec_from_file_location(
        'aim_models', 'aim/storage/structured/sql_engine/models.py'
    )
    _models = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_models)
    AimUser = _models.AimUser
    ApiToken = _models.ApiToken
    Base = _models.Base


@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class TestAimUserModel:
    def test_create_user(self, db_session: Session):
        user = AimUser(username='alice', password_hash='fakehash')
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.username == 'alice'
        assert user.is_admin is False
        assert user.created_at is not None

    def test_username_unique(self, db_session: Session):
        db_session.add(AimUser(username='alice', password_hash='hash1'))
        db_session.commit()
        db_session.add(AimUser(username='alice', password_hash='hash2'))
        with pytest.raises(Exception):
            db_session.commit()


class TestApiTokenModel:
    def test_create_token(self, db_session: Session):
        user = AimUser(username='bob', password_hash='fakehash')
        db_session.add(user)
        db_session.commit()

        token = ApiToken(user_id=user.id, name='my-token', token_hash='sha256hex')
        db_session.add(token)
        db_session.commit()

        assert token.id is not None
        assert token.user_id == user.id
        assert token.created_at is not None
