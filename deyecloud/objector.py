"""Provides the Objector class.

The objector converts the raw JSON returned by the Deye Cloud API into model objects,
mirroring how PRAW's :class:`.Objector` builds :class:`.RedditBase` instances from
response data.

The Deye Cloud API places payload fields at the top level of the response envelope.
List endpoints wrap their items in a container key such as ``stationList`` or
``deviceDataList``. The objector unwraps those containers into lists of model objects;
pagination itself is handled by :class:`.PageGenerator`.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import deyecloud

# Keys that wrap a list of homogeneous items in a response payload.
CONTAINER_KEYS = (
    "stationList",
    "deviceDataList",
    "deviceListItems",
    "stationDataItems",
    "orgInfoList",
    "recordList",
    "dataList",
    "records",
)


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
    def _is_container(data: dict[str, Any]) -> bool:
        """Whether ``data`` is a thin wrapper around a single list of items."""
        return any(key in data and isinstance(data[key], list) for key in CONTAINER_KEYS)

    def _objectify_dict(self, *, data: dict[str, Any]) -> Any:
        """Create a model object from a single item dict.

        :param data: The structured data, assumed to be a dict.

        :returns: An instance of a model, or the ``data`` dict.

        """
        if "alertId" in data:
            if {"description", "reason", "solution"}.intersection(data):
                return self.parsers["DeviceAlert"].parse(data, self._deyecloud)
            return self.parsers["StationAlert"].parse(data, self._deyecloud)
        if "measurePoints" in data:
            return data
        if "deviceSn" in data:
            return self.parsers["Device"].parse(data, self._deyecloud)
        if self._is_station(data):
            remapped = dict(data)
            if "id" in remapped and "station_id" not in remapped:
                remapped["station_id"] = remapped.pop("id")
            if "name" in remapped and "station_name" not in remapped:
                remapped["station_name"] = remapped.pop("name")
            return self.parsers["Station"].parse(remapped, self._deyecloud)
        if "orderId" in data:
            return self.parsers["Order"].parse(data, self._deyecloud)
        if {"companyId", "companyName", "roleName"}.issubset(data):
            return self.parsers["OrgInfo"].parse(data, self._deyecloud)
        return data

    @staticmethod
    def _is_station(data: dict[str, Any]) -> bool:
        """Whether ``data`` represents a station object.

        Stations returned by the list endpoints carry ``id`` and ``name`` together with
        telemetry or metadata fields such as ``batterySOC``, ``connectionStatus``,
        ``installedCapacity``, or ``deviceListItems``.

        """
        if "stationId" in data:
            return True
        if "id" in data and "name" in data:
            return any(
                key in data
                for key in (
                    "batterySOC",
                    "connectionStatus",
                    "generationPower",
                    "installedCapacity",
                    "gridInterconnectionType",
                    "deviceListItems",
                    "regionTimezone",
                )
            )
        return False
