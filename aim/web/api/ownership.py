from fastapi import HTTPException


def owned_or_public(query, model, current_user):
    """Filter query to show only owned, public, or legacy (user_id=NULL) records."""
    return query.filter(
        (model.user_id == current_user.id)
        | (model.is_public == True)  # noqa: E712
        | (model.user_id == None)  # noqa: E711
    )


def assert_owner(obj, current_user):
    """Raise 403 if current_user is not the owner. Legacy (user_id=NULL) is writable by any."""
    if obj.user_id is not None and obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail='Forbidden')


def get_visible_run_hashes(current_user):
    """Return set of run hashes visible to the current user (owned, public, or legacy)."""
    from aim.storage.structured.sql_engine.models import Run as RunModel
    from aim.web.api.utils import object_factory

    factory = object_factory()
    session = factory.get_session()
    rows = owned_or_public(session.query(RunModel.hash), RunModel, current_user).all()
    return {r.hash for r in rows}


def check_run_visibility(run_hash, current_user):
    """Raise 404 if the run is not visible to the current user."""
    from aim.storage.structured.sql_engine.models import Run as RunModel
    from aim.web.api.utils import object_factory

    factory = object_factory()
    session = factory.get_session()
    run_model = session.query(RunModel).filter(RunModel.hash == run_hash).first()
    if run_model is None:
        return  # Run not in SQL yet (legacy) — allow access
    if run_model.user_id is None or run_model.is_public:
        return  # Legacy or public — allow
    if run_model.user_id == current_user.id:
        return  # Owner — allow
    raise HTTPException(status_code=404, detail='Run not found.')
