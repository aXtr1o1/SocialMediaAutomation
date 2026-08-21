from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_authenticated_supabase_user
from app.models.processed_content import WorkflowRunRequest, WorkflowRunResponse
from app.services.workflow_service import WorkflowService, spawn_workflow

router = APIRouter()


@router.post("/run", response_model=WorkflowRunResponse)
async def run_content_workflow(
    payload: WorkflowRunRequest,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        started = WorkflowService().begin(
            str(current_user.id),
            domain_id=str(payload.domain_id),
            subdomain_ids=[str(item) for item in payload.subdomain_ids],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    run_id = started.get("workflow_run_id")
    if run_id:
        spawn_workflow(str(run_id))
    return started


@router.get("/run/{workflow_run_id}", response_model=WorkflowRunResponse)
def get_content_workflow(
    workflow_run_id: str,
    current_user=Depends(get_authenticated_supabase_user),
):
    snapshot = WorkflowService().get_run(workflow_run_id, str(current_user.id))
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This sources run was not found. Continue from Discover again.",
        )
    return snapshot


@router.post("/run/{workflow_run_id}/cancel", response_model=WorkflowRunResponse)
def cancel_content_workflow(
    workflow_run_id: str,
    current_user=Depends(get_authenticated_supabase_user),
):
    snapshot = WorkflowService().cancel(workflow_run_id, str(current_user.id))
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This sources run was not found.",
        )
    return snapshot
