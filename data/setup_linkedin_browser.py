"""
Playwright Persistent Browser Setup for LinkedIn

This script launches a Chromium browser with a persistent user data directory.
Your LinkedIn login will be saved and persist across runs.

First Run: The browser will open - log into LinkedIn manually
Subsequent Runs: Browser will open with LinkedIn already logged in
"""

from playwright.sync_api import sync_playwright
import os

def launch_persistent_browser():
    # Create a directory to store browser profile data
    user_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
    os.makedirs(user_data_dir, exist_ok=True)
    
    print(f"✅ Using persistent browser profile at: {user_data_dir}")
    print("=" * 60)
    
    with sync_playwright() as p:
        # Launch browser with persistent context
        # This saves cookies, local storage, and login sessions
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,  # Set to True to run without GUI
            viewport={"width": 1280, "height": 720},
            args=[
                '--disable-blink-features=AutomationControlled',  # Hide automation flags
            ],
        )
        
        # Create a new page
        page = context.new_page()
        
        # Navigate to LinkedIn
        print("🌐 Opening LinkedIn...")
        page.goto("https://www.linkedin.com", wait_until="domcontentloaded")
        
        # Wait a bit for the page to load
        page.wait_for_timeout(3000)
        
        # Check if already logged in
        if "feed" in page.url or "mynetwork" in page.url:
            print("✅ Already logged into LinkedIn!")
        else:
            print("⚠️  Please log into LinkedIn manually in the browser window")
            print("   Your login will be saved for future runs")
        
        print("\n" + "=" * 60)
        print("📝 INSTRUCTIONS:")
        print("   - If not logged in: Log into LinkedIn now")
        print("   - The browser will stay open for you to interact")
        print("   - Press Ctrl+C in terminal when done to close")
        print("   - Next time you run this, LinkedIn will be logged in!")
        print("=" * 60)
        
        try:
            # Keep the browser open - you can interact with it
            # Press Ctrl+C to close
            page.pause()
        except KeyboardInterrupt:
            print("\n👋 Closing browser...")
        
        context.close()

if __name__ == "__main__":
    launch_persistent_browser()
