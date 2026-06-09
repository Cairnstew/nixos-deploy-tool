from __future__ import annotations

from nixos_deploy_tool.models.result import BaseResult


def assert_ok(result: BaseResult, message_contains: str | None = None) -> None:
    """Assert the result is a success, optionally checking message content."""
    assert result.ok, f"Expected ok=True, got: {result.message}"
    if message_contains:
        assert message_contains in result.message, (
            f"Expected message to contain {message_contains!r}, got: {result.message!r}"
        )


def assert_error(result: BaseResult, error_type: str | None = None) -> None:
    """Assert the result is an error, optionally checking the error type."""
    assert not result.ok, f"Expected ok=False, got: {result}"
    if error_type:
        assert result.error_type == error_type, (
            f"Expected error_type={error_type!r}, got: {result.error_type!r}"
        )
