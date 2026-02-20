# 🤖 LinkedIn Easy Apply Automation Agent

An intelligent, end-to-end job application bot that automatically fills and submits LinkedIn Easy Apply forms — powered by **LangGraph**, **OpenAI GPT-4o-mini**, and **Playwright**.

Includes a **Profile Intelligence Portal** (React + FastAPI) where you manage your profile via AI chat and trigger the apply bot directly from the browser.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Profile Intelligence Portal                   │
│                                                                 │
│  ┌──────────────────┐          ┌───────────────────────────┐   │
│  │  React Frontend  │◄────────►│   FastAPI Backend (8000)  │   │
│  │   (Vite :5173)   │  REST    │                           │   │
│  │                  │          │  • GET/PUT /api/profile    │   │
│  │  • ProfilePanel  │          │  • POST    /api/chat       │   │
│  │  • ChatPanel     │          │  • POST    /api/apply/start│   │
│  │  • Auto Apply Btn│          │  • GET     /api/apply/status│  │
│  └──────────────────┘          │  • POST    /api/apply/stop │   │
│                                └──────────┬────────────────┘   │
│                                           │                     │
│                                    ┌──────▼──────┐              │
│                                    │  SQLite DB  │              │
│                                    │ (profile +  │              │
│                                    │  messages)  │              │
│                                    └─────────────┘              │
└───────────────────────────────┬─────────────────────────────────┘
                                │ subprocess
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Easy Apply Agent                            │
│                                                                 │
│   run_easy_apply.py                                             │
│        │                                                        │
│        ▼                                                        │
│   ┌────────────┐    reads     ┌─────────────────────────────┐  │
│   │ LangGraph  │◄────────────►│  user_profile.py            │  │
│   │  Agent     │   profile    │  (reads SQLite DB → JSON)   │  │
│   └─────┬──────┘              └─────────────────────────────┘  │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              easy_apply_agent.py  (LangGraph)           │  │
│   │                                                         │  │
│   │  ┌───────────┐    ┌──────────────┐    ┌─────────────┐  │  │
│   │  │  extract  │───►│    fill      │───►│  navigate   │  │  │
│   │  │  form_html│    │  (GPT-4o-mini│    │  next/submit│  │  │
│   │  └───────────┘    │  + Pydantic) │    └─────────────┘  │  │
│   │                   └──────────────┘                     │  │
│   └──────────────────────────┬──────────────────────────────┘  │
│                              │ JS execution                     │
│                              ▼                                  │
│                   ┌──────────────────┐                         │
│                   │  Playwright      │                         │
│                   │  (Chromium)      │◄── browser_data/        │
│                   │  LinkedIn.com    │    (persistent session)  │
│                   └──────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
linkedin-easy-apply-agent/
│
├── easy_apply_agent.py          # LangGraph agent — form analysis + JS fill actions
├── run_easy_apply.py            # Entry point — Playwright orchestration loop
├── user_profile.py              # Profile loader (reads from SQLite DB or fallback)
│
├── data/
│   └── setup_linkedin_browser.py  # One-time LinkedIn login & session save
│
├── browser_data/                # Persistent Playwright session (gitignored)
│
├── profile_portal/              # Web UI to manage profile + trigger apply
│   ├── backend/                 # FastAPI app
│   │   ├── main.py              # API routes (profile, chat, apply control)
│   │   ├── chat_service.py      # LLM chat logic (LangGraph memory + Pydantic)
│   │   ├── db.py                # SQLite helpers
│   │   └── requirements.txt
│   └── frontend/                # React + Vite
│       └── src/
│           ├── App.jsx           # Layout + Auto Apply button
│           ├── components/
│           │   ├── ChatPanel.jsx      # AI chat interface
│           │   └── ProfilePanel.jsx   # Profile viewer + delete custom keys
│           └── api/client.js         # All API calls
│
├── requirements.txt             # Agent dependencies (playwright, langchain, etc.)
├── .env                         # API keys (gitignored)
└── .gitignore
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/akashcodejames/linkedin-easy-apply-agent
cd linkedin-easy-apply-agent

# Agent dependencies (Playwright, LangChain, etc.)
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

This opens a Chromium window — log in manually. The session is saved to `browser_data/` so you never log in again.

### 4. Start the Profile Portal

```bash
# Terminal 1 — Backend
cd profile_portal/backend
source venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd profile_portal/frontend
npm install && npm run dev
```

Open **http://localhost:5173** — use the AI chat to review and update your profile.

### 5. Run the Apply Bot

**Option A — From the Portal UI:**
Click **⚡ Start Auto Apply** in the header.

**Option B — From the terminal:**
```bash
python run_easy_apply.py
```

---

## How It Works

### Profile Portal (AI Chat)
- Chat with an LLM to update your profile: *"change my expected salary to 8 LPA"*, *"add AWS certifications"*
- Profile is stored in SQLite and **automatically used** by the apply bot on next run
- Custom fields (certifications, languages, etc.) are created dynamically and shown in the UI

### Easy Apply Agent (LangGraph)
Each application runs through a state machine:

```
extract_form_html → analyze_with_llm → execute_js → navigate_next → [repeat or submit]
```

1. **Extract**: Playwright reads the current Easy Apply modal HTML
2. **Analyze**: GPT-4o-mini returns structured `List[FillAction]` (field, value, JS)
3. **Execute**: Playwright runs the JS to fill each field
4. **Navigate**: Python clicks Next/Review/Submit based on button detection
5. **Retry**: Up to 3 retries per step, 10 total before graceful exit

### Pydantic Structured Output
Uses `with_structured_output(FillAction)` — the LLM returns a typed list of actions, not free text. This makes form filling deterministic and debuggable.

---

## Key Tech

| Layer | Tech |
|---|---|
| Browser automation | Playwright (Chromium, persistent session) |
| Agent orchestration | LangGraph state machine |
| LLM | OpenAI GPT-4o-mini |
| Structured output | Pydantic + `with_structured_output()` |
| Profile storage | SQLite (via FastAPI backend) |
| Portal backend | FastAPI + uvicorn |
| Portal frontend | React + Vite |

---

## Notes

- The agent **only applies to Easy Apply jobs** (blue button on LinkedIn)
- Always test with a few applications manually before running at scale
- `browser_data/` is gitignored — protect your LinkedIn session
