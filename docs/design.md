# UI/UX & System Design — The Lenny Growth Assistant

**Project:** The Lenny Growth Assistant  
**Date:** October 9, 2026  
**Tech Stack:** React, JavaScript (JSX), Vite, Tailwind CSS, FastAPI, PostgreSQL  

---

## 1. Design Philosophy & Visual System

The Lenny Growth Assistant interface is built with a modern, high-contrast dark aesthetic featuring glassmorphism elements, fluid micro-interactions, and subtle gradient highlights. It emphasizes clarity, citation transparency, and seamless side-by-side artifact inspection.

### 1.1 Color Palette & Typography
* **Base Theme:** Dark Mode (`#0F172A` Slate-900 / `#1E293B` Slate-800)
* **Accent Colors:**
  * Primary Action / Brand: Indigo (`#6366F1`)
  * Grounded Citations: Emerald (`#10B981`)
  * Artifact / Essay Skills: Amber (`#F59E0B`)
  * Danger / Error Diagnostic: Rose (`#F43F5E`)
* **Typography:** `Inter`, `system-ui`, `-apple-system`, sans-serif. Monospace for code/HTML artifacts (`Fira Code`, `JetBrains Mono`).

---

## 2. Layout & Component Architecture

The interface uses a 3-column / split-screen layout:
1. **Sidebar Navigation (260px)** — Session management, model provider status, and prompt shortcuts.
2. **Main Chat Workspace (Flexible)** — Message stream with inline citation pills, streaming responses, and skill action triggers.
3. **Side-by-Side Artifact Workspace (Collapsible / Flexible 50%)** — Live sandboxed iframe preview, code viewer, and download tools.

```text
+-----------------------------------------------------------------------------------+
|  THE LENNY GROWTH ASSISTANT                   [ Active Model: Ollama qwen3:4b v ] |
+------------------+----------------------------------+-----------------------------+
| + New Session    | User: How do I measure PLG onboarding?                          |
|                  |                                  | ARTIFACT PREVIEW (HTML)     |
| Sessions         | Assistant: Based on Lenny's      | +-------------------------+ |
| ---------------- | podcast with Elena Verna...      | |  Onboarding Funnel      | |
| > B2B Onboarding |                                  | |  Conversion Dashboard   | |
|   Pricing Models | [Citation: Elena Verna - Ep 42]  | |  [Live Sandboxed View]  | |
|   Ship30 Essay 1 |                                  | +-------------------------+ |
|                  | [Action: Generate Artifact  ]    | [ Preview ] [ View Code ]   |
|                  |                                  | [ Copy Code ] [ Download ]  |
|                  | +------------------------------+ |                             |
|                  | | Ask a PM or growth question..| |                             |
|                  | +------------------------------+ |                             |
+------------------+----------------------------------+-----------------------------+
```

### 2.2 Component Hierarchy (React / JSX)
```text
src/
├── components/
│   ├── layout/
│   │   ├── Header.jsx           # App title, health status, ModelSelector
│   │   ├── Sidebar.jsx          # Session list, creation, deletion
│   │   └── MainLayout.jsx       # Grid container for split views
│   ├── chat/
│   │   ├── ChatWindow.jsx       # Scrollable message list & input bar
│   │   ├── MessageItem.jsx      # Message bubble with Markdown formatting
│   │   ├── CitationCard.jsx     # Grounded transcript quote drawer
│   │   ├── StreamingBubble.jsx  # SSE live token stream indicator
│   │   └── PromptShortcuts.jsx  # Quick buttons ("Ship 30 for 30 Essay", "Pricing Table Widget")
│   ├── artifact/
│   │   ├── ArtifactViewer.jsx   # Tab container (Preview vs Raw Code)
│   │   ├── SandboxedIframe.jsx  # Isolated HTML renderer
│   │   └── CodeEditorView.jsx   # Syntax-highlighted HTML/Markdown view
│   └── common/
│       ├── ModelSelector.jsx    # Model/Provider dropdown
│       ├── Badge.jsx            # Status indicators
│       └── ErrorBanner.jsx      # Diagnostic error display
├── hooks/
│   ├── useChatSession.js        # Session persistence & state
│   ├── useArtifact.js           # Active artifact management
│   └── useModelProvider.js      # Model selection state
└── utils/
    ├── api.js                   # Axios/Fetch client with base URL configuration
    └── security.js              # HTML sanitization & iframe srcdoc helpers
```

---

