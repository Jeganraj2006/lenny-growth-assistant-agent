import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func
from app.main import app
from app.db.session import engine, AsyncSessionLocal
from app.db.models import SessionModel, MessageModel, ArtifactModel

@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_engine():
    """Dispose engine connections before and after each test to prevent event loop sharing issues."""
    await engine.dispose()
    yield
    await engine.dispose()

@pytest.mark.asyncio
async def test_create_session():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test creation with default title
        res = await client.post("/api/v1/sessions", json={})
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        assert data["title"] == "New Conversation"
        assert data["message_count"] == 0
        session_id = data["id"]

        # Test creation with custom title
        res_custom = await client.post("/api/v1/sessions", json={"title": "Custom Growth Session"})
        assert res_custom.status_code == 201
        data_custom = res_custom.json()
        assert data_custom["title"] == "Custom Growth Session"

    # Clean up created sessions in DB
    async with AsyncSessionLocal() as session:
        stmt = select(SessionModel).where(SessionModel.id.in_([uuid.UUID(session_id), uuid.UUID(data_custom["id"])]))
        result = await session.execute(stmt)
        for s in result.scalars().all():
            await session.delete(s)
        await session.commit()

@pytest.mark.asyncio
async def test_list_and_get_session_details():
    # Insert test session in DB
    async with AsyncSessionLocal() as session:
        test_sess = SessionModel(title="Test Session for Listing")
        session.add(test_sess)
        await session.commit()
        await session.refresh(test_sess)
        sess_id = str(test_sess.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test List Sessions
        res_list = await client.get("/api/v1/sessions")
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert "total" in list_data
        assert "sessions" in list_data
        assert list_data["total"] >= 1

        # Test Get Session Detail
        res_detail = await client.get(f"/api/v1/sessions/{sess_id}")
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["id"] == sess_id
        assert detail_data["title"] == "Test Session for Listing"

    # Cleanup
    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_update_session_title():
    async with AsyncSessionLocal() as session:
        test_sess = SessionModel(title="Old Title")
        session.add(test_sess)
        await session.commit()
        await session.refresh(test_sess)
        sess_id = str(test_sess.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(f"/api/v1/sessions/{sess_id}", json={"title": "Updated Title"})
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Updated Title"

    # Cleanup
    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_delete_session_and_cascade():
    sess_id = None
    msg_id = None
    async with AsyncSessionLocal() as session:
        test_sess = SessionModel(title="Session to Delete")
        session.add(test_sess)
        await session.commit()
        await session.refresh(test_sess)
        sess_id = test_sess.id

        test_msg = MessageModel(
            session_id=sess_id,
            role="user",
            content="Hello world"
        )
        session.add(test_msg)
        await session.commit()
        await session.refresh(test_msg)
        msg_id = test_msg.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_del = await client.delete(f"/api/v1/sessions/{sess_id}")
        assert res_del.status_code == 200

        # Verify session is 404
        res_check = await client.get(f"/api/v1/sessions/{sess_id}")
        assert res_check.status_code == 404

    # Verify message was deleted via cascade in DB
    async with AsyncSessionLocal() as session:
        m_obj = await session.get(MessageModel, msg_id)
        assert m_obj is None

@pytest.mark.asyncio
async def test_session_messages_chronological_and_pagination():
    async with AsyncSessionLocal() as session:
        test_sess = SessionModel(title="Message History Session")
        session.add(test_sess)
        await session.commit()
        await session.refresh(test_sess)
        sess_id = test_sess.id

        # Add 3 test messages
        msg1 = MessageModel(session_id=sess_id, role="user", content="First query")
        msg2 = MessageModel(session_id=sess_id, role="assistant", content="First answer")
        msg3 = MessageModel(session_id=sess_id, role="user", content="Second query")
        session.add_all([msg1, msg2, msg3])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get all messages
        res = await client.get(f"/api/v1/sessions/{sess_id}/messages")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 3
        assert len(data["messages"]) == 3
        # Chronological order check
        assert data["messages"][0]["content"] == "First query"
        assert data["messages"][1]["content"] == "First answer"
        assert data["messages"][2]["content"] == "Second query"

        # Test pagination (limit=2, offset=1)
        res_page = await client.get(f"/api/v1/sessions/{sess_id}/messages?limit=2&offset=1")
        assert res_page.status_code == 200
        page_data = res_page.json()
        assert page_data["total"] == 3
        assert len(page_data["messages"]) == 2
        assert page_data["messages"][0]["content"] == "First answer"
        assert page_data["messages"][1]["content"] == "Second query"

    # Cleanup
    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, sess_id)
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_invalid_uuid_and_missing_session_handling():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid UUID format string
        res_invalid = await client.get("/api/v1/sessions/not-a-valid-uuid")
        assert res_invalid.status_code == 422

        # Non-existent UUID
        missing_uuid = str(uuid.uuid4())
        res_missing = await client.get(f"/api/v1/sessions/{missing_uuid}")
        assert res_missing.status_code == 404
        assert "not found" in res_missing.json()["detail"].lower()

        res_msg_missing = await client.get(f"/api/v1/sessions/{missing_uuid}/messages")
        assert res_msg_missing.status_code == 404

        res_del_missing = await client.delete(f"/api/v1/sessions/{missing_uuid}")
        assert res_del_missing.status_code == 404
