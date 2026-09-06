from app.dependencies.session import get_session


class _Req:
    def __init__(self, cookies):
        self.cookies = cookies


def test_get_session_returns_cookie_value():
    assert get_session(_Req({"chat_session": "abc"})) == "abc"


def test_get_session_returns_none_when_missing():
    assert get_session(_Req({})) is None
