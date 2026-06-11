---
name: run-pipeline-lab
description: Run, launch, start, smoke-test, or screenshot the pipeline-lab FastAPI service. Use when asked to start the server, hit its endpoints, verify the /todos API works, or confirm an endpoint change works against the live app (not just pytest).
---

# Run pipeline-lab

`pipeline-lab` is a tiny FastAPI service (`app.main:app`) exposing a `/health`
check and an in-memory `/todos` CRUD API (GET list, GET by id, POST, PUT).
There is no GUI — it's driven over HTTP. The agent path is a **smoke driver**
that launches uvicorn, exercises every endpoint, and tears the server down.

All paths below are relative to the repo root (`<unit>/` = `C:\projects\01_pipeline_lab`).
This was authored and verified on Windows 11 with PowerShell 7 (`pwsh`).

## Prerequisites

Deps are already installed in the committed `.venv` (Python 3.12, FastAPI
0.115, uvicorn 0.32, httpx, pytest). To recreate from scratch:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Always invoke Python via `.\.venv\Scripts\python.exe` — the system `python`
on this machine does **not** have uvicorn installed.

## Run (agent path) — the smoke driver

This is the primary path. It self-contains launch + drive + teardown:

```powershell
pwsh -File .claude\skills\run-pipeline-lab\smoke.ps1
```

Expected output (exit code 0):

```
PASS  GET /health -> status ok
PASS  GET /todos -> count matches list
PASS  GET /todos/1 -> id 1
PASS  GET /todos/9999 -> 404
PASS  POST /todos -> 201 with id
PASS  PUT /todos/{id} -> updated fields
PASS  PUT change persists across GET
PASS  PUT /todos/9999 -> 404

All checks passed
```

The driver starts uvicorn on `127.0.0.1:8000`, polls `/health` until ready
(up to 20s), runs the assertions, and **always** kills the server it spawned
(via `finally`). Server stdout/stderr go to `.uvicorn.smoke.log` / `.out` in
the repo root. To add a check for a new endpoint, edit the driver and add a
`Check "<name>" (<condition>)` line.

## Run (human path)

For interactive poking (Swagger UI at `/docs`):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs`. Ctrl-C to stop. Useless for
headless/automated runs — it blocks forever waiting for a window/keypress.

## Direct invocation (no server)

Most endpoint changes can be verified without launching uvicorn at all —
FastAPI's `TestClient` calls the app in-process. This is what the pytest
suite uses:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

12 tests, ~0.3s. Prefer this for logic changes; use the smoke driver when you
need to confirm real HTTP wiring (status codes, serialization, path coercion).

## Gotchas

- **Background jobs do not survive between separate PowerShell tool calls** —
  each call is a fresh shell, so `Start-Job` from one call is gone in the next.
  The driver sidesteps this by launching uvicorn as a child process and driving
  it within a *single* script run. Don't try to "start the server" in one
  command and "curl it" in another.
- **`_todos` is in-memory and mutable across requests within one server run.**
  Tests that mutate todo id 1 (e.g. the PUT test) leave it changed for the rest
  of that process's life. The persistence test creates its *own* todo via POST
  instead of reusing id 1, so it's order-independent.
- **`PUT` does partial updates.** `TodoUpdate` has `title`/`done` both optional
  (`str | None = None`); the handler only overwrites a field when it's
  `is not None`. Sending `{"done": true}` alone leaves the title untouched.
- **Non-integer ids return 422, not 404.** `todo_id: int` makes FastAPI reject
  `/todos/abc` before the handler runs — that's a validation error (422), not a
  missing-resource error (404).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No module named 'uvicorn'` | You used system `python`. Use `.\.venv\Scripts\python.exe`. |
| `FAIL server never came up` | Check `.uvicorn.smoke.log` in the repo root. Usually port 8000 is already in use — kill the stale process or change the port in `smoke.ps1`. |
| `IndentationError` on pytest collection | A test in `tests/test_main.py` has misaligned `assert` lines; the whole file fails to import. Fix the indentation. |
