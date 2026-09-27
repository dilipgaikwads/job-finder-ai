# Getting started with Job Finder AI

**Written for non-technical readers.** No prior coding experience assumed. If a step doesn't work, jump to the "Troubleshooting" section at the end.

---

## What this app does (in plain English)

You upload your resume. The app:

1. Reads your resume and extracts your skills, experience, and contact info.
2. Fetches real job postings from legitimate sources (Greenhouse and Lever — the systems Airbnb, Stripe, Figma, Notion, and thousands of other companies use to post jobs).
3. Runs each posting through a **verifier** that looks for scam signs (fake application URLs, upfront fee requests, suspicious phrases).
4. Ranks the jobs against your profile with a transparent breakdown (skills match, remote/onsite, AI relevance, etc.).
5. **Never sends you a notification for a suspicious job.** High-risk postings are filtered out before they ever reach you.

There is no dark-web sourcing — that was a deliberate design decision (see `docs/SOURCING_POLICY.md`).

---

## Part 1 — What you need to install first (one time)

Two things: **Python** (the language the app is written in) and **Git** (the tool to download the code).

### On a Mac

**Step 1. Open the Terminal app.**
Press `Cmd + Space` to open Spotlight, type `Terminal`, and press Enter. A black or white window with text appears — this is the Terminal. You'll type commands here.

**Step 2. Check whether Python is already installed.**
In the Terminal, type this exactly and press Enter:

```
python3 --version
```

If you see something like `Python 3.11.5` or higher (3.11, 3.12, 3.13, 3.14 — anything 3.11+), you're done with Python. Skip to Step 4.

If you see `command not found` or a version below 3.11, continue to Step 3.

**Step 3. Install Python.**
Go to <https://www.python.org/downloads/macos/> in your browser. Click the yellow "Download Python 3.12.x" button. When the download finishes, double-click the `.pkg` file and follow the on-screen installer (click "Continue" and "Agree" through the prompts). After it finishes, close and reopen Terminal, and run `python3 --version` again to confirm.

**Step 4. Check whether Git is already installed.**
In the Terminal, type:

```
git --version
```

If you see something like `git version 2.39.0`, you're done. Skip to Part 2.

If macOS pops up a dialog asking you to install "Command Line Developer Tools," click **Install** and wait for it to finish (a few minutes). After it's done, run `git --version` again to confirm.

### On Windows

**Step 1. Open PowerShell.**
Click the Start button (the Windows logo in the bottom-left), type `PowerShell`, and click "Windows PowerShell." A blue window with text appears — this is PowerShell. You'll type commands here.

**Step 2. Check whether Python is already installed.**
In PowerShell, type this and press Enter:

```
python --version
```

If you see `Python 3.11.x` or higher, skip to Step 4.

If you see nothing useful, or the Microsoft Store opens, continue to Step 3.

**Step 3. Install Python.**
Go to <https://www.python.org/downloads/windows/> in your browser. Click the yellow "Download Python 3.12.x" button. When the download finishes, double-click the `.exe` file.

**Very important:** on the first screen of the installer, tick the checkbox that says **"Add python.exe to PATH"** at the bottom. Then click "Install Now." When it's done, **close PowerShell and open it again** (this is required for it to see Python).

Run `python --version` again to confirm.

**Step 4. Check whether Git is already installed.**
In PowerShell:

```
git --version
```

If you see a version, skip to Part 2. Otherwise, go to <https://git-scm.com/download/win> and download the installer. Run it and accept every default (click "Next" on each screen). Close and reopen PowerShell when it's done.

---

## Part 2 — Download the app

This step is the same on Mac and Windows.

**Step 1. Choose where to put it.**
In the Terminal (Mac) or PowerShell (Windows), type:

```
cd ~
```

That means "go to my home folder." Then type:

```
mkdir job-finder && cd job-finder
```

That creates a folder called `job-finder` and moves into it.

**Step 2. Download the code.**

```
git clone https://github.com/dilipgaikwads/job-finder-ai.git
cd job-finder-ai
```

