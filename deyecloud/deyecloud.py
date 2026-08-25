"""Provide the DeyeCloud class.

The :class:`.DeyeCloud` class is the gateway to interacting with the Deye Cloud API,
mirroring how :class:`.Reddit` is the gateway for PRAW.

"""

from __future__ import annotations

import configparser
import os
from typing import TYPE_CHECKING, Any

from deyecloud import models
from deyecloud.config import Config
from deyecloud.core import DeyeCloudAuthorizer, DeyeCloudRequestor, DeyeCloudSession
from deyecloud.exceptions import ClientException
from deyecloud.objector import Objector

if TYPE_CHECKING:
    from collections.abc import Mapping


class DeyeCloud:
    """The DeyeCloud class provides convenient access to the Deye Cloud API.

    Instances of this class are the gateway to interacting with the Deye Cloud API
    through the client. The canonical way to obtain an instance of this class is via:

    .. code-block:: python

        import deyecloud

        deye = deyecloud.DeyeCloud(
            app_id="201911067156002",
            app_secret="APPSECRET",
            email="user@example.com",
            password="PASSWORD",
        )

    """

    def __init__(
        self,
        site_name: str | None = None,
        *,
        config_interpolation: str | None = None,
        requestor_class: type[DeyeCloudRequestor] | None = None,
        requestor_kwargs: dict[str, Any] | None = None,
        **config_settings: str | bool | int | None,
    ) -> None:
        """Initialize a :class:`.DeyeCloud` instance.

        :param site_name: The name of a section in your ``deye.ini`` file from which to
            load settings from. If ``site_name`` is ``None``, the site name will be
            looked for in the environment variable ``deye_site``, falling back to the
            ``DEFAULT`` section (default: ``None``).
        :param config_interpolation: Config parser interpolation type that will be
            passed to :class:`.Config` (default: ``None``).
        :param requestor_class: A class that will be used to create a requestor. If not
            set, use :class:`.DeyeCloudRequestor` (default: ``None``).
        :param requestor_kwargs: Dictionary with additional keyword arguments used to
            initialize the requestor (default: ``None``).

        Additional keyword arguments will be used to initialize the :class:`.Config`
        object. This can be used to specify configuration settings during instantiation.

        Required settings are:

        - ``app_id``
        - ``app_secret``
        - ``password``
        - exactly one of ``email``, ``mobile``, or ``username`` (``country_code`` is
          required when using ``mobile``)

        """
        self._objector: Objector
        self._core: DeyeCloudSession

        try:
            config_section = site_name or os.getenv("deye_site") or "DEFAULT"
            self.config = Config(config_section, config_interpolation, **config_settings)
        except configparser.NoSectionError as exc:
            help_message = (
                "You provided the name of a deye.ini configuration which does not"
                " exist.\n\nFor help with creating a DeyeCloud instance, visit the"
                " project documentation."
            )
            if site_name is not None:
                exc.message += f"\n{help_message}"
            raise

        self.config.validate()

        self._prepare_objector()
        self._prepare_core(requestor_class=requestor_class, requestor_kwargs=requestor_kwargs)

        self.account = models.AccountHelper(self, None)
        """An instance of :class:`.AccountHelper`.

        Provides the interface for interacting with the authenticated account. For
        example, to list the organizations associated with the account:

        .. code-block:: python

            for org in deye.account.info():
                print(org.company_name)

        """

        self.station = models.StationHelper(self, None)
        """An instance of :class:`.StationHelper`.

        Provides the interface for working with :class:`.Station` instances. For
        example, to obtain a lazy station and print its name:

        .. code-block:: python

            station = deye.station(322)
            print(station.station_name)

        To fetch the latest data for several stations at once:

        .. code-block:: python

            stations = deye.station.latest([322, 323])
            for station in stations:
                print(station.battery_soc)

        """

        self.device = models.DeviceHelper(self, None)
        """An instance of :class:`.DeviceHelper`.

        Provides the interface for working with :class:`.Device` instances. For
        example, to obtain a lazy device and print its type:

        .. code-block:: python

            device = deye.device("12583SS")
            print(device.device_type)

        To fetch the latest data for several devices at once:

        .. code-block:: python

            devices = deye.device.latest(["12583SS", "2401110313"])
            for device in devices:
                print(device.device_state)

        """

        self.order = models.OrderHelper(self, None)
        """An instance of :class:`.OrderHelper`.

        Provides the interface for sending control commands to devices and for
        inspecting the asynchronous command results. For example:

        .. code-block:: python

            order = deye.order.work_mode(device_sn="12583SS", work_mode="SELLING_FIRST")
            print(order.order_id)

        """

        self.system = models.SystemHelper(self, None)
        """An instance of :class:`.SystemHelper`.

        Provides read-only access to a device's configuration. For example:

        .. code-block:: python

            battery = deye.system.battery(device_sn="12583SS")
            print(battery.batt_low_capacity)

        """

        self.strategy = models.StrategyHelper(self, None)
        """An instance of :class:`.StrategyHelper`.

        Provides the interface for dynamic control strategies. For example:

        .. code-block:: python

            order = deye.strategy.read(device_sn="12583SS")
            result = deye.strategy.read_result(order.order_id)

        """

    def _prepare_objector(self) -> None:
        parsers = {
            "Device": models.Device,
            "DeviceAlert": models.DeviceAlert,
            "Order": models.Order,
            "OrgInfo": models.OrgInfo,
            "Station": models.Station,
            "StationAlert": models.StationAlert,
        }
        self._objector = Objector(self, parsers)

    def _prepare_core(
        self,
        *,
        requestor_class: type[DeyeCloudRequestor] | None = None,
        requestor_kwargs: dict[str, Any] | None = None,
    ) -> None:
        requestor_class = requestor_class or DeyeCloudRequestor
        requestor_kwargs = requestor_kwargs or {}
        requestor = requestor_class(timeout=self.config.timeout, **requestor_kwargs)

        authorizer = DeyeCloudAuthorizer(
            app_id=self.config.app_id,
            app_secret=self.config.app_secret,
            base_url=self.config.base_url,
            email=self.config.email,
            mobile=self.config.mobile,
            country_code=self.config.country_code,
            username=self.config.username,
            password=self.config.password,
            company_id=self.config.company_id,
            requestor=requestor,
        )
        self._core = DeyeCloudSession(authorizer=authorizer, requestor=requestor)

    def _objectify_request(
        self,
        *,
        data: Mapping[str, Any] | None = None,
        json: dict[Any, Any] | list[Any] | None = None,
        method: str = "",
        params: Mapping[str, str | int] | None = None,
        path: str = "",
    ) -> Any:
        """Run a request through the ``Objector``.

        :param data: Dictionary to send in the body of the request (default: ``None``).
        :param json: JSON-serializable object to send in the body of the request
            (default: ``None``). If ``json`` is provided, ``data`` should not be.
        :param method: The HTTP method (e.g., ``"GET"``, ``"POST"``).
        :param params: The query parameters to add to the request (default: ``None``).
        :param path: The path to fetch.

        """
        return self._objector.objectify(
            data=self.request(
                data=data,
                json=json,
                method=method,
                params=params,
                path=path,
            )
        )

    def _paginate(
        self,
        *,
        path: str,
        json: dict[str, Any] | None = None,
        params: Mapping[str, str | int] | None = None,
        limit: int | None = None,
        page_size: int = 20,
    ) -> models.PageGenerator:
        """Return a :class:`.PageGenerator` for a list-style endpoint."""
        return models.PageGenerator(
            self,
            path=path,
            json=json,
            params=params,
            limit=limit,
            page_size=page_size,
        )

    def get(
        self,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
    ) -> Any:
        """Return parsed objects returned from a GET request to ``path``.

        :param path: The path to fetch.
        :param params: The query parameters to add to the request (default: ``None``).

        """
        return self._objectify_request(method="GET", params=params, path=path)

    def post(
        self,
        path: str,
        *,
        data: Mapping[str, Any] | None = None,
        json: dict[Any, Any] | list[Any] | None = None,
        params: Mapping[str, str | int] | None = None,
    ) -> Any:
        """Return parsed objects returned from a POST request to ``path``.

        :param path: The path to fetch.
        :param data: Dictionary to send in the body of the request (default: ``None``).
        :param json: JSON-serializable object to send in the body of the request
            (default: ``None``). If ``json`` is provided, ``data`` should not be.
        :param params: The query parameters to add to the request (default: ``None``).

        """
        return self._objectify_request(data=data, json=json, method="POST", params=params, path=path)

    def request(
        self,
        *,
        data: Mapping[str, Any] | None = None,
        json: dict[Any, Any] | list[Any] | None = None,
        method: str,
        params: Mapping[str, str | int] | None = None,
        path: str,
    ) -> Any:
        """Return the parsed JSON data returned from a request to ``path``.

        :param data: Dictionary to send in the body of the request (default: ``None``).
        :param json: JSON-serializable object to send in the body of the request
            (default: ``None``). If ``json`` is provided, ``data`` should not be.
        :param method: The HTTP method (e.g., ``"GET"``, ``"POST"``).
        :param params: The query parameters to add to the request (default: ``None``).
        :param path: The path to fetch.

        """
        if data and json:
            msg = "At most one of 'data' or 'json' is supported."
            raise ClientException(msg)
        return self._core.request(
            data=data,
            json=json,
            method=method,
            params=params,
            path=path,
        )
