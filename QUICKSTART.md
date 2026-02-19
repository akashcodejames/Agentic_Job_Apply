# LinkedIn Automation Setup - Quick Start

## ✅ What's Ready
- Virtual environment with Playwright
- Persistent browser profile setup
- Job selector test script

## 🚀 Getting Started

### 1. First Time: Login to LinkedIn
```bash
source venv/bin/activate
python setup_linkedin_browser.py
```
- Browser opens → Log into LinkedIn manually
- Your session is saved for future runs
- Press `Ctrl+C` when done

### 2. Test Job Selector
```bash
python test_job_selector.py
```
- Opens jobs search page with your login
- **Tests** the `.job-card-container` selector
- **Prints** job IDs found (no clicking)
- Shows if selector is working

### 3. Write Your Automation
Use the template in `example_automation.py` or create your own!

## 📁 Files

| File | Purpose |
|------|---------|
| `setup_linkedin_browser.py` | First-time LinkedIn login setup |
| `test_job_selector.py` | Test job selector without clicking |
| `example_automation.py` | Automation template |

## 🔧 Fixed Issues
- ✅ Removed networkidle timeout error
- ✅ Added proper wait strategies

---

**Next**: Run `python setup_linkedin_browser.py` to save your LinkedIn session!
