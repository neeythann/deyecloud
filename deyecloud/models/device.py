"""Provide the Device class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.const import DEVICE_HISTORY_GRANULARITY
from deyecloud.endpoints import API_PATH
from deyecloud.exceptions import InvalidParameterValue
from deyecloud.models.base import DeyeModelBase
from deyecloud.util.snake import snake_case_keys

if TYPE_CHECKING:
    import deyecloud


class Device(DeyeModelBase):
    """A class representing a device (e.g. an inverter) registered with Deye Cloud.

    .. note::

        Instances obtained via ``deye.device(device_sn)`` are lazily loaded; data
        attributes are populated from the ``device/latest`` endpoint on first access.

    """

    STR_FIELD = "device_sn"

    def __init__(
        self,
        deyecloud: deyecloud.DeyeCloud,
        device_sn: str | None = None,
        _data: dict[str, Any] | None = None,
        _fetched: bool = False,
    ) -> None:
        """Initialize a :class:`.Device` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.
        :param device_sn: The serial number of the device.

        """
        if device_sn is not None and _data is None:
            _data = {"device_sn": device_sn}
        super().__init__(deyecloud, _data=_data, _fetched=_fetched)

    def _fetch(self) -> None:
        """Populate the instance with the device's latest data."""
        data = self._fetch_data()
        if isinstance(data, list):
            data = data[0] if data else {}
        elif isinstance(data, dict):
            for key in ("deviceDataList", "device_data_list"):
                value = data.get(key)
                if isinstance(value, list):
                    data = value[0] if value else {}
                    break
        if isinstance(data, dict):
            self.__dict__.update(snake_case_keys(data))
        self._fetched = True

    def _fetch_info(self) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return ("device_latest", {}, {"deviceList": [self.device_sn]})

    def latest(self, *, device_type: str | None = None) -> Device:
        """Return a :class:`.Device` instance with the latest telemetry.

        :param device_type: An optional device type used to disambiguate (default: ``None``).

        """
        return self._deyecloud.device.latest(self.device_sn, device_type=device_type)

    def history(
        self,
        granularity: str,
        *,
        measure_points: list[str] | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Fetch historical data for the device.

        :param granularity: One of ``"day"``, ``"day_range"``, ``"month"``, or
            ``"year"``.
        :param measure_points: The measure points to fetch, e.g. ``["SOC"]``.
        :param date: The date for day granularity, e.g. ``"2024-01-01"``.
        :param start_date: The start date for day-range/month-range granularity.
        :param end_date: The end date for day-range/month-range granularity.

        Additional keyword arguments are merged into the request body.

        """
        if granularity not in DEVICE_HISTORY_GRANULARITY:
            raise InvalidParameterValue("granularity", granularity, set(DEVICE_HISTORY_GRANULARITY))
        body: dict[str, Any] = {
            "deviceSn": self.device_sn,
            "granularity": DEVICE_HISTORY_GRANULARITY[granularity],
        }
        if measure_points:
            body["measurePoints"] = measure_points
        if date:
            body["date"] = date
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        body.update(kwargs)
        return self._deyecloud.post(API_PATH["device_history"], json=body)

    def history_raw(self, start_timestamp: int, end_timestamp: int) -> Any:
        """Fetch raw device history within a Unix timestamp range.

        :param start_timestamp: The start timestamp, in seconds (10 digit Unix time).
        :param end_timestamp: The end timestamp, in seconds (10 digit Unix time).

        """
        body = {
            "deviceSn": self.device_sn,
            "startTimestamp": start_timestamp,
            "endTimestamp": end_timestamp,
        }
        return self._deyecloud.post(API_PATH["device_history_raw"], json=body)

    def measure_points(self) -> Any:
        """Return the measure points available for the device."""
        return self._deyecloud.post(API_PATH["device_measure_points"], json={"deviceSn": self.device_sn})

    def alerts(
        self,
        start_timestamp: int,
        end_timestamp: int,
        *,
        limit: int | None = None,
        page_size: int = 20,
    ) -> Any:
        """Fetch alerts for the device.

        :param start_timestamp: The start timestamp, in seconds.
        :param end_timestamp: The end timestamp, in seconds.
        :param limit: The maximum number of alerts to fetch (default: ``None``).
        :param page_size: The number of alerts requested per page (default: ``20``).

        """
        body = {"deviceSn": self.device_sn, "startTimestamp": start_timestamp, "endTimestamp": end_timestamp}
        return self._deyecloud._paginate(path="v1.0/device/alertList", json=body, limit=limit, page_size=page_size)
