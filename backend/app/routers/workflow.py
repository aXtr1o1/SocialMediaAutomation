from fastapi import APIRouter, Depends

from app.core.security import get_authenticated_supabase_user
from app.services.redis_state_service import RedisStateService

router = APIRouter()


@router.get("/session")
def get_workflow_session(
    current_user=Depends(get_authenticated_supabase_user),
):
    service = RedisStateService()

    return service.get_session(
        str(current_user.id)
    )


@router.patch("/session")
def update_workflow_session(
    payload: dict,
    current_user=Depends(get_authenticated_supabase_user),
):
    service = RedisStateService()

    return service.update_session(
        str(current_user.id),
        **payload,
    )


@router.post("/session/step")
def update_workflow_step(
    payload: dict,
    current_user=Depends(get_authenticated_supabase_user),
):
    service = RedisStateService()

    return service.update_session(
        str(current_user.id),
        current_step=payload.get("current_step"),
        current_workflow=payload.get("current_workflow"),
    )


@router.delete("/session")
def clear_workflow_session(
    current_user=Depends(get_authenticated_supabase_user),
):
    service = RedisStateService()

    service.clear_session(
        str(current_user.id)
    )

    return {
        "message": "Workflow session cleared"
    }