import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from app.main import app
from app.db.session import engine, AsyncSessionLocal
from app.db.models import SessionModel, ArtifactModel

@pytest_asyncio.fixture(autouse=True)
async def cleanup_db_engine():
    await engine.dispose()
    yield
    await engine.dispose()

@pytest.mark.asyncio
async def test_artifact_crud_and_listing():
    sess_id = None
    art_id = None
    async with AsyncSessionLocal() as session:
        sess = SessionModel(title="Artifact CRUD Session")
        session.add(sess)
        await session.commit()
        await session.refresh(sess)
        sess_id = str(sess.id)

        art = ArtifactModel(
            session_id=sess.id,
            title="Sample Essay Artifact",
            format="html",
            content="<h1>Ship 30 Essay</h1><p>Sample essay content</p>",
            citations=[{"episode_title": "Elena Verna PLG"}]
        )
        session.add(art)
        await session.commit()
        await session.refresh(art)
        art_id = str(art.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test List Session Artifacts
        res_list = await client.get(f"/api/v1/sessions/{sess_id}/artifacts")
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert list_data["total"] == 1
        assert list_data["artifacts"][0]["id"] == art_id
        assert list_data["artifacts"][0]["title"] == "Sample Essay Artifact"

        # Test Get Artifact Detail
        res_get = await client.get(f"/api/v1/artifacts/{art_id}")
        assert res_get.status_code == 200
        get_data = res_get.json()
        assert get_data["id"] == art_id
        assert get_data["format"] == "html"

        # Test Delete Artifact
        res_del = await client.delete(f"/api/v1/artifacts/{art_id}")
        assert res_del.status_code == 200

        # Verify 404 after deletion
        res_404 = await client.get(f"/api/v1/artifacts/{art_id}")
        assert res_404.status_code == 404

    # Cleanup session
    async with AsyncSessionLocal() as session:
        s_obj = await session.get(SessionModel, uuid.UUID(sess_id))
        if s_obj:
            await session.delete(s_obj)
            await session.commit()

@pytest.mark.asyncio
async def test_artifact_missing_session_and_missing_artifact():
    transport = ASGITransport(app=app)
    missing_uuid = str(uuid.uuid4())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_sess_404 = await client.get(f"/api/v1/sessions/{missing_uuid}/artifacts")
        assert res_sess_404.status_code == 404

        res_art_404 = await client.get(f"/api/v1/artifacts/{missing_uuid}")
        assert res_art_404.status_code == 404

        res_del_404 = await client.delete(f"/api/v1/artifacts/{missing_uuid}")
        assert res_del_404.status_code == 404

@pytest.mark.asyncio
async def test_cross_session_artifact_isolation():
    sess_a_id = None
    sess_b_id = None
    art_a_id = None
    async with AsyncSessionLocal() as session:
        sess_a = SessionModel(title="Session A")
        sess_b = SessionModel(title="Session B")
        session.add_all([sess_a, sess_b])
        await session.commit()
        await session.refresh(sess_a)
        await session.refresh(sess_b)
        sess_a_id = str(sess_a.id)
        sess_b_id = str(sess_b.id)

        art_a = ArtifactModel(
            session_id=sess_a.id,
            title="Session A Essay",
            format="markdown",
            content="# Essay A",
            citations=[]
        )
        session.add(art_a)
        await session.commit()
        await session.refresh(art_a)
        art_a_id = str(art_a.id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Session A artifacts list should contain art_a
        res_a = await client.get(f"/api/v1/sessions/{sess_a_id}/artifacts")
        assert res_a.status_code == 200
        data_a = res_a.json()
        assert data_a["total"] == 1
        assert data_a["artifacts"][0]["id"] == art_a_id

        # Session B artifacts list MUST NOT contain Session A's artifact
        res_b = await client.get(f"/api/v1/sessions/{sess_b_id}/artifacts")
        assert res_b.status_code == 200
        data_b = res_b.json()
        assert data_b["total"] == 0
        assert len(data_b["artifacts"]) == 0

    # Cleanup
    async with AsyncSessionLocal() as session:
        sa = await session.get(SessionModel, uuid.UUID(sess_a_id))
        sb = await session.get(SessionModel, uuid.UUID(sess_b_id))
        if sa:
            await session.delete(sa)
        if sb:
            await session.delete(sb)
        await session.commit()