The first line downloads the app; the second moves into the downloaded folder. You should now see a message like "Cloning into 'job-finder-ai'..." and, after it finishes, no error.

*If you get an authentication error*, the repo may still be private. Ask the account owner to add you as a collaborator, or make the repo public.

---

## Part 3 — Set up the backend

The backend is the "brain" of the app. It runs on your computer and listens for requests.

**Step 1. Move into the backend folder.**

```
cd backend
```

**Step 2. Create a private space for the app's tools.**
This is called a "virtual environment." It keeps the app's dependencies from mixing with anything else on your computer.

On **Mac**:

```
python3 -m venv .venv
source .venv/bin/activate
```

On **Windows** (PowerShell):

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell says "running scripts is disabled on this system," run this one-time command and answer `Y`:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then run the `.\.venv\Scripts\Activate.ps1` line again.

You'll know it worked when your prompt now starts with `(.venv)`.

**Step 3. Install the app's tools.**

```
pip install -e ".[dev]"
pip install pypdf python-docx python-multipart
```

The first command installs the main tools; the second grabs a few extras used for reading resumes and receiving file uploads. You'll see a wall of text as things download — this is normal. It takes 1–3 minutes.

**Step 4. Run the tests to confirm everything works.**

```
pytest
```

You should see something like `27 passed in 2.5s` at the bottom. If any tests fail, jump to Troubleshooting.

---

## Part 4 — Start the app

Still in the `backend` folder with `(.venv)` in your prompt, run:

```
uvicorn app.main:app --reload
```

You should see output ending with:

```
Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**The app is now running.** Leave this window open. As long as you keep it open, the app stays up.

Open a web browser and go to:

<http://127.0.0.1:8000/docs>

You'll see an interactive page listing all the endpoints. This is the API documentation, and you can try each endpoint by clicking "Try it out."

To stop the app, go back to the Terminal/PowerShell window and press `Ctrl + C`.

---

## Part 5 — Try it: upload a resume and search for jobs

There are two easy ways. Pick one.

### Option A — Use the web page at /docs (easiest)

1. Go to <http://127.0.0.1:8000/docs> in your browser.
2. Find `POST /resumes`, click it, then click **"Try it out."**
3. Under `file`, click "Choose File" and pick your resume (`.pdf`, `.docx`, or `.txt`).
4. Click the big blue **"Execute"** button.
5. Scroll down to the "Response body." Copy **both** the `user_id` value (a long string) and the `token` value (a longer random string). You will need the token for every next step — it's your login for this session.
6. At the top of the `/docs` page, click the **"Authorize"** button (a padlock icon on the right). In the box that opens, paste your `token` and click "Authorize," then "Close." Every subsequent request from this page will now carry your token automatically.
7. Now find `POST /profiles/{user_id}/search`, click it, click "Try it out."
8. Paste your `user_id`. In the request-body box, replace the text with:

```
{
  "targets": [
    {"adapter": "greenhouse", "employer_slug": "airbnb"},
    {"adapter": "greenhouse", "employer_slug": "stripe"},
    {"adapter": "lever", "employer_slug": "figma"}
  ],
  "top_n": 10,
  "notify": false
}
```

9. Click **Execute**. In a few seconds you'll see a ranked list of jobs from those companies, with verification status and a match score.

*(You can swap in any employer's Greenhouse or Lever slug. The "slug" is the last part of their careers URL. For example, Airbnb's Greenhouse URL is `https://boards.greenhouse.io/airbnb` — the slug is `airbnb`.)*

### Option B — Use curl from another Terminal window

Open a **second** Terminal/PowerShell window (leave the first one running the app). Then:

```
curl -F "file=@/path/to/your/resume.pdf" http://127.0.0.1:8000/resumes
```

Replace `/path/to/your/resume.pdf` with the real path. On Mac you can drag the resume file into the Terminal window and it will paste the path.

The response will include your `user_id` **and** a `token`. Copy both. Then, replacing the placeholders below:

