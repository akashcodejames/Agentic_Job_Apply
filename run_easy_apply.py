"""
LinkedIn Easy Apply Runner — Main orchestrator.

This script:
1. Opens LinkedIn jobs search with persistent login
2. Scrolls to load all jobs
3. Iterates through each job
4. Checks for Easy Apply vs external redirect
5. Calls the LangGraph agent to fill and submit each application
6. Logs results and handles errors gracefully

Usage:
    export GOOGLE_API_KEY="your-gemini-api-key"
    python run_easy_apply.py
"""

from playwright.sync_api import sync_playwright
import os
import sys
import random
import time

from dotenv import load_dotenv
load_dotenv()
from datetime import datetime

from easy_apply_agent import run_easy_apply


# ──────────────────────────────────────────────
# Scrolling helpers (from test_job_selector.py)
# ──────────────────────────────────────────────

def scroll_container_to_bottom(page):
    """Scroll the job list's scrollable container to the bottom."""
    page.evaluate("""
        (() => {
            const jobCards = document.querySelectorAll('.job-card-container');
            if (jobCards.length === 0) return;
            let el = jobCards[0];
            while (el && el !== document.body) {
                el = el.parentElement;
                if (!el) break;
                const style = window.getComputedStyle(el);
                if (el.scrollHeight > el.clientHeight && 
                    (style.overflowY === 'auto' || style.overflowY === 'scroll')) {
                    el.scrollTop = el.scrollHeight;
                    return;
                }
            }
            window.scrollBy(0, 800);
        })()
    """)


def get_total_list_items(page):
    """Get total job list items (handles LinkedIn's occlusion/virtual scrolling)."""
    return page.evaluate("""
        (() => {
            const jobCards = document.querySelectorAll('.job-card-container');
            if (jobCards.length === 0) return 0;
            let el = jobCards[0];
            while (el && el !== document.body) {
                el = el.parentElement;
                if (!el) break;
                if (el.tagName === 'UL') {
                    return el.children.length;
                }
            }
            return jobCards.length;
        })()
    """)


def scroll_list_item_into_view(page, index):
    """Scroll a specific list item into view by index to hydrate it."""
    page.evaluate(f"""
        (() => {{
            const jobCards = document.querySelectorAll('.job-card-container');
            if (jobCards.length === 0) return;
            let el = jobCards[0];
            while (el && el !== document.body) {{
                el = el.parentElement;
                if (!el) break;
                if (el.tagName === 'UL') {{
                    const item = el.children[{index}];
                    if (item) item.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                    return;
                }}
            }}
        }})()
    """)


def get_job_card_at_index(page, index):
    """Get job card data-job-id at a specific list index after scrolling into view."""
    return page.evaluate(f"""
        (() => {{
            const jobCards = document.querySelectorAll('.job-card-container');
            if (jobCards.length === 0) return null;
            let el = jobCards[0];
            while (el && el !== document.body) {{
                el = el.parentElement;
                if (!el) break;
                if (el.tagName === 'UL') {{
                    const item = el.children[{index}];
                    if (!item) return null;
                    const card = item.querySelector('.job-card-container');
                    if (card) return card.getAttribute('data-job-id');
                    return null;
                }}
            }}
            return null;
        }})()
    """)

# ──────────────────────────────────────────────
# Anti-Detection Utilities
# ──────────────────────────────────────────────

def human_delay(min_ms: int = 800, max_ms: int = 2500):
    """Wait a random human-like amount of time."""
    delay = random.randint(min_ms, max_ms)
    time.sleep(delay / 1000)


def jitter_mouse(page, intensity: int = 3):
    """
    Move mouse in small random increments to mimic natural human movement.
    intensity: number of micro-moves to make.
    """
    try:
        viewport = page.viewport_size
        if not viewport:
            return
        w, h = viewport["width"], viewport["height"]
        # Start near center to avoid edge issues
        x = random.randint(w // 4, 3 * w // 4)
        y = random.randint(h // 4, 3 * h // 4)
        for _ in range(intensity):
            x += random.randint(-30, 30)
            y += random.randint(-20, 20)
            x = max(10, min(x, w - 10))
            y = max(10, min(y, h - 10))
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.05, 0.15))
    except Exception:
        pass  # Never crash the main loop for a mouse jitter


def human_scroll(page, direction: str = "down", steps: int = 3):
    """Scroll in small increments with random pauses, like a human."""
    for _ in range(steps):
        delta = random.randint(100, 350) * (1 if direction == "down" else -1)
        page.mouse.wheel(0, delta)
        time.sleep(random.uniform(0.2, 0.6))


def between_job_cooldown():
    """Randomized cooldown between job applications (3–12 seconds)."""
    cooldown = random.uniform(3, 12)
    print(f"   🕒 Anti-detection cooldown: {cooldown:.1f}s")
    time.sleep(cooldown)


# ──────────────────────────────────────────────
# Main runner
# ──────────────────────────────────────────────

