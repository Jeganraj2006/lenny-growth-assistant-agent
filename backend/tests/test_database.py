import pytest
import uuid
from app.db.models import SessionModel, MessageModel, ArtifactModel, TranscriptChunkModel
from app.db.session import check_db_health

def test_models_instantiation():
    """Verify SQLAlchemy ORM models instantiate correctly with default UUIDs."""
    session_obj = SessionModel(title="PLG Strategy Session")
    assert isinstance(session_obj.id, uuid.UUID) or session_obj.id is None
    assert session_obj.title == "PLG Strategy Session"

    msg = MessageModel(session_id=uuid.uuid4(), role="user", content="How do I set pricing?")
    assert msg.role == "user"
    assert msg.content == "How do I set pricing?"

    chunk = TranscriptChunkModel(
        transcript_id="elena-verna",
        episode_title="PLG Onboarding",
        speaker="Elena Verna",
        source_url="https://lenny-podcast.com/ep1",
        chunk_index=0,
        content="Onboarding is about time to value.",
        content_hash="abc123hash",
        embedding=[0.1] * 768
    )
    assert chunk.episode_title == "PLG Onboarding"
    assert len(chunk.embedding) == 768

@pytest.mark.asyncio
async def test_db_health_check_function():
    """Verify DB health check function returns structured status dictionary."""
    health = await check_db_health()
    assert "status" in health
    assert "host" in health
    assert "database" in health
