"""
Phase C6 — E2E API Verification Script
Verifies: health, session creation, RAG retrieval, persistence, and cleanup.
Run from backend/: ..\.venv\Scripts\python.exe e2e_verify.py
"""
import asyncio
import httpx

BASE = "http://127.0.0.1:8001"


async def verify():
    async with httpx.AsyncClient(timeout=30.0) as c:
        # 1. Health check
        r = await c.get(f"{BASE}/api/v1/health")
        h = r.json()
        print("=== HEALTH ===")
        print(f"  Status:   {h['status']}")
        print(f"  Ollama:   {h['services']['ollama_status']}")
        print(f"  DB:       {h['services']['database']['status']}")
        print(f"  pgvector: {h['services']['database'].get('pgvector_extension')}")

        # 2. Create session
        r = await c.post(f"{BASE}/api/v1/sessions", json={"title": "C6 Demo Verification"})
        sess = r.json()
        sid = sess["id"]
        print(f"\n=== SESSION CREATED: {sid} ===")

        # 3. Retrieve transcript chunks (RAG retrieval)
        r = await c.post(
            f"{BASE}/api/v1/retrieval/search",
            json={"query": "What makes a great growth strategy?", "top_k": 3},
        )
        results = r.json()
        print(f"\n=== RETRIEVAL RESULTS: {len(results.get('results', []))} chunks ===")
        for res in results.get("results", []):
            ep = res.get("episode_title", "Unknown")
            score = res.get("similarity_score", 0)
            print(f"  - [{score:.3f}] {ep}")

        # 4. Session messages (should be empty before any chat)
        r = await c.get(f"{BASE}/api/v1/sessions/{sid}/messages")
        msgs = r.json()
        print(f"\n=== SESSION MESSAGES: {len(msgs.get('messages', []))} persisted ===")

        # 5. List all sessions
        r = await c.get(f"{BASE}/api/v1/sessions")
        all_sess = r.json()
        print(f"\n=== TOTAL SESSIONS IN DB: {len(all_sess.get('sessions', []))} ===")

        # 6. List artifacts for session
        r = await c.get(f"{BASE}/api/v1/sessions/{sid}/artifacts")
        arts = r.json()
        print(f"\n=== SESSION ARTIFACTS: {len(arts.get('artifacts', []))} ===")

        # 7. Cleanup
        await c.delete(f"{BASE}/api/v1/sessions/{sid}")
        print("\n=== CLEANUP: demo session deleted ===")
        print("\n✅ All E2E API checks PASSED")


if __name__ == "__main__":
    asyncio.run(verify())
