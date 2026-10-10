from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, TranscriptChunkResponse
from app.services.retrieval import search_transcript_chunks

router = APIRouter(prefix="/retrieval", tags=["Retrieval"])

@router.post("/search", response_model=RetrievalResponse, status_code=status.HTTP_200_OK)
async def search_grounded_chunks(
    payload: RetrievalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Performs pgvector cosine similarity search against ingested podcast transcript chunks.
    Returns grounded evidence chunks with source metadata and similarity scores.
    """
    try:
        matched_chunks = await search_transcript_chunks(
            db_session=db,
            query=payload.query,
            top_k=payload.top_k,
            similarity_threshold=payload.similarity_threshold
        )
        
        chunk_responses = [TranscriptChunkResponse(**chunk) for chunk in matched_chunks]
        
        return RetrievalResponse(
            query=payload.query,
            matched_count=len(chunk_responses),
            chunks=chunk_responses
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval search failed: {str(exc)}"
        )
