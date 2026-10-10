import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.chat import CitationItem

class ArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    title: str
    format: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

class ArtifactListResponse(BaseModel):
    session_id: uuid.UUID
    total: int
    artifacts: List[ArtifactResponse]
