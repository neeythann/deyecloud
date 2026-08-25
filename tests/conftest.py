"""Shared test fixtures."""

from __future__ import annotations

import json
from typing import Any

import pytest
import requests

from deyecloud.core import DeyeCloudRequestor


def make_response(payload: Any, *, status: int = 200) -> requests.Response:
    """Build a :class:`requests.Response` with a JSON payload."""
    response = requests.Response()
    response.status_code = status
    response._content = json.dumps(payload).encode("utf-8")
    response.headers["content-type"] = "application/json"
    return response


def envelope(data: Any, *, success: bool = True, code: str = "1000000", msg: str = "success") -> dict[str, Any]:
    """Build a standard Deye Cloud response envelope.

    The payload fields are placed at the top level of the envelope alongside the
    ``requestId`` / ``success`` / ``code`` / ``msg`` fields, matching the live API.

    """
    if isinstance(data, dict):
        body = dict(data)
    else:
        body = {}
    body.update({"requestId": "req-1", "success": success, "code": code, "msg": msg})
    return body


class FakeRequestor(DeyeCloudRequestor):
    """A requestor that serves canned responses keyed by URL path."""

    def __init__(self, routes: dict[str, Any] | None = None, timeout: int = 30) -> None:
        """Initialize a :class:`.FakeRequestor` with a route table."""
        super().__init__(timeout=timeout)
        self.routes = dict(routes or {})
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        *,
        method: str,
        url: str,
        data: Any = None,
        json: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> requests.Response:
        """Return the canned response for the requested URL."""
        self.calls.append({"method": method, "url": url, "json": json, "params": params, "headers": headers})
        path = url.replace("https://eu1-developer.deyecloud.com/", "")
        route = self.routes.get(path)
        if route is None:
            raise AssertionError(f"No fake route registered for {method} {path}")
        return make_response(route)


@pytest.fixture
def fake_requestor() -> FakeRequestor:
    """Return a :class:`.FakeRequestor` with no routes configured."""
    return FakeRequestor()
