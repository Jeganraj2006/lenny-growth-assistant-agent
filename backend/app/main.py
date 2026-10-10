from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import httpx
from sqlalchemy import text

from app.core.config import settings
from app.db.session import init_db, check_db_health, AsyncSessionLocal
from app.api.v1.ingest import router as ingest_router
from app.api.v1.retrieval import router as retrieval_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.chat import router as chat_router
from app.api.v1.essays import router as essays_router
from app.api.v1.artifacts import router as artifacts_router
from app.agent.proof import (
    run_ollama_local_proof,
    run_cloud_anthropic_proof,
    run_failure_handling_proof
)
from app.services.ingest import ingest_transcripts

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle startup and shutdown context manager."""
    # Step 1: Initialize DB schema (pgvector extension + tables)
    try:
        await init_db()
    except Exception:
        pass  # Startup continues cleanly even if DB container is not yet initialized

    # Step 2: Auto-ingest transcripts if the knowledge base is empty.
    # This ensures Docker Compose boots fully self-contained without a manual ingest step.
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM transcript_chunks;"))
            chunk_count = result.scalar_one_or_none() or 0
        if chunk_count == 0:
            print("[startup] No transcript chunks found — running auto-ingestion...")
            async with AsyncSessionLocal() as session:
                stats = await ingest_transcripts(db_session=session)
            print(f"[startup] Auto-ingestion complete: {stats.get('chunks_created', 0)} chunks created.")
        else:
            print(f"[startup] Knowledge base ready: {chunk_count} chunks loaded.")
    except Exception as exc:
        print(f"[startup] Auto-ingestion skipped: {exc}")

    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API routers
app.include_router(ingest_router, prefix="/api/v1")
app.include_router(retrieval_router, prefix="/api/v1")
app.include_router(sessions_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(essays_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")

@app.get("/api/v1/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Application health status endpoint.
    Checks status of local Ollama HTTP service and PostgreSQL database with pgvector.
    """
    ollama_online = False
    ollama_models = []
    
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OLLAMA_HOST}/api/tags")
            if resp.status_code == 200:
                ollama_online = True
                data = resp.json()
                ollama_models = [m.get("name") for m in data.get("models", [])]
    except Exception:
        ollama_online = False

    db_health = await check_db_health()
    has_cloud_key = bool(settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("your_"))

    return {
        "status": "healthy" if (ollama_online and db_health["status"] == "connected") else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "services": {
            "ollama_status": "online" if ollama_online else "offline",
            "ollama_host": settings.OLLAMA_HOST,
            "ollama_models": ollama_models,
            "database": db_health,
            "cloud_provider_configured": has_cloud_key
        }
    }

@app.get("/api/v1/test-agent", status_code=status.HTTP_200_OK)
async def test_agent_providers() -> Dict[str, Any]:
    """
    Provider Proof Endpoint.
    Runs empirical tests for local Ollama, cloud Anthropic, and offline failure resiliency.
    """
    local_proof = await run_ollama_local_proof()
    cloud_proof = await run_cloud_anthropic_proof()
    failure_proof = await run_failure_handling_proof()

    return {
        "title": "Agent Provider Compatibility Proof",
        "results": {
            "local_ollama": local_proof,
            "cloud_anthropic": cloud_proof,
            "failure_resilience": failure_proof
        }
    }
