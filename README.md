# fb-lease-finder

This python script automatically searches your Facebook NYC sublease groups and returns posts that match your criteria bc ain't nobody got time for that.

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
2. navigate to this folder (e.g. `cd Downloads/fb-lease-finder/`)
3. run the commands in order:

**macOS / Linux**

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
```

**Windows (PowerShell)**

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\playwright install chromium
```

You only need to do this once.

---

## How to run the program

**macOS / Linux**

```bash
.venv/bin/python3 main.py
```

**Windows (PowerShell)**

```powershell
.venv\Scripts\python main.py
```

---

## What to expect

**Step 1 — You will be prompted to answer a few questions**

For each question, use the **arrow keys** to move, **Space** to select, and press **Enter** to submit.

No selection defaults to selecting all options.

For the URL question, paste one link at a time and press **Enter**. Press **Enter** on a blank line when you're done adding URLs.

**Step 2 — Log in to Facebook**

A browser window may open and prompt you to log in to Facebook for authentication purposes. The script will continue automatically once you're logged in. Your session is saved, so you usually only need to do this once.

**Step 3 — See your results**

The script returns matching posts from the LAST 24 HOURS. **Command+Double Click** the link to open it in the browser.

---

Press **Ctrl+C** at any time to quit.

---

## Troubleshooting

**Install fails while "Building wheel for greenlet" (or another package)**

This happens when your Python version is so new that the package doesn't yet
have a prebuilt wheel, so it tries (and fails) to compile from source. The
easiest fix is to use a Python version with available wheels — any release in
the **3.10–3.14** range works. Install one from
[python.org](https://www.python.org/downloads/), then recreate the environment:

```bash
rm -rf .venv          # on Windows: rmdir /s /q .venv
python3.14 -m venv .venv   # or python3.12, python3.11, etc.
```

…and re-run the first-time setup commands above.
