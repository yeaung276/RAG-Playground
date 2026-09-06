from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Security headers applied to every response (HTML, static assets and API).
#
# CSP and X-Frame-Options are document-scoped: they only take effect on the
# /dev HTML page. On widget.js / images / the API they are inert but harmless —
# the page embedding widget.js enforces its own CSP, not a header on the script
# response.
#
# We intentionally do NOT set Cross-Origin-Resource-Policy / -Embedder-Policy:
# those would block widget.js and its assets from loading on third-party sites,
# which is the widget's primary use case. Cross-origin /send calls stay allowed
# via the existing permissive CORS policy.
_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "media-src 'self'; "
        "connect-src 'self'; "
        "frame-src 'self'; "
        "frame-ancestors 'self'; "
        "base-uri 'self'"
    ),
}

# Only honoured by browsers over HTTPS; emitted when TLS terminates here or at
# the reverse proxy (which forwards the original scheme via X-Forwarded-Proto).
_HSTS = "max-age=63072000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        for key, value in _HEADERS.items():
            response.headers.setdefault(key, value)

        scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
        if scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", _HSTS)

        return response
