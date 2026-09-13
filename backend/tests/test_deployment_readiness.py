import pytest

from app.config import parse_frontend_origins


def test_frontend_origins_support_comma_separated_values() -> None:
    assert parse_frontend_origins(
        "https://demo.example, https://review.example/"
    ) == ["https://demo.example", "https://review.example"]


def test_frontend_origins_fall_back_to_local_development() -> None:
    assert parse_frontend_origins(" , ") == ["http://localhost:5173"]


def test_frontend_origins_reject_wildcard_with_credentials_enabled() -> None:
    with pytest.raises(ValueError, match="wildcard origins"):
        parse_frontend_origins("*")
