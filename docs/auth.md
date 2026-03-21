# Aim Authentication Guide

This guide describes the multi-user authentication system added to Aim.

## Initial Setup

### 1. Set the secret key

The server requires a strong secret key for JWT signing. Set it before starting:

```bash
export AIM_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

Add this to your shell profile or deployment environment.

### 2. Create the first admin user

```bash
aim users create --username admin --password <password> --admin
```

Other CLI commands:

```bash
aim users list                                  # list all users
aim users reset-password --username <user>      # interactive password reset
```

### 3. Start the server

```bash
aim up
```

The server will refuse to start without `AIM_SECRET_KEY`.

---

## Login Flow

### Web UI

Navigate to `http://localhost:43800`. You'll be redirected to `/sign-in`. Enter username and password.

### API (programmatic)

```bash
curl -X POST http://localhost:43800/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username": "admin", "password": "yourpassword"}'
```

Response:
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

Use the access token in subsequent requests:

```bash
curl http://localhost:43800/api/projects/ \
  -H 'Authorization: Bearer <access_token>'
```

Access tokens expire in 8 hours (configurable via `AIM_ACCESS_TOKEN_EXPIRE_HOURS`). Refresh tokens expire in 7 days (`AIM_REFRESH_TOKEN_EXPIRE_DAYS`).

---

## API Tokens

For long-lived programmatic access (CI/CD, SDK), create personal API tokens in the **Settings** page or via API:

```bash
# Create a token
curl -X POST http://localhost:43800/api/settings/tokens \
  -H 'Authorization: Bearer <jwt>' \
  -H 'Content-Type: application/json' \
  -d '{"name": "ci-pipeline"}'
```

Response includes the raw token (`aim_tok_<32 hex chars>`) — **shown once only**.

```bash
# Use the API token
curl http://localhost:43800/api/projects/ \
  -H 'Authorization: Bearer aim_tok_<hex>'
```

### SDK remote tracking

Set `AIM_API_TOKEN` when using the remote tracking server:

```bash
export AIM_API_TOKEN=aim_tok_<hex>
python train.py  # SDK will use this token automatically
```

---

## Data Visibility

Each run and experiment has an owner (`user_id`) and a visibility flag (`is_public`).

| Visibility | Owner can see | Others can see |
|------------|--------------|----------------|
| Private (default) | Yes | No |
| Public | Yes | Yes |
| Legacy (no owner) | All users | All users |

Toggle visibility from the detail page (owner only) or via API:

```bash
curl -X PUT http://localhost:43800/api/runs/<hash>/visibility \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"is_public": true}'
```

---

## Admin Operations

Admin users can manage all users via the **Admin → Users** page or API:

```bash
# List users
curl http://localhost:43800/api/admin/users -H 'Authorization: Bearer <admin-jwt>'

# Create user
curl -X POST http://localhost:43800/api/admin/users \
  -H 'Authorization: Bearer <admin-jwt>' \
  -H 'Content-Type: application/json' \
  -d '{"username": "alice", "password": "pass", "is_admin": false}'

# Reset password
curl -X PUT http://localhost:43800/api/admin/users/<id>/reset-password \
  -H 'Authorization: Bearer <admin-jwt>' \
  -H 'Content-Type: application/json' \
  -d '{"password": "newpass"}'
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AIM_SECRET_KEY` | **Yes** | — | JWT signing secret (use 32+ random bytes) |
| `AIM_ACCESS_TOKEN_EXPIRE_HOURS` | No | `8` | Access token lifetime |
| `AIM_REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `AIM_API_TOKEN` | No | — | SDK transport token (overrides `AIM_RT_BEARER_TOKEN`) |
| `AIM_RT_BEARER_TOKEN` | No | — | Legacy remote tracking token (still supported) |
