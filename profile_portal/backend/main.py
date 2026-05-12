"""
FastAPI backend for Profile Portal.

Endpoints:
  GET  /api/profile           - Fetch current profile from SQLite
  PUT  /api/profile           - Directly update profile fields
  POST /api/chat              - Send a message, get LLM reply
  GET  /api/chat/history      - Get full conversation history
  DELETE /api/chat/history    - Clear conversation history
  POST /api/apply/start       - Launch run_easy_apply.py subprocess
  GET  /api/apply/status      - Check if apply bot is running
  POST /api/apply/stop        - Stop the apply bot
"""

from __future__ import annotations   # fixes X | Y union syntax on Python 3.9

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import os

from pathlib import Path
_ENV_PATH = Path(__file__).parent.parent.parent / ".env"  # elarning_Autoamtion/.env
load_dotenv(dotenv_path=_ENV_PATH)

import db
import chat_service

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Profile Portal API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup():
    db.init_db()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ProfileUpdate(BaseModel):
    updates: dict


# ---------------------------------------------------------------------------
# Profile endpoints
# ---------------------------------------------------------------------------

@app.get("/api/profile")
def get_profile():
    profile = db.get_profile()
    return {
        "profile": profile,
        "updated_at": db.get_profile_updated_at(),
    }

@app.put("/api/profile")
def update_profile(body: ProfileUpdate):
    if not body.updates:
        raise HTTPException(400, "No updates provided")
    updated = db.update_profile(body.updates)
    return {"profile": updated, "updated_at": db.get_profile_updated_at()}

@app.delete("/api/profile/key/{key_name}")
def delete_profile_key(key_name: str):
    """Delete a single key from the profile (for LLM-created custom fields)."""
    updated = db.delete_profile_key(key_name)
    return {"profile": updated, "updated_at": db.get_profile_updated_at()}


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def send_message(body: ChatRequest):
    if not body.message.strip():
        raise HTTPException(400, "Message cannot be empty")
    if not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(500, "OPENAI_API_KEY not configured")
    try:
        result = chat_service.chat(body.session_id, body.message)
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()  # prints full traceback to server terminal
        raise HTTPException(500, f"Chat error: {type(e).__name__}: {e}")


@app.get("/api/chat/history")
def get_history(session_id: str = "default"):
    messages = db.get_all_messages_for_display(session_id)
    summary = db.get_summary(session_id)
    return {"messages": messages, "summary": summary}


@app.delete("/api/chat/history")
def clear_history(session_id: str = "default"):
    db.clear_messages(session_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Auto Apply endpoints  (launches run_easy_apply.py as a subprocess)
# ---------------------------------------------------------------------------

import subprocess
import signal
import sys
from datetime import datetime, timezone

# Module-level process state
_apply_proc: subprocess.Popen | None = None
_apply_started_at: str | None = None

# Project root — two levels up from this file (profile_portal/backend → root)
_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _get_apply_status() -> dict:
    global _apply_proc
    if _apply_proc is None:
        return {"status": "idle", "pid": None, "started_at": None}
    ret = _apply_proc.poll()         # None → still running
    if ret is None:
        return {"status": "running", "pid": _apply_proc.pid, "started_at": _apply_started_at}
    _apply_proc = None               # process finished — clean up
    return {"status": "idle", "pid": None, "started_at": None}


def _find_agent_python() -> str:
    """
    Find the Python executable that has playwright / langchain installed.
    Priority: root-level venv → system python3 → sys.executable (portal venv).
    """
    import shutil
    # Check for a virtualenv at the project root (common for the agent code)
    for venv_name in ('ven', 'venv', '.venv', 'env', '.env'):
        candidate = _PROJECT_ROOT / venv_name / 'bin' / 'python'
        if candidate.exists():
            return str(candidate)
    # System python3
    system = shutil.which('python3') or shutil.which('python')
    if system:
        return system
    return sys.executable   # last resort (portal venv — may not have all deps)


@app.post("/api/apply/start")
def start_apply():
    global _apply_proc, _apply_started_at
    state = _get_apply_status()
    if state["status"] == "running":
        return {"ok": False, "message": "Already running", **state}

    script = _PROJECT_ROOT / "run_easy_apply.py"
    if not script.exists():
        raise HTTPException(404, f"run_easy_apply.py not found at {script}")

    python_exe = _find_agent_python()

    _apply_proc = subprocess.Popen(
        [python_exe, str(script)],
        cwd=str(_PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _apply_started_at = datetime.now(timezone.utc).isoformat()

    # Wait 1 s to detect immediate crashes (import errors, missing deps, etc.)
    import time
    time.sleep(1)
    if _apply_proc.poll() is not None:
        error_output = _apply_proc.stdout.read()   # read ALL output, no limit
        _apply_proc = None
        # Print full traceback to the uvicorn terminal so you can see it there too
        print("\n" + "="*60)
        print("AGENT CRASHED -- full output:")
        print("="*60)
        print(error_output)
        print("="*60 + "\n")
        raise HTTPException(500,
            f"Agent crashed on startup (Python: {python_exe}):\n{error_output}"
        )

    return {
        "ok": True,
        "message": f"Auto apply started (Python: {python_exe})",
        "pid": _apply_proc.pid,
        "started_at": _apply_started_at,
        "status": "running",
    }


@app.get("/api/apply/status")
def apply_status():
    return _get_apply_status()


@app.post("/api/apply/stop")
def stop_apply():
    global _apply_proc
    state = _get_apply_status()
    if state["status"] != "running":
        return {"ok": False, "message": "Not running", "status": "idle"}
    try:
        _apply_proc.send_signal(signal.SIGINT)   # graceful Ctrl+C
        _apply_proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _apply_proc.kill()
    _apply_proc = None
    return {"ok": True, "message": "Auto apply stopped", "status": "idle"}
