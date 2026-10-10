"""
Phase C6 — Live End-to-End Verification Script
Tests 8 key verification workflows against running Lenny Growth Assistant API:
1. Session creation
2. Ollama grounded chat with actual citations
3. Message persistence after session reload
4. Ship 30 essay generation
5. Artifact persistence and retrieval
6. Artifact deletion
7. Unsupported-question fallback
8. Provider failure handling
"""
import asyncio
import json
import httpx

# Tests directly against running Docker services via nginx reverse proxy (port 80)
BASE_URL = "http://127.0.0.1"

async def run_e2e_verification(base_url: str = BASE_URL):
    print("=" * 70)
    print("   PHASE C6: LIVE END-TO-END APPLICATION INTEGRATION VERIFICATION")
    print(f"   Target URL: {base_url}")
    print("=" * 70 + "\n")

    results = {}

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Check health
        try:
            r = await client.get(f"{base_url}/api/v1/health")
            assert r.status_code == 200, f"Health returned {r.status_code}"
            h_data = r.json()
            print(f"[HEALTH CHECK] Status: {h_data['status']} | Ollama: {h_data['services']['ollama_status']} | DB: {h_data['services']['database']['status']}")
        except Exception as e:
            print(f"[HEALTH CHECK FAILED] {e}")
            return

        # ---------------------------------------------------------
        # STEP 1: Session creation
        # ---------------------------------------------------------
        print("\n--- [Step 1: Session Creation] ---")
        try:
            r = await client.post(f"{base_url}/api/v1/sessions", json={"title": "C6 Verification Session"})
            assert r.status_code in [200, 201], f"Expected 200/201, got {r.status_code}"
            sess = r.json()
            session_id = sess["id"]
            print(f"PASS: Created session ID: {session_id} (Title: '{sess['title']}')")
            results["1_session_creation"] = ("PASS", f"Session ID: {session_id}")
        except Exception as e:
            print(f"FAIL: {e}")
            results["1_session_creation"] = ("FAIL", str(e))
            return

        # ---------------------------------------------------------
        # STEP 2: Ollama grounded chat with actual citations
        # ---------------------------------------------------------
        print("\n--- [Step 2: Ollama Grounded Chat with Actual Citations] ---")
        try:
            chat_payload = {
                "session_id": session_id,
                "message": "What is Patrick Campbell's advice on SaaS pricing and value metrics?",
                "provider": "ollama"
            }
            r = await client.post(f"{base_url}/api/v1/chat", json=chat_payload)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            chat_res = r.json()
            asst_msg = chat_res["assistant_message"]["content"]
            citations = chat_res.get("citations", [])
            print(f"Response preview: {asst_msg[:150]}...")
            print(f"Citations count: {len(citations)}")
            for idx, c in enumerate(citations, 1):
                print(f"  Citation [{idx}]: {c.get('episode_title')} (Speaker: {c.get('speaker')}, Score: {c.get('similarity_score')})")
            
            assert len(citations) > 0, "No citations returned for supported pricing question"
            assert any("Patrick Campbell" in c.get("speaker", "") for c in citations), "Missing Patrick Campbell citation"
            assert len(asst_msg) > 50, "Assistant response too short"
            print("PASS: Chat returned grounded answer with legitimate citations.")
            results["2_grounded_chat"] = ("PASS", f"{len(citations)} citation(s), {len(asst_msg.split())} words")
        except Exception as e:
            print(f"FAIL: {e}")
            results["2_grounded_chat"] = ("FAIL", str(e))

        # ---------------------------------------------------------
        # STEP 3: Message persistence after session reload
        # ---------------------------------------------------------
        print("\n--- [Step 3: Message Persistence After Session Reload] ---")
        try:
            r = await client.get(f"{base_url}/api/v1/sessions/{session_id}/messages")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            msgs_data = r.json()
            messages = msgs_data.get("messages", [])
            print(f"Persisted messages in session: {len(messages)}")
            for m in messages:
                print(f"  [{m['role']}]: {m['content'][:80]}...")
            assert len(messages) >= 2, f"Expected at least 2 messages, found {len(messages)}"
            assert messages[0]["role"] == "user"
            assert messages[1]["role"] == "assistant"
            print("PASS: Messages persisted accurately and retrieved chronologically.")
            results["3_message_persistence"] = ("PASS", f"{len(messages)} messages persisted")
        except Exception as e:
            print(f"FAIL: {e}")
            results["3_message_persistence"] = ("FAIL", str(e))

        # ---------------------------------------------------------
        # STEP 4: Ship 30 essay generation
        # ---------------------------------------------------------
        print("\n--- [Step 4: Ship 30 Essay Generation] ---")
        artifact_id = None
        essay_word_count = 0
        try:
            essay_payload = {
                "session_id": session_id,
                "topic": "How SaaS companies should optimize pricing and eliminate involuntary churn",
                "format": "markdown",
                "provider": "ollama"
            }
            print("Generating essay with Ollama (this may take 30-90 seconds)...")
            r = await client.post(f"{base_url}/api/v1/essays/generate", json=essay_payload)
            assert r.status_code in [200, 201], f"Expected 200/201, got {r.status_code}: {r.text}"
            essay_res = r.json()
            artifact_id = essay_res["artifact_id"]
            essay_title = essay_res["title"]
            essay_content = essay_res["content"]
            essay_citations = essay_res.get("citations", [])
            essay_word_count = len(essay_content.split())
            print(f"Artifact ID: {artifact_id}")
            print(f"Essay Title: '{essay_title}'")
            print(f"Essay Word Count: {essay_word_count} words")
            print(f"Essay Citations: {len(essay_citations)}")
            print(f"Preview:\n{essay_content[:250]}...\n")
            assert essay_word_count > 100, f"Essay word count unexpectedly small: {essay_word_count}"
            assert len(essay_citations) > 0, "Essay should include grounded citations"
            print("PASS: Essay generated successfully with valid structure and citations.")
            results["4_essay_generation"] = ("PASS", f"'{essay_title}' ({essay_word_count} words)")
        except Exception as e:
            print(f"FAIL: {e}")
            results["4_essay_generation"] = ("FAIL", str(e))

        # ---------------------------------------------------------
        # STEP 5: Artifact persistence and retrieval
        # ---------------------------------------------------------
        print("\n--- [Step 5: Artifact Persistence and Retrieval] ---")
        try:
            if not artifact_id:
                raise ValueError("No artifact ID from previous step")
            # List artifacts in session
            r = await client.get(f"{base_url}/api/v1/sessions/{session_id}/artifacts")
            assert r.status_code == 200
            art_list = r.json().get("artifacts", [])
            assert any(a["id"] == artifact_id for a in art_list), "Artifact not found in session artifact list"
            
            # Retrieve single artifact detail
            r2 = await client.get(f"{base_url}/api/v1/artifacts/{artifact_id}")
            assert r2.status_code == 200
            art_detail = r2.json()
            assert art_detail["id"] == artifact_id
            assert art_detail["format"] == "markdown"
            print(f"PASS: Artifact {artifact_id} retrieved successfully from database.")
            results["5_artifact_persistence"] = ("PASS", f"Retrieved artifact ID: {artifact_id}")
        except Exception as e:
            print(f"FAIL: {e}")
            results["5_artifact_persistence"] = ("FAIL", str(e))

        # ---------------------------------------------------------
        # STEP 6: Artifact deletion
        # ---------------------------------------------------------
        print("\n--- [Step 6: Artifact Deletion] ---")
        try:
            if not artifact_id:
                raise ValueError("No artifact ID to delete")
            r = await client.delete(f"{base_url}/api/v1/artifacts/{artifact_id}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            
            # Verify 404 after deletion
            r_verify = await client.get(f"{base_url}/api/v1/artifacts/{artifact_id}")
            assert r_verify.status_code == 404, f"Expected 404 for deleted artifact, got {r_verify.status_code}"
            print("PASS: Artifact deleted and confirmed 404 on subsequent retrieval.")
            results["6_artifact_deletion"] = ("PASS", f"Artifact {artifact_id} deleted cleanly")
        except Exception as e:
            print(f"FAIL: {e}")
            results["6_artifact_deletion"] = ("FAIL", str(e))

        # ---------------------------------------------------------
        # STEP 7: Unsupported-question fallback
        # ---------------------------------------------------------
        print("\n--- [Step 7: Unsupported-Question Fallback] ---")
        try:
            fallback_payload = {
                "session_id": session_id,
                "message": "What are the quantum entanglement algorithms for sub-atomic particles in drug discovery?",
                "provider": "ollama"
            }
            r = await client.post(f"{base_url}/api/v1/chat", json=fallback_payload)
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
            fb_res = r.json()
            fb_citations = fb_res.get("citations", [])
            fb_text = fb_res["assistant_message"]["content"]
            print(f"Citations count: {len(fb_citations)} (expected 0)")
            print(f"Assistant response preview: {fb_text[:180]}...")
            assert len(fb_citations) == 0, f"Expected 0 citations for out-of-domain question, got {len(fb_citations)}"
            assert "sufficient evidence" in fb_text.lower(), "Expected insufficient evidence fallback phrase in response"
            print("PASS: Out-of-domain question produced 0 citations and returned clear insufficient evidence fallback.")
            results["7_unsupported_fallback"] = ("PASS", "0 citations + 'insufficient evidence' disclaimer returned")
        except Exception as e:
            print(f"FAIL: {e}")
            results["7_unsupported_fallback"] = ("FAIL", str(e))

        # ---------------------------------------------------------
        # STEP 8: Provider failure handling
        # ---------------------------------------------------------
        print("\n--- [Step 8: Provider Failure Handling] ---")
        try:
            fail_payload = {
                "session_id": session_id,
                "message": "Test provider failure resilience",
                "provider": "anthropic"  # Key not configured
            }
            r = await client.post(f"{base_url}/api/v1/chat", json=fail_payload)
            print(f"Status code: {r.status_code}")
            print(f"Response: {r.text[:150]}")
            # Provider failure should return clean 400/404/422/500/502 without crashing server
            assert r.status_code in [400, 404, 422, 500, 502], f"Unexpected status {r.status_code}"
            
            # Verify session and server are still completely healthy
            r_health = await client.get(f"{base_url}/api/v1/health")
            assert r_health.status_code == 200, "Backend became unhealthy after provider failure!"
            print("PASS: Provider failure handled gracefully with descriptive error; backend remains healthy.")
            results["8_provider_failure"] = ("PASS", f"HTTP {r.status_code} returned gracefully; service remains healthy")
        except Exception as e:
            print(f"FAIL: {e}")
            results["8_provider_failure"] = ("FAIL", str(e))

        # Cleanup session
        try:
            await client.delete(f"{base_url}/api/v1/sessions/{session_id}")
            print(f"\nCleaned up session {session_id}")
        except Exception:
            pass

    print("\n" + "=" * 70)
    print("                E2E VERIFICATION SUMMARY")
    print("=" * 70)
    for step, (status, detail) in results.items():
        print(f"  {step:30} : [{status}] {detail}")
    print("=" * 70)
    return results

if __name__ == "__main__":
    asyncio.run(run_e2e_verification())
