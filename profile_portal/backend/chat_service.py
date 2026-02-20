"""
Chat service — LLM integration with:
  - ConversationSummaryBuffer memory (slides + compresses for unlimited history)
  - Pydantic structured output (LLM can't return garbage)
  - Profile update intent detection (LLM decides whether to update SQLite)
"""

import os
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

import db

# ---------------------------------------------------------------------------
# Pydantic schemas  (same pattern as FillAction in easy_apply_agent.py)
# ---------------------------------------------------------------------------

class ProfileUpdateItem(BaseModel):
    """
    One field update.  'key' can be ANY profile field — existing ones like
    'skills', 'expected_ctc', or brand-new ones like 'certifications', 'languages'.
    Using a LIST of these instead of a bare dict lets OpenAI express a fixed
    JSON Schema (no additionalProperties problem).
    """
    key: str = Field(
        description=(
            "Profile field name in snake_case. "
            "Existing: name, email, phone, location, about, skills, target_roles, "
            "expected_ctc, current_ctc, notice_period, experience_years, relocation, remote. "
            "New (create freely): certifications, languages, awards, hobbies, etc."
        )
    )
    value: Union[str, int, float, bool, List[str]] = Field(
        description=(
            "New value for the field. "
            "str  → text fields (name, about, location, notice_period). "
            "int/float → numbers (expected_ctc: 350000). "
            "bool → flags (relocation: true). "
            "List[str] → list fields (skills, certifications, target_roles)."
        )
    )


