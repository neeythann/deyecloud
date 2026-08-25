"""Provide the Station class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.const import STATION_HISTORY_GRANULARITY
from deyecloud.endpoints import API_PATH
from deyecloud.exceptions import InvalidParameterValue
from deyecloud.models.base import DeyeModelBase
from deyecloud.util.cache import cachedproperty
from deyecloud.util.snake import snake_case_keys

if TYPE_CHECKING:
    import deyecloud


class Station(DeyeModelBase):
    """A class representing a Deye power station.

    .. note::

        Instances obtained via ``deye.station(station_id)`` are lazily loaded; data
        attributes are populated from the ``station/latest`` endpoint on first access.

    """

    STR_FIELD = "station_id"

    def __init__(
        self,
        deyecloud: deyecloud.DeyeCloud,
        station_id: int | None = None,
        _data: dict[str, Any] | None = None,
        _fetched: bool = False,
    ) -> None:
        """Initialize a :class:`.Station` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.
        :param station_id: The numeric identifier of the station.

        """
        if station_id is not None and _data is None:
            _data = {"station_id": station_id}
        super().__init__(deyecloud, _data=_data, _fetched=_fetched)

    def _fetch(self) -> None:
        """Populate the instance with the station's latest data."""
        data = self._fetch_data()
        if isinstance(data, list):
            data = data[0] if data else {}
        elif isinstance(data, dict):
            for key in ("dataList", "data_list"):
                value = data.get(key)
                if isinstance(value, list):
                    data = value[0] if value else {}
                    break
        if isinstance(data, dict):
            self.__dict__.update(snake_case_keys(data))
        self._fetched = True

    def _fetch_info(self) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return ("station_latest", {}, {"stationId": self.station_id})

    def latest(self) -> Station:
        """Return a :class:`.Station` instance with the latest telemetry.

        Example usage:

        .. code-block:: python

            station = deye.station(322).latest()
            print(station.battery_soc)

        """
        return self._deyecloud.station.latest(self.station_id)

    @cachedproperty
    def stream(self) -> StationStream:
        """Provide an instance of :class:`.StationStream`.

        Streams can be used to indefinitely retrieve live station telemetry as it is
        updated, like:

        .. code-block:: python

            station = deye.station(322)
            for snapshot in station.stream.latest():
                print(snapshot.generation_power)

        """
        from deyecloud.models.stream import StationStream  # ruff:ignore[import-outside-top-level]

        return StationStream(self)

    def history(
        self,
        granularity: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Fetch historical data for the station.

        :param granularity: One of ``"frame"``, ``"day"``, ``"month"``, or ``"year"``.
        :param start_date: The start date, e.g. ``"2024-01-01"``.
        :param end_date: The end date, e.g. ``"2024-01-31"``.

        Additional keyword arguments are merged into the request body.

        """
        if granularity not in STATION_HISTORY_GRANULARITY:
            raise InvalidParameterValue("granularity", granularity, set(STATION_HISTORY_GRANULARITY))
        body = {"stationId": self.station_id, "granularity": STATION_HISTORY_GRANULARITY[granularity]}
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        body.update(kwargs)
        return self._deyecloud.post(API_PATH["station_history"], json=body)

    def history_power(self, start_timestamp: int, end_timestamp: int) -> Any:
        """Fetch power history for the station within a Unix timestamp range.

        :param start_timestamp: The start timestamp, in seconds (10 digit Unix time).
        :param end_timestamp: The end timestamp, in seconds (10 digit Unix time).

        """
        body = {
            "stationId": self.station_id,
            "startTimestamp": start_timestamp,
            "endTimestamp": end_timestamp,
        }
        return self._deyecloud.post(API_PATH["station_history_power"], json=body)

    def alerts(
        self,
        start_timestamp: int,
        end_timestamp: int,
        *,
        limit: int | None = None,
        page_size: int = 20,
    ) -> Any:
        """Fetch alerts raised by devices in the station.

        :param start_timestamp: The start timestamp, in seconds.
        :param end_timestamp: The end timestamp, in seconds.
        :param limit: The maximum number of alerts to fetch (default: ``None``).
        :param page_size: The number of alerts requested per page (default: ``20``).

        """
        body = {"stationId": self.station_id, "startTimestamp": start_timestamp, "endTimestamp": end_timestamp}
        return self._deyecloud._paginate(
            path="v1.0/station/alertList", json=body, limit=limit, page_size=page_size
        )

    def devices(
        self,
        *,
        device_type: str | None = None,
        limit: int | None = None,
        page_size: int = 20,
    ) -> Any:
        """Fetch the devices registered under the station.

        :param device_type: An optional device type filter, e.g. ``"INVERTER"``.
        :param limit: The maximum number of devices to fetch (default: ``None``).
        :param page_size: The number of devices requested per page (default: ``20``).

        """
        body = {"stationIds": [self.station_id]}
        if device_type:
            body["deviceType"] = device_type
        return self._deyecloud._paginate(path="v1.0/station/device", json=body, limit=limit, page_size=page_size)
