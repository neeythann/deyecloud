"""Provide the stream classes.

The Deye Cloud API is pull-based, so streams poll the latest telemetry for a station or
device and yield a snapshot whenever a new sample (identified by its timestamp) becomes
available. This mirrors PRAW's ``SubredditStream`` / ``RedditorStream`` pattern.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.models.util import stream_generator

if TYPE_CHECKING:
    from collections.abc import Iterator

    from deyecloud.models.device import Device
    from deyecloud.models.station import Station


class StationStream:
    """Provides a stream of live station telemetry."""

    def __init__(self, station: Station) -> None:
        """Initialize a :class:`.StationStream` instance.

        :param station: The station associated with the stream.

        """
        self.station = station

    def latest(self, **stream_options: Any) -> Iterator[Station]:
        """Yield station telemetry snapshots as they are updated.

        Snapshots are yielded whenever the station's ``lastUpdateTime`` advances.
        Keyword arguments are passed to :func:`.stream_generator`.

        .. note::

            The first call returns the current telemetry, unless ``skip_existing`` is
            passed.

        For example, to monitor a station's generation power:

        .. code-block:: python

            station = deye.station(322)
            for snapshot in station.stream.latest():
                print(snapshot.generation_power)

        To only report changes starting after the stream is created, pass
        ``skip_existing=True``:

        .. code-block:: python

            for snapshot in station.stream.latest(skip_existing=True):
                print(snapshot.generation_power)

        """
        return stream_generator(
            lambda **kwargs: [self.station.latest()],
            attribute_name="last_update_time",
            **stream_options,
        )


class DeviceStream:
    """Provides a stream of live device telemetry."""

    def __init__(self, device: Device) -> None:
        """Initialize a :class:`.DeviceStream` instance.

        :param device: The device associated with the stream.

        """
        self.device = device

    def latest(self, **stream_options: Any) -> Iterator[Device]:
        """Yield device telemetry snapshots as they are updated.

        Snapshots are yielded whenever the device's ``collectionTime`` advances.
        Keyword arguments are passed to :func:`.stream_generator`.

        .. note::

            The first call returns the current telemetry, unless ``skip_existing`` is
            passed.

        For example, to monitor a device's state:

        .. code-block:: python

            device = deye.device("12583SS")
            for snapshot in device.stream.latest():
                print(snapshot.device_state)

        """
        return stream_generator(
            lambda **kwargs: [self.device.latest()],
            attribute_name="collection_time",
            **stream_options,
        )
