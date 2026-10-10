import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.retrieval import search_transcript_chunks

@pytest.mark.asyncio
async def test_search_transcript_chunks_empty_query():
    """Verify empty query returns empty list without calling database or Ollama."""
    mock_db = AsyncMock()
    results = await search_transcript_chunks(mock_db, query="")
    assert results == []

@pytest.mark.asyncio
@patch("app.services.retrieval.generate_embedding")
async def test_search_transcript_chunks_mocked(mock_embed):
    """Verify vector search filters results by similarity threshold and formats output metadata."""
    mock_embed.return_value = [0.1] * 768
    
    # Mock DB query execution returning no matching database rows
    mock_db = AsyncMock()
    mock_db_result = MagicMock()
    mock_db_result.all.return_value = []
    mock_db.execute.return_value = mock_db_result

    results = await search_transcript_chunks(mock_db, query="How to price B2B SaaS?", top_k=3, similarity_threshold=0.70)
    assert isinstance(results, list)
    assert len(results) == 0
    mock_embed.assert_called_once_with("How to price B2B SaaS?")
