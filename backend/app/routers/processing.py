from fastapi import APIRouter, Depends

from app.core.security import get_authenticated_supabase_user
from app.services.workflow_service import WorkflowService

router = APIRouter()


@router.post("/run")
async def run_content_workflow(current_user=Depends(get_authenticated_supabase_user)):
    return await WorkflowService().run(str(current_user.id))
