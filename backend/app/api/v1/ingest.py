from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.ingest import IngestRequest, IngestResponse
from app.services.ingest import ingest_transcripts

router = APIRouter(prefix="/ingest", tags=["Ingestion"])

@router.post("", response_model=IngestResponse, status_code=status.HTTP_200_OK)
async def trigger_transcript_ingestion(
    payload: Optional[IngestRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers transcript parsing, deterministic chunking, embedding generation,
    and idempotent PostgreSQL vector storage.
    """
    data_dir = payload.data_dir if payload else None
    c_size = payload.chunk_size if payload else None
    c_overlap = payload.chunk_overlap if payload else None

    try:
        stats = await ingest_transcripts(
            db_session=db,
            data_dir=data_dir,
            chunk_size=c_size,
            overlap=c_overlap
        )
        return IngestResponse(
            status="completed" if stats["failures"] == 0 else "completed_with_warnings",
            files_discovered=stats["files_discovered"],
            files_ingested=stats["files_ingested"],
            chunks_created=stats["chunks_created"],
            chunks_skipped=stats["chunks_skipped"],
            failures=stats["failures"],
            diagnostics=stats["diagnostics"]
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion process failed: {str(exc)}"
        )
