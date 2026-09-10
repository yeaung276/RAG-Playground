import base64

from app.schemas.agent import KV, ToolWrite
from app.services.agents.tool_runner import MASK, build_request


def tool(**kwargs) -> ToolWrite:
    return ToolWrite(name="search", **kwargs)


def test_placeholders_are_filled_everywhere():
    sent, _ = build_request(
        tool(
            method="post",
            url="https://api.test/orders/{{order_id}}",
            query=[KV(key="province", value="{{province}}")],
            headers=[KV(key="X-Trace", value="req-{{order_id}}")],
            body='{"id": "{{order_id}}"}',
        ),
        {"order_id": "42", "province": "Phuket"},
        None,
    )
    assert sent.method == "POST"
    assert sent.url == "https://api.test/orders/42"
    assert sent.query == {"province": "Phuket"}
    assert sent.headers["X-Trace"] == "req-42"
    assert sent.body == '{"id": "42"}'


def test_unknown_placeholder_is_left_visible():
    sent, _ = build_request(tool(url="https://api.test/{{missing}}"), {}, None)
    assert sent.url == "https://api.test/{{missing}}"


def test_bearer_token_is_masked_in_the_echo():
    sent, auth = build_request(tool(auth="bearer"), {}, "tok-1")
    assert auth == {"Authorization": "Bearer tok-1"}
    assert sent.headers["Authorization"] == MASK


def test_api_key_header_uses_the_configured_name():
    sent, auth = build_request(tool(auth="header", authHeader="X-Api-Key"), {}, "tok-1")
    assert auth == {"X-Api-Key": "tok-1"}
    assert sent.headers["X-Api-Key"] == MASK


def test_basic_auth_encodes_user_and_pass():
    _, auth = build_request(tool(auth="basic", authUser="u", authPass="p"), {}, None)
    assert auth["Authorization"] == f"Basic {base64.b64encode(b'u:p').decode()}"


def test_no_auth_sends_no_credential():
    sent, auth = build_request(tool(auth="none"), {}, "tok-1")
    assert auth == {}
    assert "Authorization" not in sent.headers
