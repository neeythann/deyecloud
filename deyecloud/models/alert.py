"""Provide the device and station alert classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.models.base import DeyeBase

if TYPE_CHECKING:
    import deyecloud


class AlertMixin:
    """Shared convenience properties for alert objects."""

    @property
    def is_open(self) -> bool:
        """Whether the alert is currently open."""
        return getattr(self, "status", 0) in {1, "1", "OPEN"}

    @property
    def level_name(self) -> str:
        """The human readable name of the alert level."""
        return {0: "NOTICE", 1: "WARNING", 2: "FAILURE"}.get(getattr(self, "level", None), "UNKNOWN")


class DeviceAlert(AlertMixin, DeyeBase):
    """A class representing an alert raised by a device."""

    def __str__(self) -> str:
        """Return a string representation of the instance."""
        return f"{getattr(self, 'alertCode', '')} ({getattr(self, 'deviceSn', '')})"

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return f"DeviceAlert(alertId={getattr(self, 'alertId', None)!r}, deviceSn={getattr(self, 'deviceSn', None)!r})"


class StationAlert(AlertMixin, DeyeBase):
    """A class representing an alert raised within a station."""

    def __str__(self) -> str:
        """Return a string representation of the instance."""
        return f"{getattr(self, 'alertCode', '')} ({getattr(self, 'stationId', '')})"

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return f"StationAlert(alertId={getattr(self, 'alertId', None)!r}, stationId={getattr(self, 'stationId', None)!r})"
