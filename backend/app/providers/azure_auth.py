"""Azure Entra ID authentication manager for containerised deployments.

Provides two authentication paths that work inside Docker:

1. **Device Code Flow** — interactive login via any browser.  The user
   clicks *Login with Azure* in the UI, receives a code and URL, opens
   the URL on *any* device, enters the code, and signs in.  The resulting
   tokens are cached in Redis so both the FastAPI backend and Celery
   worker containers can use them.

2. **Service Principal** — persistent, non-interactive.  The user enters
   ``tenant_id``, ``client_id``, and ``client_secret`` in the provider
   config UI.  Tokens are acquired silently via ``ClientSecretCredential``.

The module exposes a singleton ``azure_auth_manager`` accessed via
:func:`get_azure_auth_manager`.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

# Well-known Microsoft first-party public clients for device code flow.
# Tried in order until one succeeds — different tenants allow different apps.
_WELL_KNOWN_PUBLIC_CLIENTS = [
    # Microsoft Azure PowerShell — pre-consented in most tenants
    "1950a258-227b-4e31-a9cf-717495945fc2",
    # Azure CLI — common but some restricted tenants block it
    "04b07795-a710-4e7b-9e71-ecb5e6134648",
    # Microsoft Graph Command Line Tools
    "14d82eec-204b-4c2f-b7e8-296a70dab67e",
]

# Token scope for all Cognitive Services APIs.
_COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"

# Redis key prefix
_REDIS_PREFIX = "atlas:azure:auth"


@dataclass
class DeviceCodeInfo:
    """State of an in-progress device code flow."""
    user_code: str = ""
    verification_uri: str = ""
    message: str = ""
    expires_at: float = 0.0
    # Resolved once the flow completes or fails
    completed: bool = False
    error: str | None = None


@dataclass
class AzureAuthStatus:
    """Snapshot of current Azure authentication state."""
    authenticated: bool = False
    auth_method: str | None = None  # "device_code", "service_principal", "default_credential"
    user_display_name: str | None = None
    user_email: str | None = None
    expires_at: float | None = None
    expires_in_seconds: int | None = None
    device_code_pending: bool = False
    device_code_info: DeviceCodeInfo | None = None
    error: str | None = None


class AzureAuthManager:
    """Manages Azure Entra ID credentials for the Speech provider.

    Thread-safe.  A single instance is shared across the application via
    :func:`get_azure_auth_manager`.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._device_code_info: DeviceCodeInfo | None = None
        self._device_code_thread: threading.Thread | None = None
        # Event used to signal the background polling thread to stop early
        self._cancel_event = threading.Event()
        # In-memory token cache (fast path, same process)
        self._cached_token: str | None = None
        self._cached_expires_on: float = 0

    # ------------------------------------------------------------------
    # Redis helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_redis():
        """Get a sync Redis client from the app's connection pool."""
        import redis
        from app.core.config import settings
        return redis.from_url(settings.redis_url, decode_responses=True)

    def _store_token_in_redis(
        self,
        access_token: str,
        expires_on: float,
        auth_method: str,
        user_info: dict | None = None,
    ) -> None:
        """Persist tokens in Redis with TTL so all containers can read them."""
        try:
            r = self._get_redis()
            ttl = max(int(expires_on - time.time()), 60)
            pipe = r.pipeline()
            pipe.setex(f"{_REDIS_PREFIX}:access_token", ttl, access_token)
            pipe.setex(f"{_REDIS_PREFIX}:expires_on", ttl, str(expires_on))
            pipe.setex(f"{_REDIS_PREFIX}:auth_method", ttl, auth_method)
            if user_info:
                pipe.setex(f"{_REDIS_PREFIX}:user_info", ttl, json.dumps(user_info))
            pipe.execute()
            logger.info("azure_auth_token_stored_redis", auth_method=auth_method, ttl=ttl)
        except Exception as exc:
            logger.warning("azure_auth_redis_store_failed", error=str(exc))

    def _load_token_from_redis(self) -> tuple[str | None, float, str | None, dict | None]:
        """Load cached token from Redis. Returns (token, expires_on, method, user_info)."""
        try:
            r = self._get_redis()
            token = r.get(f"{_REDIS_PREFIX}:access_token")
            if not token:
                return None, 0, None, None
            expires_on = float(r.get(f"{_REDIS_PREFIX}:expires_on") or 0)
            method = r.get(f"{_REDIS_PREFIX}:auth_method")
            user_info_raw = r.get(f"{_REDIS_PREFIX}:user_info")
            user_info = json.loads(user_info_raw) if user_info_raw else None
            return token, expires_on, method, user_info
        except Exception as exc:
            logger.warning("azure_auth_redis_load_failed", error=str(exc))
            return None, 0, None, None

    def _clear_redis_tokens(self) -> None:
        """Remove all cached tokens from Redis."""
        try:
            r = self._get_redis()
            r.delete(
                f"{_REDIS_PREFIX}:access_token",
                f"{_REDIS_PREFIX}:expires_on",
                f"{_REDIS_PREFIX}:auth_method",
                f"{_REDIS_PREFIX}:user_info",
            )
            logger.info("azure_auth_redis_cleared")
        except Exception as exc:
            logger.warning("azure_auth_redis_clear_failed", error=str(exc))

    # ------------------------------------------------------------------
    # Device Code Flow  (uses MSAL directly for reliable two-step flow)
    # ------------------------------------------------------------------

    def initiate_device_code(
        self, tenant_id: str = "", device_code_client_id: str = "",
    ) -> DeviceCodeInfo:
        """Start a device code authentication flow.

        Uses MSAL ``initiate_device_flow()`` which is a synchronous HTTP
        call that immediately returns the user code and URL (or an error).
        Then spawns a background thread to poll for the user's sign-in
        completion via ``acquire_token_by_device_flow()``.

        If *device_code_client_id* is provided (from the provider config's
        ``client_id`` field), that app registration is used.  Otherwise the
        method tries several well-known Microsoft first-party public clients
        until one is accepted by the tenant.
        """
        with self._lock:
            # Cancel any existing flow — signal the old polling thread to stop
            if self._device_code_thread and self._device_code_thread.is_alive():
                self._cancel_event.set()
                logger.info("azure_device_code_cancelling_previous_flow")
            self._cancel_event = threading.Event()
            self._device_code_info = None

        try:
            import msal
        except ImportError:
            raise ImportError(
                "msal package is required for device code flow. "
                "Install with: pip install msal"
            )

        effective_tenant = tenant_id.strip() if tenant_id else ""
        if not effective_tenant:
            raise ValueError(
                "tenant_id is required for Azure device code login. "
                "Please set the Tenant ID in the Azure Speech provider configuration first."
            )

        authority = f"https://login.microsoftonline.com/{effective_tenant}"

        # Build candidate list: user-provided first, then well-known fallbacks
        candidates = []
        if device_code_client_id and device_code_client_id.strip():
            candidates.append(device_code_client_id.strip())
        candidates.extend(_WELL_KNOWN_PUBLIC_CLIENTS)

        # Try each client ID until one is accepted by the tenant
        flow = None
        app = None
        last_error = ""
        for cid in candidates:
            try:
                app = msal.PublicClientApplication(
                    client_id=cid, authority=authority,
                )
                flow = app.initiate_device_flow(
                    scopes=[_COGNITIVE_SERVICES_SCOPE],
                )
                if "error" not in flow:
                    logger.info(
                        "azure_device_code_client_accepted",
                        client_id=cid,
                        tenant=effective_tenant,
                    )
                    break  # Success!
                last_error = flow.get("error_description", flow.get("error", ""))
                logger.warning(
                    "azure_device_code_client_rejected",
                    client_id=cid, error=last_error,
                )
                flow = None
                app = None
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "azure_device_code_client_failed",
                    client_id=cid, error=last_error,
                )
                flow = None
                app = None

        if flow is None or app is None:
            raise RuntimeError(
                f"None of the known Azure public client IDs are accepted by "
                f"your tenant '{effective_tenant}'. Last error: {last_error}\n\n"
                f"To fix this, create an App Registration in your Azure AD tenant:\n"
                f"1. Go to Entra ID → App registrations → New registration\n"
                f"2. Name: 'Atlas Vox' (or any name)\n"
                f"3. Supported account types: 'Single tenant'\n"
                f"4. Redirect URI: leave blank (not needed for device code)\n"
                f"5. After creating, go to Authentication → Advanced → Allow public client flows → Yes\n"
                f"6. Go to API permissions → Add → Azure Cognitive Services → user_impersonation\n"
                f"7. Copy the Application (client) ID and paste it into the 'Client / App ID' field\n"
                f"8. Leave Client Secret empty (public client doesn't need one for device code)"
            )

        info = DeviceCodeInfo(
            user_code=flow.get("user_code", ""),
            verification_uri=flow.get("verification_uri", "https://microsoft.com/devicelogin"),
            message=flow.get("message", ""),
            expires_at=time.time() + flow.get("expires_in", 900),
        )

        with self._lock:
            self._device_code_info = info

        logger.info(
            "azure_device_code_issued",
            user_code=info.user_code,
            verification_uri=info.verification_uri,
            tenant=effective_tenant,
        )

        # Step 2 — background thread polls for user sign-in completion
        cancel_event = self._cancel_event  # capture for closure

        def _poll_for_token():
            try:
                # MSAL's acquire_token_by_device_flow blocks — poll cancel event
                # alongside by checking periodically if cancelled.  Unfortunately
                # MSAL doesn't expose a cancel API, so we rely on the expiry
                # timeout if the event is set.
                result = app.acquire_token_by_device_flow(flow)

                # If cancelled while waiting, discard result
                if cancel_event.is_set():
                    logger.info("azure_device_code_cancelled_during_poll")
                    return

                if "error" in result:
                    error_msg = result.get("error_description", result.get("error", "Unknown"))
                    with self._lock:
                        if self._device_code_info:
                            self._device_code_info.completed = True
                            self._device_code_info.error = error_msg
                    logger.error("azure_device_code_failed", error=error_msg)
                    return

                access_token = result.get("access_token", "")
                expires_in = result.get("expires_in", 3600)
                expires_on = time.time() + expires_in

                with self._lock:
                    self._cached_token = access_token
                    self._cached_expires_on = expires_on
                    if self._device_code_info:
                        self._device_code_info.completed = True

                # Extract user info from id_token claims or JWT
                user_info = None
                id_claims = result.get("id_token_claims")
                if id_claims:
                    user_info = {
                        "name": id_claims.get("name", ""),
                        "email": id_claims.get("preferred_username",
                                               id_claims.get("upn", id_claims.get("email", ""))),
                        "oid": id_claims.get("oid", ""),
                        "tid": id_claims.get("tid", ""),
                    }
                else:
                    user_info = self._decode_token_claims(access_token)

                self._store_token_in_redis(
                    access_token=access_token,
                    expires_on=expires_on,
                    auth_method="device_code",
                    user_info=user_info,
                )
                logger.info("azure_device_code_authenticated", expires_on=expires_on)

            except Exception as exc:
                with self._lock:
                    if self._device_code_info:
                        self._device_code_info.completed = True
                        self._device_code_info.error = str(exc)
                logger.error("azure_device_code_failed", error=str(exc))

        thread = threading.Thread(target=_poll_for_token, daemon=True, name="azure-device-code")
        thread.start()

        with self._lock:
            self._device_code_thread = thread

        return info

    @staticmethod
    def _decode_token_claims(token: str) -> dict | None:
        """Decode JWT payload (no verification — just for display info)."""
        try:
            import base64
            parts = token.split(".")
            if len(parts) < 2:
                return None
            payload = parts[1]
            # Add padding
            payload += "=" * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            claims = json.loads(decoded)
            return {
                "name": claims.get("name", ""),
                "email": claims.get("upn", claims.get("email", claims.get("preferred_username", ""))),
                "oid": claims.get("oid", ""),
                "tid": claims.get("tid", ""),
            }
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Status & Logout
    # ------------------------------------------------------------------

    def get_status(self) -> AzureAuthStatus:
        """Get the current Azure authentication status."""
        status = AzureAuthStatus()

        # Check device code flow state
        with self._lock:
            dci = self._device_code_info
            if dci and not dci.completed and time.time() < dci.expires_at:
                status.device_code_pending = True
                status.device_code_info = dci

        # Check Redis for cached token
        token, expires_on, method, user_info = self._load_token_from_redis()

        if token and expires_on > time.time():
            status.authenticated = True
            status.auth_method = method
            status.expires_at = expires_on
            status.expires_in_seconds = max(int(expires_on - time.time()), 0)
            if user_info:
                status.user_display_name = user_info.get("name")
                status.user_email = user_info.get("email")
        elif self._device_code_info and self._device_code_info.error:
            status.error = self._device_code_info.error

        return status

    def logout(self) -> None:
        """Clear all cached Azure credentials and stop any in-flight polling."""
        with self._lock:
            self._cached_token = None
            self._cached_expires_on = 0
            # Signal polling thread to stop
            self._cancel_event.set()
            if self._device_code_info:
                self._device_code_info.completed = True
            self._device_code_info = None
        self._clear_redis_tokens()
        logger.info("azure_auth_logged_out")

    # ------------------------------------------------------------------
    # Token retrieval (used by AzureTokenManager)
    # ------------------------------------------------------------------

    def get_cached_token(self, config: dict | None = None) -> str | None:
        """Get a valid cached token if one exists.

        Priority:
        1. In-memory cache (same process, fastest)
        2. Redis cache (cross-container)
        3. Service principal credential (if config has SP fields)
        4. None (caller should fall back to DefaultAzureCredential)
        """
        now = time.time()

        # 1. In-memory cache
        with self._lock:
            if self._cached_token and self._cached_expires_on > now + 60:
                return self._cached_token

        # 2. Redis cache
        token, expires_on, method, _ = self._load_token_from_redis()
        if token and expires_on > now + 60:
            with self._lock:
                self._cached_token = token
                self._cached_expires_on = expires_on
            return token
        elif token and expires_on <= now + 60:
            # Token expired — clear from Redis so we don't keep returning stale data
            logger.info("azure_auth_redis_token_expired", method=method,
                        expired_ago=int(now - expires_on))
            self._clear_redis_tokens()

        # 3. Service principal (if configured)
        if config:
            sp_token = self._try_service_principal(config)
            if sp_token:
                return sp_token

        return None

    def _try_service_principal(self, config: dict) -> str | None:
        """Attempt to get a token using service principal credentials from config."""
        tenant_id = config.get("tenant_id", "")
        client_id = config.get("client_id", "")
        client_secret = config.get("client_secret", "")

        if not (tenant_id and client_id and client_secret):
            return None

        try:
            from azure.identity import ClientSecretCredential

            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            result = credential.get_token(_COGNITIVE_SERVICES_SCOPE)

            with self._lock:
                self._cached_token = result.token
                self._cached_expires_on = result.expires_on

            self._store_token_in_redis(
                access_token=result.token,
                expires_on=result.expires_on,
                auth_method="service_principal",
            )
            return result.token

        except Exception as exc:
            logger.warning("azure_service_principal_auth_failed", error=str(exc))
            return None


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_manager: AzureAuthManager | None = None
_manager_lock = threading.Lock()


def get_azure_auth_manager() -> AzureAuthManager:
    """Get the singleton AzureAuthManager instance."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = AzureAuthManager()
    return _manager
