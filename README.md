# 🤖 LinkedIn Easy Apply Automation Agent

An intelligent, end-to-end job application bot that automatically fills and submits LinkedIn Easy Apply forms — powered by **LangGraph**, **OpenAI GPT-4o-mini**, and **Playwright**.

Includes a **Profile Intelligence Portal** (React + FastAPI) where you manage your profile via AI chat and trigger the apply bot directly from the browser.

---

## System Architecture

```mermaid
graph TB
    subgraph Portal["🖥️ Profile Intelligence Portal"]
        FE["React Frontend<br/>(Vite :5173)"]
        BE["FastAPI Backend<br/>(:8000)"]
        DB[("SQLite DB<br/>profile + messages")]

        FE -- "REST API" --> BE
        BE -- "read / write" --> DB
    end

    subgraph Agent["🤖 Easy Apply Agent"]
        run_easy_apply["run_easy_apply.py<br/>Playwright orchestrator"]
        easy_apply_agent["easy_apply_agent.py<br/>LangGraph state machine"]
        user_profile["user_profile.py<br/>reads SQLite DB"]
        playwright["Playwright<br/>Chromium browser"]
        browser_data[("browser_data/<br/>persistent session")]

        run_easy_apply --> easy_apply_agent
        easy_apply_agent --> user_profile
        run_easy_apply --> playwright
        playwright -- "session" --> browser_data
    end

    FE -- "⚡ Start Auto Apply<br/>subprocess" --> run_easy_apply
    DB -- "live profile JSON" --> user_profile
    user_profile -- "json.dumps" --> easy_apply_agent
    easy_apply_agent -- "JS fill actions" --> playwright
    playwright -- "form HTML" --> easy_apply_agent

    OAI["☁️ OpenAI<br/>GPT-4o-mini"]
    easy_apply_agent -- "with_structured_output" --> OAI
    OAI -- "List[FillAction]" --> easy_apply_agent
    BE -- "chat LLM calls" --> OAI
```

---

## Easy Apply Agent — LangGraph Workflow

```mermaid
flowchart TD
    start_job(["▶ Start Job"]) --> open_easy_apply

    open_easy_apply["open_easy_apply<br/>Click Easy Apply button"]
    extract_form_html["extract_form_html<br/>Read modal step HTML"]
    analyze_form["analyze_form<br/>GPT-4o-mini → List[FillAction]"]
    execute_js_actions["execute_js_actions<br/>Playwright runs JS per field"]
    check_navigation{"check_navigation<br/>Which button visible?"}
    click_next["click_next<br/>→ Next step"]
    click_review["click_review<br/>→ Review page"]
    submit_application["submit_application<br/>→ Final Submit"]
    retry_or_skip{"retry_count < 3?"}
    log_success(["✅ Logged & next job"])
    skip_job(["⏭ Skip job"])

    open_easy_apply --> extract_form_html
    extract_form_html --> analyze_form
    analyze_form --> execute_js_actions
    execute_js_actions --> check_navigation
    check_navigation -- "Next" --> click_next
    check_navigation -- "Review" --> click_review
    check_navigation -- "Submit" --> submit_application
    check_navigation -- "None found" --> retry_or_skip
    click_next --> extract_form_html
    click_review --> submit_application
    submit_application --> log_success
    retry_or_skip -- "Yes" --> analyze_form
    retry_or_skip -- "No" --> skip_job

    style start_job fill:#7c3aed,color:#fff
    style submit_application fill:#10b981,color:#fff
    style skip_job fill:#ef4444,color:#fff
    style analyze_form fill:#4f46e5,color:#fff
```

---

## Profile Portal — AI Chat Workflow

```mermaid
sequenceDiagram
    actor User
    participant React as React Frontend
    participant API as FastAPI /api/chat
    participant chat_service as chat_service.py
    participant GPT as GPT-4o-mini
    participant DB as SQLite DB

    User->>React: "add TensorFlow to my skills"
    React->>API: POST /api/chat
    API->>chat_service: chat(session_id, message)
    chat_service->>DB: get_profile()
    chat_service->>DB: get_messages(session_id)
    chat_service->>GPT: SystemPrompt + profile JSON<br/>+ conversation history
    Note over GPT: with_structured_output(ChatReply)<br/>returns typed Pydantic model
    GPT-->>chat_service: ChatReply {<br/>  response, should_update,<br/>  updates: [ProfileUpdateItem],<br/>  delete_keys: []<br/>}
    chat_service->>DB: update_profile(updates_dict)
    chat_service->>DB: add_message(user + assistant)
    chat_service-->>API: response dict
    API-->>React: {response, profile_updated, profile}
    React->>User: Reply shown + ProfilePanel refreshed
```

---

## Project Structure

```
linkedin-easy-apply-agent/
│
├── easy_apply_agent.py          # LangGraph agent (form analysis + FillAction output)
├── run_easy_apply.py            # Entry point — Playwright orchestration loop
├── user_profile.py              # Profile loader (SQLite DB → json.dumps → LLM prompt)
│
├── data/
│   └── setup_linkedin_browser.py  # One-time LinkedIn login & session save
│
├── browser_data/                # Persistent Playwright session (gitignored)
│
├── profile_portal/
│   ├── backend/
│   │   ├── main.py              # Routes: profile, chat, apply start/stop/status
│   │   ├── chat_service.py      # LLM chat (memory buffer + Pydantic structured output)
│   │   ├── db.py                # SQLite helpers (profile CRUD + messages)
│   │   └── requirements.txt
│   └── frontend/
│       └── src/
│           ├── App.jsx                # Layout + ⚡ Auto Apply button
│           ├── components/
│           │   ├── ChatPanel.jsx      # AI chat (markdown rendering)
│           │   └── ProfilePanel.jsx   # Profile viewer + × delete custom keys
│           └── api/client.js          # fetch wrappers for all endpoints
│
├── requirements.txt             # Agent deps (playwright, langchain, langgraph, openai)
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
| Profile storage | SQLite → `json.dumps` directly into LLM prompt |
| Portal backend | FastAPI + uvicorn |
| Portal frontend | React + Vite |
| Chat memory | ConversationSummaryBuffer (auto-compresses old messages) |

---

> **Note:** The bot only applies to jobs with the blue **Easy Apply** button. Always test with a few applications manually before running at scale.
