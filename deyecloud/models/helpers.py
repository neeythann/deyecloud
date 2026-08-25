"""Provide the helper classes.

These are attached to the :class:`.DeyeCloud` instance (e.g. ``deye.station``) and
provide the primary interface for interacting with each resource, mirroring PRAW's
helper classes such as :class:`.SubredditHelper`.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.const import (
    BATTERY_PARAMETERS,
    BATTERY_TYPES,
    DEVICE_HISTORY_GRANULARITY,
    ENERGY_PATTERNS,
    LIMIT_CONTROL_MODES,
    STATION_HISTORY_GRANULARITY,
    WEEKDAYS,
    WORK_MODES,
)
from deyecloud.endpoints import API_PATH
from deyecloud.exceptions import InvalidParameterValue
from deyecloud.models.account import Account
from deyecloud.models.base import DeyeBase
from deyecloud.models.device import Device
from deyecloud.models.listing import PageGenerator
from deyecloud.models.order import Order
from deyecloud.models.station import Station
from deyecloud.util.snake import snake_case_keys

if TYPE_CHECKING:
    import deyecloud


def _validate(value: Any, name: str, valid: set[str]) -> None:
    if value not in valid:
        raise InvalidParameterValue(name, value, valid)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, (list, tuple)) else [value]


class AccountHelper(DeyeBase):
    """Provide a set of functions to interact with the authenticated account."""

    @property
    def token(self) -> str:
        """Return the current access token, acquiring one if necessary."""
        return self._deyecloud._core._authorizer.token()

    def info(self) -> Any:
        """Return the organizations (and roles) associated with the account.

        Example usage:

        .. code-block:: python

            for org in deye.account.info():
                print(org.company_id, org.company_name)

        """
        return self._deyecloud.post(API_PATH["account_info"])

    def me(self) -> Account:
        """Return an :class:`.Account` instance describing the authenticated user."""
        authorizer = self._deyecloud._core._authorizer
        token = authorizer.token()
        data = {
            "uid": authorizer._uid,
            "accessToken": token,
            "refreshToken": authorizer._refresh_token,
            "tokenType": "bearer",
        }
        return Account(self._deyecloud, _data=data)


class StationHelper(DeyeBase):
    """Provide a set of functions to interact with stations."""

    def __call__(self, station_id: int) -> Station:
        """Return a lazy instance of :class:`.Station`.

        :param station_id: The numeric identifier of the station.

        Example usage:

        .. code-block:: python

            station = deye.station(322)
            print(station.station_name)

        """
        return Station(self._deyecloud, station_id=station_id)

    def list(
        self,
        *,
        keyword: str | None = None,
        limit: int | None = None,
        page_size: int = 20,
    ) -> PageGenerator:
        """Fetch the stations accessible to the account.

        :param keyword: An optional keyword to filter stations by (default: ``None``).
        :param limit: The maximum number of stations to fetch (default: ``None``).
        :param page_size: The number of stations requested per page (default: ``20``).

        :returns: A generator that yields :class:`.Station` instances.

        """
        body: dict[str, Any] = {}
        if keyword:
            body["keyword"] = keyword
        return PageGenerator(
            self._deyecloud, path=API_PATH["station_list"], json=body, limit=limit, page_size=page_size
        )

    def with_devices(
        self,
        *,
        device_type: str | None = None,
        limit: int | None = None,
        page_size: int = 20,
    ) -> PageGenerator:
        """Fetch stations together with their devices.

        :param device_type: An optional device type filter, e.g. ``"INVERTER"``.
        :param limit: The maximum number of stations to fetch (default: ``None``).
        :param page_size: The number of stations requested per page (default: ``20``).

        """
        body: dict[str, Any] = {}
        if device_type:
            body["deviceType"] = device_type
        return PageGenerator(
            self._deyecloud,
            path=API_PATH["station_list_with_device"],
            json=body,
            limit=limit,
            page_size=page_size,
        )

    def latest(self, station_id: int) -> Station:
        """Fetch the latest telemetry for a single station.

        :param station_id: The numeric identifier of the station.

        :returns: A :class:`.Station` instance carrying the latest telemetry.

        Example usage:

        .. code-block:: python

            station = deye.station.latest(322)
            print(station.generation_power)

        """
        body = {"stationId": station_id}
        data = self._deyecloud.request(method="POST", json=body, path=API_PATH["station_latest"])
        if not isinstance(data, dict):
            data = {}
        return Station(self._deyecloud, _data={"station_id": station_id, **snake_case_keys(data)}, _fetched=True)

    def history(
        self,
        station_id: int,
        granularity: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Fetch historical data for a station.

        :param station_id: The numeric identifier of the station.
        :param granularity: One of ``"frame"``, ``"day"``, ``"month"``, or ``"year"``.
        :param start_date: The start date, e.g. ``"2024-01-01"``.
        :param end_date: The end date, e.g. ``"2024-01-31"``.

        Additional keyword arguments are merged into the request body.

        """
        if granularity not in STATION_HISTORY_GRANULARITY:
            raise InvalidParameterValue("granularity", granularity, set(STATION_HISTORY_GRANULARITY))
        body: dict[str, Any] = {
            "stationId": station_id,
            "granularity": STATION_HISTORY_GRANULARITY[granularity],
        }
        if start_date:
            body["startDate"] = start_date
        if end_date:
            body["endDate"] = end_date
        body.update(kwargs)
        return self._deyecloud.post(API_PATH["station_history"], json=body)

    def history_power(self, station_id: int, start_timestamp: int, end_timestamp: int) -> Any:
        """Fetch power history for a station within a Unix timestamp range.

        :param station_id: The numeric identifier of the station.
        :param start_timestamp: The start timestamp, in seconds.
        :param end_timestamp: The end timestamp, in seconds.

        """
        body = {
            "stationId": station_id,
            "startTimestamp": start_timestamp,
            "endTimestamp": end_timestamp,
        }
        return self._deyecloud.post(API_PATH["station_history_power"], json=body)

    def alerts(
        self,
        station_id: int,
        start_timestamp: int,
        end_timestamp: int,
        *,
        limit: int | None = None,
        page_size: int = 20,
    ) -> PageGenerator:
        """Fetch alerts raised within a station.

        :param station_id: The numeric identifier of the station.
        :param start_timestamp: The start timestamp, in seconds.
        :param end_timestamp: The end timestamp, in seconds.
        :param limit: The maximum number of alerts to fetch (default: ``None``).
        :param page_size: The number of alerts requested per page (default: ``20``).

        """
        body = {"stationId": station_id, "startTimestamp": start_timestamp, "endTimestamp": end_timestamp}
        return PageGenerator(
            self._deyecloud, path=API_PATH["station_alert_list"], json=body, limit=limit, page_size=page_size
        )

    def devices(
        self,
        station_ids: list[int] | int,
        *,
        device_type: str | None = None,
        limit: int | None = None,
        page_size: int = 20,
    ) -> PageGenerator:
        """Fetch the devices registered under one or more stations.

        :param station_ids: A station id or a list of up to 10 station ids.
        :param device_type: An optional device type filter (default: ``None``).
        :param limit: The maximum number of devices to fetch (default: ``None``).
        :param page_size: The number of devices requested per page (default: ``20``).

        """
        ids = _as_list(station_ids)
        if len(ids) > 10:
            msg = "A maximum of 10 station ids can be requested at a time."
            raise ValueError(msg)
        body: dict[str, Any] = {"stationIds": ids}
        if device_type:
            body["deviceType"] = device_type
        return PageGenerator(
            self._deyecloud, path=API_PATH["station_device"], json=body, limit=limit, page_size=page_size
        )

    def create(
        self,
        *,
        station_name: str,
        country_code: str,
        timezone: str,
        currency: str,
        capacity: float,
        **kwargs: Any,
    ) -> Any:
        """Create a new station.

        :param station_name: The name of the station.
        :param country_code: The ISO 3166 alpha-2 country code.
        :param timezone: The IANA timezone of the station, e.g. ``"Europe/Istanbul"``.
        :param currency: The ISO 4217 currency code.
        :param capacity: The capacity of the station, in kW.

        Additional keyword arguments are merged into the request body.

        :returns: The newly created :class:`.Station`.

        """
        body: dict[str, Any] = {
            "stationName": station_name,
            "countryCode": country_code,
            "timeZone": timezone,
            "currency": currency,
            "capacity": capacity,
        }
        body.update(kwargs)
        return self._deyecloud.post(API_PATH["station_create"], json=body)


