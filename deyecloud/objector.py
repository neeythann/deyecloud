"""Provides the Objector class.

The objector converts the raw (envelope-unwrapped) JSON returned by the Deye Cloud API
into model objects, mirroring how PRAW's :class:`.Objector` builds
:class:`.RedditBase` instances from response data.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.models.listing import Page

if TYPE_CHECKING:
    import deyecloud

# Keys that wrap a list of homogeneous items in a response payload.
CONTAINER_KEYS = ("deviceDataList", "dataList", "stationList", "recordList", "orgInfoList")


class Objector:
    """The objector builds model objects from API response data."""

    def __init__(
        self,
        deyecloud: deyecloud.DeyeCloud,
        parsers: dict[str, Any] | None = None,
    ) -> None:
        """Initialize an :class:`.Objector` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.

        """
        self.parsers = {} if parsers is None else parsers
        self._deyecloud = deyecloud

    def objectify(
        self,
        *,
        data: dict[str, Any] | list[Any] | bool | None,
    ) -> Any:
        """Create model objects from ``data``.

        :param data: The structured data.

        :returns: An instance of a model, a plain ``dict``/``list``, or ``None``.

        """
        if data is None:
            return None
        if isinstance(data, bool):
            return data
        if isinstance(data, list):
            return [self.objectify(data=item) for item in data]
        if isinstance(data, dict):
            if self._is_page(data):
                return self._objectify_page(data=data)
            model = self._objectify_dict(data=data)
            if model is not data:
                return model
            if self._is_container(data):
                for key in CONTAINER_KEYS:
                    if key in data and isinstance(data[key], list):
                        return self.objectify(data=data[key])
            return data
        return data

    @staticmethod
    def _is_page(data: dict[str, Any]) -> bool:
        """Whether ``data`` represents a paginated list response."""
        if "records" in data:
            return True
        return "page" in data and "total" in data and any(key in data for key in CONTAINER_KEYS)

    @staticmethod
    def _is_container(data: dict[str, Any]) -> bool:
        """Whether ``data`` is a thin wrapper around a single list of items."""
        return any(key in data and isinstance(data[key], list) for key in CONTAINER_KEYS)

    def _objectify_page(self, *, data: dict[str, Any]) -> Page:
        """Build a :class:`.Page` with objectified records."""
        records = data.get("records", data.get("recordList", data.get("dataList", [])))
        objectified = self.objectify(data=records)
        if not isinstance(objectified, list):
            objectified = [objectified] if objectified is not None else []
        return Page(self._deyecloud, _data=data, _records=objectified)

    def _objectify_dict(self, *, data: dict[str, Any]) -> Any:
        """Create a model object from a single item dict.

        :param data: The structured data, assumed to be a dict.

        :returns: An instance of a model, or the ``data`` dict.

        """
        if "alertId" in data:
            if {"description", "reason", "solution"}.intersection(data):
                return self.parsers["DeviceAlert"].parse(data, self._deyecloud)
            return self.parsers["StationAlert"].parse(data, self._deyecloud)
        if "deviceSn" in data:
            return self.parsers["Device"].parse(data, self._deyecloud)
        if "stationId" in data:
            return self.parsers["Station"].parse(data, self._deyecloud)
        if "orderId" in data:
            return self.parsers["Order"].parse(data, self._deyecloud)
        if {"companyId", "companyName", "roleName"}.issubset(data):
            return self.parsers["OrgInfo"].parse(data, self._deyecloud)
        return data
