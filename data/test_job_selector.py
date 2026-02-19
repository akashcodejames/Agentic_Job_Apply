"""
Test script for LinkedIn job selector with proper scrolling

LinkedIn uses "virtual scrolling" (occlusion) - it removes the content of
job cards that scroll out of view. So .job-card-container count will always
be less than the actual total. This script handles that by:
1. Finding the scrollable container dynamically
2. Scrolling to load all list items
3. Scrolling each item into view before clicking (to "hydrate" it)
"""

from playwright.sync_api import sync_playwright
import os

def find_scrollable_container(page):
    """Find the scrollable parent container of job cards using JavaScript."""
    return page.evaluate("""
        (() => {
            const jobCards = document.querySelectorAll('.job-card-container');
            if (jobCards.length === 0) return null;
            let el = jobCards[0];
            while (el && el !== document.body) {
                el = el.parentElement;
                if (!el) break;
                const style = window.getComputedStyle(el);
                if (el.scrollHeight > el.clientHeight && 
                    (style.overflowY === 'auto' || style.overflowY === 'scroll')) {
                    return true;
                }
            }
            return false;
        })()
    """)

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
            // Fallback
            window.scrollBy(0, 800);
        })()
    """)

def get_total_list_items(page):
    """
    Get the REAL total number of job list items (not just visible .job-card-container).
    LinkedIn uses occlusion - items outside viewport lose their .job-card-container class.
    The <li> items inside the scrollable <ul> give the true count.
    """
    return page.evaluate("""
        (() => {
            const jobCards = document.querySelectorAll('.job-card-container');
            if (jobCards.length === 0) return 0;
            // Walk up to find the <ul> that contains the job list
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
    """Scroll a specific list item into view by its index to hydrate it."""
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

def test_job_selector():
    # Same user data directory for persistent login
    user_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
    
    if not os.path.exists(user_data_dir):
        print("⚠️  Browser profile not found!")
        print("   Please run 'python setup_linkedin_browser.py' first to login")
        return
    
    print("🔍 Testing job selector on LinkedIn...")
    print("=" * 60)
    
    with sync_playwright() as p:
        # Launch with persistent context (should be logged in)
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
        
        # Wait for page to load
        print("⏳ Waiting for page to load...")
        page.wait_for_timeout(5000)
        
        # --- Step 1: Scroll the container to load all list items ---
        print("\n📜 Scrolling to load all jobs...")
        print("-" * 60)
        
        previous_total = 0
        stable_rounds = 0
        
        while stable_rounds < 3:
            current_total = get_total_list_items(page)
            visible = page.locator(".job-card-container").count()
            
            print(f"   Total items: {current_total} (visible cards: {visible})")
            
            if current_total == previous_total:
                stable_rounds += 1
            else:
                stable_rounds = 0
            
            previous_total = current_total
            
            # Scroll the container to the bottom
            scroll_container_to_bottom(page)
            page.wait_for_timeout(2000)
        
        print(f"   ✅ All jobs loaded! Total: {previous_total}")
        print("-" * 60)
        
        # --- Step 2: Click through each job ---
        print(f"\n🎯 Found {previous_total} jobs in the list")
        print(f"\n🖱️  Clicking through {previous_total} jobs with 3-second delays...")
        print("   Watch the right-hand panel update!\n")
        print("-" * 60)
        
        try:
            for i in range(previous_total):
                # Scroll this specific item into view (this "hydrates" it)
                scroll_list_item_into_view(page, i)
                page.wait_for_timeout(500)  # Small wait for hydration
                
                # Now find the job card container inside this item
                job_card = page.evaluate(f"""
                    (() => {{
                        const jobCards = document.querySelectorAll('.job-card-container');
                        if (jobCards.length === 0) return null;
                        let el = jobCards[0];
                        while (el && el !== document.body) {{
                            el = el.parentElement;
                            if (!el) break;
                            if (el.tagName === 'UL') {{
                                const item = el.children[{i}];
                                if (!item) return null;
                                const card = item.querySelector('.job-card-container');
                                if (card) return card.getAttribute('data-job-id');
                                return 'no-card';
                            }}
                        }}
                        return null;
                    }})()
                """)
                
                if job_card == 'no-card' or job_card is None:
                    print(f"� [{i+1}/{previous_total}] ⏭️  Card not hydrated, skipping...")
                    continue
                
                # Click using the data-job-id
                try:
                    card_locator = page.locator(f".job-card-container[data-job-id='{job_card}']")
                    if card_locator.count() > 0:
                        # Try to get title
                        title = "N/A"
                        try:
                            title_elem = card_locator.locator(".job-card-list__title")
                            if title_elem.count() > 0:
                                title = title_elem.inner_text().strip()
                        except:
                            pass
                        
                        print(f"🔘 [{i+1}/{previous_total}] Job ID: {job_card}")
                        print(f"   Title: {title}")
                        
                        card_locator.click()
                        page.wait_for_timeout(3000)  # 3 seconds delay
                        print("   ✅ Clicked! Right panel updated.\n")
                    else:
                        print(f"🔘 [{i+1}/{previous_total}] ⏭️  Card not found, skipping...")
                except Exception as e:
                    print(f"🔘 [{i+1}/{previous_total}] ⚠️  Click failed: {e}\n")
            
            print("=" * 60)
            print("✅ All jobs clicked!")
            print("   Browser will stay open - Press Ctrl+C to close")
            
            # Keep browser open to inspect
            page.pause()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print("\n💡 Tip: Make sure you're logged into LinkedIn first")
            print("   Run: python setup_linkedin_browser.py")
        
        context.close()

if __name__ == "__main__":
    test_job_selector()
