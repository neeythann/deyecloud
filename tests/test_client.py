"""End-to-end tests using a fake HTTP layer."""

from __future__ import annotations

import pytest

import deyecloud
from deyecloud.exceptions import ClientException

from conftest import FakeRequestor, envelope


def make_deyecloud(routes: dict) -> tuple[deyecloud.DeyeCloud, FakeRequestor]:
    deye = deyecloud.DeyeCloud(
        app_id="123",
        app_secret="secret",
        email="a@b.c",
        password="pw",
        requestor_class=FakeRequestor,
        requestor_kwargs={"routes": routes},
    )
    return deye, deye._core._requestor


TOKEN = envelope({"accessToken": "Bearer token123", "refreshToken": "r", "expiresIn": 3600, "uid": "u1"})


class TestAccount:
    def test_info(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/account/info": envelope(
                    {"orgInfoList": [{"companyId": 7, "companyName": "Acme", "roleName": "admin"}]}
                ),
            }
        )
        orgs = deye.account.info()
        assert len(orgs) == 1
        assert orgs[0].company_name == "Acme"

    def test_token_property(self):
        deye, _ = make_deyecloud({"v1.0/account/token": TOKEN})
        assert deye.account.token == "Bearer token123"


class TestStation:
    STATION = {
        "stationId": 322,
        "stationName": "Home",
        "batterySOC": 75,
        "generationPower": 1200,
    }

    def test_latest_single(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/latest": envelope({"dataList": [self.STATION]}),
            }
        )
        station = deye.station.latest(322)
        assert station.station_name == "Home"
        assert station.battery_soc == 75

    def test_latest_multi(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/latest": envelope({"dataList": [self.STATION, dict(self.STATION, stationId=323)]}),
            }
        )
        stations = deye.station.latest([322, 323])
        assert len(stations) == 2
        assert stations[0].station_id == 322
        assert stations[1].station_id == 323

    def test_latest_batch_limit(self):
        deye, _ = make_deyecloud({"v1.0/account/token": TOKEN})
        with pytest.raises(ValueError):
            deye.station.latest(list(range(11)))

    def test_lazy_station_fetch(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/latest": envelope({"dataList": [self.STATION]}),
            }
        )
        station = deye.station(322)
        assert station.station_id == 322
        assert station.station_name == "Home"  # triggers lazy fetch
        assert station._fetched

    def test_station_alerts_paginated(self):
        pages = [
            envelope(
                {
                    "page": 1,
                    "size": 1,
                    "total": 2,
                    "records": [
                        {"alertId": 1, "stationId": 322, "alertCode": "A1", "deviceSn": "s1", "deviceType": "INVERTER"}
                    ],
                }
            ),
            envelope(
                {
                    "page": 2,
                    "size": 1,
                    "total": 2,
                    "records": [
                        {"alertId": 2, "stationId": 322, "alertCode": "A2", "deviceSn": "s1", "deviceType": "INVERTER"}
                    ],
                }
            ),
        ]
        calls = {"n": 0}

        class SeqRequestor(FakeRequestor):
            def request(self, **kwargs):
                path = kwargs["url"].replace("https://eu1-developer.deyecloud.com/", "")
                if path == "v1.0/station/alertList":
                    body = kwargs.get("json") or {}
                    page = body.get("page", 1)
                    return self._response_for(pages[page - 1])
                return self._response_for(self.routes[path])

            def _response_for(self, payload):
                from conftest import make_response

                return make_response(payload)

        deye = deyecloud.DeyeCloud(
            app_id="123",
            app_secret="secret",
            email="a@b.c",
            password="pw",
            requestor_class=SeqRequestor,
            requestor_kwargs={"routes": {"v1.0/account/token": TOKEN}},
        )
        alerts = list(deye.station(322).alerts(1700000000, 1700001000, page_size=1))
        assert len(alerts) == 2
        assert alerts[0].alert_id == 1
        assert alerts[1].alert_id == 2


