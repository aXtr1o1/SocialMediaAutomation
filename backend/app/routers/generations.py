from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_authenticated_supabase_user
from app.models.generation import GenerationCreate, GenerationResponse
from app.services.generation_service import GenerationService

router = APIRouter()


@router.post("", response_model=GenerationResponse)
async def create_generation(
    payload: GenerationCreate,
    current_user=Depends(get_authenticated_supabase_user),
):
    try:
        return await GenerationService().create(
            article_id=str(payload.article_id),
            platforms=list(payload.platforms),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
