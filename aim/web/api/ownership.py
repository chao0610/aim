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