def main():
    # Check for API key (only required if OpenAI mode)
    if os.environ.get("MODEL_PROVIDER", "ollama").lower() == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("   Run: export OPENAI_API_KEY='your-key-here'")
        sys.exit(1)
    
    user_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
    
    if not os.path.exists(user_data_dir):
        print("⚠️  Browser profile not found!")
        print("   Run 'python setup_linkedin_browser.py' first to login")
        sys.exit(1)
    
    # Results tracking
    results = {"applied": [], "skipped": [], "failed": []}
    
    print("🚀 LinkedIn Easy Apply Bot")
    print("=" * 60)
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 720},
            # Anti-fingerprinting: make the browser look more human
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )
        
        page = context.new_page()
        initial_page_count = len(context.pages)
        
        # Navigate to LinkedIn jobs search
        url = "https://www.linkedin.com/jobs/search/?keywords=python%20developer&location=India&f_TPR=r86400&f_AL=true"
        print(f"\n📍 Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        
        print("⏳ Waiting for page to load...")
        page.wait_for_timeout(5000)
        
        # --- Scroll to load all jobs ---
        print("\n📜 Scrolling to load all jobs...")
        print("-" * 60)
        
        previous_total = 0
        stable_rounds = 0
        
        while stable_rounds < 3:
            current_total = get_total_list_items(page)
            visible = page.locator(".job-card-container").count()
            print(f"   Total items: {current_total} (visible: {visible})")
            
            if current_total == previous_total:
                stable_rounds += 1
            else:
                stable_rounds = 0
            
            previous_total = current_total
            scroll_container_to_bottom(page)
            page.wait_for_timeout(2000)
        
        total_jobs = previous_total
        print(f"   ✅ All jobs loaded! Total: {total_jobs}")
        print("-" * 60)
        
        # --- Process each job ---
        print(f"\n🎯 Processing {total_jobs} jobs...")
        print("=" * 60)
        
        try:
            for i in range(total_jobs):
                print(f"\n{'='*60}")
                print(f"📋 Job [{i+1}/{total_jobs}]")
                print(f"{'='*60}")
                
                # Scroll item into view and jitter mouse (looks human)
                scroll_list_item_into_view(page, i)
                jitter_mouse(page, intensity=2)
                human_delay(800, 1800)
                
                # Get job card ID
                job_id = get_job_card_at_index(page, i)
                if not job_id:
                    print("   ⏭️  No card found, skipping")
                    results["skipped"].append(f"Job {i+1} (no card)")
                    continue
                
                # Click the job card
                card = page.locator(f".job-card-container[data-job-id='{job_id}']")
                if card.count() == 0:
                    print("   ⏭️  Card not visible, skipping")
                    results["skipped"].append(f"Job {i+1} (not visible)")
                    continue
                
                # Get job title
                job_title = "Unknown"
                try:
                    title_el = card.locator(".job-card-list__title")
                    if title_el.count() > 0:
                        job_title = title_el.inner_text().strip()
                except:
                    pass
                
                print(f"   Title: {job_title}")
                print(f"   ID:    {job_id}")
                
                # Click the job card (with small pre-click hover)
                try:
                    box = card.bounding_box()
                    if box:
                        page.mouse.move(
                            box["x"] + box["width"] / 2,
                            box["y"] + box["height"] / 2,
                        )
                        human_delay(200, 500)
                except Exception:
                    pass
                card.click()
                human_delay(2500, 4500)  # Wait for details panel
                
                # --- Check for Easy Apply button ---
                easy_apply_btn = page.locator("#jobs-apply-button-id").first
                
                if not easy_apply_btn.is_visible():
                    # Try fallback selector
                    easy_apply_btn = page.locator("button.jobs-apply-button").first
                
                if not easy_apply_btn.is_visible():
                    print("   ⏭️  No Easy Apply button — skipping")
                    results["skipped"].append(f"{job_title} (no Easy Apply)")
                    continue
                
                # Check button text — must say "Easy Apply", not just "Apply"
                btn_text = ""
                try:
                    btn_text = easy_apply_btn.inner_text().strip()
                except:
                    pass
                
                if "Easy Apply" not in btn_text and "easy apply" not in btn_text.lower():
                    print(f"   ⏭️  Button says '{btn_text}' (not Easy Apply) — skipping")
                    results["skipped"].append(f"{job_title} (external apply)")
                    continue
                
                # Click Easy Apply
                print("   🔘 Clicking Easy Apply...")
                current_page_count = len(context.pages)
                easy_apply_btn.click()
                human_delay(1500, 3000)
                
                # --- Check for redirect (new tab) ---
                if len(context.pages) > current_page_count:
                    print("   ⏭️  External redirect detected — closing tab, skipping")
                    try:
                        context.pages[-1].close()
                    except:
                        pass
                    results["skipped"].append(f"{job_title} (redirect)")
                    continue
                
                # --- Check modal opened ---
                modal = page.locator("div.jobs-easy-apply-modal")
                if modal.count() == 0:
                    print("   ⏭️  Easy Apply modal didn't open — skipping")
                    results["skipped"].append(f"{job_title} (no modal)")
                    continue
                
                print("   ✅ Easy Apply modal opened!")
                
                # --- Run the LangGraph agent ---
                result = run_easy_apply(page, job_title)
                
                if result == "APPLIED":
                    results["applied"].append(job_title)
                elif result == "SKIPPED":
                    results["skipped"].append(f"{job_title} (agent skipped)")
                else:
                    results["failed"].append(f"{job_title} ({result})")
                
                # Anti-detection: randomized cooldown between jobs
                between_job_cooldown()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user (Ctrl+C)")
        
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        
        # --- Print summary ---
        print("\n\n" + "=" * 60)
        print("📊 FINAL SUMMARY")
        print("=" * 60)
        print(f"   ✅ Applied:  {len(results['applied'])}")
        for title in results["applied"]:
            print(f"      • {title}")
        print(f"   ⏭️  Skipped:  {len(results['skipped'])}")
        for title in results["skipped"]:
            print(f"      • {title}")
        print(f"   ❌ Failed:   {len(results['failed'])}")
        for title in results["failed"]:
            print(f"      • {title}")
        print("=" * 60)
        print(f"   Total: {len(results['applied']) + len(results['skipped']) + len(results['failed'])} jobs processed")
        print(f"   Time:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Keep browser open for inspection
        print("\n   Browser stays open — press Ctrl+C to close")
        try:
            page.pause()
        except KeyboardInterrupt:
            pass
        
        context.close()


if __name__ == "__main__":
    main()
