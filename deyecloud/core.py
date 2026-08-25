"""Low level HTTP interface to the Deye Cloud API.

This module plays the role that ``prawcore`` plays for PRAW: it manages
authentication (token acquisition and refresh) and issues HTTP requests while checking
the Deye Cloud business response envelope (``success`` / ``code`` / ``msg``).

"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import TYPE_CHECKING, Any

import requests

from deyecloud.const import SUCCESS_CODE
from deyecloud.exceptions import (
    DeyeCloudAPIException,
    InvalidToken,
    ResponseException,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger("deyecloud")


class DeyeCloudRequestor:
    """Wrap the low level HTTP requests against the Deye Cloud API."""

    def __init__(self, *, timeout: int = 30) -> None:
        """Initialize a :class:`.DeyeCloudRequestor` instance.

        :param timeout: The number of seconds to wait for a response (default: ``30``).

        """
        self._session = requests.Session()
        self.timeout = timeout

    def request(
        self,
        *,
        method: str,
        url: str,
        data: Mapping[str, Any] | None = None,
        json: Any | None = None,
        params: Mapping[str, str | int] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> requests.Response:
        """Perform the HTTP request and return the raw response.

        :param method: The HTTP method (e.g. ``"GET"``, ``"POST"``).
        :param url: The fully qualified request URL.
        :param data: Form encoded data to send (default: ``None``).
        :param json: JSON serializable object to send (default: ``None``).
        :param params: Query string parameters (default: ``None``).
        :param headers: Additional request headers (default: ``None``).

        """
        kwargs: dict[str, Any] = {"data": data}
        if json is not None:
            kwargs["json"] = json
        if params:
            kwargs["params"] = params
        if headers:
            kwargs["headers"] = headers
        kwargs["timeout"] = self.timeout
        return self._session.request(method, url, **kwargs)


class DeyeCloudAuthorizer:
    """Manage the access token used to authenticate requests."""

    TOKEN_PATH = "v1.0/account/token"

    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        base_url: str,
        email: str | None = None,
        mobile: str | None = None,
        country_code: str | None = None,
        username: str | None = None,
        password: str | None = None,
        company_id: str | None = None,
        requestor: DeyeCloudRequestor | None = None,
    ) -> None:
        """Initialize a :class:`.DeyeCloudAuthorizer` instance.

        Exactly one of ``email``, ``mobile``, or ``username`` must be provided.

        """
        self._app_id = app_id
        self._app_secret = app_secret
        self._base_url = base_url.rstrip("/")
        self._company_id = company_id
        self._country_code = country_code
        self._email = email
        self._mobile = mobile
        self._password = password
        self._username = username
        self._requestor = requestor or DeyeCloudRequestor()

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0
        self._uid: str | None = None

    @property
    def access_token(self) -> str | None:
        """The currently held access token, or ``None`` if not authenticated."""
        return self._access_token

    @property
    def is_authenticated(self) -> bool:
        """Whether a valid access token is currently held."""
        return self._access_token is not None and time.time() < self._expires_at

    @staticmethod
    def _hash_password(password: str) -> str:
        """Return the SHA-256 hex digest of ``password``."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _build_token_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "appSecret": self._app_secret,
            "password": self._hash_password(self._password or ""),
        }
        if self._email is not None:
            payload["email"] = self._email
        elif self._mobile is not None:
            payload["mobile"] = self._mobile
            payload["countryCode"] = self._country_code
        elif self._username is not None:
            payload["username"] = self._username
        if self._company_id is not None:
            payload["companyId"] = self._company_id
        return payload

    def refresh(self) -> None:
        """Issue a new access token using the configured credentials.

        :raises: :class:`.DeyeCloudAPIException` if the server rejects the request.

        """
        url = f"{self._base_url}/{self.TOKEN_PATH}"
        response = self._requestor.request(
            method="POST",
            url=url,
            json=self._build_token_payload(),
            params={"appId": self._app_id},
        )
        data = _parse_response(response)
        self._access_token = data.get("accessToken")
        self._refresh_token = data.get("refreshToken")
        self._uid = data.get("uid")
        self._expires_at = time.time() + float(data.get("expiresIn", 3600))
        if not self._access_token:
            msg = "The token endpoint did not return an accessToken."
            raise InvalidToken(msg)
        logger.debug("Obtained a new access token (uid=%s)", self._uid)

    def token(self) -> str:
        """Return a valid access token, acquiring one if necessary.

        :raises: :class:`.InvalidToken` if a token cannot be obtained.

        """
        if not self.is_authenticated:
            self.refresh()
        assert self._access_token is not None
        return self._access_token


class DeyeCloudSession:
    """Issue authenticated requests and validate the Deye Cloud response envelope."""

    def __init__(
        self,
        *,
        authorizer: DeyeCloudAuthorizer,
        requestor: DeyeCloudRequestor | None = None,
    ) -> None:
        """Initialize a :class:`.DeyeCloudSession` instance."""
        self._authorizer = authorizer
        self._requestor = requestor or authorizer._requestor
        self._base_url = authorizer._base_url

    def request(
        self,
        *,
        method: str,
        path: str,
        data: Mapping[str, Any] | None = None,
        json: Any | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> Any:
        """Perform an authenticated request and return the parsed business payload.

        :param method: The HTTP method (e.g. ``"GET"``, ``"POST"``).
        :param path: The API path, e.g. ``"v1.0/station/latest"``.
        :param data: Form encoded data to send (default: ``None``).
        :param json: JSON serializable object to send (default: ``None``).
        :param params: Query string parameters (default: ``None``).

        :returns: The parsed response body (the Deye Cloud envelope fields such as
            ``code`` / ``msg`` are removed only when they are absent; all other fields
            are returned as-is at the top level).

        """
        token = self._authorizer.token()
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {"authorization": f"Bearer {token}"}
        response = self._requestor.request(
            method=method, url=url, data=data, json=json, params=params, headers=headers
        )
        return _parse_response(response)


def _parse_response(response: requests.Response) -> Any:
    """Parse a raw HTTP response into the Deye Cloud business payload.

    The Deye Cloud API places the payload fields at the top level of the response
    envelope alongside ``requestId`` / ``success`` / ``code`` / ``msg``, so the full
    body is returned on success.

    :raises: :class:`.ResponseException` on non-2xx status codes.
    :raises: :class:`.DeyeCloudAPIException` when the business envelope reports failure.

    """
    try:
        body = response.json()
    except ValueError:
        body = None

    if not (200 <= response.status_code < 300):
        message = body if body is not None else response.text
        raise ResponseException(status=response.status_code, message=str(message))

    if not isinstance(body, dict):
        return body

    success = body.get("success")
    if success is False or (success is None and body.get("code") not in {None, SUCCESS_CODE}):
        raise DeyeCloudAPIException(
            request_id=body.get("requestId"),
            code=body.get("code"),
            msg=body.get("msg"),
        )

    return body
