from typing import List, Optional
from pydantic import BaseModel, Field

class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string for RAG vector search")
    top_k: Optional[int] = Field(default=5, ge=1, le=20, description="Max number of top chunks to return")
    similarity_threshold: Optional[float] = Field(default=0.55, ge=0.0, le=1.0, description="Minimum cosine similarity cutoff threshold")

class TranscriptChunkResponse(BaseModel):
    chunk_id: str
    transcript_id: str
    episode_title: str
    speaker: str
    source_url: str
    chunk_index: int
    content: str
    similarity_score: float
    distance: float

class RetrievalResponse(BaseModel):
    query: str
    matched_count: int
    chunks: List[TranscriptChunkResponse]
