# Getting started with Job Finder AI

**Written for non-technical readers.** No prior coding experience assumed.

---

## What this app does

Job Finder AI is an evidence-first career workspace. In this development version you can upload a resume, review extracted details, set job preferences, search supported Greenhouse and Lever boards, inspect verification status and matching explanations, and review local notification records.

The application searches supported employer ATS sources only. It does not submit job applications, generate cover letters, run interview coaching, or maintain a persistent application tracker yet. Those are later roadmap phases.

---

## Start the web dashboard on macOS

Open Terminal and run:

```bash
cd "$HOME/Job Finder AI"
git switch feature/local-web-dashboard
git pull --ff-only origin feature/local-web-dashboard
cd backend
./.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep that Terminal window open. Open **http://127.0.0.1:8000/** in Chrome to use the dashboard. The interactive API reference remains available at **http://127.0.0.1:8000/docs**, and the health check is at **http://127.0.0.1:8000/health**.

If you have not created the virtual environment yet, run these commands from the `backend` folder:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -e ".[dev]"
```

The dashboard is served by FastAPI from the same local origin, so no separate frontend development server or CORS setup is required.

## Use the dashboard

1. Open **My profile** and upload a PDF, DOCX or TXT resume (maximum 4 MB).
2. Review the extracted name, email, skills and experience count. Treat extracted content as a draft and correct it.
3. Confirm the job preferences and save them.
4. Open **Find jobs**, enter employer slugs for Greenhouse or Lever, choose the maximum results and run the search.
5. Review match score, verification status, risk indicators, job details and the official application link.
6. Open **Notifications** to inspect records created in the current backend session.

The sample employer slugs in the form are editable examples, not guaranteed to have current vacancies.

## Important development-version limitations

- The backend uses in-memory profile, token, evidence and notification stores. Restarting Uvicorn clears them. The browser stores the current session token in tab session storage; clearing the session does not delete the in-memory backend profile.
- The default notifier logs messages locally. Real email requires SMTP environment variables configured before startup.
- The UI is a local single-user development workspace, not a production multi-user service.
- Application submission, resume/cover-letter generation, interview preparation, learning plans and long-term application tracking are not implemented yet.
- Keep the server bound to 127.0.0.1. Do not expose this development server to the public internet.

## Stop the application

Return to the Terminal window running Uvicorn and press **Ctrl + C**.

## Troubleshooting

**The browser displays `{"detail":"Not Found"}`.** Open `http://127.0.0.1:8000/` after updating the dashboard branch. The API root itself was not previously configured as a webpage.

**Port 8000 is already in use.** Stop the other process or start with `--port 8001`, then use `http://127.0.0.1:8001/`.

**The dashboard reports that the API is offline.** Check the Uvicorn Terminal for startup errors and confirm `http://127.0.0.1:8000/health` returns `{"status":"ok"}`.

**A profile session stops working after a server restart.** This is expected with the current in-memory stores. Upload your resume again to create a new session.

**A search returns no jobs.** Confirm the employer slug and source (Greenhouse or Lever). Not all employers use these systems, and not all boards have open roles.

For API-level troubleshooting, open `http://127.0.0.1:8000/docs`.
