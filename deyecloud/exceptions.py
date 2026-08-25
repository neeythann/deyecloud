"""Client exception classes.

Includes two main exceptions: :class:`.DeyeCloudAPIException` for when something goes
wrong on the server side, and :class:`.ClientException` when something goes wrong on the
client side. Both extend :class:`.DeyeCloudException`.

All other exceptions are subclassed from :class:`.ClientException`.

"""

from __future__ import annotations

from typing import Any


class DeyeCloudException(Exception):
    """The base exception that all other exception classes extend."""


class ClientException(DeyeCloudException):
    """Indicate exceptions that don't involve interaction with the Deye Cloud API."""


class InvalidToken(ClientException):
    """Indicate exceptions that involve a missing, expired, or rejected token."""

    def __init__(self) -> None:
        """Initialize an :class:`.InvalidToken` instance."""
        super().__init__(
            "The access token is missing, expired, or invalid. Attempting to re-authenticate."
        )


class MissingRequiredAttributeException(ClientException):
    """Indicate exceptions caused by not including a required attribute."""


class InvalidParameterValue(ClientException):
    """Indicate exceptions caused by passing an invalid parameter value."""

    def __init__(self, name: str, value: Any, valid: set[str]) -> None:
        """Initialize an :class:`.InvalidParameterValue` instance."""
        super().__init__(
            f"The value {value!r} is invalid for parameter {name!r}. Valid values are: "
            f"{', '.join(sorted(valid))}."
        )


class DeyeCloudAPIException(DeyeCloudException):
    """Container for error messages returned by the Deye Cloud API."""

    def __init__(
        self,
        *,
        request_id: str | None = None,
        code: str | None = None,
        msg: str | None = None,
        items: list[DeyeCloudErrorItem] | None = None,
    ) -> None:
        """Initialize a :class:`.DeyeCloudAPIException` instance.

        :param request_id: The ``requestId`` echoed back by the server (default: ``None``).
        :param code: The business error ``code`` returned by the server (default: ``None``).
        :param msg: The human readable error ``msg`` returned by the server (default: ``None``).
        :param items: A list of parsed error items (default: ``None``).

        """
        self.items = items if items is not None else []
        self.request_id = request_id
        self.code = code
        self.msg = msg
        super().__init__(*self.items, f"{code}: {msg}" if code else msg)


class DeyeCloudErrorItem:
    """Represent a single error returned from the Deye Cloud API."""

    def __init__(
        self,
        *,
        code: str | None = None,
        msg: str | None = None,
        field: str | None = None,
    ) -> None:
        """Initialize a :class:`.DeyeCloudErrorItem` instance."""
        self.code = code
        self.msg = msg
        self.field = field

    @property
    def error_message(self) -> str:
        """The completed error message string."""
        if self.field:
            return f"{self.field}: {self.msg}" if self.msg else self.field
        return self.msg or self.code or ""

    def __str__(self) -> str:
        """Return a human readable representation of the error."""
        parts = [part for part in (self.code, self.error_message) if part]
        return ": ".join(parts)

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return f"DeyeCloudErrorItem(code={self.code!r}, msg={self.msg!r}, field={self.field!r})"


class ResponseException(DeyeCloudException):
    """Indicate exceptions caused by an unexpected HTTP-level response.

    This mirrors how HTTP status errors are surfaced before the response body can be
    parsed into the standard business envelope.

    """

    def __init__(self, *, status: int | None = None, message: str = "") -> None:
        """Initialize a :class:`.ResponseException` instance.

        :param status: The HTTP status code of the response (default: ``None``).
        :param message: The response body or reason (default: ``""``).

        """
        self.status = status
        self.message = message
        super().__init__(f"Received an unexpected response (status {status}): {message}")
