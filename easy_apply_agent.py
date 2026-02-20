"""
LinkedIn Easy Apply Agent — LangGraph-based form filler.

Uses an LLM to analyze each Easy Apply form step and generate
JavaScript code to fill fields. Playwright executes the JS.
Navigation (Next/Review/Submit) is handled by Python logic
with LLM fallback.

Retry limits:
- Max 3 retries per form step
- Max 10 retries across entire application
- Graceful exit on unrecoverable errors
"""

import json
import os
from typing import Any, TypedDict, List
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from user_profile import get_profile_text

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

MAX_RETRIES_PER_STEP = 3
MAX_RETRIES_TOTAL = 10

BUTTON_SELECTORS = {
    "submit": 'button[aria-label="Submit application"]',
    "review": 'button[aria-label="Review your application"]',
    "next": 'button[data-easy-apply-next-button]',
}

SYSTEM_PROMPT = """You are a LinkedIn Easy Apply form-filling assistant.

YOUR TASK:
You receive the HTML of one step of a LinkedIn Easy Apply popup form.
You must return JavaScript code to fill every empty/unfilled field in that form.

═══════════════════════════════════════════
 CRITICAL RULES
═══════════════════════════════════════════

1. ONLY fill form fields. DO NOT click "Next", "Review", or "Submit" buttons.
   Navigation buttons are handled separately by the system.

2. If a field is already correctly filled, SKIP it. Do not overwrite.

3. After setting any input/textarea value, ALWAYS dispatch events.
   CRITICAL: Check if element exists before setting value!
     const el = document.querySelector('...');
     if (el) {
       el.value = "value";
       el.dispatchEvent(new Event('input', {bubbles: true}));
       el.dispatchEvent(new Event('change', {bubbles: true}));
     }

4. For radio buttons, click the LABEL (not the input):
     document.querySelector('label[for="radioId"]').click();

5. For checkboxes, only click if not already checked:
     if (!checkbox.checked) checkbox.click();

6. For <select> dropdowns:
     select.value = "optionValue";
     select.dispatchEvent(new Event('change', {bubbles: true}));

7. For LinkedIn's custom dropdowns (artdeco), click to open,
   then click the matching option text.

8. If you genuinely cannot determine the answer from the user profile,
   use the safest/most common option. Never leave a required field empty.

═══════════════════════════════════════════
 OUTPUT FORMAT (strict JSON)
═══════════════════════════════════════════

Return ONLY valid JSON. No markdown, no explanation, no extra text.
Do NOT wrap in ```json``` code fences.

{
  "actions": [
    {
      "type": "fill",
      "field_name": "Human-readable field name",
      "value": "The value being filled",
      "js": "(() => { /* JavaScript to fill this one field */ })()",
      "selector": ""
    }
  ]
}

For TYPEAHEAD fields use type: "typeahead" and provide the CSS selector instead of JS:
{
  "actions": [
    {
      "type": "typeahead",
      "field_name": "Location (city)",
      "value": "Ghaziabad, Uttar Pradesh, India",
      "js": "",
      "selector": "#ember123"
    }
  ]
}

If all fields are already filled correctly, return:
{"actions": []}

═══════════════════════════════════════════
 FIELD-FILLING EXAMPLES
═══════════════════════════════════════════

--- Text input ---
{
  "type": "fill",
  "field_name": "Years of experience",
  "value": "2",
  "js": "(() => { const el = document.querySelector('#ember123'); el.value = '2'; el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true})); })()"
}

--- Radio button (Yes/No) ---
{
  "type": "fill",
  "field_name": "Work authorization",
  "value": "Yes",
  "js": "(() => { document.querySelector('label[for=\\"radio-yes\\"]').click(); })()"
}

--- Select dropdown ---
{
  "type": "fill",
  "field_name": "Country code",
  "value": "India (+91)",
  "js": "(() => { const el = document.querySelector('#ember789'); el.value = 'IN'; el.dispatchEvent(new Event('change', {bubbles: true})); })()"
}

--- Resume selection (radio card, already selected) ---
Skip if the most recent resume is already selected.

--- Typeahead / Autocomplete fields (Location, City, etc.) ---
IMPORTANT: Some fields use a typeahead/autocomplete widget.
Signs of a typeahead field:
- Labels containing: city, location, address, country, region
- Input has autocomplete-related aria attributes
- Setting .value directly causes "Please enter a valid answer" errors

For these, use type: "typeahead" with the input's actual CSS selector:
{
  "type": "typeahead",
  "field_name": "Location (city)",
  "value": "Ghaziabad, Uttar Pradesh, India",
  "js": "",
  "selector": "#ember456"
}
Playwright will handle the typing and dropdown selection automatically.

═══════════════════════════════════════════
 USER PROFILE
═══════════════════════════════════════════

""" + get_profile_text()


