"""Tests for configuration, core, and the objector."""

from __future__ import annotations

import hashlib

import pytest

from deyecloud.config import Config
from deyecloud.core import DeyeCloudAuthorizer, DeyeCloudRequestor, _parse_response
from deyecloud.exceptions import (
    DeyeCloudAPIException,
    MissingRequiredAttributeException,
    ResponseException,
)
from deyecloud.objector import Objector
from deyecloud.util.snake import camel_to_snake, snake_case_keys

from conftest import envelope, make_response


class TestSnake:
    def test_camel_to_snake(self):
        assert camel_to_snake("batterySOC") == "battery_soc"
        assert camel_to_snake("deviceSn") == "device_sn"
        assert camel_to_snake("lastUpdateTime") == "last_update_time"

    def test_snake_case_keys(self):
        assert snake_case_keys({"deviceSn": "x", "batterySOC": 1}) == {"device_sn": "x", "battery_soc": 1}


class TestConfig:
    def test_required_settings_via_kwargs(self):
        config = Config(
            "DEFAULT",
            app_id="123",
            app_secret="secret",
            email="a@b.c",
            password="pw",
        )
        config.validate()
        assert config.app_id == "123"
        assert config.base_url == "https://eu1-developer.deyecloud.com"
        assert config.timeout == 30

    def test_env_variables(self, monkeypatch):
        monkeypatch.setenv("deye_app_id", "123")
        monkeypatch.setenv("deye_app_secret", "secret")
        monkeypatch.setenv("deye_email", "a@b.c")
        monkeypatch.setenv("deye_password", "pw")
        config = Config("DEFAULT")
        config.validate()
        assert config.app_id == "123"

    def test_missing_app_secret(self):
        config = Config(
            "DEFAULT",
            app_id="123",
            email="a@b.c",
            password="pw",
        )
        with pytest.raises(MissingRequiredAttributeException):
            config.validate()

    def test_missing_login_identifier(self):
        config = Config("DEFAULT", app_id="123", app_secret="s", password="pw")
        with pytest.raises(MissingRequiredAttributeException):
            config.validate()

    def test_mobile_requires_country_code(self):
        config = Config("DEFAULT", app_id="123", app_secret="s", mobile="5551234", password="pw")
        with pytest.raises(MissingRequiredAttributeException):
            config.validate()


class TestParseResponse:
    def test_success_returns_full_body(self):
        response = make_response(envelope({"foo": "bar"}))
        body = _parse_response(response)
        assert body["foo"] == "bar"
        assert body["success"] is True

    def test_business_error_raises(self):
        response = make_response(
            envelope(None, success=False, code="5001000", msg="bad thing")
        )
        with pytest.raises(DeyeCloudAPIException) as exc_info:
            _parse_response(response)
        assert exc_info.value.code == "5001000"
        assert exc_info.value.msg == "bad thing"

    def test_http_error_raises(self):
        response = make_response({"error": "nope"}, status=500)
        with pytest.raises(ResponseException):
            _parse_response(response)


class TestAuthorizer:
    def test_password_is_sha256_hashed(self):
        authorizer = DeyeCloudAuthorizer(
            app_id="123",
            app_secret="secret",
            base_url="https://eu1-developer.deyecloud.com",
            email="a@b.c",
            password="password",
            requestor=DeyeCloudRequestor(timeout=5),
        )
        expected = hashlib.sha256(b"password").hexdigest()
        assert authorizer._build_token_payload()["password"] == expected

    def test_token_payload_login_fields(self):
        authorizer = DeyeCloudAuthorizer(
            app_id="123",
            app_secret="secret",
            base_url="https://eu1-developer.deyecloud.com",
            mobile="5551234",
            country_code="49",
            password="password",
            requestor=DeyeCloudRequestor(timeout=5),
        )
        payload = authorizer._build_token_payload()
        assert payload["mobile"] == "5551234"
        assert payload["countryCode"] == "49"
        assert "email" not in payload


class TestObjector:
    def _objector(self, deyecloud=None):
        if deyecloud is None:
            deyecloud = object()  # type: ignore[assignment]
        from deyecloud.models import Device, DeviceAlert, Order, OrgInfo, Station, StationAlert

        return Objector(deyecloud, {
            "Device": Device,
            "DeviceAlert": DeviceAlert,
            "Order": Order,
            "OrgInfo": OrgInfo,
            "Station": Station,
            "StationAlert": StationAlert,
        })

    def test_device(self):
        result = self._objector().objectify(data={"deviceSn": "x", "deviceType": "INVERTER"})
        from deyecloud.models import Device

        assert isinstance(result, Device)
        assert result.device_sn == "x"

    def test_station(self):
        result = self._objector().objectify(data={"stationId": 322, "stationName": "Home"})
        from deyecloud.models import Station

        assert isinstance(result, Station)
        assert result.station_id == 322

    def test_order(self):
        result = self._objector().objectify(data={"orderId": "1", "connectionStatus": 1})
        from deyecloud.models import Order

        assert isinstance(result, Order)
        assert result.order_id == "1"

    def test_device_container(self):
        result = self._objector().objectify(
            data={"deviceDataList": [{"deviceSn": "x", "deviceType": "INVERTER"}]}
        )
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].device_sn == "x"

    def test_container_unwrap(self):
        result = self._objector().objectify(
            data={
                "total": 2,
                "stationList": [
                    {"id": 1, "name": "A", "batterySOC": 10},
                    {"id": 2, "name": "B", "batterySOC": 20},
                ],
            }
        )
        from deyecloud.models import Station

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, Station) for item in result)
        assert result[0].station_id == 1
        assert result[1].station_name == "B"

    def test_measure_points_not_device(self):
        result = self._objector().objectify(
            data={"deviceSn": "x", "measurePoints": ["SOC", "TotalChargeEnergy"]}
        )
        assert isinstance(result, dict)
        assert result["measurePoints"] == ["SOC", "TotalChargeEnergy"]

    def test_plain_dict_passthrough(self):
        result = self._objector().objectify(data={"foo": 1})
        assert result == {"foo": 1}
