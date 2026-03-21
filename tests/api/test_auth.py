import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from aim.storage.structured.sql_engine.models import AimUser, ApiToken, Base, Experiment, Run


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


class TestOwnershipColumns:
    def test_run_has_user_id_and_is_public(self, db_session: Session):
        user = AimUser(username='carol', password_hash='hash')
        db_session.add(user)
        db_session.commit()

        run = Run('abc123')
        run.user_id = user.id
        run.is_public = True
        db_session.add(run)
        db_session.commit()

        assert run.user_id == user.id
        assert run.is_public is True

    def test_run_defaults(self, db_session: Session):
        run = Run('def456')
        db_session.add(run)
        db_session.commit()

        assert run.user_id is None
        assert run.is_public is False

    def test_experiment_has_user_id_and_is_public(self, db_session: Session):
        user = AimUser(username='dave', password_hash='hash')
        db_session.add(user)
        db_session.commit()

        exp = Experiment('test-exp')
        exp.user_id = user.id
        exp.is_public = True
        db_session.add(exp)
        db_session.commit()

        assert exp.user_id == user.id
        assert exp.is_public is True
