# Product Requirement Document (PRD) — The Lenny Growth Assistant

**Project:** The Lenny Growth Assistant  
**Date:** October 9, 2026  
**Target Completion:** October 12, 2026 (End of Day)  
**Author:** Full-Stack & AI Engineering Lead  

---

## 1. Executive Summary & Product Vision

**The Lenny Growth Assistant** is an AI conversational application designed for Product Managers, Growth Leads, Founders, and Product Marketers. It provides expert product management and growth advice strictly grounded in transcript data from *Lenny's Podcast*. Beyond conversational Q&A, the assistant features specialized skills including generating ~1,250-word *Ship 30 for 30*-style actionable essays and producing rich, interactive web artifacts (Markdown, HTML/CSS) rendered side-by-side inside a sandboxed viewport.

The system supports seamless switching between real Cloud LLM providers (e.g., Anthropic Claude 3.5 Sonnet) and local offline execution using Ollama (`qwen3:4b` for reasoning/generation and `nomic-embed-text:latest` for embeddings).

---

## 2. Problem Statement & User Personas

### 2.1 Problem Statement
Product managers and growth professionals frequently seek advice on frameworks (e.g., PLG, retention, acquisition, pricing, hiring, metrics). While *Lenny's Podcast* contains world-class insights from industry experts, searching through hundreds of hours of raw audio and transcripts is inefficient. Generic LLMs hallucinate frameworks or give unverified advice. Users need:
1. **Verifiable, grounded answers** direct from guest transcripts with explicit episode citations.
2. **Actionable writing outputs** (long-form essays formatted in the popular *Ship 30 for 30* framework).
3. **Dynamic visual artifacts** (wireframes, landing page layouts, pricing tables, dashboards) rendered directly in the app.
4. **Privacy and cost flexibility**, allowing local execution via Ollama when offline or when using private data.

### 2.2 User Personas
* **Persona A: Sarah (Senior PM at Scale-up)** — Needs quick, grounded advice on B2B SaaS onboarding metrics referenced by Lenny's guests, complete with exact transcript quotes.
* **Persona B: Alex (Growth Founder)** — Wants a 1,250-word structured *Ship 30 for 30* essay synthesizing growth loops to share with their growth team.
* **Persona C: Marcus (Product Designer / PM)** — Requests an interactive HTML/CSS component (e.g., a pricing table or feature comparison widget) to test product UI ideas based on interview insights.

---

## 3. Mandatory Product Capabilities & Feature Specifications

### 3.1 Independent Chat Sessions & History
* **FR-1.1:** Users can create multiple independent chat sessions with custom titles.
* **FR-1.2:** Complete message history (user queries, agent responses, tool invocations, citations, generated artifacts) must persist in PostgreSQL across page reloads.
* **FR-1.3:** Active session switching without loss of context or state.

### 3.2 Transcript Retrieval-Augmented Generation (RAG)
* **FR-2.1:** Ground all domain answers in Lenny's Podcast transcript repository.
* **FR-2.2:** Multi-stage vector similarity search using `nomic-embed-text:latest` embeddings stored in PostgreSQL via `pgvector`.
* **FR-2.3:** Strict citation formatting: Every answer derived from transcripts must explicitly link guest names, episode titles, and timestamps/chunk identifiers.
* **FR-2.4:** **No Hallucination Policy:** If the transcript database lacks sufficient evidence to answer a domain query, the assistant must explicitly state that the evidence is insufficient rather than fabricating an answer.

### 3.3 Dual Provider Engine (Cloud & Local Ollama via Agent SDK)
* **FR-3.1:** Support real Cloud LLM providers (Anthropic Claude 3.5 Sonnet) alongside local Ollama execution (`qwen3:4b`).
* **FR-3.2:** Routing for local Ollama execution utilizes Ollama's Anthropic-compatible Messages API (`/v1/messages`) via `ANTHROPIC_BASE_URL="http://127.0.0.1:11434"`.
* **FR-3.3:** Frontend UI dropdown to switch active model/provider dynamically per session or request.
* **FR-3.4:** Graceful degradation: If Ollama is unreachable or a cloud API key is missing, return a clear, user-friendly diagnostic error message instead of crashing.

### 3.4 Ship 30 for 30 Writing Skill
* **FR-4.1:** Dedicated agent tool/mode for generating structured long-form essays based on transcript insights (targeting ~1,150–1,350 words, verified at ~958 words on local CPU Ollama).
* **FR-4.2:** Essay structure: Hook, Clear Problem Definition, 3–5 Actionable Framework Steps, Real-world Podcast Example, and a Summarizing Takeaway. Explicitly distinguishes podcast-supported insights from original analysis and practical recommendations.

