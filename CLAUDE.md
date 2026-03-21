# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Aim

Aim is an open-source, self-hosted ML experiment tracking tool. It logs training runs via a Python SDK and provides a web UI for exploring and comparing thousands of runs. Version: 3.29.1.

## Build & Development Commands

### Python Backend

```bash
# Dev install (editable)
pip install -r requirements.dev.txt
pip install -e .

# Build Cython extensions (required after modifying .pyx files)
python setup.py build_ext --inplace

# Lint / format
ruff check .
ruff format .
```

### Frontend (React/TypeScript)

```bash
cd aim/web/ui
npm install
npm start              # Dev server → http://localhost:3000
npm run build          # Production build
npm run lint
npm run format:fix
npm run storybook      # Component storybook → :6006
npm run crc 'Name'     # Scaffold new component
```

### Running the Server

```bash
aim up                            # Default: http://127.0.0.1:43800
aim up --repo /path --dev         # Custom repo, debug logging
aim up -h 0.0.0.0 -p 8080 --workers 4
aim up --read-only                # Disable write endpoints
aim server --port 53800           # Remote tracking server (separate from web UI)
```

### Testing

```bash
pytest tests/                         # Full suite
pytest tests/sdk/test_run.py          # Single file
pytest tests/sdk/test_run.py::TestRun::test_method  # Single test
```

Pytest config: `pytest.ini` (uses IPython debugger). Python style: `ruff.toml` (120 char line length, single quotes, isort with `aim` as first-party).

## Architecture

### Two-Database Storage

Aim uses two databases together:

1. **RocksDB** (via `aimrocks` + Cython wrappers): Primary storage. Each `Run` gets its own RocksDB at `.aim/<run_hash>/`. Stores all sequence data (metrics, images, audio, text, figures, distributions) and run metadata in a tree-view key structure. An additional **union index** at `.aim/index/` aggregates all runs for fast cross-run queries.

2. **SQLite** (`run_metadata.sqlite`): Structured metadata — run names, descriptions, experiments, tags, notes, audit logs. Managed by SQLAlchemy ORM + Alembic migrations (`aim/web/migrations/`).

Cython modules (`aim/storage/*.pyx`) handle performance-critical encoding, hashing, and RocksDB access. **Never edit `.pyx` files without understanding Cython**; run `build_ext --inplace` after changes.

### Three Operational Modes

- **Local** (`aim up`): SDK writes directly to local `.aim/`, FastAPI serves UI from the same process.
- **Remote tracking** (`aim server`): Training clients connect via WebSocket to a central tracking server.
- **Programmatic** (`from aim import Repo`): SDK-only access for querying runs without the web server.

### Web Server (`aim/web/`)

FastAPI app (`aim/web/run.py`) with:
- REST routers per resource in `aim/web/api/` (runs, experiments, tags, projects, dashboards, reports, apps)
- Startup: runs Alembic DB migrations, starts `RepoIndexManager` thread (continuous RocksDB indexing), starts `RunStatusManager` thread (detects stalled runs)
- Streaming responses: metric/run search endpoints return newline-delimited streaming JSON for large datasets
- Query language: Python expressions evaluated via `RestrictedPython` (e.g., `run.hparams.lr > 0.001 and metric.name == 'loss'`)

### Frontend (`aim/web/ui/src/`)

React 17 + TypeScript. Key patterns:
- **No Redux**: custom observable model pattern (`services/models/`), `useModel()` hook for subscriptions
- Routes lazy-loaded (`routes/routes.tsx`), all page-level components in `pages/`
- `BaseExplorer` module (`modules/BaseExplorer/`) is the generic explorer framework used by new-style pages
- Metric data arrives as binary streams decoded in-browser by a custom decoder
- **Boards feature**: Python-in-browser via Pyodide (`services/pyodide/`)
- API client: `services/api/api.ts` (fetch wrapper) + `services/api/endpoints.ts` (URL constants)

### Authentication

**JWT-based multi-user auth is enabled on the `main-server` branch.** The system requires `AIM_SECRET_KEY` to be set before starting the server. CORS remains `allow_origins=['*']`.

Key pieces:
- `aim/web/api/auth/` — auth module: `jwt_utils.py` (token creation/decoding), `deps.py` (`get_current_user` FastAPI dependency), `views.py` (login/refresh endpoints)
- `aim/web/api/ownership.py` — `owned_or_public()` SQLAlchemy filter, `assert_owner()` 403 guard
- `aim/web/api/visibility.py` — `PUT /runs/{id}/visibility` and `PUT /experiments/{id}/visibility`
- `aim/web/api/settings/` — API token CRUD (`/settings/tokens`)
- `aim/web/api/admin/` — admin user management (`/admin/users`)
- `aim/web/run.py` — validates `AIM_SECRET_KEY` at startup
- Frontend sign-in page: `aim/web/ui/src/pages/SignIn/`
- Frontend settings page: `aim/web/ui/src/pages/Settings/`
- Frontend admin page: `aim/web/ui/src/pages/Admin/`

**Env vars:**
- `AIM_SECRET_KEY` (required) — JWT signing secret
- `AIM_API_TOKEN` — SDK transport auth token (preferred over legacy `AIM_RT_BEARER_TOKEN`)

**Initial setup:** Create the first admin user with `aim users create --username admin --admin`.

**Testing:** All auth tests in `tests/api/` run with `--noconftest` due to Cython imports in conftest. The `deps._get_db_session` function is monkey-patchable for test isolation — always import it via `from aim.web.api.auth import deps as auth_deps` and call `auth_deps._get_db_session()` (not a direct import) to ensure testability.

## Key Files & Locations

| What | Where |
|------|-------|
| SDK public API | `aim/__init__.py` |
| FastAPI app entry | `aim/web/run.py` |
| Web server configs / env vars | `aim/web/configs.py` |
| SDK env vars | `aim/sdk/configs.py` |
| SQLite ORM models | `aim/storage/structured/sql_engine/models.py` |
| SQLite migrations | `aim/web/migrations/versions/` |
| API routers | `aim/web/api/<resource>/views.py` |
| RocksDB container | `aim/storage/rockscontainer.pyx` |
| Union index | `aim/storage/union.pyx` |
| Background threads (indexing, stall detection) | `aim/web/run.py` startup section |
| CLI commands | `aim/cli/` |
| Remote transport | `aim/ext/transport/` |

## Data Model Summary

**Run** (core entity): identified by a content-addressed `hash`. Belongs to one optional **Experiment**. Has many **Tags** (M2M). Has many **Notes**. Tracks sequences: `Metric`, `Images`, `Audios`, `Distributions`, `Figures`, `Texts`.

**Repository** (`.aim/` directory): contains per-run RocksDB shards + union index + SQLite file. Not a multi-user concept in the current design — it's a single-directory, single-user store.

## Release Process

- Version string in `aim/VERSION`
- npm package `aim-ui` published separately and pinned in `setup.py`
- Build distribution: `python setup.py sdist bdist_wheel`
