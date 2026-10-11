# The Lenny Growth Assistant

An AI conversational assistant for product management and growth insights, **grounded strictly in _Lenny's Podcast_ transcripts** via a full RAG pipeline built from scratch.

> Built as a coding-agent development project across 6 iterative phases (C1–C6).

---

## What This Project Demonstrates

| Capability | Implementation |
|---|---|
| **RAG Pipeline** | Transcript ingestion → SHA-256 idempotent chunking → `nomic-embed-text:latest` 768-dim embeddings → `pgvector` cosine similarity retrieval |
| **Chat Persistence** | PostgreSQL-backed session & message history; full CRUD; cascade deletes |
| **Ollama Integration** | Direct HTTP adapter for `llama3.2:3b` / `qwen3:4b` local LLMs with structured prompt injection and citation extraction |
| **Dual Provider** | Runtime switch between local Ollama and cloud Anthropic (Claude 3.5 Sonnet) with graceful HTTP 503 fallback |
| **Essay Skill** | Ship 30 for 30 essay generation (~958 words verified on CPU Ollama, targeting ~1,250 words) with grounded transcript citations |
| **Sandboxed Artifact Viewer** | iframe with `sandbox=""` (no scripts, no same-origin) + DOMPurify sanitization for safe HTML/Markdown rendering |
| **Security** | XSS prevention, strict CSP-equivalent iframe sandbox, DOMPurify, blocked dangerous URL schemes |
| **Full Test Coverage** | 36 backend tests + 6 frontend security regression tests (100% passing) |

---

## Tech Stack

- **Backend:** Python 3.12, FastAPI, Pydantic v2, Async SQLAlchemy 2.0, asyncpg, pgvector
- **Frontend:** React (JavaScript / JSX), Vite, Tailwind CSS, DOMPurify
- **Database:** PostgreSQL 16 + `pgvector` extension
- **AI Models:** Ollama `llama3.2:3b` (fast instruction chat) / `qwen3:4b` (reasoning) & `nomic-embed-text:latest` (768-dim embeddings)
- **Infrastructure:** Docker Compose (postgres + backend + nginx frontend)

---

## Real System Limitations & Constraints

Please note the following verified real-world operational characteristics:
1. **Curated Transcript Corpus:** The vector database indexes 6 genuine, publicly accessible *Lenny's Podcast* transcript excerpts (1,225 total words, 6 active chunks) covering Elena Verna, Patrick Campbell, Shreyas Doshi, Brian Balfour, Geoff Charles, and Casey Winters. Questions outside this scope honestly receive an insufficient-evidence response rather than hallucinated claims.
2. **Local CPU Inference Latency:** Running local LLMs on consumer CPUs takes approximately 20–40 seconds for grounded conversational answers and 2–3 minutes for complete essay generation.
4. **Verified Essay Output:** Live local essay generation achieves approximately 686–958 words of structured narrative prose across 5 Ship 30 sections without repeating claims or fabricating quotes. The system includes an explicit target word count comparison (~1,250 words) and honestly reports whether the generated output meets the target (`target_word_count: 1250`, `meets_target`).
5. **Clean Checkout Docker Builds:** The frontend uses a multi-stage Docker build (`node:20-alpine` builder → `nginx:1.27-alpine`), guaranteeing that `docker compose up --build` compiles and serves the latest frontend code directly from source without requiring host Node.js installation.

---

## Quick Start — Docker Compose (Recommended)

