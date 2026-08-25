"""Provide the base model classes."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from deyecloud.endpoints import API_PATH
from deyecloud.util.snake import snake_case_keys

if TYPE_CHECKING:
    import deyecloud


class DeyeBase:
    """Superclass for all models in the client."""

    @staticmethod
    def _safely_add_arguments(*, arguments: dict[str, Any], key: str, **new_arguments: Any) -> None:
        """Replace arguments[key] with a deepcopy and update.

        This method is often called when new parameters need to be added to a request.
        By calling this method and adding the new or updated parameters we can insure we
        don't modify the dictionary passed in by the caller.

        """
        value = deepcopy(arguments[key]) if key in arguments else {}
        value.update(new_arguments)
        arguments[key] = value

    @staticmethod
    def _to_local_datetime(timestamp: float) -> datetime:
        """Return ``timestamp`` as a timezone-aware :class:`datetime.datetime`.

        :param timestamp: A `Unix Time`_ value, in seconds.

        The returned object is localized to the system's timezone.

        .. _unix time: https://en.wikipedia.org/wiki/Unix_time

        """
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone()

    @classmethod
    def parse(cls, data: dict[str, Any], deyecloud: deyecloud.DeyeCloud) -> DeyeBase:
        """Return an instance of ``cls`` from ``data``.

        :param data: The structured data.
        :param deyecloud: An instance of :class:`.DeyeCloud`.

        """
        return cls(deyecloud, _data=data)

    def __init__(self, deyecloud: deyecloud.DeyeCloud, _data: dict[str, Any] | None) -> None:
        """Initialize a :class:`.DeyeBase` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.

        """
        self._deyecloud = deyecloud
        if _data:
            for attribute, value in snake_case_keys(_data).items():
                setattr(self, attribute, value)


class DeyeModelBase(DeyeBase):
    """Base class that represents actual Deye Cloud objects.

    Provides lazy loading: accessing a data attribute not yet fetched triggers a
    request to populate the instance (mirroring :class:`.RedditBase`).

    """

    STR_FIELD: str | None = None

    def __eq__(self, other: Any | str | int) -> bool:
        """Return whether the other instance equals the current."""
        if isinstance(other, (str, int)):
            return other == str(self)
        return isinstance(other, self.__class__) and str(self) == str(other)

    def __getattr__(self, attribute: str) -> Any:
        """Return the value of ``attribute``."""
        if not attribute.startswith("_") and not self._fetched:
            self._fetch()
            return getattr(self, attribute)
        msg = f"{self.__class__.__name__!r} object has no attribute {attribute!r}"
        raise AttributeError(msg)

    def __hash__(self) -> int:
        """Return the hash of the current instance."""
        return hash(self.__class__.__name__) ^ hash(str(self))

    def __init__(
        self,
        deyecloud: deyecloud.DeyeCloud,
        _data: dict[str, Any] | None,
        *,
        _fetched: bool = False,
        _str_field: bool = True,
    ) -> None:
        """Initialize a :class:`.DeyeModelBase` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.

        """
        super().__init__(deyecloud, _data=_data)
        self._fetched = _fetched
        if _str_field and self.STR_FIELD is not None and self.STR_FIELD not in self.__dict__:
            msg = f"An invalid value was specified for {self.STR_FIELD}. Check that the argument for the {self.STR_FIELD} parameter is not empty."
            raise ValueError(msg)

    def __ne__(self, other: object) -> bool:
        """Return whether the other instance differs from the current."""
        return not self == other

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return f"{self.__class__.__name__}({self.STR_FIELD}={str(self)!r})"

    def __str__(self) -> str:
        """Return a string representation of the instance."""
        if self.STR_FIELD is None:
            return super().__repr__()
        return str(getattr(self, self.STR_FIELD))

    def _fetch(self) -> None:
        """Populate the instance from the API (implemented by subclasses)."""
        self._fetched = True

    def _fetch_data(self) -> Any:
        """Return the raw payload for a lazy fetch.

        By default this issues a POST request using the body built by
        :meth:`_fetch_info`. Subclasses that load via GET (e.g. :class:`.Order`)
        override this method.

        """
        name, fields, body = self._fetch_info()
        path = API_PATH[name].format(**fields)
        return self._deyecloud.request(method="POST", json=body, path=path)

    def _fetch_info(self) -> tuple[str, dict[str, Any], dict[str, Any]]:
        """Return ``(api_path_key, format_fields, request_body)`` for the lazy fetch."""
        raise NotImplementedError

    def _reset_attributes(self, *attributes: str) -> None:
        for attribute in attributes:
            if attribute in self.__dict__:
                del self.__dict__[attribute]
        self._fetched = False
