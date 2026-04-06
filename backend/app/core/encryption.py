"""Fernet symmetric encryption for provider API keys at rest.

Values encrypted by this module are stored with an ``enc:`` prefix so that
``load_provider_configs`` can distinguish encrypted ciphertext from legacy
plaintext.
"""

from __future__ import annotations

import base64

import structlog
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

logger = structlog.get_logger(__name__)

# Prefix that marks an encrypted value in the database
ENC_PREFIX = "enc:"

# Module-level cache so we only derive the key once per process
_fernet: Fernet | None = None


def get_fernet_key() -> Fernet:
    """Derive a Fernet key from ``settings.jwt_secret_key`` via HKDF-SHA256.

    The key is cached after the first call.  The default dev secret
    (``change-me-in-production``) is accepted as-is so encryption still works
    in local development, although the protection is obviously weaker.
    """
    global _fernet
    if _fernet is not None:
        return _fernet

    from app.core.config import settings

    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"atlas-vox-encryption",
        info=b"provider-config",
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.jwt_secret_key.encode()))
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
