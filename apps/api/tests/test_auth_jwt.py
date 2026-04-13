import pytest

from midas_api.handlers.auth import _decode_token, _generate_tokens
from midas_api import __main__ as api_main


class DummyRequest:
    def __init__(self, token: str) -> None:
        self.headers = {"Authorization": f"Bearer {token}"}


@pytest.mark.unit
def test_generate_tokens_emits_string_subject() -> None:
    tokens = _generate_tokens(42)
    claims = _decode_token(tokens["access_token"])

    assert claims is not None
    assert claims["sub"] == "42"
    assert claims["type"] == "access"
    assert claims["exp"] > claims["iat"]


@pytest.mark.unit
def test_extract_user_from_access_token() -> None:
    tokens = _generate_tokens(101)
    user_id = api_main._extract_user(DummyRequest(tokens["access_token"]))

    assert user_id == 101
