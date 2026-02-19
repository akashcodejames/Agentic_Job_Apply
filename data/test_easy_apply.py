"""
Test Easy Apply button click flow

This script:
1. Opens LinkedIn jobs search with persistent login
2. Scrolls to load all jobs
3. Clicks the FIRST job card
4. Clicks the "Easy Apply" button on the right panel
5. Stops (keeps browser open for inspection)
"""

from playwright.sync_api import sync_playwright
import os

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

def test_easy_apply():
    user_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
    
    if not os.path.exists(user_data_dir):
        print("⚠️  Browser profile not found!")
        print("   Run 'python setup_linkedin_browser.py' first to login")
        return
    
    print("🚀 Test: Click Job → Click Easy Apply")
    print("=" * 60)
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            viewport={"width": 1280, "height": 720},
        )
        
        page = context.new_page()
        
        # Navigate to LinkedIn jobs search
        url = "https://www.linkedin.com/jobs/search/?keywords=python%20developer&location=India&f_TPR=r86400&f_AL=true"
        print(f"📍 Navigating to: {url}")
        page.goto(url, wait_until="domcontentloaded")
        
        print("⏳ Waiting for page to load...")
        page.wait_for_timeout(5000)
        
        # --- Step 1: Scroll to load all jobs ---
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
        
        print(f"   ✅ All jobs loaded! Total: {previous_total}")
        print("-" * 60)
        
        # --- Step 2: Click the FIRST job ---
        print("\n🔘 Step 1: Clicking the first job card...")
        
        # Scroll first item into view to hydrate it
        scroll_list_item_into_view(page, 0)
        page.wait_for_timeout(1000)
        
        first_job = page.locator(".job-card-container").first
        if first_job.count() == 0:
            print("❌ No job card found!")
            context.close()
            return
        
        job_id = first_job.get_attribute("data-job-id")
        
        # Try to get job title
        title = "N/A"
        try:
            title_elem = first_job.locator(".job-card-list__title")
            if title_elem.count() > 0:
                title = title_elem.inner_text().strip()
        except:
            pass
        
        print(f"   Job ID: {job_id}")
        print(f"   Title:  {title}")
        
        first_job.click()
        print("   ✅ Job card clicked!")
        
        # Wait for right panel to load
        print("   ⏳ Waiting for job details panel...")
        page.wait_for_timeout(3000)
        
        # --- Step 3: Click Easy Apply button ---
        print("\n🎯 Step 2: Looking for Easy Apply button...")
        
        try:
            # LinkedIn renders TWO buttons with same ID - use .first
            easy_apply_btn = page.locator("#jobs-apply-button-id").first
            
            if easy_apply_btn.is_visible():
                btn_label = easy_apply_btn.get_attribute("aria-label") or ""
                print(f"   ✅ Found Easy Apply button")
                print(f"   Label: {btn_label}")
                
                # Click Easy Apply
                easy_apply_btn.click()
                print("   🎉 Easy Apply button clicked!")
                page.wait_for_timeout(2000)
                print("   ✅ Easy Apply modal should be open now!")
            else:
                # Fallback: try other selectors
                alt_btn = page.locator("button.jobs-apply-button").first
                if alt_btn.is_visible():
                    print("   ✅ Found Easy Apply button (alt selector)")
                    alt_btn.click()
                    print("   🎉 Easy Apply button clicked!")
                    page.wait_for_timeout(2000)
                else:
                    print("   ⚠️  Easy Apply button NOT found!")
                    print("   This job may not have Easy Apply.")
        except Exception as e:
            print(f"   ⚠️  Error with Easy Apply: {e}")
        
        # --- Done: ALWAYS keep browser open ---
        print("\n" + "=" * 60)
        print("✅ Test complete!")
        print("   Browser will stay open - Press Ctrl+C to close")
        
        try:
            page.pause()
        except KeyboardInterrupt:
            pass
        
        context.close()

if __name__ == "__main__":
    test_easy_apply()
