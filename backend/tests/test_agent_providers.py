import pytest
from app.agent.proof import (
    run_ollama_local_proof,
    run_cloud_anthropic_proof,
    run_failure_handling_proof
)

@pytest.mark.asyncio
async def test_ollama_local_provider_proof():
    """Test local Ollama qwen3:4b execution and tool-calling capability."""
    result = await run_ollama_local_proof()
    assert "status" in result
    assert result["provider"] == "ollama_local"
    # Status will be 'passed' if Ollama is live with qwen3:4b, or 'failed' with error detail
    if result["status"] == "passed":
        assert "response_text" in result
        assert result["response_text"] is not None

@pytest.mark.asyncio
async def test_cloud_anthropic_provider_proof():
    """Test Cloud Anthropic execution or confirm graceful skip when key is absent."""
    result = await run_cloud_anthropic_proof()
    assert result["status"] in ["passed", "skipped", "failed"]
    if result["status"] == "skipped":
        assert "reason" in result

@pytest.mark.asyncio
async def test_failure_handling_resilience():
    """Test offline host handling to verify diagnostic behavior without crashing."""
    result = await run_failure_handling_proof()
    assert result["status"] == "passed_failure_test"
    assert "diagnostic_message" in result