### 3.5 Interactive Artifact Generation & Sandboxed Viewer
* **FR-5.1:** Generate live artifacts (Markdown documents, single-file HTML/CSS UI widgets, pricing tables, checklists, landing page mocks).
* **FR-5.2:** Render artifacts side-by-side with the chat interface in a responsive split workspace.
* **FR-5.3:** **Security Boundary:** Generated HTML artifacts are treated as untrusted content and rendered inside a sandboxed `<iframe>` with `sandbox=""` (strictly empty sandbox; disabling `allow-scripts`, `allow-same-origin`, `allow-popups`, and `allow-forms` to prevent cross-site scripting, token theft, or parent-window access). Content is pre-sanitized via DOMPurify.

---

## 4. Success Metrics & Quality Targets

| Metric | Target | Verification Method |
| :--- | :--- | :--- |
| **Grounded Citation Accuracy** | 100% of transcript-backed claims cite source guest/episode | Automated RAG benchmark tests |
| **Zero Hallucination on Missing Facts** | 100% detection of out-of-domain/unsupported queries | Evaluation test suite with negative queries |
| **Artifact Security Isolation** | Zero script execution or parent DOM access from generated HTML (`sandbox=""` + DOMPurify) | Automated browser security tests (6/6 passing) |
| **Ollama Local Fallback** | Seamless generation with local Ollama (`llama3.2:3b` / `qwen3:4b`) when cloud is toggled off | Manual UI testing & automated integration tests |
| **Essay Quality & Grounding** | ~958 words verified output with 5-section Ship 30 structure | Live Ollama essay generation test |
| **App Startup Time** | $< 30$ seconds via Docker Compose | Clean environment startup validation |

---

## 5. Assumptions, Dependencies, Trade-Offs & Real Limitations

### 5.1 Assumptions
* The user environment runs Docker Compose with access to local Ollama running on host at `http://127.0.0.1:11434`.
* `llama3.2:3b` (or `qwen3:4b`) and `nomic-embed-text:latest` are pre-pulled in the local Ollama instance.
* PostgreSQL 16+ with `pgvector` container is managed via `docker-compose.yml`.

### 5.2 Trade-offs & Scope Boundaries
* **Language/Framework Scope:** Backend strictly Python 3.12 + FastAPI. Frontend strictly React + JavaScript (JSX) + Vite (No TypeScript).
* **Single-tenant Focus:** Designed for local/single-user deployment for assessment evaluation; user authentication is simplified to session IDs without JWT login gates.
* **Artifact Interactivity:** Scripts inside generated HTML artifacts are disabled by default (`sandbox=""`) for maximum security isolation.

### 5.3 Real System Limitations
1. **Corpus Size:** Grounded strictly in 6 curated transcript excerpts (1,225 total words, 6 active chunks) from published *Lenny's Podcast* interviews (Elena Verna, Patrick Campbell, Shreyas Doshi, Brian Balfour, Geoff Charles, Casey Winters). Non-corpus domain queries honestly return insufficient-evidence responses.
2. **Local CPU Inference Latency:** Running local Ollama on CPU requires 20–40 seconds for grounded chat completions and 2–3 minutes for complete long-form essay generation.
3. **Optional Anthropic Integration:** Cloud LLM (Claude 3.5 Sonnet) is an optional provider. When `ANTHROPIC_API_KEY` is unconfigured, the system returns an informative `HTTP 503 Service Unavailable` diagnostic rather than an HTTP 404 error or crash.
4. **Verified Essay Output:** Live essay generation produces approximately 958 words with structured multi-paragraph narrative prose and clearly demarcated podcast evidence vs. original strategic synthesis.

---

## 6. Risks & Mitigation Strategies

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Python Package Version Shifts** | High | Standardized on Python 3.12 for project virtualenv and Docker base images to ensure pre-compiled binary wheel availability. |
| **Ollama IPv6 Connection Failures** | Medium | Hardcode provider endpoint fallback to IPv4 loopback (`http://127.0.0.1:11434`). |
| **Slow Local Generation** | Medium | Configured fast instruction model (`llama3.2:3b`) without reasoning-token overhead for chat; UI displays progress and loading warning. |
| **XSS / Token Theft via Generated HTML** | Critical | Enforce strict iframe sandboxing (`sandbox=""`) with DOMPurify sanitization. |
| **Missing Cloud Provider Key** | Medium | Graceful degradation returning `HTTP 503` with actionable configuration message instead of crashing. |