# ──────────────────────────────────────────────
# State
# ──────────────────────────────────────────────

class EasyApplyState(TypedDict):
    page: Any                   # Playwright page object
    form_html: str              # Current modal step HTML
    actions: list               # LLM-returned fill actions
    errors: list                # Validation error messages
    step_retry_count: int       # Retries for current step (max 3)
    total_retry_count: int      # Total retries across all steps (max 10)
    status: str                 # NEXT_STEP / APPLIED / SKIPPED / ERROR
    job_title: str              # For logging



# ──────────────────────────────────────────────
# Pydantic Schema (Structured Output)
# ──────────────────────────────────────────────

class FillAction(BaseModel):
    """One field fill action with its JavaScript."""
    type: str = Field(description="Action type: 'fill' for regular JS injection, 'typeahead' for autocomplete/location fields")
    field_name: str = Field(description="Human-readable name of the form field")
    value: str = Field(description="The value to fill or search for")
    js: str = Field(default="", description="Executable JavaScript (IIFE) to fill this field. Leave empty for typeahead actions.")
    selector: str = Field(default="", description="CSS selector for the input element. Required for typeahead actions.")


class EasyApplyResponse(BaseModel):
    """Structured LLM response: list of fill actions for the current form step."""
    actions: List[FillAction] = Field(
        default_factory=list,
        description="List of fill actions. Empty list if all fields already filled."
    )


# ──────────────────────────────────────────────
# LLM
# ──────────────────────────────────────────────

def get_llm():
    """Create the LLM instance. Defaults to OpenAI (supports structured output)."""
    provider = os.environ.get("MODEL_PROVIDER", "openai").lower()

    if provider == "ollama":
        # NOTE: Ollama/DeepSeek doesn't reliably support .with_structured_output()
        model_name = os.environ.get("OLLAMA_MODEL", "deepseek-coder-v2")
        print(f"   🤖 Using Local Ollama Model: {model_name} (no structured output)")
        return ChatOllama(
            model=model_name,
            temperature=0,
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    # Default: OpenAI — supports structured output via function calling
    print(f"   🤖 Using OpenAI: gpt-4o-mini (structured output enabled)")
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.environ.get("OPENAI_API_KEY"),
    )


# ──────────────────────────────────────────────
# Node: OBSERVE — Extract modal HTML
# ──────────────────────────────────────────────

def observe_node(state: EasyApplyState) -> dict:
    """Extract the current Easy Apply modal form HTML."""
    page = state["page"]
    
    try:
        modal = page.locator("div.jobs-easy-apply-modal")
        if modal.count() == 0:
            print("   ❌ Modal not found!")
            return {"status": "ERROR", "form_html": ""}
        
        # Get the modal content HTML (form area only)
        form_html = modal.locator(".artdeco-modal__content").first.inner_html()
        
        # Also get the footer (for button context in error cases)
        footer_html = ""
        try:
            footer_html = modal.locator("footer").first.inner_html()
        except:
            pass
        
        full_html = form_html + "\n<!-- FOOTER -->\n" + footer_html
        
        print(f"   📄 Extracted form HTML ({len(full_html)} chars)")
        return {"form_html": full_html}
    
    except Exception as e:
        print(f"   ❌ Observe error: {e}")
        return {"status": "ERROR", "form_html": ""}


# ──────────────────────────────────────────────
# Node: FILL — LLM generates fill actions
# ──────────────────────────────────────────────

