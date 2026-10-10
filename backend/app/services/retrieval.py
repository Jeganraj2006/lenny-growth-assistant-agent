import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector

from app.core.config import settings
from app.db.models import TranscriptChunkModel
from app.services.ingest import generate_embedding

async def search_transcript_chunks(
    db_session: Optional[AsyncSession] = None,
    query: Optional[str] = None,
    top_k: Optional[int] = None,
    similarity_threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """
    Embeds query using nomic-embed-text:latest and performs cosine similarity search
    against PostgreSQL transcript_chunks table using pgvector.
    """
    if not query or not query.strip():
        return []

    limit = top_k or settings.RETRIEVAL_TOP_K
    min_score = similarity_threshold if similarity_threshold is not None else settings.RETRIEVAL_THRESHOLD

    # Step 1: Embed query string via Ollama (HTTP call BEFORE DB transaction)
    query_vector = await generate_embedding(query.strip())

    # Step 2: Query pgvector using cosine distance
    distance_expr = TranscriptChunkModel.embedding.cosine_distance(query_vector)
    
    stmt = (
        select(
            TranscriptChunkModel,
            distance_expr.label("distance")
        )
        .order_by(distance_expr)
        .limit(limit)
    )

    if db_session is not None:
        results = await db_session.execute(stmt)
        rows = results.all()
    else:
        from app.db.session import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            results = await session.execute(stmt)
            rows = results.all()

    matched_chunks = []

    for row in rows:
        chunk_obj, dist = row[0], row[1]
        sim_score = max(0.0, 1.0 - float(dist))

        # Filter by similarity threshold
        if sim_score >= min_score:
            matched_chunks.append({
                "chunk_id": str(chunk_obj.id),
                "transcript_id": chunk_obj.transcript_id,
                "episode_title": chunk_obj.episode_title,
                "speaker": chunk_obj.speaker or "Lenny's Guest",
                "source_url": chunk_obj.source_url or "",
                "chunk_index": chunk_obj.chunk_index,
                "content": chunk_obj.content,
                "similarity_score": round(sim_score, 4),
                "distance": round(float(dist), 4)
            })

    return matched_chunks