> **Prerequisites:** Docker Desktop, [Ollama](https://ollama.com) running locally with models pulled.

### Step 1 — Pull Ollama models (one-time)

```bash
ollama pull llama3.2:3b
ollama pull qwen3:4b
ollama pull nomic-embed-text:latest
```

### Step 2 — Configure environment

```bash
cp .env.example .env
# Edit .env if needed (defaults work for local Docker setup)
```

### Step 3 — Start all services

```bash
docker compose up --build
```

This will:
1. Start PostgreSQL 16 with pgvector on port `5433`
2. Build and start the FastAPI backend on port `8002` (internal `8000`)
3. **Auto-ingest all 6 transcript chunks** into pgvector on first boot (no manual step needed)
4. Build and serve the React frontend via nginx on **[http://localhost](http://localhost)**

> **Note:** Ollama runs on your host machine. The backend reaches it via `host.docker.internal:11434`.

### Step 4 — Open the app

Navigate to **[http://localhost](http://localhost)** in your browser.

---

## Local Development Setup (No Docker)

### Prerequisites
- Python 3.12, Node.js v24+
- PostgreSQL 16 with pgvector, Ollama

### 1. Start PostgreSQL

```bash
docker compose up postgres -d
```

### 2. Backend

```powershell
cd backend
# Install dependencies
..\.venv\Scripts\pip install -r requirements.txt

# Run ingestion (loads 6 transcript chunks into pgvector)
$env:PYTHONPATH="."
..\.venv\Scripts\python.exe -m app.services.run_ingest

# Start FastAPI dev server
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

---

## 2–3 Minute Technical Interview Demonstration Script

Follow this structured workflow to present the core architecture, grounding, and security controls:

### Phase 1 — System Health & Diagnostics (0:00 – 0:30)
1. Navigate to **[http://localhost](http://localhost)** in Chrome or your preferred browser.
2. Observe the top bar: Active Model selector (`Ollama: llama3.2:3b`), and real-time connectivity status.
3. Open the **Diag** tab in the sidebar (or execute `curl http://localhost:8000/api/v1/health` in a terminal).
4. Point out:
   - Database: `connected` (PostgreSQL 16 + pgvector)
   - Ollama Status: `online` (`llama3.2:3b`, `qwen3:4b`, `nomic-embed-text:latest` detected)
   - Cloud Provider: `anthropic: false (unconfigured, returns 503 fallback)`

### Phase 2 — Session Creation & Message Persistence (0:30 – 1:00)
1. Click **+ New Session** in the sidebar. A new UUID-backed chat session is created immediately.
2. In the chat input, type: `hi` and send.
3. Notice: Immediate conversational greeting response (sub-100ms) with zero fabricated citations.
4. Refresh the browser page: verify the session and greeting reload instantly from PostgreSQL.

### Phase 3 — Grounded Ollama RAG Answer with Citation (1:00 – 1:45)
1. In the same session, send the domain query:
   > *"What is Patrick Campbell's advice on SaaS pricing and value metrics?"*
2. As the response completes (~25–35s on CPU), observe:
   - Direct synthesized answer highlighting value metrics, avoiding 100% feature pricing, and aligning pricing tiers with customer value.
   - **📚 Grounded Transcript Evidence** card appears below the message displaying:
     - Episode: *Patrick Campbell: SaaS Pricing & Monetization*
     - Speaker: *Patrick Campbell*
     - Similarity Score: *77% cosine match*
     - Source link to verified Lenny Substack article.
3. Test conceptual accuracy: Ask *"What is the relation between SaaS and B2B?"*
   - Model correctly clarifies SaaS is a software delivery/business model, B2B describes the target customer base, SaaS can be B2B or B2C, and B2B SaaS is their intersection — with no falsely attributed podcast claims.

### Phase 4 — Ship 30 Essay & Sandboxed Artifact Preview (1:45 – 2:30)
1. Click the **Artifacts** tab in the sidebar to view previously persisted artifacts, or click **✍️ Generate Ship 30 Essay**.
2. Select the existing essay artifact: *"The 10x Pricing Playbook: Why Most SaaS Founders Undercharge"*.
3. Highlight the structured Ship 30 layout:
   - **Hook:** Opening counterintuitive thesis on SaaS monetization.
   - **Problem:** Why 80% of founders fail at value metric definition.
   - **Podcast Grounded Insight:** Verified Patrick Campbell excerpt quote on 10x value metric alignment.
   - **Original Strategic Synthesis & Actionable Playbook:** 3 implementation steps and takeaway checklist (~958 words).
4. Toggle between **Preview** and **Source Code**:
   - Show the sandboxed `<iframe>` with `sandbox=""` and DOMPurify sanitization.
   - Emphasize zero script execution, no parent window access, and complete XSS protection.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | DB + Ollama health status |
| `POST` | `/api/v1/ingest` | Trigger transcript ingestion |
| `POST` | `/api/v1/retrieval/search` | Cosine similarity transcript search |
| `POST` | `/api/v1/sessions` | Create chat session |
| `GET` | `/api/v1/sessions` | List sessions (by `updated_at` DESC) |
| `PATCH` | `/api/v1/sessions/{id}` | Update session title |
| `DELETE` | `/api/v1/sessions/{id}` | Delete session + cascade |
| `GET` | `/api/v1/sessions/{id}/messages` | Paginated message history |
| `POST` | `/api/v1/chat` | Grounded RAG chat completion |
| `POST` | `/api/v1/essays/generate` | Generate Ship 30 essay artifact |
| `GET` | `/api/v1/sessions/{id}/artifacts` | List session artifacts |
| `DELETE` | `/api/v1/artifacts/{id}` | Delete artifact |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Running Automated Tests

```powershell
# 1. Backend: 36 automated unit, DB, RAG, essay, and error-handling tests
cd backend
$env:PYTHONPATH="."
..\.venv\Scripts\pytest.exe -v

# 2. 10-Question Retrieval Quality Evaluation Benchmark (100% accuracy)
..\.venv\Scripts\python.exe -m app.services.run_eval

# 3. Live 7-Turn RAG Quality Acceptance Suite (Docker / Live Stack)
..\.venv\Scripts\python.exe tests/run_quality_acceptance.py

# 4. Frontend: 6 DOMPurify / Sandboxed Iframe security regression tests
cd ..\frontend
npm test -- --run

# 5. Frontend Production Build (clean, zero-warning bundle)
npm run build
```

---

## Grounded Knowledge Base Corpus (Phase C5 Audit Verified)

6 real, publicly accessible *Lenny's Podcast* transcript excerpts stored in `backend/data/transcripts/`:

| Guest | Topic | Words | Source |
|---|---|---|---|
| Elena Verna | Product-Led Growth & Freemium Conversion | 271 | lennysnewsletter.com |
| Patrick Campbell | B2B SaaS Pricing & Value Metrics | 236 | lennysnewsletter.com |
| Shreyas Doshi | PM Frameworks & LNO Prioritization | 193 | lennysnewsletter.com |
| Brian Balfour | Growth Loops & Retention Engines | 184 | lennysnewsletter.com |
| Geoff Charles | Ramp Velocity & Product Speed | 168 | lennysnewsletter.com |
| Casey Winters | Search SEO Loops & Marketplaces | 173 | lennysnewsletter.com |

**Corpus:** 6 files · 1,225 total words · **6 active vector chunks** (768-dim `nomic-embed-text:latest`)  
**Retrieval Benchmark:** 100% score across 10 evaluation queries (8 grounded + 2 out-of-scope with proper insufficient-evidence fallback)  
**Provenance:** Curated excerpts from published Substack episodes. Source URLs and guest attributions preserved in every chunk.

---

## Coding-Agent Development Trajectory Logs

In accordance with assignment requirements, the full authentic development session history recorded during this project (Phases C1–C6) is available in:
- [`docs/agent_logs/README.md`](docs/agent_logs/README.md)
- [`docs/agent_logs/trajectory_transcript.jsonl`](docs/agent_logs/trajectory_transcript.jsonl)

This JSONL log captures the chronological trajectory of agent tool invocations, shell commands, test executions, and model reasoning without any historical alterations or synthetic modifications.

---

## Security Notes

- HTML and Markdown artifacts are rendered inside a **strictly sandboxed `<iframe sandbox="">`** (no scripts, no same-origin, no popups, no forms)
- All HTML is sanitized with **DOMPurify** before entering the iframe
- `javascript:` URLs and dangerous event handlers are stripped
- `.env` is gitignored; no secrets are committed
- Missing cloud API keys return `HTTP 503 Service Unavailable` with actionable troubleshooting messages rather than HTTP 404 or process crashes.

---

## Documentation

- [Product Requirements Document](docs/PRD.md)
- [UI/UX & System Design](docs/design.md)
- [Technical Architecture](docs/architecture.md)
- [Development Trajectory Logs](docs/agent_logs/README.md)

