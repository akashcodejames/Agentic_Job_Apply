# LinkedIn Automation with Playwright - Setup Guide

This project sets up Playwright with a **persistent browser profile** so your LinkedIn login is saved across runs.

## ✅ Setup Complete!

Your virtual environment and Playwright are already installed and ready to use.

---

## 🚀 Quick Start Guide

### Step 1: Activate Virtual Environment

Every time you want to run your scripts, activate the virtual environment first:

```bash
source venv/bin/activate
```

### Step 2: First-Time LinkedIn Login Setup

Run the setup script to log into LinkedIn (only needed once):

```bash
python setup_linkedin_browser.py
```

**What happens:**
- A browser window opens
- Navigate to LinkedIn and **log in manually**
- Your login credentials will be saved in the `browser_data/` folder
- Press `Ctrl+C` in the terminal when you're done

### Step 3: Run Your Automation

Now you can run automation scripts without logging in again:

```bash
python example_automation.py
```

The browser will open with LinkedIn already logged in! ✅

---

## 📁 Project Structure

```
elarning_Autoamtion/
├── venv/                          # Virtual environment (don't commit)
├── browser_data/                  # Persistent browser profile (don't commit)
├── setup_linkedin_browser.py      # First-time login setup
├── example_automation.py          # Example automation script
├── requirements.txt               # Python dependencies
├── .gitignore                     # Ignore sensitive files
└── README.md                      # This file
```

---

## 📝 Writing Your Own Automation Scripts

### Template for Your Scripts:

```python
from playwright.sync_api import sync_playwright
import os

def my_automation():
    user_data_dir = os.path.join(os.path.dirname(__file__), "browser_data")
    
    with sync_playwright() as p:
        # Launch with persistent context (LinkedIn already logged in)
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,  # Set True for headless mode
        )
        
        page = context.new_page()
        page.goto("https://www.linkedin.com/jobs/")
        
        # Your automation code here
        # ...
        
        context.close()

if __name__ == "__main__":
    my_automation()
```

---

## 🔧 Common Commands

| Command | Description |
|---------|-------------|
| `source venv/bin/activate` | Activate virtual environment |
| `deactivate` | Deactivate virtual environment |
| `pip install -r requirements.txt` | Reinstall dependencies |
| `playwright install chromium` | Reinstall browser |

---

## ⚠️ Important Notes

1. **Browser Data Security**: The `browser_data/` folder contains your LinkedIn session. **Never commit this to Git** (it's already in `.gitignore`)

2. **Session Expiry**: LinkedIn sessions may expire after some time. Just run `setup_linkedin_browser.py` again to re-login.

3. **Headless Mode**: To run without showing the browser window, change `headless=False` to `headless=True` in your scripts.

4. **Virtual Environment**: Always activate the virtual environment before running scripts:
   ```bash
   source venv/bin/activate
   ```

---

## 🎯 Next Steps

1. ✅ Virtual environment is set up
2. ✅ Playwright is installed
3. ⏭️  Run `python setup_linkedin_browser.py` to log into LinkedIn
4. ⏭️  Start writing your automation code!

---

## 🐛 Troubleshooting

**Browser doesn't open:**
```bash
# Reinstall Playwright browsers
source venv/bin/activate
playwright install chromium
```

**"Module not found" error:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate
```

**LinkedIn session expired:**
```bash
# Re-run the setup to login again
python setup_linkedin_browser.py
```

---

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [Playwright Persistent Context](https://playwright.dev/python/docs/auth#reuse-authentication-state)

---

Happy Automating! 🚀
