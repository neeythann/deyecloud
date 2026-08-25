"""Provides the code to load the client's configuration file ``deye.ini``."""

from __future__ import annotations

import configparser
import os
from importlib.resources import files
from pathlib import Path
from threading import Lock
from types import MappingProxyType
from typing import Any

from deyecloud.const import DEFAULT_BASE_URL
from deyecloud.exceptions import MissingRequiredAttributeException


class _NotSet:
    def __bool__(self) -> bool:
        return False

    __nonzero__ = __bool__

    def __str__(self) -> str:
        return "NotSet"


class Config:
    """A class containing the configuration for a Deye Cloud site."""

    CONFIG: configparser.ConfigParser | None = None
    CONFIG_NOT_SET = _NotSet()  # Represents a config value that is not set.
    INTERPOLATION_LEVEL = MappingProxyType({
        "basic": configparser.BasicInterpolation,
        "extended": configparser.ExtendedInterpolation,
    })
    LOCK = Lock()

    # Attributes populated by _initialize_attributes.
    app_id: str
    app_secret: str | None
    base_url: str
    company_id: str | int | None
    country_code: str | None
    email: str | None
    mobile: str | None
    password: str | None
    timeout: int
    username: str | None

    @staticmethod
    def _config_boolean(*, item: bool | str | _NotSet) -> bool:
        if isinstance(item, bool):
            return item
        if isinstance(item, _NotSet):
            return False
        return item.lower() in {"1", "yes", "true", "on"}

    @classmethod
    def _load_config(cls, *, config_interpolation: str | None = None) -> None:
        """Attempt to load settings from various deye.ini files."""
        if config_interpolation is not None:
            interpolator_class = cls.INTERPOLATION_LEVEL[config_interpolation]()
        else:
            interpolator_class = None

        config = configparser.ConfigParser(interpolation=interpolator_class)
        assert __package__ is not None
        with files(__package__).joinpath("deye.ini").open("r") as hdl:
            config.read_file(hdl)

        if "APPDATA" in os.environ:  # Windows
            os_config_path = Path(os.environ["APPDATA"])
        elif "XDG_CONFIG_HOME" in os.environ:  # Modern Linux
            os_config_path = Path(os.environ["XDG_CONFIG_HOME"])
        elif "HOME" in os.environ:  # Legacy Linux
            os_config_path = Path(os.environ["HOME"]) / ".config"
        else:
            os_config_path = None

        locations = ["deye.ini"]

        if os_config_path is not None:
            locations.insert(0, str(os_config_path / "deye.ini"))

        config.read(locations)
        cls.CONFIG = config

    def __init__(
        self,
        site_name: str,
        config_interpolation: str | None = None,
        **settings: str | bool | int | None,
    ) -> None:
        """Initialize a :class:`.Config` instance."""
        with Config.LOCK:
            if Config.CONFIG is None:
                self._load_config(config_interpolation=config_interpolation)

        self._settings = settings
        assert Config.CONFIG is not None
        self.custom = dict(Config.CONFIG.items(site_name), **settings)

        self._initialize_attributes()

    def _fetch(self, key: str) -> Any:
        value = self.custom[key]
        del self.custom[key]
        return value

    def _fetch_default(self, key: str, *, default: bool | float | str | None = None) -> Any:
        if key not in self.custom:
            return default
        return self._fetch(key)

    def _fetch_or_not_set(self, key: str) -> Any | _NotSet:
        if key in self._settings:  # Passed in values have the highest priority
            return self._fetch(key)

        env_value = os.getenv(f"deye_{key}")
        ini_value = self._fetch_default(key)  # Needed to remove from custom

        # Environment variables have higher priority than deye.ini settings
        return env_value or ini_value or self.CONFIG_NOT_SET

    def _initialize_attributes(self) -> None:
        for attribute in (
            "app_id",
            "app_secret",
            "company_id",
            "country_code",
            "email",
            "mobile",
            "password",
            "username",
        ):
            setattr(self, attribute, self._fetch_or_not_set(attribute))

        self.base_url = self._fetch_default("base_url", default=DEFAULT_BASE_URL)
        self.timeout = int(self._fetch_default("timeout", default=30))

        if self.app_id not in {self.CONFIG_NOT_SET, None}:
            self.app_id = str(self.app_id)

        if self.company_id not in {self.CONFIG_NOT_SET, None}:
            self.company_id = str(self.company_id)

    def validate(self) -> None:
        """Ensure all required configuration settings are present.

        :raises: :class:`.MissingRequiredAttributeException` when a required setting is
            missing.

        """
        required_message = (
            "Required configuration setting {!r} missing. \nThis setting can be"
            " provided in a deye.ini file, as a keyword argument to the DeyeCloud class"
            " constructor, or as an environment variable."
        )
        for attribute in ("app_id", "app_secret", "password"):
            if getattr(self, attribute) in {self.CONFIG_NOT_SET, None}:
                raise MissingRequiredAttributeException(required_message.format(attribute))

        login_fields = [field for field in ("email", "mobile", "username") if getattr(self, field, None)]
        if len(login_fields) != 1:
            msg = "Exactly one of 'email', 'mobile', or 'username' must be provided."
            raise MissingRequiredAttributeException(msg)
        if login_fields[0] == "mobile" and not self.country_code:
            msg = "The 'country_code' setting is required when logging in with 'mobile'."
            raise MissingRequiredAttributeException(msg)
