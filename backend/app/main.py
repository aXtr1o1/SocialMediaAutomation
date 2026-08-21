from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.supabase import get_supabase_client
from app.routers import auth, sources, accounts, processing, generations


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url.rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
    }


@app.get("/health/supabase")
def supabase_health_check() -> dict[str, str]:
    supabase = get_supabase_client()

    supabase.table("users").select("id").limit(1).execute()

    return {
        "status": "healthy",
        "database": "supabase",
    }


app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

app.include_router(
    sources.router,
    prefix="/sources",
    tags=["Sources"],
)

app.include_router(
    accounts.router,
)

app.include_router(
    processing.router,
    prefix="/processing",
    tags=["Content Processing"],
)

app.include_router(
    generations.router,
    prefix="/generations",
    tags=["Generations"],
)
