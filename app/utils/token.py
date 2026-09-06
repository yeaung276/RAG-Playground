"""Signed-cookie admin sessions via itsdangerous — no server-side store.

The cookie holds the admin id signed + timestamped; validity (and expiry) is
proven by the signature alone, checked against the app secret on each request.
"""
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_SALT = "admin-session"


def _serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt=_SALT)


def sign_token(subject: str, secret: str) -> str:
    return _serializer(secret).dumps(subject)


def verify_token(token: str, secret: str, max_age: int) -> str | None:
    """Return the signed subject if valid and within max_age (seconds), else None."""
    try:
        return _serializer(secret).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