def fill_node(state: EasyApplyState) -> dict:
    """Send form HTML to LLM, get back fill actions as JSON."""
    form_html = state.get("form_html", "")
    errors = state.get("errors", [])
    
    if not form_html:
        return {"actions": [], "status": "ERROR"}
    
    llm = get_llm()
    
    # Build user message
    user_msg = "Here is the current Easy Apply form step HTML.\n"
    user_msg += "Analyze all fields and return fill actions for any empty/unfilled fields.\n\n"
    
    if errors:
        user_msg += "⚠️ PREVIOUS ATTEMPT HAD ERRORS:\n"
        for err in errors:
            user_msg += f"  - {err}\n"
        user_msg += "\nPlease fix the fields that caused these errors.\n\n"
    
    user_msg += f"FORM HTML:\n---\n{form_html}\n---"
    
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_msg),
    ]

    try:
        print("   🤖 Asking LLM to analyze form (Pydantic structured output)...")
        
        # Use structured output — OpenAI enforces schema via function calling
        structured_llm = llm.with_structured_output(EasyApplyResponse)
        response: EasyApplyResponse = structured_llm.invoke(messages)
        
        # Convert Pydantic objects to plain dicts for state storage
        actions = [a.model_dump() for a in response.actions]
        
        print(f"   🤖 LLM returned {len(actions)} fill action(s)")
        for a in actions:
            print(f"      → {a.get('field_name', '?')}: {a.get('value', '?')}")
        
        return {"actions": actions, "errors": []}
    
    except Exception as e:
        print(f"   ❌ LLM/Pydantic error: {e}")
        return {"actions": [], "status": "ERROR"}


# ──────────────────────────────────────────────
# TypeAhead Helper
# ──────────────────────────────────────────────

def handle_typeahead(page, selector: str, value: str) -> bool:
    """
    Fill a LinkedIn typeahead/autocomplete field using Playwright keyboard simulation.
    
    Flow:
      1. Click the field
      2. Clear any existing text
      3. Type the search term character by character (triggers dropdown)
      4. Wait for dropdown to appear
      5. Click the first matching option
    
    Returns True if successful, False if dropdown never appeared.
    """
    import time
    
    # Common LinkedIn typeahead dropdown selectors
    DROPDOWN_SELECTORS = [
        ".basic-typeahead__triggered-content li",
        "[data-test-autocomplete-filter] li",
        ".artdeco-typeahead__results-list li",
        "ul[role='listbox'] li",
        ".typeahead-results li",
    ]
    
    try:
        field = page.locator(selector).first
        
        if field.count() == 0:
            print(f"      ⚠️ TypeAhead: selector '{selector}' not found")
            return False
        
        # 1. Click to focus
        field.click()
        time.sleep(0.3)
        
        # 2. Clear existing text
        field.fill("")
        
        # 3. Use short search term (first 4-6 chars usually enough for dropdown)
        search_term = value.split(",")[0]  # e.g. "Ghaziabad" from full city string
        
        # Type character by character with human-like delays
        for char in search_term:
            field.type(char)
            time.sleep(0.08 + 0.04 * (len(search_term) % 3))  # ~80-120ms per key
        
        # 4. Wait for dropdown to appear
        page.wait_for_timeout(1800)
        
        # 5. Try each dropdown selector
        for dropdown_sel in DROPDOWN_SELECTORS:
            items = page.locator(dropdown_sel)
            if items.count() > 0:
                # Try to find the best match (contains the city name)
                city = search_term.lower()
                matched = False
                for idx in range(min(items.count(), 5)):
                    try:
                        item_text = items.nth(idx).inner_text().strip().lower()
                        if city in item_text:
                            items.nth(idx).click()
                            print(f"      ✅ TypeAhead: clicked '{item_text}'")
                            matched = True
                            break
                    except:
                        pass
                
                if not matched:
                    # Fallback: click the first option
                    items.first.click()
                    try:
                        print(f"      ✅ TypeAhead: clicked first option (fallback)")
                    except:
                        pass
                
                page.wait_for_timeout(500)
                return True
        
        # No dropdown found — try pressing Arrow Down + Enter as last resort
        print("      ⚠️ TypeAhead: no dropdown found, trying ArrowDown+Enter")
        field.press("ArrowDown")
        page.wait_for_timeout(500)
        field.press("Enter")
        page.wait_for_timeout(500)
        return False
    
    except Exception as e:
        print(f"      ❌ TypeAhead error: {e}")
        return False


