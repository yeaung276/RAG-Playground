"""Envelope encryption for secrets at rest.

Each secret is sealed with its own random DEK (AES-256-GCM); the DEK is then
sealed with the KEK mounted from the environment. Only the two ciphertexts are
stored — the KEK never reaches the database.
"""
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings

NONCE_BYTES = 12


def _kek() -> AESGCM:
    raw = base64.b64decode(get_settings().MODEL_KEK)
    if len(raw) != 32:
        raise RuntimeError("MODEL_KEK must be 32 bytes, base64-encoded")
    return AESGCM(raw)


def _seal(key: AESGCM, plaintext: bytes, aad: bytes | None = None) -> bytes:
    nonce = os.urandom(NONCE_BYTES)
    return nonce + key.encrypt(nonce, plaintext, aad)


def _unseal(key: AESGCM, blob: bytes, aad: bytes | None = None) -> bytes:
    return key.decrypt(blob[:NONCE_BYTES], blob[NONCE_BYTES:], aad)


def encrypt_secret(
    secret: str, aad: str, wrapped_dek: bytes | None = None
) -> tuple[bytes, bytes]:
    """Return (ciphertext, KEK-wrapped DEK) for a secret bound to `aad`.
    Pass `wrapped_dek` to seal under a key the row already owns."""
    wrapped = wrapped_dek or _seal(_kek(), os.urandom(32))
    return _seal(AESGCM(_unseal(_kek(), wrapped)), secret.encode(), aad.encode()), wrapped


def decrypt_secret(ciphertext: bytes, wrapped_dek: bytes, aad: str) -> str:
    dek = _unseal(_kek(), wrapped_dek)
    return _unseal(AESGCM(dek), ciphertext, aad.encode()).decode()
