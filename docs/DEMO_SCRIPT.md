# Technical Interview Demonstration Script (2–3 Minutes)

**Project:** The Lenny Growth Assistant  
**Audience:** Technical Interviewers / Assessment Evaluators  
**Stack:** React (Vite / Tailwind / DOMPurify), FastAPI, PostgreSQL 16 + pgvector, Ollama (`llama3.2:3b` / `nomic-embed-text:latest`)  
**Deployment:** Docker Compose (`http://localhost`)

---

## Quick Setup Before Presenting
1. Ensure Ollama is running on host with models pulled:
   ```bash
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text:latest
   ```
2. Ensure Docker Compose containers are up:
   ```bash
   docker compose up -d
   ```
3. Open `http://localhost` in your browser.

---

## Timed Demonstration Flow

### 1. Application & System Health (0:00 – 0:30)
- **Action:**
  - View the application header at `http://localhost`.
  - Point to the active model badge: `Ollama: llama3.2:3b`.
  - In the sidebar, click the **Diag** tab.
- **Talking Points:**
  - *"The assistant is containerized via Docker Compose with an nginx reverse proxy, FastAPI backend, and PostgreSQL 16 with pgvector."*
  - *"Our diagnostic endpoint reports PostgreSQL connected with pgvector active, Ollama online with 768-dim embeddings and chat models detected, and cloud Anthropic identified as optional."*
  - *"All transcript embeddings are auto-ingested into pgvector on container boot."*

---

### 2. Session Creation & Immediate Greeting (0:30 – 1:00)
- **Action:**
  - Click **+ New Session** in the sidebar.
  - Type `hi` and send.
- **Talking Points:**
  - *"Sessions are persisted in PostgreSQL with UUID primary keys and cascade-delete relationships."*
  - *"For conversational greetings like 'hi', the assistant answers instantly in under 100 milliseconds without executing redundant vector searches or fabricating misleading citation badges."*
  - Refresh the page to prove session and greeting persistence across reloads.

---

### 3. Grounded Ollama RAG Answer with Citation (1:00 – 1:45)
- **Action:**
  - In the active session, ask:
    > *"What is Patrick Campbell's advice on SaaS pricing and value metrics?"*
  - While waiting (~25–35s for local CPU generation), point out the subtle loading indicator.
- **Talking Points:**
  - *"The user prompt is embedded using `nomic-embed-text:latest` and matched via cosine similarity in pgvector against our genuine transcript excerpts."*
  - *"The host dialogue is preserved so the guest's substantive advice is retrieved intact."*
  - Show the response and the **📚 Grounded Transcript Evidence** card:
    - Guest: *Patrick Campbell*
    - Episode: *Patrick Campbell on SaaS Pricing, Monetization, and Value Metrics*
    - Cosine Similarity: *~77%*
    - Direct link to Lenny's published Substack article.
- **Action (Conceptual Accuracy):**
  - Ask: *"What is the relation between SaaS and B2B?"*
- **Talking Points:**
  - *"Notice the conceptual precision: SaaS is defined as a delivery model, B2B as a target customer segment, SaaS can be B2B or B2C, and B2B SaaS is their intersection — with zero false attribution to podcast guests."*

---

### 4. Persisted Messages, Ship 30 Essay & Sandboxed Artifact (1:45 – 2:30)
- **Action:**
  - Click the **Artifacts** tab in the sidebar.
  - Select the previously generated essay: *"The 10x Pricing Playbook: Why Most SaaS Founders Undercharge"*.
  - (Or generate a new one via **✍️ Generate Ship 30 Essay** on topic *"3 Rules for SaaS Pricing & Value Metrics"*).
- **Talking Points:**
  - *"Our Ship 30 writing skill generates structured ~958-word essays following the 5-step Ship 30 format: Hook, Problem, Podcast Grounded Evidence, Original Strategic Synthesis, and Takeaways."*
  - *"We clearly delineate verified podcast claims from original analysis and practical frameworks."*
  - Toggle between **Preview** and **Source Code**.
- **Action (Security Demo):**
  - Inspect the HTML preview iframe in DevTools or mention its attributes:
    - `sandbox=""` (strictly empty sandbox).
    - Scripts disabled (`allow-scripts` omitted).
    - Same-origin disabled (`allow-same-origin` omitted).
    - Forms and popups disabled.
    - DOMPurify sanitization before insertion.
  - *"Untrusted generated artifacts can never execute JavaScript, steal session tokens, or access the parent DOM."*

---

## Summary of Passing Quality Benchmarks
- **Backend Test Suite:** 36/36 tests passing (`pytest -v`)
- **10-Question Retrieval Benchmark:** 10/10 passing (100% precision with negative query fallbacks)
- **Frontend Security Suite:** 6/6 DOMPurify / Sandboxed Iframe tests passing
- **Frontend Production Build:** Clean Vite production build with zero warnings