class DeviceHelper(DeyeBase):
    """Provide a set of functions to interact with devices."""

    def __call__(self, device_sn: str) -> Device:
        """Return a lazy instance of :class:`.Device`.

        :param device_sn: The serial number of the device.

        Example usage:

        .. code-block:: python

            device = deye.device("12583SS")
            print(device.device_type)

        """
        return Device(self._deyecloud, device_sn=device_sn)

    def list(
        self,
        *,
        keyword: str | None = None,
        limit: int | None = None,
        page_size: int = 20,
    ) -> PageGenerator:
        """Fetch the devices accessible to the account (business members only).

        :param keyword: An optional keyword to filter devices by (default: ``None``).
        :param limit: The maximum number of devices to fetch (default: ``None``).
        :param page_size: The number of devices requested per page (default: ``20``).

        """
        body: dict[str, Any] = {}
        if keyword:
            body["keyword"] = keyword
        return PageGenerator(
            self._deyecloud, path=API_PATH["device_list"], json=body, limit=limit, page_size=page_size
        )

    def latest(self, device_sns: list[str] | str, *, device_type: str | None = None) -> Any:
        """Fetch the latest data for one or more devices.

        :param device_sns: A device serial number or a list of up to 10 serial numbers.
        :param device_type: An optional device type used to disambiguate (default: ``None``).

        :returns: A :class:`.Device` instance (when a single sn is given), or a list of
            :class:`.Device` instances.

        """
        sns = _as_list(device_sns)
        if len(sns) > 10:
            msg = "A maximum of 10 device serial numbers can be requested at a time."
            raise ValueError(msg)
        body: dict[str, Any] = {"deviceList": sns}
        if device_type:
            body["deviceType"] = device_type
        result = self._deyecloud.post(API_PATH["device_latest"], json=body)
        if isinstance(device_sns, str):
            return result[0] if isinstance(result, list) and result else result
        return result

    def history(
        self,
        device_sn: str,
        granularity: str,
        *,
        measure_points: list[str] | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Fetch historical data for a device.

        :param device_sn: The serial number of the device.
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
            "deviceSn": device_sn,
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

    def history_raw(self, device_sn: str, start_timestamp: int, end_timestamp: int) -> Any:
        """Fetch raw device history within a Unix timestamp range.

        :param device_sn: The serial number of the device.
        :param start_timestamp: The start timestamp, in seconds.
        :param end_timestamp: The end timestamp, in seconds.

        """
        body = {
            "deviceSn": device_sn,
            "startTimestamp": start_timestamp,
            "endTimestamp": end_timestamp,
        }
        return self._deyecloud.post(API_PATH["device_history_raw"], json=body)

    def measure_points(self, device_sn: str) -> Any:
        """Return the measure points available for a device.

        :param device_sn: The serial number of the device.

        """
        return self._deyecloud.post(API_PATH["device_measure_points"], json={"deviceSn": device_sn})

    def alerts(
        self,
        device_sn: str,
        start_timestamp: int,
        end_timestamp: int,
        *,
        limit: int | None = None,
        page_size: int = 20,
    ) -> PageGenerator:
        """Fetch alerts for a device.

        :param device_sn: The serial number of the device.
        :param start_timestamp: The start timestamp, in seconds.
        :param end_timestamp: The end timestamp, in seconds.
        :param limit: The maximum number of alerts to fetch (default: ``None``).
        :param page_size: The number of alerts requested per page (default: ``20``).

        """
        body = {"deviceSn": device_sn, "startTimestamp": start_timestamp, "endTimestamp": end_timestamp}
        return PageGenerator(
            self._deyecloud, path=API_PATH["device_alert_list"], json=body, limit=limit, page_size=page_size
        )

    def register(self, *, device_sn: str, gateway_sn: str, station_id: int) -> Any:
        """Add a datalogger into a station.

        :param device_sn: The serial number of the datalogger.
        :param gateway_sn: The serial number of the gateway.
        :param station_id: The numeric identifier of the station.

        """
        body = {"deviceSn": device_sn, "gatewaySn": gateway_sn, "stationId": station_id}
        return self._deyecloud.post(API_PATH["device_register"], json=body)

    def add_logger(self, device_sns: list[str] | str) -> Any:
        """Add loggers to the business account.

        :param device_sns: A serial number or a list of up to 10 serial numbers.

        """
        sns = _as_list(device_sns)
        if len(sns) > 10:
            msg = "A maximum of 10 loggers can be added at a time."
            raise ValueError(msg)
        return self._deyecloud.post(API_PATH["device_add_logger"], json={"deviceSnList": sns})

    def delete_logger(self, device_sns: list[str] | str) -> Any:
        """Remove loggers from the business account.

        :param device_sns: A serial number or a list of up to 10 serial numbers.

        """
        sns = _as_list(device_sns)
        if len(sns) > 10:
            msg = "A maximum of 10 loggers can be removed at a time."
            raise ValueError(msg)
        return self._deyecloud.post(API_PATH["device_delete_logger"], json={"deviceSnList": sns})


class OrderHelper(DeyeBase):
    """Provide a set of functions to send control commands and inspect their results."""

    def __call__(self, order_id: str) -> Order:
        """Return a lazy instance of :class:`.Order`.

        :param order_id: The identifier of the control command.

        Example usage:

        .. code-block:: python

            order = deye.order("123456")
            print(order.status)

        """
        return Order(self._deyecloud, order_id=order_id)

    def result(self, order_id: str) -> Order:
        """Fetch the result of a control command.

        :param order_id: The identifier of the control command.

        """
        return self._deyecloud.get(API_PATH["order_result"].format(order_id=order_id))

    def custom_control(self, *, device_sn: str, content: str, timeout_seconds: int | None = None) -> Order:
        """Send a raw Modbus protocol command to a device.

        :param device_sn: The serial number of the device.
        :param content: The raw Modbus protocol content, e.g. ``"0103000102ABCD"``.
        :param timeout_seconds: The command timeout, between 10 and 600 (default: ``None``).

        """
        body: dict[str, Any] = {"deviceSn": device_sn, "content": content}
        if timeout_seconds is not None:
            body["timeoutSeconds"] = timeout_seconds
        return self._deyecloud.post(API_PATH["order_custom_control"], json=body)

    def battery_mode(self, *, device_sn: str, charge_mode: str, enable: bool) -> Order:
        """Enable or disable a battery charge mode.

        :param device_sn: The serial number of the device.
        :param charge_mode: Either ``"GRID_CHARGE"`` or ``"GEN_CHARGE"``.
        :param enable: Whether to enable the charge mode.

        """
        _validate(charge_mode, "charge_mode", {"GRID_CHARGE", "GEN_CHARGE"})
        body = {"deviceSn": device_sn, "chargeMode": charge_mode, "enable": enable}
        return self._deyecloud.post(API_PATH["order_battery_mode"], json=body)

    def battery_parameter(
        self,
        *,
        device_sn: str,
        parameter: str,
        value: float,
    ) -> Order:
        """Update a battery parameter.

        :param device_sn: The serial number of the device.
        :param parameter: One of ``"MAX_CHARGE_CURRENT"``, ``"MAX_DISCHARGE_CURRENT"``,
            ``"GRID_CHARGE_AMPERE"``, or ``"BATT_LOW"`` (minimum battery SOC).
        :param value: The new value of the parameter.

        """
        _validate(parameter, "parameter", BATTERY_PARAMETERS)
        body = {"deviceSn": device_sn, "paramterType": parameter, "value": value}
        return self._deyecloud.post(API_PATH["order_battery_parameter"], json=body)

    def battery_type(self, *, device_sn: str, battery_type: str) -> Order:
        """Set the battery type of a device.

        :param device_sn: The serial number of the device.
        :param battery_type: One of ``"BATT_V"``, ``"BATT_SOC"``, ``"LI"``, or
            ``"NO_BATTERY"`` (availability depends on the inverter model).

        """
        _validate(battery_type, "battery_type", BATTERY_TYPES)
        body = {"deviceSn": device_sn, "batteryType": battery_type}
        return self._deyecloud.post(API_PATH["order_battery_type"], json=body)

    def grid_peak_shaving(self, *, device_sn: str, enable: bool) -> Order:
        """Enable or disable grid peak shaving.

        :param device_sn: The serial number of the device.
        :param enable: Whether to enable grid peak shaving.

        """
        body = {"deviceSn": device_sn, "enable": enable}
        return self._deyecloud.post(API_PATH["order_grid_peak_shaving"], json=body)

    def smartload(self, *, device_sn: str, **settings: Any) -> Order:
        """Update smart load parameters.

        :param device_sn: The serial number of the device.

        Additional keyword arguments are merged into the request body.

        """
        body = {"deviceSn": device_sn}
        body.update(settings)
        return self._deyecloud.post(API_PATH["order_smartload"], json=body)

    def energy_pattern(self, *, device_sn: str, energy_pattern: str) -> Order:
        """Set the energy pattern of a device.

        :param device_sn: The serial number of the device.
        :param energy_pattern: Either ``"BATTERY_FIRST"`` or ``"LOAD_FIRST"``.

        """
        _validate(energy_pattern, "energy_pattern", ENERGY_PATTERNS)
        body = {"deviceSn": device_sn, "energyPattern": energy_pattern}
        return self._deyecloud.post(API_PATH["order_energy_pattern"], json=body)

    def limit_control(self, *, device_sn: str, limit_control: str) -> Order:
        """Set the limit control mode (Micro ESS only).

        :param device_sn: The serial number of the device.
        :param limit_control: One of ``"SELL_FIRST"``, ``"ZERO_EXPORT_TO_UPS_LOAD"``,
            ``"ZERO_EXPORT_TO_CT"``, or ``"ZERO_EXPORT_TO_WIRELESS_CT"``.

        """
        _validate(limit_control, "limit_control", LIMIT_CONTROL_MODES)
        body = {"deviceSn": device_sn, "limitControl": limit_control}
        return self._deyecloud.post(API_PATH["order_limit_control"], json=body)

    def power(self, *, device_sn: str, power: str, value: float) -> Order:
        """Set a system power limit.

        :param device_sn: The serial number of the device.
        :param power: One of ``"MAX_SELL_POWER"``, ``"MAX_SOLAR_POWER"``, or
            ``"ZERO_EXPORT_POWER"``.
        :param value: The power value, in watts.

        """
        _validate(power, "power", {"MAX_SELL_POWER", "MAX_SOLAR_POWER", "ZERO_EXPORT_POWER"})
        body = {"deviceSn": device_sn, "power": power, "value": value}
        return self._deyecloud.post(API_PATH["order_power_update"], json=body)

    def solar_sell(self, *, device_sn: str, enable: bool) -> Order:
        """Enable or disable solar selling.

        :param device_sn: The serial number of the device.
        :param enable: Whether to enable solar selling.

        """
        body = {"deviceSn": device_sn, "enable": enable}
        return self._deyecloud.post(API_PATH["order_solar_sell"], json=body)

    def tou_switch(self, *, device_sn: str, enable: bool, days: list[str] | None = None) -> Order:
        """Turn time-of-use on or off.

        :param device_sn: The serial number of the device.
        :param enable: Whether to enable time-of-use.
        :param days: An optional list of days, e.g. ``["MONDAY", "TUESDAY"]``.

        """
        if days is not None:
            for day in days:
                _validate(day, "days", set(WEEKDAYS))
        body: dict[str, Any] = {"deviceSn": device_sn, "enable": enable}
        if days is not None:
            body["days"] = days
        return self._deyecloud.post(API_PATH["order_tou_switch"], json=body)

    def tou_update(self, *, device_sn: str, intervals: list[dict[str, Any]]) -> Order:
        """Set the time-of-use schedule.

        :param device_sn: The serial number of the device.
        :param intervals: A list of six interval dicts, in sequence, each with keys such
            as ``time`` (5 minute steps, e.g. ``"02:05"``), ``power``, ``soc``, and
            ``voltage``.

        """
        if len(intervals) != 6:
            msg = "Exactly 6 time-of-use intervals must be provided."
            raise ValueError(msg)
        body = {"deviceSn": device_sn, "timeUseSettingItems": intervals}
        return self._deyecloud.post(API_PATH["order_tou_update"], json=body)

    def work_mode(self, *, device_sn: str, work_mode: str) -> Order:
        """Set the system work mode.

        :param device_sn: The serial number of the device.
        :param work_mode: One of ``"SELLING_FIRST"``, ``"ZERO_EXPORT_TO_LOAD"``, or
            ``"ZERO_EXPORT_TO_CT"`` (micro storage additionally supports
            ``"GREEN_POWER_MODE"``, ``"FULL_CHARGE_MODE"``, and ``"CUSTOMIZED_MODE"``).

        """
        valid = WORK_MODES | {
            "GREEN_POWER_MODE",
            "FULL_CHARGE_MODE",
            "CUSTOMIZED_MODE",
        }
        _validate(work_mode, "work_mode", valid)
        body = {"deviceSn": device_sn, "workMode": work_mode}
        return self._deyecloud.post(API_PATH["order_work_mode"], json=body)


class SystemHelper(DeyeBase):
    """Provide read-only access to a device's configuration.

    Corresponds to the "Configuration Operation" group of the API.

    """

    def battery(self, *, device_sn: str) -> Any:
        """Return the battery parameters of a device.

        :param device_sn: The serial number of the device.

        """
        return self._deyecloud.post(API_PATH["config_battery"], json={"deviceSn": device_sn})

    def system(self, *, device_sn: str) -> Any:
        """Return the system work mode parameters of a device.

        :param device_sn: The serial number of the device.

        """
        return self._deyecloud.post(API_PATH["config_system"], json={"deviceSn": device_sn})

    def tou(self, *, device_sn: str) -> Any:
        """Return the time-of-use configuration of a device.

        :param device_sn: The serial number of the device.

        """
        return self._deyecloud.post(API_PATH["config_tou"], json={"deviceSn": device_sn})


class StrategyHelper(DeyeBase):
    """Provide a set of functions to interact with dynamic control strategies."""

    def dynamic_control(self, *, device_sn: str, **settings: Any) -> Order:
        """Set dynamic control parameters for a device.

        :param device_sn: The serial number of the device.

        Additional keyword arguments are merged into the request body (e.g. work mode,
        TOU, grid charge, sell power, and solar sell settings).

        :returns: An :class:`.Order` representing the issued command.

        """
        body = {"deviceSn": device_sn}
        body.update(settings)
        return self._deyecloud.post(API_PATH["strategy_dynamic_control"], json=body)

    def read(self, *, device_sn: str) -> Order:
        """Send a read command for the current dynamic control parameters.

        :param device_sn: The serial number of the device.

        :returns: An :class:`.Order` whose result can be polled.

        """
        return self._deyecloud.post(API_PATH["strategy_dynamic_control_read"], json={"deviceSn": device_sn})

    def read_result(self, order_id: str) -> Any:
        """Fetch the result of a previous :meth:`read` command.

        :param order_id: The identifier of the read command.

        """
        return self._deyecloud.post(API_PATH["strategy_dynamic_control_result"], json={"orderId": order_id})
