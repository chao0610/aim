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

### New Table: `user`

```sql
CREATE TABLE user (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,       -- bcrypt
    is_admin     BOOLEAN DEFAULT FALSE,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Modified Table: `run`

New columns added via Alembic migration:

```sql
ALTER TABLE run ADD COLUMN user_id  INTEGER REFERENCES user(id);
ALTER TABLE run ADD COLUMN is_public BOOLEAN DEFAULT FALSE;
```

### Modified Table: `experiment`

```sql
ALTER TABLE experiment ADD COLUMN user_id  INTEGER REFERENCES user(id);
ALTER TABLE experiment ADD COLUMN is_public BOOLEAN DEFAULT FALSE;
```

### New Table: `api_token` (Phase 3)

```sql
CREATE TABLE api_token (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES user(id),
    name       TEXT NOT NULL,
    token_hash TEXT UNIQUE NOT NULL,   -- SHA-256 of the raw token
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Migration Strategy

A single Alembic migration adds all new columns. Existing rows get `user_id = NULL` and `is_public = FALSE`. Rows with `user_id IS NULL` are treated as legacy data visible to all authenticated users (smooth upgrade path).

---

## Authentication

### Endpoints

```
POST /api/auth/login     { username, password } → { access_token, refresh_token }
POST /api/auth/refresh   { refresh_token }      → { access_token }
POST /api/auth/logout    (client clears tokens)
```

- `access_token`: JWT, 8-hour expiry
- `refresh_token`: JWT, 7-day expiry
- Passwords stored as bcrypt hashes

### FastAPI Dependencies

Two reusable dependencies in `aim/web/api/auth/deps.py`:

```python
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Required auth — raises HTTP 401 if not authenticated."""

async def get_current_user_optional(token: str = ...) -> User | None:
    """Optional auth — returns None if not authenticated (reserved for future public links)."""
```

`get_current_user` accepts two credential types:
1. **JWT** — issued by `/api/auth/login`, short-lived, used by the web UI
2. **Personal API Token** — long-lived, used by Python SDK and scripts, passed as `Authorization: Bearer aim_tok_<value>`

Both paths resolve to the same `User` object. Business logic is credential-type agnostic.

All existing routers receive `get_current_user` via `dependencies=[Depends(get_current_user)]` at the router level, requiring no changes to individual view functions.

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
def owned_or_public(query, model, current_user: User):
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
def assert_owner(obj, current_user: User):
    if obj.user_id is not None and obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
```

`user_id IS NULL` (legacy) records are writable by any authenticated user during the transition period.

### Visibility Toggle API

```
PUT /api/runs/{run_id}/visibility        { is_public: bool }
PUT /api/experiments/{exp_id}/visibility { is_public: bool }
```

Owner-only. Returns 403 for non-owners.

### New Run Ownership

When a run is created via `aim server` (remote tracking), the authenticated user's `user_id` is written to `run.user_id` at creation time. Runs created via local file system access retain `user_id = NULL`.

---

## Personal API Token (Phase 3)

Users generate tokens in the web UI settings page. The raw token value (format: `aim_tok_<32 random hex chars>`) is shown once and never stored. Only the SHA-256 hash is persisted in `api_token`.

**Python SDK usage:**

```bash
export AIM_API_TOKEN=aim_tok_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

The `aim server` remote tracking client reads this env var and sends it as `Authorization: Bearer <token>`. The existing `AIM_RT_BEARER_TOKEN` mechanism is unified into this new token system.

---

## Frontend Changes

### New Pages

| Route | Purpose |
|-------|---------|
| `/login` | Username/password login form |
| `/settings` | Personal API token management, change password |
| `/admin/users` | Create users, reset passwords (admin only) |

### Modified Behavior

- **App startup**: Validates token on load; redirects to `/login` if missing or expired
- **Run / Experiment detail page**: Owner sees a public/private toggle switch
- **All list/explorer pages**: No UI changes — filtering is backend-only

### Reusing Existing Scaffolding

The frontend already has `AuthToken` types, `getAPIAuthToken()`, and `AUTH` endpoint constants in `services/api/`. These stubs are wired up to the real login flow with minimal changes.

---

## Implementation Phases

### Phase 1 — Authentication Foundation

1. Alembic migration: `user` table + ownership columns on `run` and `experiment`
2. `aim users` CLI commands (create / list / reset-password)
3. `POST /api/auth/login` and `POST /api/auth/refresh` endpoints
4. `get_current_user` FastAPI dependency, injected into all existing routers
5. Frontend: login page, JWT storage in `localStorage`, redirect-to-login guard

**Deliverable:** Aim requires login. All existing data remains visible to all authenticated users.

### Phase 2 — Data Isolation and Visibility

1. `owned_or_public` filter applied to all run/experiment list and search queries
2. Owner assertion on all write operations
3. `PUT /api/runs/{id}/visibility` and `PUT /api/experiments/{id}/visibility` endpoints
4. Frontend: public/private toggle on run and experiment detail pages
5. New run ownership assigned at creation time via remote tracking server

**Deliverable:** Each user sees only their own runs + public runs. Visibility is user-controlled.

### Phase 3 — Personal API Token

1. `api_token` table + Alembic migration
2. Token generation/revocation endpoints + frontend settings page
3. `get_current_user` extended to validate Bearer API tokens
4. `aim server` updated to read `AIM_API_TOKEN` env var

**Deliverable:** Python SDK and scripts authenticate via API token without interactive login.

---

## Key Files to Modify or Create

| File | Change |
|------|--------|
| `aim/storage/structured/sql_engine/models.py` | Add `User`, `ApiToken` models; add `user_id`, `is_public` to `Run`, `Experiment` |
| `aim/web/migrations/versions/` | New Alembic migration file |
| `aim/web/api/auth/` | New module: login endpoints, JWT utils, `get_current_user` dependency |
| `aim/web/api/utils/ownership.py` | New file: `owned_or_public`, `assert_owner` helpers |
| `aim/web/api/runs/views.py` | Inject auth dependency; apply ownership filter; add visibility endpoint |
| `aim/web/api/experiments/views.py` | Same as runs |
| `aim/web/run.py` | Register auth router |
| `aim/cli/users.py` | New CLI module for user management |
| `aim/cli/__init__.py` | Register `users` command group |
| `aim/ext/transport/` | Read `AIM_API_TOKEN`, pass as Bearer on remote tracking requests |
| `aim/web/ui/src/pages/Login/` | New login page component |
| `aim/web/ui/src/pages/Settings/` | New settings page (API token management) |
| `aim/web/ui/src/pages/Admin/` | New admin user management page |
| `aim/web/ui/src/services/api/api.ts` | Wire `getAPIAuthToken()` to JWT storage |
| `aim/web/ui/src/App.tsx` | Add auth guard, route to `/login` |
