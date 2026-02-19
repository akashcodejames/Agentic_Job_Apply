"""
User profile configuration for LinkedIn Easy Apply agent.

Fixed fields are used directly for known form fields.
The `about_me` text gives the LLM context to answer ANY question.
"""

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


def get_profile_text():
    """Format the user profile as a single text block for the LLM prompt."""
    p = USER_PROFILE
    return f"""Name: Akash Yadav
Email: {p['email']}
Phone: {p['country_code']} {p['phone']}
Resume preference: {p['resume']}

{p['about_me'].strip()}
"""
