"""Provide the Account and OrgInfo classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from deyecloud.models.base import DeyeBase

if TYPE_CHECKING:
    import deyecloud


class OrgInfo(DeyeBase):
    """A class representing an organization associated with an account.

    Returned by ``deye.account.info()``. A personal-user token is used when no
    ``companyId`` is configured; business-member tokens are scoped to a ``companyId``.

    """

    def __str__(self) -> str:
        """Return a string representation of the instance."""
        return f"{getattr(self, 'companyName', '')} ({getattr(self, 'companyId', '')})"

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return (
            f"OrgInfo(companyId={getattr(self, 'companyId', None)!r}, "
            f"companyName={getattr(self, 'companyName', None)!r}, "
            f"roleName={getattr(self, 'roleName', None)!r})"
        )


class Account(DeyeBase):
    """A class representing the authenticated account.

    Exposes the details returned by the token endpoint, such as the user id.

    """

    def __str__(self) -> str:
        """Return a string representation of the instance."""
        return str(getattr(self, "uid", ""))

    def __repr__(self) -> str:
        """Return an object initialization representation of the instance."""
        return f"Account(uid={getattr(self, 'uid', None)!r})"
