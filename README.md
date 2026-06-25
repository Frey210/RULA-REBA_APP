# RULA-REBA APP

ErgoQuipt Phase 1 application repository.

This repository contains the FastAPI backend, PostgreSQL data model, analytics/reporting services, and the future Electron desktop application for the RULA/REBA ergonomic assessment platform.

## Current Status

Implemented:

- Architecture and API documentation.
- Backend scaffold.
- JWT/Bearer authentication foundation.
- SQLAlchemy model foundation.
- Alembic initial migration.
- Smoke tests for auth, worker ownership, pairing, and session lifecycle.

Planned next:

- WebSocket ingest.
- Edge pairing workflow.
- Electron desktop app.
- RULA/REBA scoring service extraction from the legacy reference repo.

## Backend Development

Use Python 3.12 explicitly because the Windows `python` command on this machine points to Python 2.7.

```powershell
cd D:\Aerasea\RULA-REBA_APP\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

For local SQLite migration smoke tests:

```powershell
$env:DATABASE_URL='sqlite:///./migration_smoke.sqlite3'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Electron Development

The Electron command starts FastAPI, Vite, and Electron together:

```powershell
cd D:\Aerasea\RULA-REBA_APP\desktop
npm.cmd run electron
```

It uses `backend\.venv` and the local SQLite database `backend\dev_server.sqlite3`.
Set `ERGOQUIPT_DATABASE_URL` before launching only when a different database is required.
Pending Alembic migrations are applied automatically before FastAPI starts.

Worker enrollment photos are stored privately under `backend\media\worker-enrollments`.
The frontend retrieves them through authenticated API requests; the media directory
is intentionally excluded from Git.
