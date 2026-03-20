# Aim SaaS Multi-User Transformation Design

**Date:** 2026-03-20
**Status:** Approved
**Scope:** Internal small team deployment

---

## Overview

Transform Aim from a single-tenant self-hosted tool into a multi-user system supporting authentication, per-user data isolation, and public/private visibility controls. The target deployment is a small internal team (not a public SaaS).

**Out of scope (future work):**
- Organization/workspace hierarchy
- Per-user sharing (invite specific users)
- Public share links (unauthenticated access)
- SSO / OAuth login

---

## Approach

**Option A selected:** Add user ownership to the existing SQLite metadata layer and enforce access control at the API layer. The RocksDB storage layer is unchanged. All filtering happens in FastAPI before data is returned.

This approach was chosen over per-user RocksDB directories (too complex for cross-user public queries) and PostgreSQL migration (unnecessary infrastructure overhead for a small team).

---

## Data Model

### New Table: `aim_user`

Named `aim_user` (not `user`) to avoid the SQL reserved keyword.

```sql
CREATE TABLE aim_user (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,       -- bcrypt
    is_admin      BOOLEAN DEFAULT FALSE,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Modified Table: `run`

New columns added via Alembic migration:

```sql
ALTER TABLE run ADD COLUMN user_id  INTEGER REFERENCES aim_user(id);
ALTER TABLE run ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT FALSE;
```

### Modified Table: `experiment`

```sql
ALTER TABLE experiment ADD COLUMN user_id  INTEGER REFERENCES aim_user(id);
ALTER TABLE experiment ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT FALSE;
```

### New Table: `api_token` (Phase 3)

```sql
CREATE TABLE api_token (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES aim_user(id),
    name       TEXT NOT NULL,
    token_hash TEXT UNIQUE NOT NULL,   -- SHA-256 of the raw token
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Migration Strategy

A single Alembic migration adds all new tables and columns. Existing `run` and `experiment` rows get `user_id = NULL` and `is_public = FALSE`. Rows with `user_id IS NULL` are treated as legacy data visible to all authenticated users, providing a smooth upgrade path without data loss.

---

## Authentication

### Endpoints

```
POST /api/auth/login     { username, password } → { access_token, refresh_token }
POST /api/auth/refresh   { refresh_token }      → { access_token }
```

- `access_token`: JWT, 8-hour expiry, signed with `AIM_SECRET_KEY` env var (required; server refuses to start if unset)
- `refresh_token`: JWT, 7-day expiry, same signing key
- Passwords stored as bcrypt hashes
- Both tokens passed as JSON body (not cookies) to align with the existing frontend `AuthToken` scaffolding

**No logout endpoint.** The frontend clears tokens from `localStorage` on logout. Token blacklisting is out of scope.

### JWT Secret Key

Configured via `AIM_SECRET_KEY` environment variable. The server raises a startup error if this variable is missing. There is no auto-generated fallback (which would invalidate all tokens on restart).

### FastAPI Dependencies

Single reusable dependency in `aim/web/api/auth/deps.py`:

```python
async def get_current_user(request: Request) -> AimUser:
    """
    Required auth — raises HTTP 401 if not authenticated.
    Accepts two credential formats:
      1. Authorization: Bearer <jwt>          (web UI)
      2. Authorization: Bearer aim_tok_<hex>  (Personal API Token, Phase 3)
    Identifies token type by 'aim_tok_' prefix.
    """
```

Both credential paths resolve to the same `AimUser` object. Business logic is credential-type agnostic. No `get_current_user_optional` is defined in these three phases.

### Auth Injection Strategy

Auth is applied at the `api_app` level in `aim/web/api/__init__.py`:

```python
api_app = FastAPI(dependencies=[Depends(get_current_user)])
```

This covers all routers (runs, experiments, projects, tags, dashboards, reports, apps) without per-router changes.

### Admin CLI

```bash
aim users create --username alice [--password xxx] [--admin]
aim users list
aim users reset-password --username alice --password yyy
```

Implemented as `aim/cli/users.py`, registered under the existing `aim` CLI group.

---

## Data Access Control

### Query Filtering

All list/search queries on `run` and `experiment` apply this filter automatically:

```python
# aim/web/api/utils/ownership.py
def owned_or_public(query, model, current_user: AimUser):
    return query.filter(
        (model.user_id == current_user.id) |
        (model.is_public == True) |
        (model.user_id == None)   # legacy data
    )
```

This helper is called from a shared base layer, not repeated in individual view functions.

### Write Protection

Mutating operations (update, delete, archive) verify ownership before proceeding:

```python
def assert_owner(obj, current_user: AimUser):
    if obj.user_id is not None and obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
```

`user_id IS NULL` (legacy) records are writable by any authenticated user during the transition period.

### Visibility Toggle API

```
PUT /api/runs/{run_id}/visibility        { is_public: bool }
PUT /api/experiments/{exp_id}/visibility { is_public: bool }
```

Owner-only. Returns 403 for non-owners. `is_public` defaults to `false` for all new runs/experiments regardless of creation method; visibility can only be changed via this API from the web UI.

### New Run Ownership (Remote Tracking)

When a run is created via `aim server`, `user_id` must be propagated from the HTTP transport layer into the run creation call. The implementation path:

1. `aim/ext/transport/server.py`: validate the Bearer token from the request header, resolve to an `AimUser`, attach `user_id` to the request context
2. `aim/ext/transport/handlers.py`: `get_structured_run()` reads `user_id` from context and passes it to `repo.request_props(hash_, read_only, created_at, user_id=user_id)`
3. `aim/sdk/repo.py`: `request_props` forwards `user_id` to the structured DB `create_run()` call
4. `aim/storage/structured/db.py`: `create_run()` accepts an optional `user_id` parameter and writes it to the `run` row

Runs created via local file system access (`aim.Run(repo='/path')`) retain `user_id = NULL`.

---

## Personal API Token (Phase 3)

### Token Endpoints

```
GET    /api/settings/tokens             → list user's tokens (id, name, created_at; no hash)
POST   /api/settings/tokens             { name } → { id, name, token, created_at }  (token shown once)
DELETE /api/settings/tokens/{token_id}  → 204
```

Users generate tokens in the web UI settings page (`/settings`). The raw token value (format: `aim_tok_<32 random hex chars>`) is returned only in the `POST` response and never stored. Only the SHA-256 hash is persisted in `api_token`.

### Python SDK Usage

```bash
export AIM_API_TOKEN=aim_tok_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The `aim server` remote tracking client (`aim/ext/transport/client.py`) reads `AIM_API_TOKEN` from the environment in `Client.__init__` and sets it in `self.request_headers`:

```python
token = os.environ.get('AIM_API_TOKEN')
if token:
    self.request_headers['Authorization'] = f'Bearer {token}'
```

The existing `AIM_RT_BEARER_TOKEN` constant in `aim/ext/transport/config.py` is replaced by `AIM_API_TOKEN`. The `get_current_user` dependency identifies Personal API Tokens by the `aim_tok_` prefix and validates them against SHA-256 hashes in the `api_token` table.

---

## Frontend Changes

### New Pages

| Route | Purpose |
|-------|---------|
| `/sign-in` | Username/password login form |
| `/settings` | Personal API token management (Phase 3), change password |
| `/admin/users` | Create users, reset passwords (admin only) |

### Modified Behavior

- **App startup**: Validates `access_token` from `localStorage` on load; attempts refresh via `POST /api/auth/refresh` with stored `refresh_token`; redirects to `/sign-in` if both are missing or expired
- **Run / Experiment detail page**: Owner sees a public/private toggle switch
- **All list/explorer pages**: No UI changes — filtering is backend-only

### Reusing Existing Scaffolding

The frontend already has `AuthToken` types, `getAPIAuthToken()`, `setAuthToken()`, `removeAuthToken()`, and `AUTH` endpoint constants in `services/api/`. The existing refresh logic in `api.ts` uses a GET request; this will be updated to `POST /api/auth/refresh` with the `refresh_token` in the request body to match the spec.

---

## Implementation Phases

### Phase 1 — Authentication Foundation

1. Alembic migration: `aim_user` table + ownership columns on `run` and `experiment`
2. `aim users` CLI commands (create / list / reset-password)
3. `POST /api/auth/login` and `POST /api/auth/refresh` endpoints
4. `get_current_user` FastAPI dependency, applied to `api_app` in `aim/web/api/__init__.py`
5. Frontend: `/sign-in` page, JWT storage in `localStorage`, token refresh on startup, redirect-to-sign-in guard

**Deliverable:** Aim requires login. All existing data remains visible to all authenticated users.

### Phase 2 — Data Isolation and Visibility

1. `owned_or_public` filter applied to all run/experiment list and search queries
2. Owner assertion on all write operations
3. `PUT /api/runs/{id}/visibility` and `PUT /api/experiments/{id}/visibility` endpoints
4. Frontend: public/private toggle on run and experiment detail pages
5. New run ownership assigned at creation time via remote tracking server (propagation path described above)

**Deliverable:** Each user sees only their own runs + public runs. Visibility is user-controlled via web UI.

### Phase 3 — Personal API Token

1. `api_token` table + Alembic migration
2. `GET/POST/DELETE /api/settings/tokens` endpoints
3. `get_current_user` extended to validate `aim_tok_` Bearer tokens against `api_token` table
4. `aim/ext/transport/client.py` reads `AIM_API_TOKEN`, sets `Authorization` header; retire `AIM_RT_BEARER_TOKEN`
5. Frontend settings page: list, generate, and revoke tokens

**Deliverable:** Python SDK and scripts authenticate via API token without interactive login.

---

## Key Files to Modify or Create

| File | Change |
|------|--------|
| `aim/storage/structured/sql_engine/models.py` | Add `AimUser`, `ApiToken` ORM models; add `user_id`, `is_public` to `Run`, `Experiment` |
| `aim/web/migrations/versions/` | New Alembic migration: `aim_user` table, ownership columns, `api_token` table (Phase 3) |
| `aim/web/api/__init__.py` | Apply `get_current_user` dependency to `api_app`; register auth router |
| `aim/web/api/auth/` | New module: login/refresh endpoints, JWT utils, `get_current_user` dependency |
| `aim/web/api/utils/ownership.py` | New file: `owned_or_public`, `assert_owner` helpers |
| `aim/web/api/runs/views.py` | Apply ownership filter; add visibility endpoint; add owner assertion on writes |
| `aim/web/api/experiments/views.py` | Same as runs |
| `aim/web/api/settings/` | New module: API token CRUD endpoints (Phase 3) |
| `aim/web/run.py` | Read and validate `AIM_SECRET_KEY` at startup |
| `aim/cli/users.py` | New CLI module for user management |
| `aim/cli/__init__.py` | Register `users` command group |
| `aim/ext/transport/server.py` | Validate Bearer token, attach `user_id` to request context |
| `aim/ext/transport/handlers.py` | Pass `user_id` from context to `repo.request_props()` |
| `aim/ext/transport/client.py` | Read `AIM_API_TOKEN`, set `Authorization` header; retire `AIM_RT_BEARER_TOKEN` |
| `aim/sdk/repo.py` | Forward `user_id` in `request_props` |
| `aim/storage/structured/db.py` | Accept `user_id` in `create_run()` |
| `aim/web/ui/src/pages/SignIn/` | New sign-in page component (route: `/sign-in`) |
| `aim/web/ui/src/pages/Settings/` | New settings page (API token management, Phase 3) |
| `aim/web/ui/src/pages/Admin/` | New admin user management page |
| `aim/web/ui/src/services/api/api.ts` | Update refresh to `POST` with body; wire token storage to real JWT flow |
| `aim/web/ui/src/App.tsx` | Add auth guard, token refresh on startup, route to `/login` |