```
curl -X POST http://127.0.0.1:8000/profiles/PASTE_USER_ID/search \
  -H "Authorization: Bearer PASTE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"targets":[{"adapter":"greenhouse","employer_slug":"airbnb"}],"top_n":5,"notify":false}'
```

The `Authorization: Bearer` line is required — the app rejects unauthorized user-scoped requests with a `401`.

---

## Part 6 — Getting email notifications (optional)

By default, notifications are just logged (not emailed). To get real emails, you need an SMTP account (Gmail with an App Password, Sendgrid, Postmark, etc.).

Stop the app (`Ctrl + C`), then set these environment variables **before** starting it again.

On **Mac**:

```
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=you@gmail.com
export SMTP_PASSWORD=your-app-password
export SMTP_FROM=you@gmail.com
uvicorn app.main:app --reload
```

On **Windows** (PowerShell):

```
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="you@gmail.com"
$env:SMTP_PASSWORD="your-app-password"
$env:SMTP_FROM="you@gmail.com"
uvicorn app.main:app --reload
```

For Gmail, you must generate an **App Password** at <https://myaccount.google.com/apppasswords> (this requires 2-Step Verification to be enabled on your Google account). Never use your real Google password.

When you send `POST /profiles/{user_id}/search` with `"notify": true`, notifications will now be emailed to the address on the profile.

---

## Part 7 — Running the app inside Claude Code (right here, on this Mac)

You are already talking to Claude inside the Claude desktop app. Claude can start the app for you here without you having to open a Terminal at all.

Just ask Claude:

> **"Please start the Job Finder AI backend and confirm it's running."**

Claude will run the same `uvicorn app.main:app --reload` command in a background process on your Mac, then confirm the health-check endpoint responds. You'll get back a URL you can open in your browser (`http://127.0.0.1:8000/docs`) — same as Part 4 above.

To stop it, ask Claude:

> **"Please stop the backend."**

The app only listens on `127.0.0.1`, which means it's only reachable from this Mac — no one else on the internet or your Wi-Fi can hit it. That is intentional.

---

## Troubleshooting

**"command not found: python3" on Mac after installing Python.**
Close and reopen Terminal. The installer only updates the path for new Terminal windows.

**"pip install" fails with a compiler error on Mac.**
Run `xcode-select --install` in the Terminal, wait for it to finish, then re-run the pip command.

**"Activate.ps1 cannot be loaded because running scripts is disabled" on Windows.**
Run PowerShell as Administrator once and execute:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
Answer `Y`. Then activate the venv again.

**Port 8000 is already in use.**
Something else is using port 8000. Run the app on a different port:
`uvicorn app.main:app --reload --port 8001`
Then use `http://127.0.0.1:8001/docs` in your browser.

**Tests fail with "ModuleNotFoundError: No module named 'docx'."**
You forgot the second `pip install` line. Run:
`pip install pypdf python-docx python-multipart`

**Resume upload returns "Resume produced no extractable text (scanned image?)."**
Your resume is a scan-based PDF (an image of a document, not real text). Save it as a Word `.docx` first, or copy-paste its content into a `.txt` file, and try that.

**Search returns "total_discovered: 0" but no errors.**
The employer slug is wrong or the company doesn't post on that ATS. Try one of: `airbnb`, `stripe`, `notion`, `figma` (Lever), `anthropic` (Greenhouse — if public).

**"gh: not found" when trying to push to GitHub.**
You don't need `gh` to *use* the app. It's only for uploading changes back to GitHub. If you want it: on Mac run `brew install gh`, on Windows go to <https://cli.github.com/> and download the installer.

---

## Where to go next

- Read `docs/ARCHITECTURE.md` to understand how the pieces fit together.
- Read `docs/SOURCING_POLICY.md` to understand what job sources are allowed and why.
- Read `docs/ROADMAP.md` to see what's built and what's coming.

If you get stuck at any step, screenshot the error and ask Claude for help — describing exactly which step you were on and pasting the error text is the fastest way to get an accurate fix.
