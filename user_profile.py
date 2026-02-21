"""
User profile configuration for LinkedIn Easy Apply agent.

HOW IT WORKS:
  1. If the Profile Portal has been started and a profile exists in the SQLite DB,
     the agent fetches the live JSON from there automatically.
  2. If the DB does not yet exist (first run without portal), it falls back to
     EXAMPLE_PROFILE below — edit it with your own details.

TIP: The easiest way to set up your profile is to run the Profile Portal
     and chat with the AI: "my expected CTC is 8 LPA, I know Python and AWS..."
"""

from __future__ import annotations   # fixes X | Y union syntax on Python 3.9

# ──────────────────────────────────────────────────────────────────────────────
# EXAMPLE_PROFILE — fallback used when the SQLite DB is not yet available.
# If you are cloning this repo, replace these values with your own details.
# All fields are optional — add or remove keys freely.
# ──────────────────────────────────────────────────────────────────────────────
EXAMPLE_PROFILE = {
    # ── Basic info ────────────────────────────────────────────────────────────
    "name":           "Jane Doe",                       # ← your full name
    "email":          "jane.doe@example.com",           # ← your email
    "phone":          "+91 9000000000",                 # ← your phone
    "location":       "Bengaluru, Karnataka, India",    # ← your city
    "linkedin":       "https://linkedin.com/in/janedoe",
    "github":         "https://github.com/janedoe",
    "portfolio":      "https://janedoe.dev",

    # ── Professional summary ──────────────────────────────────────────────────
    "about": (
        "Full-stack developer with 3 years of experience building scalable "
        "web applications. Proficient in Python, React, and cloud infrastructure. "
        "Passionate about clean code and developer tooling."
    ),

    # ── Education ─────────────────────────────────────────────────────────────
    "education": "B.Tech Computer Science, XYZ University (2021)",

    # ── Experience ────────────────────────────────────────────────────────────
    "experience_years":  3,
    "experience_months": 6,

    # ── Job preferences ───────────────────────────────────────────────────────
    "target_roles":       ["Software Engineer", "Backend Developer", "Full Stack Developer"],
    "notice_period":      "30 days",
    "current_ctc":        600000,    # annual, in INR
    "expected_ctc":       900000,    # annual, in INR
    "work_authorization": "Authorized to work in India",
    "relocation":         True,
    "remote":             True,

    # ── Skills ────────────────────────────────────────────────────────────────
    "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "AWS"],

    # ── Projects (optional) ────────────────────────────────────────────────────
    "projects": [
        {
            "name":        "Portfolio Site",
            "stack":       "Next.js, TailwindCSS, Vercel",
            "description": "Personal portfolio with blog and project showcase.",
        },
    ],
}

def _get_profile_from_db() -> dict | None:
    """
    Read the latest profile from the profile_portal SQLite DB.
    Returns None if the DB doesn't exist yet (first run before portal is launched).
    """
    try:
        from pathlib import Path
        import sqlite3, json as _json
        db_path = Path(__file__).parent / "profile_portal" / "backend" / "profile_portal.db"
        if not db_path.exists():
            return None
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT data FROM profile WHERE id=1").fetchone()
        conn.close()
        if row:
            return _json.loads(row["data"])
    except Exception as e:
        print(f"[user_profile] Warning: could not read DB profile: {e}")
    return None


# Module-level cache — populated once on first call, reused forever after.
_profile_cache: str | None = None


def get_profile_text() -> str:
    """
    Returns the user profile as a JSON string for the LLM system prompt.

    Fetched only ONCE per process run (cached in _profile_cache).
    Priority:
      1. Live profile from SQLite DB (set up via the Profile Portal chat).
      2. EXAMPLE_PROFILE fallback — edit it in this file with your own details.
    """
    global _profile_cache
    import json as _json

    if _profile_cache is not None:
        return _profile_cache  # already fetched this run — skip DB/file read

    p = _get_profile_from_db()
    if p:
        print("[user_profile] ✓ Profile loaded from SQLite DB (cached for this run).")
        _profile_cache = _json.dumps(p, indent=2)
    else:
        print("[user_profile] DB not found — using EXAMPLE_PROFILE fallback (cached for this run). "
              "Run the Profile Portal and update your details via chat for best results.")
        _profile_cache = _json.dumps(EXAMPLE_PROFILE, indent=2)

    return _profile_cache