# ──────────────────────────────────────────────
# Node: EXECUTE — Run fill actions via Playwright
# ──────────────────────────────────────────────

def execute_node(state: EasyApplyState) -> dict:
    """Execute each fill action's JavaScript via page.evaluate()."""
    page = state["page"]
    actions = state.get("actions", [])
    
    if not actions:
        print("   ℹ️  No actions to execute (all fields pre-filled)")
        return {}
    
    print(f"   ⚡ Executing {len(actions)} fill action(s)...")
    
    for i, action in enumerate(actions):
        field_name = action.get("field_name", f"Field {i+1}")
        value = action.get("value", "?")
        action_type = action.get("type", "fill")
        
        # ── TypeAhead field (Location, City, etc.) ──
        if action_type == "typeahead":
            selector = action.get("selector", "")
            if not selector:
                print(f"      ⚠️ {field_name}: typeahead action missing selector, skipping")
                continue
            print(f"      🔍 TypeAhead: {field_name} = {value}")
            handle_typeahead(page, selector, value)
            continue
        
        # ── Regular JS fill ──
        js_code = action.get("js", "")
        if not js_code:
            print(f"      ⏭️  {field_name}: No JS code, skipping")
            continue
        
        try:
            page.evaluate(js_code)
            print(f"      ✅ {field_name} = {value}")
            page.wait_for_timeout(500)  # Let UI update
        except Exception as e:
            print(f"      ❌ {field_name}: JS error — {e}")
    
    # Small extra wait for all fields to settle
    page.wait_for_timeout(1000)
    return {}


# ──────────────────────────────────────────────
# Node: VERIFY — Check for validation errors
# ──────────────────────────────────────────────

def verify_node(state: EasyApplyState) -> dict:
    """Check if any validation errors appeared after filling."""
    page = state["page"]
    step_retries = state.get("step_retry_count", 0)
    total_retries = state.get("total_retry_count", 0)
    
    # Check for validation error messages
    error_elements = page.locator("div.artdeco-inline-feedback--error")
    error_count = error_elements.count()
    
    if error_count > 0:
        errors = []
        for i in range(error_count):
            try:
                err_text = error_elements.nth(i).inner_text().strip()
                if err_text:
                    errors.append(err_text)
            except:
                pass
        
        if errors:
            print(f"   ⚠️  {len(errors)} validation error(s) found:")
            for err in errors:
                print(f"      - {err}")
            
            return {
                "errors": errors,
                "step_retry_count": step_retries + 1,
                "total_retry_count": total_retries + 1,
            }
    
    print("   ✅ No validation errors")
    return {"errors": []}


# ──────────────────────────────────────────────
# Node: NAVIGATE — Click Next / Review / Submit
# ──────────────────────────────────────────────

def navigate_node(state: EasyApplyState) -> dict:
    """Click the navigation button. Python first, LLM fallback."""
    page = state["page"]
    total_retries = state.get("total_retry_count", 0)
    
    # Priority: Submit > Review > Next
    for btn_name, selector in [
        ("Submit", BUTTON_SELECTORS["submit"]),
        ("Review", BUTTON_SELECTORS["review"]),
        ("Next", BUTTON_SELECTORS["next"]),
    ]:
        btn = page.locator(selector)
        if btn.count() > 0 and btn.first.is_visible():
            try:
                print(f"   🔘 Clicking '{btn_name}' button...")
                btn.first.click()
                page.wait_for_timeout(2000)
                
                if btn_name == "Submit":
                    return {"status": "SUBMIT_CLICKED"}
                else:
                    # Reset step retries on successful navigation
                    return {"status": "NEXT_STEP", "step_retry_count": 0}
                    
            except Exception as e:
                print(f"   ❌ Click failed for '{btn_name}': {e}")
    
    # Fallback: Ask LLM what to click
    print("   ⚠️  Standard buttons not found — asking LLM for fallback...")
    return _llm_navigate_fallback(page, total_retries)


