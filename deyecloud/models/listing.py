"""Provide the Page and PageGenerator classes.

The Deye Cloud API paginates list-style endpoints with ``page`` and ``size`` query or
body parameters. A :class:`.Page` wraps a single page of results and a
:class:`.PageGenerator` transparently fetches successive pages until a limit is
reached.

"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from deyecloud.models.base import DeyeBase

if TYPE_CHECKING:
    import deyecloud


class Page(DeyeBase):
    """A class representing a single page of results from a list endpoint."""

    def __init__(
        self,
        deyecloud: deyecloud.DeyeCloud,
        _data: dict[str, Any] | None,
        *,
        _records: list[Any] | None = None,
    ) -> None:
        """Initialize a :class:`.Page` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.
        :param _data: The structured data from the API.
        :param _records: The objectified records for this page (default: ``None``).

        """
        super().__init__(deyecloud, _data=_data or {})
        self.records = _records if _records is not None else []
        if not self.records:
            self.records = self._extract_records(_data or {})
        self.page = getattr(self, "page", 1)
        self.size = getattr(self, "size", len(self.records))
        self.total = getattr(self, "total", None)

    @staticmethod
    def _extract_records(data: dict[str, Any]) -> list[Any]:
        for key in ("records", "recordList", "record_list", "dataList", "data_list", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        return []

    def __iter__(self) -> Iterator[Any]:
        """Permit :class:`.Page` to operate as an iterator over its records."""
        return iter(self.records)

    def __len__(self) -> int:
        """Return the number of records in this page."""
        return len(self.records)

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return f"Page(page={self.page!r}, size={self.size!r}, total={self.total!r}, records={len(self.records)})"


class PageGenerator(DeyeBase, Iterator):
    """Instances of this class generate records across multiple pages.

    .. warning::

        This class should not be directly utilized. Instead, you will find a number of
        helper methods that return instances of the class.

    """

    def __init__(
        self,
        deyecloud: deyecloud.DeyeCloud,
        *,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, str | int] | None = None,
        limit: int | None = None,
        page_size: int = 20,
    ) -> None:
        """Initialize a :class:`.PageGenerator` instance.

        :param deyecloud: An instance of :class:`.DeyeCloud`.
        :param path: The literal API path to request.
        :param json: The JSON body to send with each page request (default: ``None``).
        :param params: Additional query string parameters (default: ``None``).
        :param limit: The number of records to fetch. If ``None``, fetch as many
            records as the API exposes (default: ``None``).
        :param page_size: The number of records requested per page (default: ``20``).

        """
        super().__init__(deyecloud, _data=None)
        self._path = path
        self._params = params
        self._json = json or {}
        self.limit = limit
        self.page_size = page_size
        self.total: int | None = None
        self.yielded = 0

        self._page = 0
        self._records: list[Any] = []
        self._index = 0
        self._exhausted = False

    def __iter__(self) -> PageGenerator:
        """Permit :class:`.PageGenerator` to operate as an iterator."""
        return self

    def __next__(self) -> Any:
        """Permit :class:`.PageGenerator` to operate as a generator."""
        if self.limit is not None and self.yielded >= self.limit:
            raise StopIteration

        if self._index >= len(self._records):
            self._next_page()

        if self._index >= len(self._records):
            raise StopIteration

        record = self._records[self._index]
        self._index += 1
        self.yielded += 1
        return record

    def _next_page(self) -> None:
        if self._exhausted:
            raise StopIteration

        self._page += 1
        body = {**self._json, "page": self._page, "size": self.page_size}
        page = self._deyecloud.post(self._path, params=self._params, json=body)
        self._records = list(page) if isinstance(page, Page) else []
        self.total = page.total if isinstance(page, Page) else None
        self._index = 0

        if not self._records:
            self._exhausted = True
        elif self.total is not None and self.yielded + len(self._records) >= self.total:
            self._exhausted = True
