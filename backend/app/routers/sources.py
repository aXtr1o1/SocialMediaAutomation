from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_authenticated_supabase_user
from app.models.source import (
    SourceCreate,
    SourceResponse,
    SourceUpdate,
)
from app.services.source_service import SourceService

router = APIRouter()


def get_source_service() -> SourceService:
    return SourceService()


@router.post(
    "",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_source(
    source: SourceCreate,
    current_user=Depends(get_authenticated_supabase_user),
    service: SourceService = Depends(get_source_service),
):
    user_id = UUID(str(current_user.id))

    return service.create_source(
        source=source,
        user_id=user_id,
    )


@router.get(
    "",
    response_model=list[SourceResponse],
)
def get_sources(
    current_user=Depends(
        get_authenticated_supabase_user
    ),
    service: SourceService = Depends(
        get_source_service
),
):
    user_id = UUID(str(current_user.id))

    return service.get_sources(
        user_id=user_id,
    )


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
)
def get_source(
    source_id: UUID,
    current_user=Depends(
        get_authenticated_supabase_user
    ),
    service: SourceService = Depends(
        get_source_service
    ),
):
    user_id = UUID(str(current_user.id))

    source = service.get_source(
        source_id=source_id,
        user_id=user_id,
    )

    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    return source


@router.put(
    "/{source_id}",
    response_model=SourceResponse,
)
def update_source(
    source_id: UUID,
    source: SourceUpdate,
    current_user=Depends(
        get_authenticated_supabase_user
    ),
    service: SourceService = Depends(
        get_source_service
    ),
):
    user_id = UUID(str(current_user.id))

    updated_source = service.update_source(
        source_id=source_id,
        source=source,
        user_id=user_id,
    )

    if updated_source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    return updated_source


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_source(
    source_id: UUID,
    current_user=Depends(
        get_authenticated_supabase_user
    ),
    service: SourceService = Depends(
        get_source_service
    ),
):
    user_id = UUID(str(current_user.id))

    deleted = service.delete_source(
        source_id=source_id,
        user_id=user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found.",
        )

    return None