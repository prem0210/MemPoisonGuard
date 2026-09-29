from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.init_db import initialize_database
from app.services.ollama_service import check_ollama_health
from app.services.vector_store import collection_counts, initialize_collections

from app.api.routes.baseline import router as baseline_router

from app.api.routes.guarded import router as guarded_router
from app.api.routes.evaluation import router as evaluation_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    initialize_collections()
    yield


app = FastAPI(
    title="MemPoisonGuard API",
    description="Provenance-aware long-term memory poisoning defense for AI agents.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(baseline_router)
app.include_router(guarded_router)
app.include_router(evaluation_router)

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "MemPoisonGuard API is running.",
        "environment": settings.app_env,
        "configured_model": settings.ollama_model,
    }


@app.get("/health", tags=["System"])
async def health_check():
    ollama = await check_ollama_health()

    return {
        "application": {
            "status": "healthy",
            "name": settings.app_name,
            "environment": settings.app_env,
        },
        "ollama": ollama,
        "vector_store": {
            "status": "healthy",
            "collections": collection_counts(),
        },
        "database": {
            "status": "healthy",
            "url": settings.sqlite_database_url,
        },
    }