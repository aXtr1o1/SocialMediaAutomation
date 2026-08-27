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
)
from app.services.generation_service import GenerationService

router = APIRouter()


@router.post("", response_model=GenerationResponse)
async def create_generation(
    payload: GenerationCreate,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return await GenerationService().create(
            user_id=str(current_user.id),
            article_id=str(payload.article_id),
            platforms=list(payload.platforms),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


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
    draft_id: str,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return GenerationService().get_draft(user_id=str(current_user.id), draft_id=draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/versions", response_model=GenerationDraft)
def add_generation_version(
    draft_id: str,
    payload: AddVersionRequest,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        service = GenerationService()
        service.add_version(
            user_id=str(current_user.id),
            draft_id=draft_id,
            full_post=payload.full_post,
            label=payload.label,
            source=payload.source,
            target_text=payload.target_text,
            instruction=payload.instruction,
            replacement_text=payload.replacement_text,
        )
        return service.get_draft(user_id=str(current_user.id), draft_id=draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/drafts/{draft_id}/current", response_model=GenerationDraft)
def set_generation_current_version(
    draft_id: str,
    payload: SetCurrentVersionRequest,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return GenerationService().set_current_version(
            user_id=str(current_user.id),
            draft_id=draft_id,
            version_id=str(payload.version_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/drafts/{draft_id}/versions/{version_id}", response_model=GenerationDraft)
def delete_generation_version(
    draft_id: str,
    version_id: str,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return GenerationService().delete_version(
            user_id=str(current_user.id),
            draft_id=draft_id,
            version_id=version_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
