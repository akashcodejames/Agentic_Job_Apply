"""
Example automation script using the persistent browser

This demonstrates how to use the persistent browser context in your automation code.
LinkedIn will already be logged in when this runs.
"""

from playwright.sync_api import sync_playwright
import os

def run_automation():
    # Same user data directory as setup script
    user_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
    
    if not os.path.exists(user_data_dir):
        print("❌ Browser profile not found!")
        print("   Please run 'python setup_linkedin_browser.py' first")
        return
    
    print("🚀 Starting automation with persistent LinkedIn session...")
    
    with sync_playwright() as p:
        # Launch with the same persistent context
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,  # Change to True for headless mode
            viewport={"width": 1280, "height": 720},
        )
        
        page = context.new_page()
        
        # Navigate to LinkedIn - you should already be logged in
        page.goto("https://www.linkedin.com/feed/")
        page.wait_for_load_state("networkidle")
        
        print("✅ Opened LinkedIn feed")
        
        # Your automation code goes here
        # Example: Get your profile name
        try:
            # This is just an example - adjust selectors as needed
            print("📝 You can now write your automation code here...")
            print("   The browser will stay logged in across runs!")
            
            # Keep browser open to see the result
            page.pause()
            
        except Exception as e:
            print(f"⚠️  Error: {e}")
        
        context.close()
        print("✅ Automation completed!")

if __name__ == "__main__":
    run_automation()
