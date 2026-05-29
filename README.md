# fb-sublease-finder

Automated workflow that searches Facebook NYC sublease groups and returns posts that match your criteria bc ain't nobody got time for that.

---

## Prerequisites

You'll need **Python 3.9 or higher** installed. To check, open your terminal and run:

```bash
python3 --version
```

If you don't have it, download it from [python.org](https://www.python.org/downloads/).

---

## First-time setup

1. open your terminal  
2. navigate to this folder (e.g. `cd Downloads/fb-sublease-finder/`)
3. run these commands in order: 

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

You only need to do this once.

---

## How to run the program

```bash
.venv/bin/python3 main.py
```

---

## What to expect

**Step 1 — You will be prompted to answer a few questions**

For each question, use the **arrow keys** to move, **Space** to select, and press **Enter** to submit.

For the URL question, paste one link at a time and press **Enter**. Press **Enter** on a blank line when you're done adding URLs.

**Step 2 — Log in to Facebook**

A browser window may open and prompt you to log in to Facebook for authentication purposes. The script will continue automatically once you're logged in. Your session is saved, so you usually only need to do this once.

**Step 3 — See your results**

The script returns matching posts from the LAST 24 HOURS. **Command+Double Click** the link to open it in the browser.

---

Press **Ctrl+C** at any time to quit.
