"""Fernet symmetric encryption for provider API keys at rest.

Values encrypted by this module are stored with an ``enc:`` prefix so that
``load_provider_configs`` can distinguish encrypted ciphertext from legacy
plaintext.
"""

from __future__ import annotations

import base64
import os
import threading

import structlog
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = structlog.get_logger(__name__)

# Prefix that marks an encrypted value in the database
ENC_PREFIX = "enc:"

# Module-level cache so we only derive the key once per process
_fernet: Fernet | None = None
_fernet_lock = threading.Lock()

# Salt configuration
_SALT_FILE = os.path.join("data", ".encryption_salt")
_STATIC_SALT = b"atlas-vox-encryption"
_SALT_LENGTH = 32


def _get_or_create_salt() -> bytes:
    """Get the HKDF salt, generating and persisting a random one on first use.

    On the very first run a cryptographically random 32-byte salt is written to
    ``data/.encryption_salt``.  Subsequent starts read back that file.

    If the file does not exist **and** there is already encrypted data in the
    system (signalled by a prior Fernet instance), the static legacy salt is
    returned for backward compatibility.
    """
    if os.path.isfile(_SALT_FILE):
        with open(_SALT_FILE, "rb") as f:
            salt = f.read()
        if len(salt) == _SALT_LENGTH:
            return salt
        logger.warning(
            "encryption_salt_invalid_length",
            expected=_SALT_LENGTH,
            got=len(salt),
            hint="Falling back to static salt. Delete the file and restart to regenerate.",
        )
        return _STATIC_SALT

    # File doesn't exist — check whether we should fall back to static salt
    # for backward compatibility with data encrypted before salt-file support.
    # We use a simple heuristic: if the data directory already exists and
    # contains a database file, there may be encrypted data.
    data_dir = os.path.dirname(_SALT_FILE)
    if os.path.isdir(data_dir) and any(
        f.endswith((".db", ".sqlite", ".sqlite3")) for f in os.listdir(data_dir)
    ):
        logger.warning(
            "encryption_salt_legacy_fallback",
            hint="Existing data directory detected — using static salt for backward "
            "compatibility. To migrate to a random salt, re-encrypt values and then "
            "delete the old database or create the salt file manually.",
        )
        return _STATIC_SALT

    # Fresh install — generate and persist a random salt
    os.makedirs(data_dir, exist_ok=True)
    salt = os.urandom(_SALT_LENGTH)
    try:
        with open(_SALT_FILE, "wb") as f:
            f.write(salt)
        logger.info("encryption_salt_created", path=_SALT_FILE)
    except OSError as exc:
        logger.error(
            "encryption_salt_write_failed",
            error=str(exc),
            hint="Falling back to static salt. Fix file permissions and restart.",
        )
        return _STATIC_SALT

    return salt


def get_fernet_key() -> Fernet:
    """Derive a Fernet key via HKDF-SHA256.

    Uses ``settings.encryption_key`` if set, otherwise falls back to
    ``settings.jwt_secret_key`` for backward compatibility.  The key is
    cached after the first call.

    Thread-safe: a ``threading.Lock`` guards the lazy initialization of the
    module-level ``_fernet`` singleton.
    """
    global _fernet
    if _fernet is not None:
        return _fernet

    with _fernet_lock:
        # Double-checked locking
        if _fernet is not None:
            return _fernet

        from app.core.config import settings

        # Prefer dedicated encryption key; fall back to JWT secret (dev-only)
        secret = settings.encryption_key or settings.jwt_secret_key
        if not settings.encryption_key:
            logger.warning(
                "encryption_key_fallback",
                hint="ENCRYPTION_KEY is not set — falling back to JWT_SECRET_KEY. "
                "Set a dedicated ENCRYPTION_KEY to decouple JWT rotation from encrypted data.",
            )
        if secret == "change-me-in-production":
            raise RuntimeError(
                "Cannot encrypt with the default insecure key. "
                "Set ENCRYPTION_KEY or change JWT_SECRET_KEY from the default."
            )

        salt = _get_or_create_salt()

        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"provider-config",
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        _fernet = Fernet(key)
        return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt *plaintext* and return a string prefixed with ``enc:``.

    The returned string is safe to store in a text column.
    """
    f = get_fernet_key()
    token = f.encrypt(plaintext.encode())
    return ENC_PREFIX + token.decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a value previously produced by :func:`encrypt_value`.

    If *ciphertext* does not carry the ``enc:`` prefix it is returned
    unchanged (legacy plaintext fallback).
    """
    if not ciphertext.startswith(ENC_PREFIX):
        return ciphertext

    f = get_fernet_key()
    try:
        return f.decrypt(ciphertext[len(ENC_PREFIX):].encode()).decode()
    except InvalidToken:
        logger.error(
            "decrypt_value_failed",
            hint="The jwt_secret_key may have changed since this value was encrypted.",
        )
        raise
