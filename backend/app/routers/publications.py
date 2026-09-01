from __future__ import annotations

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_authenticated_supabase_user
from app.models.publication import (
    PublicationCreate,
    PublicationResponse,
    PublicationListResponse,
)
from app.services.publication_service import PublicationServices


router = APIRouter()

@router.post("", response_model=PublicationResponse)
async def publish_post( payload: PublicationCreate, current_user=Depends(get_authenticated_supabase_user)):

    user_id = UUID(str(current_user["id"]))

    try: 
        return await PublicationServices().publish(
            user_id=user_id,
            draft_id=payload.draft_id,
            connected_account_id=payload.connected_account_id,
        )
    except HTTPException:
        raise

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)) from e

@router.post("/multiple", response_model=PublicationListResponse)
async def publish_multiple_posts(publications: list[PublicationCreate],current_user=Depends(get_authenticated_supabase_user),) -> PublicationListResponse:

    user_id = UUID(str(current_user.id))

    results = await PublicationServices().publish_multiple(
        user_id=user_id,
        publications=[
            publication.model_dump()
            for publication in publications
        ],
    )

    return PublicationListResponse(
        publications=results
    )