def _llm_navigate_fallback(page, total_retries: int) -> dict:
    """LLM fallback for navigation when standard selectors fail."""
    try:
        modal = page.locator("div.jobs-easy-apply-modal")
        footer_html = modal.locator("footer").first.inner_html()
    except:
        print("   ❌ Cannot read modal footer for fallback")
        return {"status": "ERROR", "total_retry_count": total_retries + 1}
    
    llm = get_llm()
    
    fallback_prompt = f"""The standard navigation buttons were not found in the LinkedIn Easy Apply modal.
Here is the current modal footer HTML. Return ONLY a JavaScript one-liner to click 
the correct progression button (Next, Review, or Submit).

Return ONLY the JS code, no JSON, no explanation.

Footer HTML:
---
{footer_html}
---

Attempt: {total_retries + 1}/{MAX_RETRIES_TOTAL}"""
    
    messages = [
        SystemMessage(content="You help navigate LinkedIn Easy Apply forms. Return ONLY executable JavaScript."),
        HumanMessage(content=fallback_prompt),
    ]
    
    try:
        response = llm.invoke(messages)
        js_code = response.content.strip()
        
        # Clean up
        if js_code.startswith("```"):
            js_code = js_code.split("\n", 1)[1]
            if js_code.endswith("```"):
                js_code = js_code[:-3]
            js_code = js_code.strip()
        
        print(f"   🤖 LLM fallback JS: {js_code[:100]}...")
        page.evaluate(js_code)
        page.wait_for_timeout(2000)
        
        return {"status": "NEXT_STEP", "step_retry_count": 0,
                "total_retry_count": total_retries + 1}
    
    except Exception as e:
        print(f"   ❌ LLM navigate fallback failed: {e}")
        return {"status": "ERROR", "total_retry_count": total_retries + 1}


# ──────────────────────────────────────────────
# Node: POST_SUBMIT — Handle success popup
# ──────────────────────────────────────────────

def post_submit_node(state: EasyApplyState) -> dict:
    """Dismiss the success popup after application is submitted."""
    page = state["page"]
    job_title = state.get("job_title", "Unknown")
    
    print(f"   🎉 Application submitted for: {job_title}")
    
    page.wait_for_timeout(2000)
    page.keyboard.press("Escape")  # Dismiss success popup
    page.wait_for_timeout(1000)
    
    print(f"   ✅ Success popup dismissed")
    return {"status": "APPLIED"}


# ──────────────────────────────────────────────
# Routing functions
# ──────────────────────────────────────────────

def route_after_observe(state: EasyApplyState) -> str:
    """Route after OBSERVE: go to FILL or end on error."""
    if state.get("status") == "ERROR":
        return "end"
    return "fill"


def route_after_verify(state: EasyApplyState) -> str:
    """Route after VERIFY: retry FILL if errors, else NAVIGATE."""
    errors = state.get("errors", [])
    step_retries = state.get("step_retry_count", 0)
    total_retries = state.get("total_retry_count", 0)
    
    if errors:
        if step_retries >= MAX_RETRIES_PER_STEP:
            print(f"   ❌ Max step retries ({MAX_RETRIES_PER_STEP}) reached — skipping")
            return "end"
        if total_retries >= MAX_RETRIES_TOTAL:
            print(f"   ❌ Max total retries ({MAX_RETRIES_TOTAL}) reached — skipping")
            return "end"
        print(f"   🔄 Retrying fill (step attempt {step_retries + 1}/{MAX_RETRIES_PER_STEP})")
        return "fill"
    
    return "navigate"


def route_after_navigate(state: EasyApplyState) -> str:
    """Route after NAVIGATE: loop, submit, or end."""
    status = state.get("status", "")
    total_retries = state.get("total_retry_count", 0)
    
    if status == "SUBMIT_CLICKED":
        return "post_submit"
    
    if status == "NEXT_STEP":
        return "observe"
    
    if total_retries >= MAX_RETRIES_TOTAL:
        print(f"   ❌ Max total retries ({MAX_RETRIES_TOTAL}) — giving up")
        return "end"
    
    # ERROR: try once more
    return "observe"


# ──────────────────────────────────────────────
# Build the LangGraph
# ──────────────────────────────────────────────

