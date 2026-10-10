import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, String, Text, Integer, Float, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class SessionModel(Base):
    """Chat session model."""
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, default="New Conversation")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("MessageModel", back_populates="session", cascade="all, delete-orphan")
    artifacts = relationship("ArtifactModel", back_populates="session", cascade="all, delete-orphan")

class MessageModel(Base):
    """Chat message model."""
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    citations = Column(JSONB, nullable=True, default=list)
    provider_used = Column(String(50), nullable=True)
    model_used = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    session = relationship("SessionModel", back_populates="messages")

class ArtifactModel(Base):
    """Generated code/content artifact model."""
    __tablename__ = "artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    format = Column(String(50), nullable=False)  # html, markdown
    content = Column(Text, nullable=False)
    citations = Column(JSONB, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    session = relationship("SessionModel", back_populates="artifacts")

class TranscriptChunkModel(Base):
    """Lenny's Podcast transcript chunk model with vector embedding."""
    __tablename__ = "transcript_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id = Column(String(255), nullable=False, index=True)
    episode_title = Column(String(255), nullable=False, index=True)
    speaker = Column(String(255), nullable=True, default="Unknown Guest")
    source_url = Column(String(512), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, unique=True, index=True)
    embedding = Column(Vector(768), nullable=False)  # Verified 768-dim nomic-embed-text vector
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_transcript_chunks_embedding", embedding, postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
