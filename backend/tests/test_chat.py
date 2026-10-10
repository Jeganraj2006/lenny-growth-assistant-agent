import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.db.session import engine, AsyncSessionLocal
from app.db.models import SessionModel, MessageModel, TranscriptChunkModel

@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_engine():
    """Dispose engine connections before and after each test."""
    await engine.dispose()
    yield
    await engine.dispose()

@pytest.mark.asyncio
async def test_chat_missing_session_and_invalid_payload():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid UUID format -> 422
        res_422 = await client.post("/api/v1/chat", json={"session_id": "not-a-uuid", "message": "hello"})
        assert res_422.status_code == 422

        # Non-existent session -> 404
        missing_uuid = str(uuid.uuid4())
        res_404 = await client.post("/api/v1/chat", json={"session_id": missing_uuid, "message": "hello"})
        assert res_404.status_code == 404
        assert "not found" in res_404.json()["detail"].lower()

@pytest.mark.asyncio
async def test_chat_completion_success_and_persistence():
    # 1. Setup test session & chunk in DB
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="PLG Test Chat Session")
        session.add(sess)
        
        chash = f"hash_elena_verna_{uuid.uuid4()}"
        chunk = TranscriptChunkModel(
            transcript_id="elena-verna-test",
            episode_title="Elena Verna on PLG",
            speaker="Elena Verna",
            source_url="https://lenny-podcast.com/elena",
            chunk_index=0,
            content="Onboarding is about accelerating time to value.",
            content_hash=chash,
            embedding=[0.1] * 768
        )
        session.add(chunk)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    transport = ASGITransport(app=app)
    mock_llm_response = "According to Elena Verna, onboarding is about accelerating time-to-value."

    with patch("app.services.chat.call_ollama_chat", return_value=mock_llm_response):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/chat", json={
                "session_id": sess_id,
                "message": "What is onboarding about in PLG?",
                "provider": "ollama",
                "model": "qwen3:4b"
            })
            assert res.status_code == 200
            data = res.json()
            assert data["session_id"] == sess_id
            assert data["user_message"]["content"] == "What is onboarding about in PLG?"
            assert data["assistant_message"]["content"] == mock_llm_response
            assert data["provider_used"] == "ollama"
            assert data["model_used"] == "qwen3:4b"
            assert len(data["citations"]) >= 1
            assert "Elena Verna" in data["citations"][0]["episode_title"]

    # Verify messages persisted in DB
    async with AsyncSessionLocal() as session:
        msgs_stmt = (
            select(MessageModel)
            .where(MessageModel.session_id == uuid.UUID(sess_id))
            .order_by(MessageModel.created_at.asc())
        )
        result = await session.execute(msgs_stmt)
        msgs = result.scalars().all()
        assert len(msgs) == 2
        assert msgs[0].role == "user"
        assert msgs[1].role == "assistant"
        assert msgs[1].provider_used == "ollama"

        # Cleanup
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        c_obj = await session.get(TranscriptChunkModel, chunk.id)
        if s_obj:
            await session.delete(s_obj)
        if c_obj:
            await session.delete(c_obj)
        await session.commit()

@pytest.mark.asyncio
async def test_session_isolation():
    # Create Session A and Session B
    sess_a_id = None
    sess_b_id = None
    async with AsyncSessionLocal() as session:
        sess_a = SessionModel(title="Session A")
        sess_b = SessionModel(title="Session B")
        session.add_all([sess_a, sess_b])
        await session.commit()
        await session.refresh(sess_a)
        await session.refresh(sess_b)
        sess_a_id = str(sess_a.id)
        sess_b_id = str(sess_b.id)

    transport = ASGITransport(app=app)
    with patch("app.services.chat.call_ollama_chat", return_value="Isolated Response"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Send message in Session A
            res_a = await client.post("/api/v1/chat", json={"session_id": sess_a_id, "message": "Msg in A"})
            assert res_a.status_code == 200

            # Check messages in Session B (must be 0)
            res_b_msgs = await client.get(f"/api/v1/sessions/{sess_b_id}/messages")
            assert res_b_msgs.status_code == 200
            assert res_b_msgs.json()["total"] == 0

            # Check messages in Session A (must be 2)
            res_a_msgs = await client.get(f"/api/v1/sessions/{sess_a_id}/messages")
            assert res_a_msgs.status_code == 200
            assert res_a_msgs.json()["total"] == 2

    # Cleanup
    async with AsyncSessionLocal() as session:
        for sid in [sess_a_id, sess_b_id]:
            s_obj = await session.get(SessionModel, uuid.UUID(sid))
            if s_obj:
                await session.delete(s_obj)
        await session.commit()

@pytest.mark.asyncio
async def test_provider_failure_resilience():
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Failure Resiliency Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    transport = ASGITransport(app=app)
    with patch("app.services.chat.call_ollama_chat", side_effect=RuntimeError("Ollama connection timed out")):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/chat", json={"session_id": sess_id, "message": "Test provider failure"})
            assert res.status_code == 502
            assert "ollama connection timed out" in res.json()["detail"].lower()

    # Cleanup
    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_unconfigured_anthropic_key_returns_503_service_unavailable():
    """Verify that unconfigured Anthropic API key returns HTTP 503 instead of 404."""
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Anthropic Error Test Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/chat", json={
            "session_id": sess_id,
            "message": "What is PLG?",
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
async def test_conversational_greeting_bypasses_vector_retrieval():
    """Verify that greetings return natural responses with 0 citations immediately."""
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Greeting Test Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/chat", json={
            "session_id": sess_id,
            "message": "hello"
        })
        assert res.status_code == 200
        data = res.json()
        assert "hello" in data["assistant_message"]["content"].lower() or "lenny" in data["assistant_message"]["content"].lower()
        assert data["citations"] == []

    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_conceptual_saas_and_b2b_accuracy():
    """Verify that SaaS vs B2B conceptual questions correctly distinguish delivery model vs customer type."""
    sess_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Conceptual Accuracy Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

    mock_accurate_explanation = (
        "SaaS is a software delivery and subscription business model, while B2B describes "
        "selling to businesses rather than consumers. SaaS is not inherently B2B; SaaS can be "
        "B2B (e.g. Slack) or B2C (e.g. Spotify). B2B SaaS represents the intersection of the two."
    )

    transport = ASGITransport(app=app)
    with patch("app.services.chat.call_ollama_chat", return_value=mock_accurate_explanation):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post("/api/v1/chat", json={
                "session_id": sess_id,
                "message": "What is the relationship between SaaS and B2B?",
                "provider": "ollama"
            })
            assert res.status_code == 200
            content = res.json()["assistant_message"]["content"]
            assert "delivery" in content.lower() or "model" in content.lower()
            assert "not inherently b2b" in content.lower() or "intersection" in content.lower()
            # General conceptual answer should not attach citations unless grounded in transcript
            assert res.json()["citations"] == []

    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()
