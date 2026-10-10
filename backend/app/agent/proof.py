import os
import asyncio
import httpx
import json
from typing import Dict, Any, Optional
import anthropic
from app.core.config import settings

def get_sample_podcast_quote(topic: str) -> str:
    """Sample custom tool function for RAG quote retrieval proof."""
    quotes = {
        "onboarding": "Elena Verna: 'PLG onboarding is not about product tours; it is about accelerating time-to-value.'",
        "pricing": "Patrick Campbell: 'Most SaaS companies underprice by 3x because they price on features rather than value metrics.'",
        "default": "Lenny Rachitsky: 'Great growth comes from relentless focus on your primary retention loop.'"
    }
    return quotes.get(topic.lower(), quotes["default"])

def _safe_str(val: Any) -> str:
    """Helper to convert content to safe string for any console encoding."""
    if val is None:
        return ""
    if not isinstance(val, str):
        val = str(val)
    return val.encode("ascii", errors="ignore").decode("ascii")

async def run_ollama_local_proof() -> Dict[str, Any]:
    """
    Executes an empirical local model proof using Ollama qwen3:4b.
    Uses explicit IPv4 loopback (http://127.0.0.1:11434) and scoped environment configuration.
    Tests model completion and custom tool-calling schema compatibility over Ollama's native endpoint.
    """
    local_url = "http://127.0.0.1:11434"
    model_name = settings.OLLAMA_LLM_MODEL or "qwen3:4b"

    # Step 1: Health check local Ollama HTTP endpoint
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{local_url}/api/tags")
            if resp.status_code != 200:
                return {
                    "status": "failed",
                    "provider": "ollama_local",
                    "model": model_name,
                    "error": f"Ollama HTTP health check failed with status {resp.status_code}",
                    "details": resp.text
                }
        except Exception as exc:
            return {
                "status": "failed",
                "provider": "ollama_local",
                "model": model_name,
                "error": f"Ollama endpoint unreachable at {local_url}: {str(exc)}",
                "details": "Ensure Ollama desktop service is running locally on port 11434."
            }

    # Step 2: Test API endpoint execution against Ollama with generous 120s timeout for local inference
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Check Anthropic endpoint compatibility
        try:
            anthropic_resp = await client.post(
                f"{local_url}/v1/messages",
                json={
                    "model": model_name,
                    "max_tokens": 50,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
            anthropic_compatible = (anthropic_resp.status_code == 200)
        except Exception:
            anthropic_compatible = False

        tool_definition = {
            "type": "function",
            "function": {
                "name": "get_sample_podcast_quote",
                "description": "Retrieves a sample quote from Lenny's Podcast transcripts for a given topic.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "The growth or product topic (e.g. onboarding, pricing)"
                        }
                    },
                    "required": ["topic"]
                }
            }
        }

        try:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": "Use the get_sample_podcast_quote tool to find advice on onboarding."}
                ],
                "tools": [tool_definition]
            }

            response = await client.post(f"{local_url}/v1/chat/completions", json=payload)

            if response.status_code != 200:
                return {
                    "status": "failed",
                    "provider": "ollama_local",
                    "model": model_name,
                    "error": f"Ollama model invocation returned status {response.status_code}: {response.text}",
                    "anthropic_v1_messages_supported": anthropic_compatible
                }

            data = response.json()
            message_obj = data.get("choices", [{}])[0].get("message", {})
            tool_calls = message_obj.get("tool_calls", [])

            tool_invoked = False
            tool_result = None

            if tool_calls:
                tool_invoked = True
                first_tool = tool_calls[0].get("function", {})
                args = first_tool.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                topic_arg = args.get("topic", "onboarding")
                tool_result = get_sample_podcast_quote(topic_arg)

                # Format content cleanly for Ollama tool turn
                msg_content = message_obj.get("content") or ""
                followup_payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": "Use the get_sample_podcast_quote tool to find advice on onboarding."},
                        {
                            "role": "assistant",
                            "content": msg_content,
                            "tool_calls": tool_calls
                        },
                        {
                            "role": "tool",
                            "tool_call_id": tool_calls[0].get("id", "call_1"),
                            "content": tool_result
                        }
                    ]
                }
                followup_resp = await client.post(f"{local_url}/v1/chat/completions", json=followup_payload)
                if followup_resp.status_code == 200:
                    followup_data = followup_resp.json()
                    raw_text = followup_data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    final_text = _safe_str(raw_text)
                else:
                    final_text = _safe_str(msg_content)
            else:
                final_text = _safe_str(message_obj.get("content", ""))

            return {
                "status": "passed",
                "provider": "ollama_local",
                "model": model_name,
                "tool_invoked": tool_invoked,
                "tool_result": _safe_str(tool_result),
                "response_text": final_text or "Local model invocation succeeded.",
                "anthropic_v1_messages_supported": anthropic_compatible,
                "verified_endpoint": "/v1/chat/completions"
            }

        except Exception as exc:
            return {
                "status": "failed",
                "provider": "ollama_local",
                "model": model_name,
                "error": f"Ollama local model execution error: {_safe_str(type(exc).__name__)} - {_safe_str(str(exc))}",
                "anthropic_v1_messages_supported": anthropic_compatible
            }

async def run_cloud_anthropic_proof(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Executes a Cloud Anthropic provider proof if ANTHROPIC_API_KEY is configured.
    Gracefully skips test if key is missing without raising an error.
    """
    key = api_key or settings.ANTHROPIC_API_KEY
    if not key or key.strip() == "" or key.startswith("your_"):
        return {
            "status": "skipped",
            "provider": "anthropic_cloud",
            "model": "claude-3-5-sonnet-20241022",
            "reason": "ANTHROPIC_API_KEY is missing or unconfigured in environment."
        }

    try:
        client = anthropic.AsyncAnthropic(api_key=key)
        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=50,
                messages=[{"role": "user", "content": "Respond with 'Cloud Provider Connection Verified'."}]
            ),
            timeout=10.0
        )
        text = "".join([block.text for block in response.content if block.type == "text"])
        return {
            "status": "passed",
            "provider": "anthropic_cloud",
            "model": "claude-3-5-sonnet-20241022",
            "response_text": _safe_str(text)
        }
    except Exception as exc:
        return {
            "status": "failed",
            "provider": "anthropic_cloud",
            "model": "claude-3-5-sonnet-20241022",
            "error": f"Cloud Anthropic API call failed: {_safe_str(str(exc))}"
        }

async def run_failure_handling_proof() -> Dict[str, Any]:
    """
    Tests failure handling against an offline endpoint (http://127.0.0.1:11435).
    Verifies clean diagnostic response without crashing.
    """
    offline_url = "http://127.0.0.1:11435"
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.post(
                f"{offline_url}/v1/chat/completions",
                json={"model": "qwen3:4b", "messages": [{"role": "user", "content": "Hi"}]}
            )
            return {
                "status": "unexpected_success",
                "error": "Expected connection failure but call succeeded."
            }
        except Exception as exc:
            return {
                "status": "passed_failure_test",
                "tested_endpoint": offline_url,
                "caught_error_type": _safe_str(exc.__class__.__name__),
                "diagnostic_message": f"Successfully caught expected connection failure: {_safe_str(str(exc))}"
            }
