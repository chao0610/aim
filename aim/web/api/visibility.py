from fastapi import Depends, HTTPException
from pydantic import BaseModel

from aim.storage.structured.sql_engine.models import AimUser
from aim.storage.structured.sql_engine.models import Experiment as ExperimentModel
from aim.storage.structured.sql_engine.models import Run as RunModel
from aim.web.api.auth.deps import get_current_user
from aim.web.api.ownership import assert_owner
from aim.web.api.utils import APIRouter, check_read_only, object_factory

visibility_router = APIRouter()


class VisibilityIn(BaseModel):
    is_public: bool


@visibility_router.put('/runs/{run_id}/visibility')
@check_read_only
async def update_run_visibility(
    run_id: str,
    body: VisibilityIn,
    factory=Depends(object_factory),
    current_user: AimUser = Depends(get_current_user),
):
    session = factory.get_session()
    session.expire_all()
    run_model = session.query(RunModel).filter(RunModel.hash == run_id).first()
    if not run_model:
        raise HTTPException(status_code=404, detail='Run not found')
    assert_owner(run_model, current_user)
    # Use explicit UPDATE to bypass identity map caching in scoped_session
    session.query(RunModel).filter(RunModel.hash == run_id).update({'is_public': body.is_public})
    session.commit()
    return {'id': run_id, 'is_public': body.is_public, 'status': 'OK'}


@visibility_router.put('/experiments/{exp_id}/visibility')
@check_read_only
async def update_experiment_visibility(
    exp_id: str,
    body: VisibilityIn,
    factory=Depends(object_factory),
    current_user: AimUser = Depends(get_current_user),
):
    session = factory.get_session()
    session.expire_all()
    exp_model = session.query(ExperimentModel).filter(ExperimentModel.uuid == exp_id).first()
    if not exp_model:
        raise HTTPException(status_code=404, detail='Experiment not found')
    assert_owner(exp_model, current_user)
    session.query(ExperimentModel).filter(ExperimentModel.uuid == exp_id).update({'is_public': body.is_public})
    session.commit()
    return {'id': exp_id, 'is_public': body.is_public, 'status': 'OK'}