def build_easy_apply_graph():
    """Build and compile the LangGraph state graph."""
    
    graph = StateGraph(EasyApplyState)
    
    # Add nodes
    graph.add_node("observe", observe_node)
    graph.add_node("fill", fill_node)
    graph.add_node("execute", execute_node)
    graph.add_node("verify", verify_node)
    graph.add_node("navigate", navigate_node)
    graph.add_node("post_submit", post_submit_node)
    
    # Set entry point
    graph.set_entry_point("observe")
    
    # Add edges
    graph.add_conditional_edges("observe", route_after_observe, {
        "fill": "fill",
        "end": END,
    })
    graph.add_edge("fill", "execute")
    graph.add_edge("execute", "verify")
    graph.add_conditional_edges("verify", route_after_verify, {
        "fill": "fill",
        "navigate": "navigate",
        "end": END,
    })
    graph.add_conditional_edges("navigate", route_after_navigate, {
        "observe": "observe",
        "post_submit": "post_submit",
        "end": END,
    })
    graph.add_edge("post_submit", END)
    
    return graph.compile()


# ──────────────────────────────────────────────
# Graceful Modal Dismiss
# ──────────────────────────────────────────────

DISCARD_BTN   = 'button[data-control-name="discard_application_confirm_btn"]'
SAVE_DIALOG   = 'div[data-test-modal][role="alertdialog"]'

def dismiss_modal_gracefully(page):
    """
    Close the Easy Apply modal *and* handle the 'Save this application?' dialog.
    
    LinkedIn shows an alertdialog with Save/Discard when the modal is
    closed while a form is partially filled.  A bare Escape just opens
    that dialog and leaves it blocking the entire UI.

    This function:
      1. If the Save dialog is already open  → click Discard immediately.
      2. Otherwise, press Escape (may or may not trigger the dialog).
      3. Wait briefly, then check again → click Discard if dialog appeared.
      4. Final safety pass — dismiss the dialog selector one more time.
    """
    def _click_discard():
        btn = page.locator(DISCARD_BTN)
        if btn.count() > 0:
            try:
                if btn.first.is_visible():
                    btn.first.click()
                    print("   🗑️  Save dialog — clicked Discard")
                    page.wait_for_timeout(800)
                    return True
            except Exception:
                pass
        return False

    try:
        # Step 1: dialog already open?
        if page.locator(SAVE_DIALOG).count() > 0:
            _click_discard()
            return

        # Step 2: press Escape to close modal (may trigger dialog)
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)

        # Step 3: dialog appeared after Escape?
        _click_discard()

        # Step 4: final safety — press Escape one more time if anything left
        if page.locator(SAVE_DIALOG).count() > 0 or \
           page.locator("div.jobs-easy-apply-modal").count() > 0:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
            _click_discard()

    except Exception as e:
        print(f"   ⚠️ dismiss_modal error (non-critical): {e}")


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def run_easy_apply(page, job_title: str = "Unknown") -> str:
    """
    Run the Easy Apply agent on the currently open modal.
    
    Args:
        page: Playwright page with Easy Apply modal open
        job_title: Job title for logging
        
    Returns:
        "APPLIED" | "SKIPPED" | "ERROR"
    """
    print(f"\n   🤖 Starting Easy Apply agent for: {job_title}")
    print("   " + "-" * 50)
    
    graph = build_easy_apply_graph()
    
    initial_state: EasyApplyState = {
        "page": page,
        "form_html": "",
        "actions": [],
        "errors": [],
        "step_retry_count": 0,
        "total_retry_count": 0,
        "status": "",
        "job_title": job_title,
    }
    
    try:
        final_state = graph.invoke(initial_state, {"recursion_limit": 150})
        status = final_state.get("status", "ERROR")
        
        if status == "APPLIED":
            print(f"   ✅ Successfully applied to: {job_title}")
        else:
            print(f"   ⚠️  Finished with status: {status}")
            # Gracefully close modal and handle Save/Discard dialog
            dismiss_modal_gracefully(page)
            status = "SKIPPED"
        
        return status
        
    except Exception as e:
        print(f"   ❌ Agent error: {e}")
        # Gracefully close modal and handle Save/Discard dialog
        dismiss_modal_gracefully(page)
        return "ERROR"
