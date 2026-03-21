import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from aim.storage.structured.sql_engine.models import AimUser, Base, Experiment, Run


@pytest.fixture
def db_session():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def users(db_session):
    alice = AimUser(username='alice', password_hash='h')
    bob = AimUser(username='bob', password_hash='h')
    db_session.add_all([alice, bob])
    db_session.commit()
    return alice, bob


class TestOwnedOrPublic:
    def test_sees_own_runs(self, db_session, users):
        from aim.web.api.ownership import owned_or_public

        alice, bob = users
        r1 = Run('run1')
        r1.user_id = alice.id
        db_session.add(r1)
        db_session.commit()

        result = owned_or_public(db_session.query(Run), Run, alice).all()
        assert len(result) == 1

        result = owned_or_public(db_session.query(Run), Run, bob).all()
        assert len(result) == 0

    def test_sees_public_runs(self, db_session, users):
        from aim.web.api.ownership import owned_or_public

        alice, bob = users
        r1 = Run('run2')
        r1.user_id = alice.id
        r1.is_public = True
        db_session.add(r1)
        db_session.commit()

        result = owned_or_public(db_session.query(Run), Run, bob).all()
        assert len(result) == 1

    def test_sees_legacy_runs(self, db_session, users):
        from aim.web.api.ownership import owned_or_public

        _, bob = users
        r1 = Run('run3')
        r1.user_id = None
        db_session.add(r1)
        db_session.commit()

        result = owned_or_public(db_session.query(Run), Run, bob).all()
        assert len(result) == 1

    def test_hides_other_private_runs(self, db_session, users):
        from aim.web.api.ownership import owned_or_public

        alice, bob = users
        r1 = Run('run4')
        r1.user_id = alice.id
        r1.is_public = False
        db_session.add(r1)
        db_session.commit()

        result = owned_or_public(db_session.query(Run), Run, bob).all()
        assert len(result) == 0

    def test_works_with_experiments(self, db_session, users):
        from aim.web.api.ownership import owned_or_public

        alice, bob = users
        exp = Experiment('exp1')
        exp.user_id = alice.id
        db_session.add(exp)
        db_session.commit()

        assert len(owned_or_public(db_session.query(Experiment), Experiment, alice).all()) == 1
        assert len(owned_or_public(db_session.query(Experiment), Experiment, bob).all()) == 0


class TestAssertOwner:
    def test_owner_can_modify(self, db_session, users):
        from aim.web.api.ownership import assert_owner

        alice, _ = users
        r1 = Run('run5')
        r1.user_id = alice.id
        db_session.add(r1)
        db_session.commit()

        assert_owner(r1, alice)  # should not raise

    def test_non_owner_gets_403(self, db_session, users):
        from aim.web.api.ownership import assert_owner

        alice, bob = users
        r1 = Run('run6')
        r1.user_id = alice.id
        db_session.add(r1)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            assert_owner(r1, bob)
        assert exc_info.value.status_code == 403

    def test_legacy_run_writable_by_any(self, db_session, users):
        from aim.web.api.ownership import assert_owner

        _, bob = users
        r1 = Run('run7')
        r1.user_id = None
        db_session.add(r1)
        db_session.commit()

        assert_owner(r1, bob)  # should not raise
