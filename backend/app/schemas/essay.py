import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.chat import CitationItem

class EssayGenerateRequest(BaseModel):
    session_id: uuid.UUID = Field(..., description="ID of active chat session")
    topic: str = Field(..., min_length=1, max_length=500, description="Brief topic for the Ship 30 for 30 essay")
    format: Optional[str] = Field(default="markdown", description="Artifact format: 'markdown' or 'html'")
    provider: Optional[str] = Field(default="ollama", description="LLM provider: 'ollama' or 'anthropic'")
    model: Optional[str] = Field(default=None, description="Model identifier string")

class EssayGenerateResponse(BaseModel):
    artifact_id: uuid.UUID
    session_id: uuid.UUID
    title: str
    format: str
    content: str
    citations: List[CitationItem]
    word_count: Optional[int] = None
    provider_used: str
    model_used: str
    created_at: datetime
