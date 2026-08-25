"""Python Deye Cloud API Wrapper.

A Python package that provides convenient access to the Deye Cloud API. The design is
modeled after PRAW (Python Reddit API Wrapper): a central :class:`.DeyeCloud` instance
provides lazy, object-oriented access to stations, devices, and control commands.

Example usage:

.. code-block:: python

    import deyecloud

    deye = deyecloud.DeyeCloud(
        app_id="201911067156002",
        app_secret="APPSECRET",
        email="user@example.com",
        password="PASSWORD",
    )

    for station in deye.station.list():
        print(station.station_name, station.battery_soc)

"""

from deyecloud.const import __version__
from deyecloud.deyecloud import DeyeCloud

__all__ = ["DeyeCloud", "__version__"]
