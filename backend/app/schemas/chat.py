import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.session import MessageResponse

class ChatRequest(BaseModel):
    session_id: uuid.UUID = Field(..., description="ID of active chat session")
    message: str = Field(..., min_length=1, description="User prompt message string")
    provider: Optional[str] = Field(default="ollama", description="LLM provider: 'ollama' or 'anthropic'")
    model: Optional[str] = Field(default=None, description="Model identifier string")

class CitationItem(BaseModel):
    chunk_id: str
    transcript_id: str
    episode_title: str
    speaker: str
    source_url: str
    chunk_index: int
    excerpt: str
    similarity_score: float

class ChatResponse(BaseModel):
    session_id: uuid.UUID
    user_message: MessageResponse
    assistant_message: MessageResponse
    citations: List[CitationItem]
    provider_used: str
    model_used: str