class ChatReply(BaseModel):
    response: str = Field(description="Conversational reply to user (markdown supported)")
    should_update: bool = Field(
        default=False,
        description="True ONLY when the user explicitly requests a profile change OR deletion"
    )
    updates: List[ProfileUpdateItem] = Field(
        default_factory=list,
        description=(
            "List of field updates. Empty list when should_update is False. "
            "Each item has a 'key' (field name) and 'value'. "
            "Use one item per field being changed."
        )
    )
    delete_keys: List[str] = Field(
        default_factory=list,
        description=(
            "List of profile field NAMES to delete entirely. "
            "Use when user says 'remove X', 'delete X field', 'clear X from my profile'. "
            "Only applies to custom/extra fields. Core fields should not be deleted."
        )
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a professional profile improvement assistant for a LinkedIn job application bot.

You help the user review and improve their professional profile stored in a database.
The profile is used by an AI agent to fill out LinkedIn Easy Apply forms automatically.

═══════════════════════════════════════════════════════
 CURRENT USER PROFILE
═══════════════════════════════════════════════════════
{profile_json}

═══════════════════════════════════════════════════════
 CONVERSATION CONTEXT
═══════════════════════════════════════════════════════
{conversation_context}

═══════════════════════════════════════════════════════
 YOUR ROLE
═══════════════════════════════════════════════════════
1. Answer questions about the user's profile clearly
2. Suggest improvements to make the profile more impactful
3. UPDATE the profile ONLY when the user explicitly requests a change

WHEN TO UPDATE (should_update = true):
  ✓ "update my skills"
  ✓ "change my expected CTC to 800000"
  ✓ "add TensorFlow to my skills"
  ✓ "my experience is actually 2 years"
  ✓ "add a certifications field with AWS Cloud Practitioner"  ← new custom key
  ✓ "remove certifications from my profile"  ← delete: set delete_keys=["certifications"]
  ✓ "delete my hobbies field"               ← delete: set delete_keys=["hobbies"]

WHEN NOT TO UPDATE (should_update = false):
  ✗ "what skills should I add?" → give advice, don't update
  ✗ "how do I improve my about section?" → give suggestions
  ✗ "is my profile good?" → provide feedback
  ✗ Any question, discussion, or hypothetical

RULES FOR THE 'updates' LIST:
  • For KNOWN fields (skills, about, target_roles, etc.) → add one item per field
  • For NEW custom fields (certifications, languages, awards, hobbies, etc.) →
    add an item with a new snake_case key — it will appear in the UI automatically.
    Example: key="certifications", value=["AWS Cloud Practitioner", "Docker Certified"]
  • For LIST fields (skills, target_roles, certifications, etc.) →
    always provide the COMPLETE updated list as a List[str], not just the new item.
  • Only include fields the user is explicitly changing — do not touch others.
  • Leave updates as an empty list when should_update is false.
"""


# ---------------------------------------------------------------------------
# Memory — ConversationSummaryBuffer
# ---------------------------------------------------------------------------

import json as _json

BUFFER_LIMIT = 10       # messages kept verbatim
COMPRESS_TRIGGER = 15   # when to compress (compress oldest 5 → summary)


def _build_context_string(session_id: str) -> str:
    """
    Build the conversation context string for the LLM.
    Uses: stored summary (older messages) + recent verbatim buffer.
    """
    summary = db.get_summary(session_id)
    recent = db.get_recent_messages(session_id, limit=BUFFER_LIMIT)

    parts = []
    if summary:
        parts.append(f"[Summary of earlier conversation]\n{summary}")
    if recent:
        parts.append("[Recent messages]")
        for msg in recent:
            label = "User" if msg["role"] == "user" else "Assistant"
            parts.append(f"{label}: {msg['content']}")

    return "\n\n".join(parts) if parts else "No previous conversation."


def _maybe_compress_memory(session_id: str, llm: ChatOpenAI):
    """
    If message count exceeds COMPRESS_TRIGGER, compress the oldest 5 messages
    into the running summary and delete them from the messages table.
    """
    count = db.get_message_count(session_id)
    print("*"*100)
    print(count,COMPRESS_TRIGGER)
    if count <= COMPRESS_TRIGGER:
        return

    # Get oldest 5 messages to compress
    import sqlite3
    with db.get_conn() as conn:
        rows = conn.execute(
            "SELECT id, role, content FROM messages WHERE session_id=? ORDER BY id LIMIT 5",
            (session_id,)
        ).fetchall()

    if not rows:
        return

    old_summary = db.get_summary(session_id)
    messages_text = "\n".join(
        f"{'User' if r['role']=='user' else 'Assistant'}: {r['content']}"
        for r in rows
    )

    compress_prompt = f"""Compress the following conversation into a concise factual summary.
Focus on: profile changes made, key facts learned about the user, important decisions.
Preserve any profile fields that were updated.

Existing summary:
{old_summary or '(none)'}

New messages to add:
{messages_text}

Return ONLY the updated summary, nothing else."""

    response = llm.invoke([HumanMessage(content=compress_prompt)])
    new_summary = response.content.strip()
    db.save_summary(session_id, new_summary)

    # Delete the compressed messages
    ids = [r["id"] for r in rows]
    with db.get_conn() as conn:
        conn.execute(
            f"DELETE FROM messages WHERE id IN ({','.join('?'*len(ids))})",
            ids
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Public chat function
# ---------------------------------------------------------------------------

def chat(session_id: str, user_message: str) -> dict:
    """
    Process a user message:
      1. Build context from memory
      2. Call LLM with structured output
      3. If should_update → update profile in SQLite
      4. Persist messages
      5. Maybe compress old messages → summary
      6. Return response + updated_profile flag
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    profile = db.get_profile()
    profile_json = _json.dumps(profile, indent=2)
    context = _build_context_string(session_id)

    system = SYSTEM_PROMPT.format(
        profile_json=profile_json,
        conversation_context=context,
    )

    # Same pattern as easy_apply_agent.py — List[ProfileUpdateItem] lets
    # with_structured_output() work because every field has a fixed type.
    structured_llm = llm.with_structured_output(ChatReply)
    reply: ChatReply = structured_llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=user_message),
    ])

    # Convert List[ProfileUpdateItem] → dict for db.update_profile()
    updates_dict = {item.key: item.value for item in reply.updates}

    # Update profile if LLM decided to
    updated_profile = None
    if reply.should_update and updates_dict:
        updated_profile = db.update_profile(updates_dict)

    # Delete keys the LLM decided to remove
    deleted_keys = []
    if reply.should_update and reply.delete_keys:
        for key in reply.delete_keys:
            db.delete_profile_key(key)
            deleted_keys.append(key)
        updated_profile = db.get_profile()  # re-read after deletions

    # Persist messages
    db.add_message(session_id, "user", user_message)
    db.add_message(session_id, "assistant", reply.response)

    # Compress memory if needed
    _maybe_compress_memory(session_id, llm)

    return {
        "response": reply.response,
        "profile_updated": reply.should_update and (bool(updates_dict) or bool(deleted_keys)),
        "updated_fields": list(updates_dict.keys()) if updates_dict else [],
        "deleted_fields": deleted_keys,
        "profile": updated_profile or profile,
    }
