# 🤖 LinkedIn Easy Apply Automation Agent

An intelligent, end-to-end job application bot that automatically fills and submits LinkedIn Easy Apply forms — powered by **LangGraph**, **OpenAI GPT-4o-mini**, and **Playwright**.

Includes a **Profile Intelligence Portal** (React + FastAPI) where you manage your profile via AI chat and trigger the apply bot directly from the browser.

---

## System Architecture

```mermaid
graph TB
    subgraph Portal["🖥️ Profile Intelligence Portal"]
        FE["React Frontend\n(Vite :5173)"]
        BE["FastAPI Backend\n(:8000)"]
        DB[("SQLite DB\nprofile + messages")]

        FE -- "REST API" --> BE
        BE -- "read/write" --> DB
    end

    subgraph Agent["🤖 Easy Apply Agent"]
        RUN["run_easy_apply.py\n(Playwright orchestrator)"]
        LG["easy_apply_agent.py\n(LangGraph state machine)"]
        UP["user_profile.py\n(reads SQLite DB)"]
        PW["Playwright\n(Chromium browser)"]
        BD[("browser_data/\npersistent session")]

        RUN --> LG
        LG --> UP
        UP -- "json.dumps(profile)" --> LG
        RUN --> PW
        PW -- "session" --> BD
    end

    FE -- "⚡ Start Auto Apply\n(subprocess)" --> RUN
    DB -- "live profile JSON" --> UP
    LG -- "JS fill actions" --> PW
    PW -- "form HTML" --> LG

    OAI["☁️ OpenAI\nGPT-4o-mini"]
    LG -- "structured output" --> OAI
    OAI -- "List[FillAction]" --> LG
    BE -- "chat LLM calls" --> OAI
```

---

## Easy Apply Agent — LangGraph Workflow

```mermaid
flowchart TD
    START([▶ Start Application]) --> OPEN["Open job listing\nclick Easy Apply button"]
    OPEN --> EXTRACT["extract_form_html\nRead modal step HTML via Playwright"]
    EXTRACT --> LLM["analyze_with_llm\nGPT-4o-mini → List[FillAction]\n(field + value + JS selector)"]
    LLM --> EXEC["execute_js_actions\nPlaywright runs JS for each action\n(fill, select, radio, checkbox)"]
    EXEC --> CHECK{"Nav button\ndetected?"}
    CHECK -- "Next →" --> CLICK_NEXT["click_next\nPlaywright clicks Next"]
    CHECK -- "Review →" --> CLICK_REVIEW["click_review\nPlaywright clicks Review"]
    CHECK -- "Submit →" --> SUBMIT["submit_application\nPlaywright clicks Submit"]
    CHECK -- "None found" --> RETRY{"Retry\ncount < 3?"}
    CLICK_NEXT --> EXTRACT
    CLICK_REVIEW --> CONFIRM["Confirm & Submit"]
    CONFIRM --> SUBMIT
    RETRY -- "Yes" --> LLM
    RETRY -- "No (failed)" --> SKIP([⏭ Skip this job])
    SUBMIT --> LOG["Log to console\nmark applied"]
    LOG --> NEXT_JOB([🔁 Next job])

    style START fill:#7c3aed,color:#fff
    style SUBMIT fill:#10b981,color:#fff
    style SKIP fill:#ef4444,color:#fff
    style LLM fill:#4f46e5,color:#fff
```

---

## Profile Portal — AI Chat Workflow

```mermaid
sequenceDiagram
    actor User
    participant React as React Frontend
    participant API as FastAPI /api/chat
    participant LLM as GPT-4o-mini
    participant DB as SQLite DB

    User->>React: Types message<br/>"change skills to add TensorFlow"
    React->>API: POST /api/chat {message, session_id}
    API->>DB: get_profile() → JSON
    API->>DB: get_messages(session_id) → history
    API->>LLM: SystemPrompt(profile JSON)<br/>+ conversation history<br/>+ user message
    Note over LLM: with_structured_output(ChatReply)<br/>returns typed Pydantic model
    LLM-->>API: ChatReply {<br/>  response: "Done! Added TensorFlow…",<br/>  should_update: true,<br/>  updates: [{key:"skills", value:[…]}],<br/>  delete_keys: []<br/>}
    API->>DB: update_profile(updates_dict)
    API->>DB: add_message(user + assistant)
    API-->>React: {response, profile_updated, updated_fields, profile}
    React->>React: Refresh ProfilePanel
    React->>User: Shows reply + updated profile
```

---

## Project Structure

```
linkedin-easy-apply-agent/
│
├── easy_apply_agent.py          # LangGraph agent — form analysis + JS fill actions
├── run_easy_apply.py            # Entry point — Playwright orchestration loop
├── user_profile.py              # Profile loader (reads SQLite DB → json.dumps)
│
├── data/
│   └── setup_linkedin_browser.py  # One-time LinkedIn login & session save
│
├── browser_data/                # Persistent Playwright session (gitignored)
│
├── profile_portal/
│   ├── backend/                 # FastAPI app
│   │   ├── main.py              # Routes: profile, chat, apply control (start/stop/status)
│   │   ├── chat_service.py      # LLM chat (memory buffer + Pydantic structured output)
│   │   ├── db.py                # SQLite helpers (profile CRUD + messages)
│   │   └── requirements.txt
│   └── frontend/                # React + Vite
│       └── src/
│           ├── App.jsx                # Layout + ⚡ Auto Apply button
│           ├── components/
│           │   ├── ChatPanel.jsx      # AI chat interface (markdown rendering)
│           │   └── ProfilePanel.jsx   # Profile viewer + delete custom keys (×)
│           └── api/client.js          # fetch wrappers for all endpoints
│
├── requirements.txt             # Agent deps (playwright, langchain, openai, langgraph)
├── .env                         # API keys (gitignored)
└── .gitignore
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/akashcodejames/linkedin-easy-apply-agent
cd linkedin-easy-apply-agent

# Agent dependencies
pip install -r requirements.txt
playwright install chromium

# Portal backend
cd profile_portal/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cd ../..
```

### 2. Configure `.env`

```env
OPENAI_API_KEY=sk-...
```

### 3. Login to LinkedIn (one-time)

```bash
python data/setup_linkedin_browser.py
```

Opens Chromium — log in manually. Session saved to `browser_data/` permanently.

### 4. Start the Profile Portal

```bash
# Terminal 1 — Backend
cd profile_portal/backend && source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd profile_portal/frontend
npm install && npm run dev
```

Open **http://localhost:5173** and update your profile via AI chat.

### 5. Run the Apply Bot

**From the Portal UI:** Click **⚡ Start Auto Apply** in the header.

**From terminal:**
```bash
python run_easy_apply.py
```

---

## Key Tech

| Layer | Tech |
|---|---|
| Browser automation | Playwright (Chromium, persistent session) |
| Agent orchestration | LangGraph state machine |
| LLM | OpenAI GPT-4o-mini |
| Structured output | Pydantic v2 + `with_structured_output()` |
| Profile storage | SQLite (read via `json.dumps` into LLM prompt) |
| Portal backend | FastAPI + uvicorn |
| Portal frontend | React + Vite |
| Chat memory | ConversationSummaryBuffer (auto-compresses) |

---

> **Note:** The bot only applies to jobs with the blue **Easy Apply** button. Always test with a few applications manually before running at scale.
