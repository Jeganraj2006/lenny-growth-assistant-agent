# Coding-Agent Development Trajectory Logs

This directory contains the authentic, unedited development session transcripts recorded during the implementation of **The Lenny Growth Assistant** across all development phases (C1 through C6).

## Provenance Details
- **Agent Platform:** Antigravity AI Coding Assistant (Google DeepMind Advanced Agentic Coding)
- **Session / Conversation ID:** `a7c4286b-d3ee-458f-b567-c0f57b9f0640`
- **File:** `trajectory_transcript.jsonl`
- **Format:** JSON Lines (JSONL), where each line records a complete interaction step (user requests, tool executions, terminal commands, test validations, and agent reasoning).
- **Phases Documented:**
  - **Phase C1:** Backend scaffold, PostgreSQL pgvector setup, Ollama adapter, provider proof suites.
  - **Phase C2:** Transcript ingestion pipeline, chunking, 768-dimensional `nomic-embed-text` embeddings, vector storage.
  - **Phase C3.1 / C3.2:** Persistent sessions, message history CRUD, grounded RAG chat with transcript citations.
  - **Phase C4:** Ship 30 for 30 essay generation skill, sandboxed artifact viewer, DOMPurify sanitization.
  - **Phase C5:** Real transcript corpus verification, RAG quality evaluation, provenance audit.
  - **Phase C6:** Docker Compose deployment, live RAG chat quality fix, greeting handling, SaaS conceptual accuracy fix, Anthropic provider error handling (HTTP 503), essay expansion (~958 words), and delivery readiness.

## How to Inspect the Logs
Each JSON line contains:
- `step_index`: Step order in the trajectory.
- `source`: Message origin (`USER_INPUT`, `MODEL`, `SYSTEM`).
- `tool_calls`: Tool calls executed during that step (file reads/writes, bash/powershell commands, test runs).
- `content`: Text response or command output.

Example PowerShell one-liner to view user inputs across the project lifecycle:
```powershell
Get-Content docs/agent_logs/trajectory_transcript.jsonl | ConvertFrom-Json | Where-Object { $_.type -eq "USER_INPUT" } | Select-Object step_index, content
```
