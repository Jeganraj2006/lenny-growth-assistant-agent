import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.db.session import engine, AsyncSessionLocal
from app.db.models import SessionModel, ArtifactModel, TranscriptChunkModel

@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_engine():
    await engine.dispose()
    yield
    await engine.dispose()

@pytest.mark.asyncio
async def test_generate_essay_missing_session_and_invalid_format():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid format -> 422
        res_422 = await client.post("/api/v1/essays/generate", json={
            "session_id": str(uuid.uuid4()),
            "topic": "PLG Strategy",
            "format": "invalid_format"
        })
        assert res_422.status_code == 422

        # Non-existent session -> 404
        missing_uuid = str(uuid.uuid4())
        res_404 = await client.post("/api/v1/essays/generate", json={
            "session_id": missing_uuid,
            "topic": "PLG Strategy"
        })
        assert res_404.status_code == 404
        assert "not found" in res_404.json()["detail"].lower()

@pytest.mark.asyncio
async def test_generate_essay_success_and_artifact_persistence():
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Essay Test Session")
        session.add(sess)
        
        chash = f"hash_essay_chunk_{uuid.uuid4()}"
        chunk = TranscriptChunkModel(
            transcript_id="pat-campbell-pricing",
            episode_title="Patrick Campbell on Pricing",
            speaker="Patrick Campbell",
            source_url="https://lenny-podcast.com/pricing",
            chunk_index=0,
            content="Price on value metrics rather than feature lists.",
            content_hash=chash,
            embedding=[0.2] * 768
        )
        session.add(chunk)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    mock_essay_output = (
        "# 3 Rules For Pricing Your SaaS Product On Value Metrics\n\n"
        "Pricing is the highest-leverage growth lever for B2B SaaS..."
    )

    transport = ASGITransport(app=app)
    with patch("app.services.essay.call_ollama_chat", return_value=mock_essay_output):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/essays/generate", json={
                "session_id": sess_id,
                "topic": "SaaS Pricing Frameworks",
                "format": "markdown",
                "provider": "ollama"
            })
            assert res.status_code == 201
            data = res.json()
            assert data["session_id"] == sess_id
            assert data["format"] == "markdown"
            assert "Pricing" in data["title"]
            assert data["content"] == mock_essay_output
            assert len(data["citations"]) >= 1
            # Citation integrity check: derived from actual DB record
            assert data["citations"][0]["speaker"] == "Patrick Campbell"

    # Verify DB persistence
    async with AsyncSessionLocal() as session:
        art_stmt = select(ArtifactModel).where(ArtifactModel.session_id == uuid.UUID(sess_id))
        result = await session.execute(art_stmt)
        arts = result.scalars().all()
        assert len(arts) == 1
        assert arts[0].format == "markdown"
        assert len(arts[0].citations) >= 1

        # Cleanup
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        c_obj = await session.get(TranscriptChunkModel, chunk.id)
        if s_obj:
            await session.delete(s_obj)
        if c_obj:
            await session.delete(c_obj)
        await session.commit()

@pytest.mark.asyncio
async def test_generate_essay_provider_failure_no_artifact_persisted():
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Provider Failure Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    transport = ASGITransport(app=app)
    with patch("app.services.essay.call_ollama_chat", side_effect=RuntimeError("Ollama model execution error")):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/essays/generate", json={
                "session_id": sess_id,
                "topic": "Growth Loops",
                "format": "markdown",
                "provider": "ollama"
            })
            assert res.status_code == 502
            assert "execution failed" in res.json()["detail"].lower()

    # Verify NO artifact was saved in DB
    async with AsyncSessionLocal() as session:
        art_stmt = select(ArtifactModel).where(ArtifactModel.session_id == uuid.UUID(sess_id))
        result = await session.execute(art_stmt)
        arts = result.scalars().all()
        assert len(arts) == 0

        # Cleanup
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
        await session.commit()

