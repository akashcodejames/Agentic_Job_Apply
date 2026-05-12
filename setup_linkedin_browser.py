"""
setup_linkedin_browser.py — One-time LinkedIn login setup.

Run this ONCE before using the auto apply bot:
    python setup_linkedin_browser.py

It opens a real Chromium browser, lets you log in to LinkedIn manually,
then saves the session to browser_data/ so run_easy_apply.py can reuse it.
"""

import os
from playwright.sync_api import sync_playwright

USER_DATA_DIR = os.path.join(os.path.dirname(__file__), "browser_data")

def main():
    print("=" * 60)
    print("  LinkedIn Browser Setup")
    print("=" * 60)
    print()
    print("This will open a Chromium browser.")
    print("➡  Log in to LinkedIn manually, then press ENTER here.")
    print()

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            USER_DATA_DIR,
            headless=False,
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.new_page()
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")

        print("Browser opened — please log in to LinkedIn.")
        print("After logging in successfully, come back here and press ENTER.")
        print()
        input("Press ENTER once you are logged in ▶  ")

        # Verify login
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        if "feed" in page.url or "mynetwork" in page.url:
            print()
            print("✅  Login confirmed! Session saved to:", USER_DATA_DIR)
            print("   You can now run:  python run_easy_apply.py")
        else:
            print()
            print("⚠️  Could not confirm login — URL is:", page.url)
            print("   Make sure you are fully logged in before pressing ENTER.")

        context.close()

if __name__ == "__main__":
    main()