class TestStationList:
    def test_pagination_generator(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/list": envelope(
                    {
                        "page": 1,
                        "size": 2,
                        "total": 3,
                        "records": [
                            {"stationId": 1, "stationName": "A"},
                            {"stationId": 2, "stationName": "B"},
                            {"stationId": 3, "stationName": "C"},
                        ],
                    }
                ),
            }
        )
        stations = list(deye.station.list(page_size=10))
        assert len(stations) == 3
        assert [s.station_name for s in stations] == ["A", "B", "C"]

    def test_limit(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/list": envelope(
                    {
                        "page": 1,
                        "size": 5,
                        "total": 3,
                        "records": [
                            {"stationId": 1, "stationName": "A"},
                            {"stationId": 2, "stationName": "B"},
                            {"stationId": 3, "stationName": "C"},
                        ],
                    }
                ),
            }
        )
        stations = list(deye.station.list(limit=2, page_size=5))
        assert len(stations) == 2


class TestDevice:
    DEVICE = {
        "deviceSn": "12583SS",
        "deviceType": "INVERTER",
        "deviceState": 1,
        "collectionTime": 1700000000,
        "dataList": [{"key": "SOC", "value": "75", "unit": "%"}],
    }

    def test_latest(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/latest": envelope({"deviceDataList": [self.DEVICE]}),
            }
        )
        device = deye.device.latest("12583SS")
        assert device.device_sn == "12583SS"
        assert device.data_list[0]["key"] == "SOC"

    def test_lazy_device_fetch(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/latest": envelope({"deviceDataList": [self.DEVICE]}),
            }
        )
        device = deye.device("12583SS")
        assert device.device_sn == "12583SS"
        assert device.device_type == "INVERTER"  # triggers lazy fetch
        assert device._fetched

    def test_measure_points(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/measurePoints": envelope({"measurePoints": ["SOC", "TotalChargeEnergy"]}),
            }
        )
        points = deye.device.measure_points("12583SS")
        assert points["measurePoints"] == ["SOC", "TotalChargeEnergy"]

    def test_history_paths(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/history": envelope({"itemList": []}),
                "v1.0/device/historyRaw": envelope({"itemList": []}),
            }
        )
        device = deye.device("12583SS")
        device.history("day", measure_points=["SOC"], date="2024-01-01")
        device.history_raw(1700000000, 1700001000)
        requested = [call["url"] for call in requestor.calls if "token" not in call["url"]]
        assert requested == [
            "https://eu1-developer.deyecloud.com/v1.0/device/history",
            "https://eu1-developer.deyecloud.com/v1.0/device/historyRaw",
        ]


class TestStationHistory:
    def test_history_power_path(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/history/power": envelope({"dataList": []}),
            }
        )
        deye.station(322).history_power(1700000000, 1700001000)
        requested = [call["url"] for call in requestor.calls if "token" not in call["url"]]
        assert requested == ["https://eu1-developer.deyecloud.com/v1.0/station/history/power"]


class TestOrder:
    def test_work_mode_returns_order(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/order/sys/workMode/update": envelope(
                    {"orderId": "123", "collectionTime": 1700000000, "connectionStatus": 1}
                ),
            }
        )
        order = deye.order.work_mode(device_sn="12583SS", work_mode="SELLING_FIRST")
        assert order.order_id == "123"
        assert not order._fetched

    def test_work_mode_validation(self):
        deye, _ = make_deyecloud({"v1.0/account/token": TOKEN})
        with pytest.raises(ClientException):
            deye.order.work_mode(device_sn="12583SS", work_mode="BOGUS")

    def test_order_result_get(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/order/123": envelope({"orderId": "123", "status": 666}),
            }
        )
        order = deye.order.result("123")
        assert order.status == 666
        assert order.succeeded
        assert not order.failed

    def test_lazy_order_fetch(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/order/123": envelope({"orderId": "123", "status": 500}),
            }
        )
        order = deye.order("123")
        assert order.status == 500  # triggers lazy fetch
        assert order.failed
        assert order.status_name == "FAILED"

class TestConfigHelper:
    def test_system(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/config/system": envelope({"systemWorkMode": "SELLING_FIRST"}),
            }
        )
        result = deye.system.system(device_sn="12583SS")
        assert result["systemWorkMode"] == "SELLING_FIRST"


class TestStrategy:
    def test_dynamic_control_read(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/strategy/dynamicControl/read": envelope({"orderId": "9"}),
            }
        )
        order = deye.strategy.read(device_sn="12583SS")
        assert order.order_id == "9"
