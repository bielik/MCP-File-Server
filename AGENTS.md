# Repository Guidelines

## Project Structure & Modules
- `backend/`: FastAPI app (`app/` with `api/`, `services/`, `schemas/`, `models/`, `utils/`), config in `app/config.py`, tests in `backend/tests/`.
- `frontend/`: Vite + React + TypeScript UI (`src/` with `components/`, `pages/`).
- `config/`: Runtime configuration (e.g., `permissions.json`).
- `data/`: SQLite database file (`database.db`).
- `shared-fs/`: Sample files exposed via the server.
- Orchestration: `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`.

## Build, Test, Run
- Backend setup: `python -m venv .venv && .\.venv\Scripts\activate && pip install -r backend/requirements.txt`
- Run backend: `uvicorn backend.app.main:app --reload --port 8000`
- Frontend setup: `cd frontend && npm install`
- Run frontend: `npm run dev` (default port `5173`)
- Docker (full stack): `docker-compose up --build`
- Tests (backend): `pytest -q` (from `backend/`)

## Coding Style & Naming
- Python: 4-space indents, type hints where helpful, snake_case for functions/vars, PascalCase for classes, UPPER_SNAKE_CASE for constants. Keep modules small and focused under `app/{api,services,schemas,models,utils}`.
- Frontend: TypeScript, React components in PascalCase (e.g., `PermissionEditor.tsx`), variables camelCase. Lint with `npm run lint` (ESLint).
- Imports: prefer absolute imports within `backend.app.*` and concise barrel `__init__.py` where present.

## Testing Guidelines
- Framework: `pytest` (+ `pytest-asyncio`).
- Location: `backend/tests/` with files named `test_*.py`.
- Scope: favor fast, isolated tests; integration tests exist (e.g., `test_integration.py`).
- Run examples: `pytest -q`, filter with `pytest -k permission`.

## Commits & PRs
- Commits: Imperative mood, concise scope. Emoji prefixes are common in history (e.g., `🔧 Fix ...`, `🎉 Complete ...`, `🐛 Fix ...`).
- PRs: Include summary, rationale, linked issues, test plan, and screenshots for UI changes. Note any feature flags or config changes.

## Configuration & Security
- Feature flags (env): `ENABLE_CONFIG_FILE_PERMISSIONS`, `ENABLE_DATABASE_PERMISSIONS`, `DEBUG_PERMISSION_CACHE`, `ENABLE_PERFORMANCE_METRICS`.
- Ports (env): `BACKEND_PORT` (default 8000), `FRONTEND_PORT` (default 5173).
- Permissions config: edit `config/permissions.json`; avoid committing secrets. The server reads/watches this file when enabled.