## 3. API Contract Specifications

### 3.1 Session Endpoints
* **`POST /api/v1/sessions`**
  * *Request:* `{ "title": "B2B SaaS Onboarding" }`
  * *Response:* `{ "session_id": "uuid", "title": "B2B SaaS Onboarding", "created_at": "ISO-8601" }`

* **`GET /api/v1/sessions`**
  * *Response:* `[ { "session_id": "uuid", "title": "...", "created_at": "..." } ]`

* **`GET /api/v1/sessions/{session_id}/messages`**
  * *Response:* `[ { "message_id": "uuid", "role": "user|assistant", "content": "...", "citations": [...], "artifact_id": "uuid|null" } ]`

### 3.2 Chat & Agent Orchestration Endpoint
* **`POST /api/v1/chat/completions`** (Supports standard JSON and Server-Sent Events `text/event-stream`)
  * *Request:*
    ```json
    {
      "session_id": "uuid-v4",
      "prompt": "How do top PMs approach freemium vs free trial?",
      "provider": "ollama",
      "model": "qwen3:4b",
      "skill": "default | ship30_essay | generate_artifact"
    }
    ```
  * *Response Stream / JSON:*
    ```json
    {
      "message_id": "uuid-v4",
      "role": "assistant",
      "content": "According to Lenny's podcast transcript with Elena Verna...",
      "citations": [
        {
          "guest_name": "Elena Verna",
          "episode_title": "Product-Led Growth Strategies",
          "chunk_id": "ep42_chunk_12",
          "similarity_score": 0.89
        }
      ],
      "artifact": null,
      "provider_used": "ollama",
      "model_used": "qwen3:4b"
    }
    ```

### 3.3 Artifact Endpoints
* **`GET /api/v1/artifacts/{artifact_id}`**
  * *Response:* `{ "artifact_id": "uuid", "type": "html|markdown", "title": "...", "code": "<html>...</html>", "created_at": "..." }`

### 3.4 System Health & Diagnostics
* **`GET /api/v1/health`**
  * *Response:*
    ```json
    {
      "status": "healthy",
      "database": "connected",
      "ollama_status": "online",
      "ollama_models": ["qwen3:4b", "nomic-embed-text:latest"],
      "cloud_providers": { "anthropic": true }
    }
    ```

---

## 4. Security Architecture & Artifact Isolation

Generated HTML artifacts are rendered using a strict security boundary:

1. **Sandboxed `<iframe>` (`srcdoc` attribute):**
   * HTML artifacts are passed into the iframe via `srcDoc={sanitizedHtml}` inside `SandboxedArtifactViewer.jsx`.
   * `sandbox` attributes applied: `sandbox=""` (strictly empty sandbox).
   * **Disabled capabilities:** Scripts, same-origin access, popups, forms, and top-level navigation are all disabled. Untrusted generated HTML is rendered in a completely opaque, scriptless execution boundary.
2. **DOMPurify Sanitization:**
   * Before passing content to the iframe or markdown renderer, content is sanitized using DOMPurify (`frontend/src/utils/sanitizer.js`).
   * Scripts (`<script>`), untrusted iframes, objects, embeds, inline event handlers (`onload`, `onerror`, `onclick`), and pseudo-protocols (`javascript:`, `vbscript:`, `data:`) are stripped.
3. **Content Security Policy & Token Isolation:**
   * No API credentials, tokens, or session storage data are ever accessible to the iframe window object.
   * Session storage and network fetch capabilities are entirely isolated from the artifact sandbox.

---

## 5. System Limitations & Production Constraints

1. **Knowledge Base Scope:** Grounded strictly in 6 curated transcript excerpts (1,225 total words, 6 chunks) from published *Lenny's Podcast* interviews (Elena Verna, Patrick Campbell, Shreyas Doshi, Brian Balfour, Geoff Charles, Casey Winters). Non-corpus topics honestly return insufficient-evidence responses.
2. **Local CPU Inference Latency:** Running local Ollama on CPU requires 20–40s for conversational responses and 2–3 minutes for complete essay generation. The UI displays responsive loading warnings to communicate this to users.
3. **Optional Anthropic Integration:** Cloud LLM (Claude 3.5 Sonnet) is optional. When unconfigured, API requests return `HTTP 503 Service Unavailable` with clear actionable error messages rather than crashing.
4. **Verified Essay Output:** Essay generation produces ~958 words of structured, multi-paragraph content, separating verified podcast citations from original analysis.

