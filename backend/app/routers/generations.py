from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_authenticated_supabase_user
from app.models.generation import (
    AddVersionRequest,
    GenerationCreate,
    GenerationDraft,
    GenerationResponse,
    RegenerateSnippetRequest,
    RegenerateSnippetResponse,
    SetCurrentVersionRequest,
    GenerationJobResponse
)
from app.services.generation_service import (GenerationService, _GENERATION_TASKS)
import asyncio

router = APIRouter()


@router.post(
    "",
    response_model=GenerationJobResponse,
)
async def create_generation(
    payload: GenerationCreate,
    current_user=Depends(get_authenticated_supabase_user),
):
    service = GenerationService()

    try:
        job = service.create_job(
            user_id=str(current_user.id),
            article_id=str(payload.article_id),
            platforms=list(payload.platforms),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    generation_id = job["generation_id"]

    task = asyncio.create_task(
        service.run_job(generation_id)
    )

    _GENERATION_TASKS[generation_id] = task

    def cleanup(done_task: asyncio.Task) -> None:
        _GENERATION_TASKS.pop(
            generation_id,
            None,
        )

    task.add_done_callback(cleanup)

    return job


@router.post("/regenerate", response_model=RegenerateSnippetResponse)
async def regenerate_generation_snippet(
    payload: RegenerateSnippetRequest,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return await GenerationService().regenerate_snippet(
            user_id=str(current_user.id),
            platform=payload.platform,
            full_post=payload.full_post,
            target_text=payload.target_text,
            instruction=payload.instruction,
            article_id=str(payload.article_id) if payload.article_id else None,
            draft_id=str(payload.draft_id) if payload.draft_id else None,
            label=payload.label,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/drafts/{draft_id}", response_model=GenerationDraft)
def get_generation_draft(
    draft_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return GenerationService().get_draft(
            user_id=str(current_user.id),
            draft_id=str(draft_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/versions", response_model=GenerationDraft)
def add_generation_version(
    draft_id: UUID,
    payload: AddVersionRequest,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        service = GenerationService()
        draft_id_str = str(draft_id)
        service.add_version(
            user_id=str(current_user.id),
            draft_id=draft_id_str,
            full_post=payload.full_post,
            label=payload.label,
            source=payload.source,
            target_text=payload.target_text,
            instruction=payload.instruction,
            replacement_text=payload.replacement_text,
        )
        return service.get_draft(user_id=str(current_user.id), draft_id=draft_id_str)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/current", response_model=GenerationDraft)
def set_generation_current_version(
    draft_id: UUID,
    payload: SetCurrentVersionRequest,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return GenerationService().set_current_version(
            user_id=str(current_user.id),
            draft_id=str(draft_id),
            version_id=str(payload.version_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/drafts/{draft_id}/versions/{version_id}", response_model=GenerationDraft)
def delete_generation_version(
    draft_id: UUID,
    version_id: UUID,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return GenerationService().delete_version(
            user_id=str(current_user.id),
            draft_id=str(draft_id),
            version_id=str(version_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/drafts/{draft_id}/save",
    response_model=GenerationDraft,
)
def save_generation_draft(
    draft_id: UUID,
    payload: AddVersionRequest,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        service = GenerationService()

        service.add_version(
            user_id=str(current_user.id),
            draft_id=str(draft_id),
            full_post=payload.full_post,
            label=payload.label or "User Draft",
            source="restore",
            target_text=payload.target_text,
            instruction=payload.instruction,
            replacement_text=payload.replacement_text,
        )

        return service.get_draft(
            user_id=str(current_user.id),
            draft_id=str(draft_id),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
        
@router.get(
    "/jobs/{generation_id}",
    response_model=GenerationJobResponse,
)
def get_generation_job(
    generation_id: str,
    current_user=Depends(get_authenticated_supabase_user),
):
    job = GenerationService().redis.get_generation_job(
        generation_id
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job was not found.",
        )

    if str(job.get("user_id")) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job was not found.",
        )

    return job

@router.post(
    "/jobs/{generation_id}/cancel",
    response_model=GenerationJobResponse,
)
def cancel_generation_job(
    generation_id: str,
    current_user=Depends(get_authenticated_supabase_user),
):
    job = GenerationService().cancel_job(
        generation_id,
        str(current_user.id),
    )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation job was not found.",
        )

    return job