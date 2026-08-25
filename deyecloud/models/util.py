"""Provide helper classes used by other models.

The :class:`.BoundedSet`, :class:`.ExponentialCounter`, and the
:func:`.stream_generator` pattern are derived from PRAW (praw/models/util.py),
Copyright (c) 2016, Bryce Boe, licensed under the BSD 2-Clause License. See the NOTICE
file for the full license text.

"""

from __future__ import annotations

import random
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


class BoundedSet:
    """A set with a maximum size that evicts the oldest items when necessary.

    This class does not implement the complete set interface.

    """

    def __contains__(self, item: Any) -> bool:
        """Test if the :class:`.BoundedSet` contains item."""
        self._access(item)
        return item in self._set

    def __init__(self, max_items: int) -> None:
        """Initialize a :class:`.BoundedSet` instance."""
        self.max_items = max_items
        self._set = OrderedDict()

    def _access(self, item: Any) -> None:
        if item in self._set:
            self._set.move_to_end(item)

    def add(self, item: Any) -> None:
        """Add an item to the set discarding the oldest item if necessary."""
        self._access(item)
        self._set[item] = None
        if len(self._set) > self.max_items:
            self._set.popitem(last=False)


class ExponentialCounter:
    """A class to provide an exponential counter with jitter."""

    def __init__(self, max_counter: int) -> None:
        """Initialize an :class:`.ExponentialCounter` instance.

        :param max_counter: The maximum base value.

            .. note::

                The computed value may be 3.125% higher due to jitter.

        """
        self._base = 1
        self._max = max_counter

    def counter(self) -> int | float:
        """Increment the counter and return the current value with jitter."""
        max_jitter = self._base / 16.0
        value = self._base + random.random() * max_jitter - max_jitter / 2  # ruff:ignore[suspicious-non-cryptographic-random-usage]
        self._base = min(self._base * 2, self._max)
        return value

    def reset(self) -> None:
        """Reset the counter to 1."""
        self._base = 1


def stream_generator(
    function: Callable,
    *,
    attribute_name: str = "collection_time",
    exception_handler: Callable[[Exception], None] | None = None,
    pause_after: int | None = None,
    skip_existing: bool = False,
    **function_kwargs: Any,
) -> Iterator[Any]:
    """Yield new items from ``function`` as they become available.

    :param function: A callable that returns an iterable of items, e.g. a function
        wrapping :meth:`.Station.latest` or :meth:`.Device.latest`.
    :param attribute_name: The field to use as an ID (default: ``"collection_time"``).
    :param exception_handler: A callable that is invoked with the exception raised while
        fetching items, instead of letting it propagate and terminate the stream. After
        the handler returns, the stream waits (using the same exponential backoff
        applied to empty responses) and then resumes. To stop the stream, re-raise the
        exception (or raise a new one) from within the handler. When ``None``,
        exceptions propagate and terminate the stream as before (default: ``None``).
    :param pause_after: An integer representing the number of requests that result in no
        new items before this function yields ``None``, effectively introducing a pause
        into the stream. A negative value yields ``None`` after items from a single
        response have been yielded, regardless of number of new items obtained in that
        response. A value of ``0`` yields ``None`` after every response resulting in no
        new items, and a value of ``None`` never introduces a pause (default: ``None``).
    :param skip_existing: When ``True``, this does not yield any results from the first
        request thereby skipping any items that existed prior to starting the stream
        (default: ``False``).

    Additional keyword arguments will be passed to ``function``.

    .. note::

        This function internally uses an exponential delay with jitter between
        subsequent responses that contain no new results, up to a maximum delay of just
        over 16 seconds. In practice, that means that the time before pause for
        ``pause_after=N+1`` is approximately twice the time before pause for
        ``pause_after=N``.

    The Deye Cloud API is pull-based, so a stream polls the latest telemetry and yields
    an item whenever the ``attribute_name`` value changes (e.g. a new ``collectionTime``
    sample). Items whose attribute value has already been seen are skipped.

    For example, to monitor a station's live telemetry:

    .. code-block:: python

        station = deye.station(322)
        for snapshot in station.stream.latest():
            print(snapshot.generation_power)

    To stop a stream after a period of no changes, use ``pause_after``:

    .. code-block:: python

        for snapshot in station.stream.latest(pause_after=6):
            if snapshot is None:
                break
            print(snapshot.generation_power)

    To keep a stream alive across transient errors rather than having it terminate,
    pass an ``exception_handler``:

    .. code-block:: python

        def log_exception(exception):
            print(f"Stream error, retrying: {exception}")

        for snapshot in station.stream.latest(exception_handler=log_exception):
            print(snapshot.generation_power)

    """
    exponential_counter = ExponentialCounter(max_counter=16)
    seen_attributes = BoundedSet(301)
    responses_without_new = 0
    valid_pause_after = pause_after is not None
    skip_first = skip_existing
    while True:
        found = False
        try:
            items = list(function(**function_kwargs))
        except Exception as exception:
            if exception_handler is None:
                raise
            exception_handler(exception)
            time.sleep(exponential_counter.counter())
            continue
        for item in reversed(items):
            attribute = getattr(item, attribute_name, None)
            if attribute is None:
                continue
            if attribute in seen_attributes:
                continue
            found = True
            seen_attributes.add(attribute)
            if not skip_first:
                yield item
        skip_first = False
        if valid_pause_after and pause_after < 0:
            yield None
        elif found:
            exponential_counter.reset()
            responses_without_new = 0
        else:
            responses_without_new += 1
            if valid_pause_after and responses_without_new > pause_after:
                exponential_counter.reset()
                responses_without_new = 0
                yield None
            else:
                time.sleep(exponential_counter.counter())
