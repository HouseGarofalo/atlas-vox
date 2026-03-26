# Atlas Vox Security Guide

> **Authentication, authorization, API key management, webhook signing, and production hardening.**

Atlas Vox supports flexible authentication modes -- from fully disabled (single-user homelab) to JWT + API key authentication for multi-user production deployments. This guide covers every security surface of the platform.

---

## Table of Contents

- [Authentication Modes](#authentication-modes)
  - [Disabled Mode (Default)](#disabled-mode-default)
  - [JWT Authentication](#jwt-authentication)
  - [API Key Authentication](#api-key-authentication)
- [API Key System](#api-key-system)
  - [Key Format](#key-format)
  - [Hashing (Argon2id)](#hashing-argon2id)
  - [Scopes](#scopes)
  - [Key Lifecycle](#key-lifecycle)
- [JWT Configuration](#jwt-configuration)
- [CORS Configuration](#cors-configuration)
- [MCP Authentication](#mcp-authentication)
- [Webhook Security](#webhook-security)
  - [HMAC-SHA256 Signing](#hmac-sha256-signing)
  - [Signature Verification](#signature-verification)
  - [SSRF Protection](#ssrf-protection)
- [File Upload Security](#file-upload-security)
- [Input Validation](#input-validation)
- [Production Hardening Checklist](#production-hardening-checklist)

---

## Authentication Modes

Atlas Vox supports three authentication modes, controlled by the `AUTH_DISABLED` environment variable and the presence of credentials in the `Authorization` header.

```mermaid
flowchart TD
    REQ[Incoming Request] --> CHECK{AUTH_DISABLED?}
    CHECK -->|true| DEFAULT["Return default admin user<br/>{sub: 'local-user', scopes: ['admin']}"]
    CHECK -->|false| HEADER{Authorization<br/>header present?}
    HEADER -->|No| REJECT["401 Unauthorized<br/>Missing authorization header"]
    HEADER -->|Yes| SCHEME{Starts with<br/>'Bearer '?}
    SCHEME -->|Yes| JWT["Decode JWT token<br/>Validate signature + expiry"]
    SCHEME -->|No| REJECT2["401 Unauthorized<br/>Invalid authorization scheme"]
    JWT -->|Valid| CLAIMS[Return claims dict]
    JWT -->|Invalid| REJECT3["401 Unauthorized<br/>Invalid or expired token"]
```

### Disabled Mode (Default)

When `AUTH_DISABLED=true` (the default), all authentication is bypassed. Every request receives a synthetic admin identity:

```python
{"sub": "local-user", "scopes": ["admin"]}
```

This mode is designed for:
- Local development
- Single-user homelab deployments
- Testing and prototyping

> **Warning:** Never use disabled mode in a deployment accessible from the public internet.

---

### JWT Authentication

When `AUTH_DISABLED=false`, the backend expects a JWT bearer token:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token creation:**

```python
from app.core.security import create_access_token

token = create_access_token(
    data={"sub": "user@example.com", "scopes": ["read", "write"]},
    expires_delta=timedelta(hours=8),
)
```

**Token validation flow:**

1. Extract the `Bearer` prefix from the `Authorization` header
2. Decode the JWT using the configured secret key and algorithm
3. Validate the `exp` (expiration) claim
4. Return the decoded claims as a Python dict

**Relevant configuration:**

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET_KEY` | `change-me-in-production` | HMAC signing key |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `JWT_EXPIRE_MINUTES` | `1440` (24 hours) | Default token lifetime |

---

### API Key Authentication

API keys provide programmatic access to the REST API and MCP server. They are validated by hashing the provided key and comparing against stored Argon2id hashes.

The API key flow is used primarily for:
- MCP server connections
- CI/CD pipeline integration
- Third-party application access

---

## API Key System

### Key Format

API keys use a recognizable prefix format:

```
avx_<48 random characters>
```

The `avx_` prefix makes Atlas Vox keys easy to identify in secrets scanners and configuration files.

**Example:**

```
avx_7Kj2mNpQ8rStUvWxYz1aBcDeFgHiJkLmNoPqRsTuVw
```

### Hashing (Argon2id)

API keys are never stored in plaintext. Atlas Vox uses **Argon2id** -- the winner of the Password Hashing Competition and the recommended algorithm for password/secret hashing.

```python
from argon2 import PasswordHasher

ph = PasswordHasher()

# At creation time -- hash the key
key_hash = ph.hash(raw_key)  # Stored in database

# At validation time -- verify against hash
is_valid = ph.verify(key_hash, provided_key)  # Returns True/False
```

**Why Argon2id (not bcrypt or SHA-256):**

| Algorithm | Brute-force resistance | Memory-hard | Recommended |
|---|---|---|---|
| SHA-256 | Low (fast) | No | No |
| bcrypt | Good | No | Acceptable |
| **Argon2id** | **Excellent** | **Yes** | **Yes (OWASP)** |

Argon2id combines Argon2i (side-channel resistant) and Argon2d (GPU-resistant) for the best of both properties.

### Scopes

Each API key has a set of permission scopes stored as a comma-separated string:

| Scope | Allows |
|---|---|
| `read` | Read profiles, providers, presets, training status |
| `write` | Create/update/delete profiles, presets |
| `synthesize` | Text-to-speech synthesis, comparison |
| `train` | Upload samples, start/cancel training jobs |
| `admin` | All operations including API key management |

**Default scopes for new keys:** `read,synthesize`

**Scope validation:** When creating a key, the API validates all requested scopes against the `VALID_SCOPES` set and rejects unknown scopes with a 400 error.

### Key Lifecycle

```mermaid
sequenceDiagram
    participant User
    participant API as POST /api/v1/api-keys
    participant DB as Database

    User->>API: Create key (name, scopes)
    API->>API: Generate avx_ + 48 random chars
    API->>API: Hash with Argon2id
    API->>DB: Store (name, hash, prefix, scopes)
    API-->>User: Return full key (shown ONCE)

    Note over User: User stores key securely

    User->>API: Use key in Authorization header
    API->>DB: Load all active key hashes
    API->>API: Verify against each hash
    API-->>User: 200 OK or 401 Unauthorized

    User->>API: DELETE /api/v1/api-keys/{id}
    API->>DB: Set active=false
    API-->>User: 204 No Content
```

**Key properties stored in the database:**

| Column | Type | Description |
|---|---|---|
| `id` | `str(36)` | UUID primary key |
| `name` | `str(200)` | Human-readable name |
| `key_hash` | `str(500)` | Argon2id hash of the full key |
| `key_prefix` | `str(10)` | First 12 characters (e.g., `avx_7Kj2mNpQ`) for display |
| `scopes` | `text` | Comma-separated scope list |
| `active` | `bool` | Whether the key is active (revocation sets to false) |
| `last_used_at` | `datetime?` | Last usage timestamp |
| `created_at` | `datetime` | Creation timestamp |

> **Important:** The full key is returned exactly once at creation time. It cannot be retrieved again. If lost, revoke the key and create a new one.

---

## JWT Configuration

| Variable | Type | Default | Security Notes |
|---|---|---|---|
| `JWT_SECRET_KEY` | `str` | `change-me-in-production` | **Must** be changed for any non-local deployment. Use at least 32 bytes of randomness. |
| `JWT_ALGORITHM` | `str` | `HS256` | HMAC-SHA256. Sufficient for single-service deployments. Use RS256 for multi-service architectures. |
| `JWT_EXPIRE_MINUTES` | `int` | `1440` | 24 hours. Reduce for higher-security environments (e.g., 60-480 minutes). |

**Generate a secure secret:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Token structure (claims):**

```json
{
  "sub": "user@example.com",
  "scopes": ["read", "write", "synthesize"],
  "exp": 1711411200
}
```

The `exp` claim is set automatically based on `JWT_EXPIRE_MINUTES`. The `python-jose` library handles encoding and decoding.

---

## CORS Configuration

Cross-Origin Resource Sharing is configured in the FastAPI application:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

| Setting | Value | Description |
|---|---|---|
| `allow_origins` | From `CORS_ORIGINS` env | Whitelist of allowed origins |
| `allow_credentials` | `True` | Allow cookies and auth headers |
| `allow_methods` | `GET, POST, PUT, DELETE, OPTIONS` | Allowed HTTP methods |
| `allow_headers` | `Authorization, Content-Type` | Allowed request headers |

**Development defaults:** `http://localhost:3000`, `http://localhost:5173`

**Production:** Set `CORS_ORIGINS` to your exact frontend domain(s):

```env
CORS_ORIGINS=["https://vox.example.com"]
```

> **Security Warning:** Never use `["*"]` as the CORS origin in production. This allows any website to make authenticated requests to your API.

---

## MCP Authentication

The MCP endpoints (`/mcp/sse` and `/mcp/message`) use a separate authentication path that mirrors the REST API:

1. When `AUTH_DISABLED=true`: no authentication required
2. When `AUTH_DISABLED=false`: requires a valid API key in the `Authorization` header

```
Authorization: Bearer avx_your_api_key_here
```

**Validation flow:**

1. Extract the key from `Bearer <key>` format
2. Load all active `ApiKey` records from the database
3. Verify the provided key against each stored Argon2id hash
4. Accept if any match; reject with 401 otherwise

Both the SSE connection endpoint and the message endpoint perform this check independently.

---

## Webhook Security

### HMAC-SHA256 Signing

When a webhook subscription includes a `secret`, all outgoing payloads are signed with HMAC-SHA256.

**Signature generation:**

```python
import hmac
import hashlib

signature = hmac.new(
    secret.encode(),    # Webhook secret as bytes
    payload.encode(),   # JSON payload as bytes
    hashlib.sha256,
).hexdigest()
```

**Delivered header:**

```
X-Atlas-Vox-Signature: sha256=<hex digest>
```

### Signature Verification

Receiving services should verify the webhook signature like this:

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature_header: str, secret: str) -> bool:
    """Verify an Atlas Vox webhook signature."""
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    received = signature_header.removeprefix("sha256=")

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, received)
```

**Example verification in a Flask receiver:**

```python
from flask import Flask, request, abort

app = Flask(__name__)
WEBHOOK_SECRET = "your-shared-secret"

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    signature = request.headers.get("X-Atlas-Vox-Signature", "")
    if not verify_webhook(request.data, signature, WEBHOOK_SECRET):
        abort(403)

    data = request.json
    event = data["event"]
    # Handle training.completed, training.failed, etc.
    return "OK", 200
```

### SSRF Protection

The webhook dispatcher includes built-in SSRF (Server-Side Request Forgery) protection to prevent webhooks from being used to probe internal networks.

**Blocked destinations:**

| Category | Blocked Patterns |
|---|---|
| Localhost | `localhost`, `127.0.0.1`, `0.0.0.0`, `::1`, `[::1]` |
| Private networks (RFC 1918) | `10.*`, `172.16-31.*`, `192.168.*` |
| Link-local | `169.254.*` |
| Internal domains | `*.internal`, `*.local` |

**Additional protections:**

| Protection | Implementation |
|---|---|
| Redirect following | Disabled (`follow_redirects=False`) |
| Timeout | 10 seconds per request |
| Error exposure | Generic "Delivery failed" message to the caller; detailed error logged server-side |

---

## File Upload Security

Audio sample uploads are protected by multiple layers:

### Format Whitelist

Only these audio formats are accepted:

| Format | Extension |
|---|---|
| WAV | `.wav` |
| MP3 | `.mp3` |
| FLAC | `.flac` |
| Ogg Vorbis | `.ogg` |
| M4A/AAC | `.m4a` |

Any other extension is rejected with a 400 error:

```
Unsupported format 'exe'. Allowed: flac, m4a, mp3, ogg, wav
```

### Size Limits

| Limit | Value | Description |
|---|---|---|
| Per-file maximum | **50 MB** | Applied by reading the full content and checking length |
| Files per upload | **20** | Maximum number of files in a single upload request |

Files exceeding the size limit receive a 413 response:

```
File 'large_recording.wav' exceeds 50MB limit
```

### File Storage

- Uploaded files are renamed to a random 12-character hex ID + original extension (e.g., `a1b2c3d4e5f6.wav`)
- Original filenames are preserved in the database for display but never used for file system operations
- Files are stored in isolated profile directories: `storage/samples/<profile_id>/`

---

## Input Validation

All request/response data passes through **Pydantic v2** models, providing:

| Protection | Mechanism |
|---|---|
| **Type validation** | All fields are strongly typed (string, int, float, etc.) |
| **Required fields** | Missing required fields return 422 with field-level errors |
| **Enum constraints** | Status fields, actions, scopes validated against allowed values |
| **Range validation** | Numeric fields (speed, pitch, volume) constrained to valid ranges |
| **String length** | Database column lengths enforce maximum sizes |
| **JSON parsing** | Malformed JSON returns automatic 422 error |

**Example: API key scope validation:**

```python
VALID_SCOPES = {"read", "write", "synthesize", "train", "admin"}

invalid = set(data.scopes) - VALID_SCOPES
if invalid:
    raise HTTPException(
        status_code=400,
        detail=f"Invalid scopes: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_SCOPES))}",
    )
```

**Example: Webhook event validation:**

```python
VALID_EVENTS = {"training.completed", "training.failed", "*"}

invalid = set(data.events) - VALID_EVENTS
if invalid:
    raise HTTPException(
        status_code=400,
        detail=f"Invalid events: {', '.join(invalid)}",
    )
```

---

## Production Hardening Checklist

Use this checklist before deploying Atlas Vox to a production or internet-facing environment.

### Authentication and Secrets

- [ ] **Set `AUTH_DISABLED=false`** -- enable authentication
- [ ] **Change `JWT_SECRET_KEY`** -- generate a cryptographically random key (at least 32 bytes)
- [ ] **Reduce `JWT_EXPIRE_MINUTES`** -- lower from 1440 (24h) to 60-480 based on your threat model
- [ ] **Create scoped API keys** -- use minimal scopes for each integration (avoid `admin` where possible)
- [ ] **Rotate API keys periodically** -- revoke old keys and issue new ones on a schedule

### Network and Transport

- [ ] **Enable HTTPS/TLS** -- terminate TLS at your reverse proxy (nginx, Caddy, Traefik)
- [ ] **Restrict CORS origins** -- set `CORS_ORIGINS` to your exact frontend domain(s)
- [ ] **Bind to localhost** -- set `HOST=127.0.0.1` if behind a reverse proxy
- [ ] **Use a reverse proxy** -- nginx, Caddy, or Traefik with rate limiting and request size limits
- [ ] **Firewall Redis** -- ensure Redis is not exposed to the internet

### Database

- [ ] **Use PostgreSQL** -- migrate from SQLite for concurrent access and better reliability
- [ ] **Use Alembic migrations** -- do not rely on auto-create in production (`is_production` disables it)
- [ ] **Encrypt database credentials** -- use secrets management (Vault, AWS Secrets Manager, etc.)
- [ ] **Enable connection encryption** -- use `sslmode=require` in PostgreSQL URL if over network

### Storage

- [ ] **Secure the storage directory** -- restrict filesystem permissions to the application user
- [ ] **Back up storage** -- audio samples and model files are not stored in the database
- [ ] **Monitor disk usage** -- synthesized audio and training artifacts can grow large

### Operational

- [ ] **Set `APP_ENV=production`** -- disables auto-table creation and enables production behaviors
- [ ] **Set `DEBUG=false`** -- reduces log verbosity and disables debug features
- [ ] **Use structured logging** -- set `LOG_FORMAT=json` for log aggregation systems
- [ ] **Monitor webhook delivery** -- check logs for `webhook_delivery_failed` events
- [ ] **Review API key usage** -- monitor `last_used_at` and revoke unused keys

### Provider Security

- [ ] **Secure cloud API keys** -- store `ELEVENLABS_API_KEY` and `AZURE_SPEECH_KEY` in secrets management
- [ ] **Limit provider access** -- disable providers you do not use (e.g., `KOKORO_ENABLED=false`)
- [ ] **Isolate GPU containers** -- if using `docker_gpu` mode, ensure containers run with minimal privileges

### OpenAPI Documentation

- [ ] **Consider disabling Swagger UI** -- in production, set `docs_url=None` and `redoc_url=None` in `main.py` to prevent API exploration by unauthorized parties
