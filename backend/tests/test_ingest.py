import pytest
import os
import tempfile
from unittest.mock import AsyncMock, patch
from app.services.ingest import (
    chunk_text,
    compute_content_hash,
    parse_transcript_file,
    ingest_transcripts
)

def test_chunk_text_determinism_and_overlap():
    """Test text chunking determinism, word limit, and chunk overlap."""
    text = " ".join([f"word{i}" for i in range(100)])
    chunks = chunk_text(text, chunk_size=20, overlap=5)
    
    assert len(chunks) > 1
    # Check overlap: last 5 words of chunk 0 match first 5 words of chunk 1
    words0 = chunks[0].split()
    words1 = chunks[1].split()
    assert words0[-5:] == words1[:5]
    
    # Re-run to verify determinism
    chunks_retry = chunk_text(text, chunk_size=20, overlap=5)
    assert chunks == chunks_retry

def test_compute_content_hash_idempotency():
    """Verify SHA-256 content hash determinism."""
    h1 = compute_content_hash("Some chunk text", "ep1", 0)
    h2 = compute_content_hash("Some chunk text", "ep1", 0)
    h3 = compute_content_hash("Different text", "ep1", 0)

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # SHA-256 length in hex

def test_parse_transcript_file_json_and_markdown():
    """Test metadata extraction from JSON and Markdown transcript files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Test JSON file
        json_path = os.path.join(tmpdir, "test_ep.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write('{"title": "PLG Growth", "guest": "Elena", "url": "http://test", "content": "Text here"}')

        json_parsed = parse_transcript_file(json_path)
        assert json_parsed["episode_title"] == "PLG Growth"
        assert json_parsed["speaker"] == "Elena"
        assert json_parsed["content"] == "Text here"

        # Test Markdown file with frontmatter
        md_path = os.path.join(tmpdir, "test_ep.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("Title: Pricing Strategy\nGuest: Patrick\nURL: http://pricing\n\nPricing text content")

        md_parsed = parse_transcript_file(md_path)
        assert md_parsed["episode_title"] == "Pricing Strategy"
        assert md_parsed["speaker"] == "Patrick"
        assert md_parsed["content"] == "Pricing text content"

@pytest.mark.asyncio
async def test_ingest_empty_data_directory():
    """Verify clean diagnostic response when data directory is empty or missing."""
    mock_db = AsyncMock()
    with tempfile.TemporaryDirectory() as empty_dir:
        stats = await ingest_transcripts(mock_db, data_dir=empty_dir)
        assert stats["files_discovered"] == 0
        assert stats["files_ingested"] == 0
        assert len(stats["diagnostics"]) > 0
        assert "No transcript files" in stats["diagnostics"][0]

@pytest.mark.asyncio
async def test_ingest_stale_chunk_pruning():
    """Verify that re-ingesting a modified transcript deletes obsolete chunks."""
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.db.models import TranscriptChunkModel

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "stale_test.json")

        # Step 1: Write initial version with 2 chunks worth of content
        initial_data = {
            "id": "stale-test-ep",
            "title": "Stale Chunk Test Episode",
            "guest": "Test Guest",
            "url": "https://test.com/stale",
            "content": "Word " * 600  # Generates 2 chunks (500 words chunk_size)
        }
        with open(file_path, "w", encoding="utf-8") as f:
            import json
            json.dump(initial_data, f)

        mock_embedding = [0.1] * 768
        with patch("app.services.ingest.generate_embedding", return_value=mock_embedding):
            # Pre-test cleanup in case previous test run left chunks
            async with AsyncSessionLocal() as session:
                from sqlalchemy import delete
                await session.execute(delete(TranscriptChunkModel).where(TranscriptChunkModel.transcript_id == "stale-test-ep"))
                await session.commit()

            async with AsyncSessionLocal() as session:
                stats1 = await ingest_transcripts(session, data_dir=tmpdir, chunk_size=500, overlap=50)
                assert stats1["files_ingested"] == 1
                assert stats1["chunks_created"] == 2

            # Verify 2 chunks in DB
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(TranscriptChunkModel).where(TranscriptChunkModel.transcript_id == "stale-test-ep"))
                chunks = res.scalars().all()
                assert len(chunks) == 2

            # Step 2: Update transcript to much shorter content (only 1 chunk)
            updated_data = {
                "id": "stale-test-ep",
                "title": "Stale Chunk Test Episode",
                "guest": "Test Guest",
                "url": "https://test.com/stale",
                "content": "Short updated content that fits in a single chunk."
            }
            with open(file_path, "w", encoding="utf-8") as f:
                import json
                json.dump(updated_data, f)

            async with AsyncSessionLocal() as session:
                stats2 = await ingest_transcripts(session, data_dir=tmpdir, chunk_size=500, overlap=50)
                assert stats2["chunks_pruned"] >= 1

            # Verify only 1 chunk remains in DB (obsolete 2nd chunk pruned)
            async with AsyncSessionLocal() as session:
                res = await session.execute(select(TranscriptChunkModel).where(TranscriptChunkModel.transcript_id == "stale-test-ep"))
                remaining_chunks = res.scalars().all()
                assert len(remaining_chunks) == 1

                # Cleanup
                for c in remaining_chunks:
                    await session.delete(c)
                await session.commit()

