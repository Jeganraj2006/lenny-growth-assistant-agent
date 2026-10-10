import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class SessionCreate(BaseModel):
    title: Optional[str] = Field(default="New Conversation", max_length=255, description="Initial title for the session")

class SessionUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Updated session title")

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    created_at: datetime

class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = Field(default=0, description="Total number of messages in session")

class SessionListResponse(BaseModel):
    total: int
    sessions: List[SessionResponse]

class PaginatedMessagesResponse(BaseModel):
    session_id: uuid.UUID
    total: int
    limit: int
    offset: int
    messages: List[MessageResponse]
