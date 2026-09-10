import base64
import re
import time
from typing import Any

import aiohttp

from app.schemas.agent import AuthKind, SentRequest, ToolTestResult, ToolWrite

MASK = "••••••"
MAX_BODY = 4000
_PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def _fill(template: str, params: dict[str, Any]) -> str:
    """Replace `{{name}}` with the supplied value; unknown names are left as-is
    so the caller can see what went unfilled."""
    return _PLACEHOLDER.sub(
        lambda m: str(params[m.group(1)]) if m.group(1) in params else m.group(0), template
    )


def build_request(
    tool: ToolWrite, params: dict[str, Any], token: str | None
) -> tuple[SentRequest, dict[str, str]]:
    """The request the tool would make, and the auth headers to send with it.
    Auth is kept out of the echoed request so no secret reaches the browser."""
    headers = {h.key: _fill(h.value, params) for h in tool.headers if h.key}
    query = {q.key: _fill(q.value, params) for q in tool.query if q.key}

    auth: dict[str, str] = {}
    if tool.auth is AuthKind.BEARER and token:
        auth["Authorization"] = f"Bearer {token}"
    elif tool.auth is AuthKind.HEADER and token and tool.auth_header:
        auth[tool.auth_header] = token
    elif tool.auth is AuthKind.BASIC and (tool.auth_user or tool.auth_pass):
        raw = f"{tool.auth_user}:{tool.auth_pass}".encode()
        auth["Authorization"] = f"Basic {base64.b64encode(raw).decode()}"

    sent = SentRequest(
        method=tool.method.upper(),
        url=_fill(tool.url, params),
        headers={**headers, **{k: MASK for k in auth}},
        query=query,
        body=_fill(tool.body, params) or None,
    )
    return sent, auth


async def run(tool: ToolWrite, params: dict[str, Any], token: str | None) -> ToolTestResult:
    """Make the call for real and report what came back."""
    sent, auth = build_request(tool, params, token)
    started = time.perf_counter()
    timeout = aiohttp.ClientTimeout(total=tool.timeout_ms / 1000)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(
                sent.method,
                sent.url,
                params=sent.query or None,
                headers={**sent.headers, **auth},
                data=sent.body,
            ) as response:
                text = await response.text()
                return ToolTestResult(
                    request=sent,
                    status=response.status,
                    elapsed_ms=int((time.perf_counter() - started) * 1000),
                    body=text[:MAX_BODY],
                    error=None,
                )
    except Exception as exc:
        return ToolTestResult(
            request=sent,
            status=None,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
            body="",
            error=f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__,
        )
