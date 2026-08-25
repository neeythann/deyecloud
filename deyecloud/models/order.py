"""Provide the Order class.

An :class:`.Order` represents an asynchronous control command sent to a device. The
Deye Cloud API accepts a command and immediately returns an ``orderId``; the actual
result must be fetched later via ``GET /v1.0/order/{orderId}``.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.const import ORDER_STATUS
from deyecloud.endpoints import API_PATH
from deyecloud.models.base import DeyeModelBase
from deyecloud.util.snake import snake_case_keys

if TYPE_CHECKING:
    import deyecloud


class Order(DeyeModelBase):
    """A class representing the result of a control command sent to a device.

    .. note::

        Instances obtained via ``deye.order(order_id)`` are lazily loaded; the command
        result is fetched from ``GET /v1.0/order/{order_id}`` on first attribute access.

    """

    STR_FIELD = "order_id"

    def __init__(
        self,
        deyecloud: deyecloud.DeyeCloud,
        order_id: str | None = None,
        _data: dict[str, Any] | None = None,
        _fetched: bool = False,
    ) -> None:
        """Initialize an :class:`.Order` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.
        :param order_id: The identifier of the control command.

        """
        if order_id is not None and _data is None:
            _data = {"order_id": order_id}
        super().__init__(deyecloud, _data=_data, _fetched=_fetched)

    def _fetch(self) -> None:
        """Populate the instance with the order result."""
        data = self._fetch_data()
        if isinstance(data, dict):
            self.__dict__.update(snake_case_keys(data))
        self._fetched = True

    def _fetch_data(self) -> Any:
        name, fields, _body = self._fetch_info()
        path = API_PATH[name].format(**fields)
        return self._deyecloud.request(method="GET", path=path)

    def _fetch_info(self) -> tuple[str, dict[str, Any], dict[str, Any]]:
        return ("order_result", {"order_id": self.order_id}, {})

    def refresh(self) -> Order:
        """Re-fetch the order result from the API and return ``self``."""
        self._reset_attributes("orderResult", "analysisResult", "status", "error", "collectionTime")
        self._fetch()
        return self

    @property
    def succeeded(self) -> bool:
        """Whether the command completed successfully."""
        return int(getattr(self, "status", 0)) == 666

    @property
    def failed(self) -> bool:
        """Whether the command failed."""
        return int(getattr(self, "status", 0)) in {400, 500}

    @property
    def status_name(self) -> str | None:
        """The human readable name of the current command status."""
        return ORDER_STATUS.get(int(getattr(self, "status", 0)))
