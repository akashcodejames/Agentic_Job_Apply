"""
User profile configuration for LinkedIn Easy Apply agent.

Fixed fields are used directly for known form fields.
The `about_me` text gives the LLM context to answer ANY question.
"""

from __future__ import annotations   # fixes X | Y union syntax on Python 3.9

USER_PROFILE = {
    # Fixed fields (always needed)
    "email": "akashyadavazm8@gmail.com",
    "phone": "9140331096",
    "country_code": "India (+91)",
    "resume": "latest",  # Always pick the most recent resume

    # Free-text context — LLM uses this to answer any question
    "about_me": """
==================================================
APPLICANT MASTER PROFILE CONTEXT
==================================================

-------------------------
BASIC INFORMATION
-------------------------
Full Name: Akash Yadav
Phone: +91 9140331096
Email: akashyadavazm8@gmail.com
Location: Ghaziabad, Uttar Pradesh, India
Country: India
Nationality: Indian
Time Zone: IST (UTC+5:30)

LinkedIn:
https://www.linkedin.com/in/akash-yadav-46796a363/

GitHub:
https://github.com/akashcodejames

Portfolio:
https://akashcodejames.github.io/portfolio/

LeetCode:
https://leetcode.com/u/AkAsH_Ydv/

-------------------------
WORK AUTHORIZATION
-------------------------
Legally Authorized to Work in India: Yes
Require Visa Sponsorship: No
Open to Relocation: Yes (for strong opportunity)
Open to Remote Work: Yes
Open to Hybrid: Yes
Open to Onsite: Yes
Notice Period: Immediate
Currently Employed: No (Freelance)
Background Check Consent: Yes

-------------------------
HEALTH & DIVERSITY
-------------------------
Disability Status: No
Chronic Medical Condition: No
Require Workplace Accommodation: No
Gender: Male
Veteran Status: Not a veteran
Criminal Record: None

-------------------------
EDUCATION
-------------------------
Degree: Bachelor of Technology (B.Tech)
Field: Computer Science Engineering
College: NITRA Technical Campus, Ghaziabad
Graduation Year: 2025
CGPA: 7.0 / 10
Academic Status: Recent Graduate

-------------------------
EXPERIENCE SUMMARY
-------------------------
Experience Level: Entry-Level / Fresher
Total Professional Experience: 0–1 Year
Freelance Experience: Yes (Python Backend Development)
Industry Exposure: Backend Systems, AI Applications

-------------------------
TARGET ROLES
-------------------------
- Python Developer
- Backend Developer
- Software Developer
- AI Engineer (Entry Level)
- LLM / Generative AI Engineer (Junior)

-------------------------
CORE TECH STACK
-------------------------

Programming:
- Python (Strong)
- JavaScript (Basic–Intermediate)

Backend Frameworks:
- Flask (Advanced)
- FastAPI (Advanced)
- Django (Intermediate)

Databases:
- MySQL
- PostgreSQL
- Redis

DevOps & Deployment:
- Docker
- Docker Compose
- Kubernetes (Beginner)
- Nginx
- Gunicorn

Async & Task Processing:
- Celery
- Redis Queue
- AsyncIO
- aiosmtplib

AI / LLM Technologies:
- LangChain
- LangGraph
- RAG Systems
- ChromaDB (Vector Database)
- Prompt Engineering
- AI Agent Systems
- LLM Workflow Design

-------------------------
DETAILED PROJECT STACKS
-------------------------

1) College ERP System
Stack: Flask, MySQL, Redis, Docker, Nginx
Features:
- Student Management
- Attendance System
- Library Module
- Role-Based Access
- Email Notification System

2) RAG-based YouTube Chat AI
Stack: Python, LangChain, ChromaDB, OpenAI API
Features:
- Transcript Retrieval
- Context-Aware Q&A
- AI Response Generation

3) Stateful AI Chatbot
Stack: LangGraph, Persistent Memory Storage, Vector Embeddings
Features:
- Multi-session Memory
- Agent Workflow Management

4) Library Management System
Stack: Flask, MySQL, Celery, Redis, Async Email (aiosmtplib)
Features:
- Overdue Book Notifications
- Batch Email Processing
- Background Task Scheduling

5) LLM Automation Bot
Stack: Python, Browser Automation, LLM Decision Engine
Features:
- Dynamic Form Filling
- AI-based Decision Logic

-------------------------
TECHNICAL PROFICIENCY LEVEL
-------------------------
Python: Advanced (Hands-on project experience)
Backend Development: Advanced
SQL: Intermediate
Docker: Intermediate
Kubernetes: Beginner
AI / LLM Systems: Intermediate

-------------------------
SCREENING QUESTION DECISION RULES
-------------------------

Years of Python Experience:
→ 1 year (freelance + project-based)

Backend Experience:
→ 1 year project-based

Experience with AI/LLM:
→ Hands-on RAG, LangChain, Agent Systems

Experience with Docker:
→ Yes (hands-on)

Experience with Kubernetes:
→ Beginner level

Expected Salary:
→ Market Competitive / Negotiable

Immediate Joiner:
→ Yes

Willing to Relocate:
→ Yes

Willing to Work Night Shift:
→ Yes (if required)

Internet & Hardware:
→ Stable high-speed internet and personal development laptop available

-------------------------
CAREER OBJECTIVE (SHORT)
-------------------------
Entry-level backend and AI engineer focused on building scalable backend systems and LLM-powered applications using Python and modern AI frameworks.

==================================================
END PROFILE CONTEXT
==================================================
    """,
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


def get_profile_text() -> str:
    """
    Returns the user profile for the LLM system prompt.
    Reads from SQLite DB (live, edited via portal) — feeds JSON directly.
    Falls back to hardcoded USER_PROFILE if DB doesn't exist yet.
    """
    import json as _json
    p = _get_profile_from_db()
    if p:
        return _json.dumps(p, indent=2)   # structured JSON is sufficient for the LLM

    # Fallback: DB doesn't exist yet (portal never launched)
    print("[user_profile] DB not found — using hardcoded profile.")
    p = USER_PROFILE
    return _json.dumps({
        "name": "Akash Yadav",
        "email": p['email'],
        "phone": f"{p['country_code']} {p['phone']}",
        "about": p['about_me'].strip(),
        "resume": p['resume'],
    }, indent=2)