@pytest.mark.asyncio
async def test_generate_essay_oversized_content_rejection():
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Oversized Essay Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    # 600 KB string (exceeds 500 KB limit)
    oversized_text = "A" * (600 * 1024)

    transport = ASGITransport(app=app)
    with patch("app.services.essay.call_ollama_chat", return_value=oversized_text):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/essays/generate", json={
                "session_id": sess_id,
                "topic": "Huge Topic",
                "format": "markdown"
            })
            assert res.status_code == 422
            assert "exceeds maximum artifact size" in res.json()["detail"]

    # Verify NO artifact was persisted
    async with AsyncSessionLocal() as session:
        art_stmt = select(ArtifactModel).where(ArtifactModel.session_id == uuid.UUID(sess_id))
        result = await session.execute(art_stmt)
        arts = result.scalars().all()
        assert len(arts) == 0

        # Cleanup
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
        await session.commit()

@pytest.mark.asyncio
async def test_generate_essay_insufficient_transcript_evidence():
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Insufficient Evidence Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    insufficient_response = (
        "The available podcast transcripts do not contain sufficient evidence "
        "to generate a full grounded essay on this topic."
    )

    transport = ASGITransport(app=app)
    # Mock search_transcript_chunks to return empty list (no evidence)
    with patch("app.services.essay.search_transcript_chunks", return_value=[]):
        with patch("app.services.essay.call_ollama_chat", return_value=insufficient_response):
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post("/api/v1/essays/generate", json={
                    "session_id": sess_id,
                    "topic": "Obscure Quantum Computing Topic",
                    "format": "markdown"
                })
                assert res.status_code == 201
                data = res.json()
                assert data["citations"] == []
                assert "sufficient evidence" in data["content"].lower()

    # Cleanup session
    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_unconfigured_anthropic_key_essay_returns_503_service_unavailable():
    """Verify that generating an essay with unconfigured Anthropic API key returns HTTP 503."""
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Anthropic Essay Error Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/essays/generate", json={
            "session_id": sess_id,
            "topic": "Growth Loops",
            "provider": "anthropic"
        })
        assert res.status_code == 503
        assert "api key is unconfigured" in res.json()["detail"].lower()

    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_essay_word_count_and_structure_validation():
    """Verify word_count field, count_words helper, and structured Ship 30 sections."""
    from app.services.essay import count_words

    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Ship 30 Essay Word Count Test")
        session.add(sess)

        chash = f"hash_wordcount_chunk_{uuid.uuid4()}"
        chunk = TranscriptChunkModel(
            transcript_id="pat-campbell-pricing",
            episode_title="Patrick Campbell on Pricing",
            speaker="Patrick Campbell",
            source_url="https://lenny-podcast.com/pricing",
            chunk_index=0,
            content="Price on value metrics rather than feature lists. Review pricing every six months.",
            content_hash=chash,
            embedding=[0.2] * 768
        )
        session.add(chunk)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    # Generate sample essay text targeting Ship 30 format
    sample_text = (
        "# The Value Metric Advantage: Why 90% of SaaS Companies Fail at Pricing\n\n"
        "## The Hook: Why Teams Fail at Pricing\n" + ("Pricing mistake analysis. " * 50) + "\n\n"
        "## Podcast-Grounded Evidence & Frameworks\n"
        "Patrick Campbell notes that value metric pricing scales directly with utility.\n" + ("Evidence breakdown. " * 70) + "\n\n"
        "## Original Analysis & Strategic Synthesis\n" + ("Strategic unit economics synthesis. " * 80) + "\n\n"
        "## The 3-Step Actionable Playbook\n" + ("Step actionable instructions. " * 50)
    )

    actual_words = count_words(sample_text)
    assert actual_words > 500

    transport = ASGITransport(app=app)
    with patch("app.services.essay.call_ollama_chat", return_value=sample_text):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/essays/generate", json={
                "session_id": sess_id,
                "topic": "SaaS Pricing on Value Metrics",
                "format": "markdown",
                "provider": "ollama"
            })
            assert res.status_code == 201
            data = res.json()
            assert data["word_count"] == actual_words
            assert data["target_word_count"] == 1250
            assert "meets_target" in data
            assert "Original Analysis & Strategic Synthesis" in data["content"]
            assert len(data["citations"]) >= 1

    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        c_obj = await session.get(TranscriptChunkModel, chunk.id)
        if s_obj:
            await session.delete(s_obj)
        if c_obj:
            await session.delete(c_obj)
        await session.commit()


