# LinkedIn Easy Apply Agent 🤖

An intelligent, autonomous agent that applies to LinkedIn jobs for you using **LangGraph**, **Playwright**, and **LLMs** (OpenAI or Local).

## 🌟 Features

- **Agentic Workflow**: Uses a state machine (LangGraph) to Observe → Think → Act → Verify.
- **Smart Form Filling**: Uses an LLM to understand questions and fill fields based on your profile.
- **Resilient**: Handles retries, validation errors, and unexpected popups.
- **Local Model Support**: Run completely free/private using Ollama (Qwen 2.5 Coder).
- **Safe**: Human-like navigation (Python-driven) to avoid bans.

## 🚀 Quick Start

### 1. Setup

```bash
# Clone rep
git clone https://github.com/your-username/linkedin-easy-apply-agent.git
cd linkedin-easy-apply-agent

# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure

1.  **Edit `user_profile.py`**: Add your details (Experience, Education, etc.) so the LLM knows how to answer.
2.  **Set API Key** in `.env`:
    ```ini
    OPENAI_API_KEY=sk-proj-...
    # Or requesting local model:
    # MODEL_PROVIDER=ollama
    # OLLAMA_MODEL=qwen2.5-coder:7b
    ```

### 3. Login (Once)

Run the login script to save your session cookies:

```bash
python setup_linkedin_browser.py
```
*Login manually in the browser window that opens, then close it.*

### 4. Run

```bash
python run_easy_apply.py
```

## 🧠 Architecture

The agent follows this loop for every job:

1.  **OBSERVE**: Scrapes the current form Step HTML.
2.  **FILL**: LLM decides what to fill based on your `user_profile.py`.
3.  **EXECUTE**: Playwright runs the JS to fill fields.
4.  **VERIFY**: Checks for validation errors.
    *   *If error*: Retry FILL with error context.
    *   *If clean*: Proceed.
5.  **NAVIGATE**: Clicks Next/Review/Submit.

## 📁 Project Structure

| File | Purpose |
|------|---------|
| `run_easy_apply.py` | Main entry point. Scrolls jobs, filters Easy Apply, starts agent. |
| `easy_apply_agent.py` | The Brain. LangGraph agent logic (Nodes & Edges). |
| `user_profile.py` | Configuration. Your "Resume" for the bot. |
| `setup_linkedin_browser.py` | Utility to login and save session. |

## ⚠️ Safety & Disclaimer

This tool is for educational purposes. Use responsibily.
- The bot uses **Playwright** with a real browser (not headless by default) to mimic human behavior.
- We recommend running it in short bursts (e.g., 20 jobs/day) to avoid LinkedIn flags.
