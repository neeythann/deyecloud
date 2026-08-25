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
        deye, _ = make_deyecloud(
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
    STATION_LIST_ITEM = {
        "id": 61521934,
        "name": "Nathan  Xavier Golez",
        "batterySOC": 32.0,
        "connectionStatus": "NORMAL",
        "generationPower": 2548.0,
        "lastUpdateTime": 1787624055.0,
    }
    TELEMETRY = {
        "generationPower": 3838.0,
        "consumptionPower": 882.0,
        "batterySOC": 32.0,
        "lastUpdateTime": 1787624115.0,
    }

    def test_latest_single(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/latest": envelope(dict(self.TELEMETRY)),
            }
        )
        station = deye.station.latest(61521934)
        assert station.station_id == 61521934
        assert station.battery_soc == 32.0
        assert station.generation_power == 3838.0
        assert station._fetched
        body = requestor.calls[-1]["json"]
        assert body == {"stationId": 61521934}

    def test_lazy_station_fetch(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/latest": envelope(dict(self.TELEMETRY)),
            }
        )
        station = deye.station(61521934)
        assert station.station_id == 61521934
        assert station.generation_power == 3838.0  # triggers lazy fetch
        assert station._fetched

    def test_station_from_list_item(self):
        deye, _ = make_deyecloud({"v1.0/account/token": TOKEN})
        station = deye._objector.objectify(data=dict(self.STATION_LIST_ITEM))
        assert station.station_id == 61521934
        assert station.station_name == "Nathan  Xavier Golez"
        assert station.battery_soc == 32.0

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

        class SeqRequestor(FakeRequestor):
            def request(self, **kwargs):
                path = kwargs["url"].replace("https://eu1-developer.deyecloud.com/", "")
                if path == "v1.0/station/alertList":
                    body = kwargs.get("json") or {}
                    page = body.get("page", 1)
                    return make_response_for(pages[page - 1])
                return make_response_for(self.routes[path])

        def make_response_for(payload):
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
                        "total": 3,
                        "stationList": [
                            {"id": 1, "name": "A", "batterySOC": 10},
                            {"id": 2, "name": "B", "batterySOC": 20},
                            {"id": 3, "name": "C", "batterySOC": 30},
                        ],
                    }
                ),
            }
        )
        stations = list(deye.station.list(page_size=10))
        assert len(stations) == 3
        assert [s.station_name for s in stations] == ["A", "B", "C"]
        assert [s.station_id for s in stations] == [1, 2, 3]

    def test_limit(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/list": envelope(
                    {
                        "total": 3,
                        "stationList": [
                            {"id": 1, "name": "A", "batterySOC": 10},
                            {"id": 2, "name": "B", "batterySOC": 20},
                            {"id": 3, "name": "C", "batterySOC": 30},
                        ],
                    }
                ),
            }
        )
        stations = list(deye.station.list(limit=2, page_size=5))
        assert len(stations) == 2


class TestStationWithDevices:
    def test_list_with_device(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/listWithDevice": envelope(
                    {
                        "stationTotal": 1,
                        "stationList": [
                            {
                                "id": 61521934,
                                "name": "Home",
                                "deviceTotal": 1,
                                "deviceListItems": [
                                    {"deviceSn": "2505135714", "deviceId": 1, "deviceType": "INVERTER"}
                                ],
                            }
                        ],
                    }
                ),
            }
        )
        stations = list(deye.station.with_devices())
        assert len(stations) == 1
        assert stations[0].station_id == 61521934
        assert stations[0].device_total == 1


class TestStationDevices:
    def test_station_devices(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/device": envelope(
                    {
                        "total": 2,
                        "deviceListItems": [
                            {"deviceSn": "D254033588C0", "deviceId": 1, "deviceType": "COLLECTOR"},
                            {"deviceSn": "2505135714", "deviceId": 2, "deviceType": "INVERTER"},
                        ],
                    }
                ),
            }
        )
        devices = list(deye.station(61521934).devices())
        assert len(devices) == 2
        assert devices[0].device_type == "COLLECTOR"
        assert devices[1].device_sn == "2505135714"


class TestStationHistory:
    def test_history_power_path(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/station/history/power": envelope(
                    {"total": 1, "stationDataItems": [{"generationPower": 2020.0, "timeStamp": 1787539200.0}]}
                ),
            }
        )
        deye.station(61521934).history_power(1700000000, 1700001000)
        requested = [call["url"] for call in requestor.calls if "token" not in call["url"]]
        assert requested == ["https://eu1-developer.deyecloud.com/v1.0/station/history/power"]


class TestDevice:
    DEVICE = {
        "deviceSn": "2505135714",
        "deviceType": "INVERTER",
        "deviceState": 1,
        "collectionTime": 1787624175,
        "dataList": [{"key": "SOC", "value": "75", "unit": "%"}],
    }

    def test_latest(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/latest": envelope({"deviceDataList": [self.DEVICE]}),
            }
        )
        device = deye.device.latest("2505135714")
        assert device.device_sn == "2505135714"
        assert device.data_list[0]["key"] == "SOC"

    def test_latest_multi(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/latest": envelope(
                    {"deviceDataList": [self.DEVICE, dict(self.DEVICE, deviceSn="12583SS")]}
                ),
            }
        )
        devices = deye.device.latest(["2505135714", "12583SS"])
        assert len(devices) == 2
        assert devices[0].device_sn == "2505135714"
        assert devices[1].device_sn == "12583SS"

    def test_lazy_device_fetch(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/latest": envelope({"deviceDataList": [self.DEVICE]}),
            }
        )
        device = deye.device("2505135714")
        assert device.device_sn == "2505135714"
        assert device.device_type == "INVERTER"  # triggers lazy fetch
        assert device._fetched

    def test_measure_points(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/measurePoints": envelope(
                    {"deviceSn": "2505135714", "measurePoints": ["SOC", "TotalChargeEnergy"]}
                ),
            }
        )
        points = deye.device.measure_points("2505135714")
        assert points["measurePoints"] == ["SOC", "TotalChargeEnergy"]

    def test_history_paths(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/device/history": envelope({"itemList": []}),
                "v1.0/device/historyRaw": envelope({"itemList": []}),
            }
        )
        device = deye.device("2505135714")
        device.history("day", measure_points=["SOC"], date="2024-01-01")
        device.history_raw(1700000000, 1700001000)
        requested = [call["url"] for call in requestor.calls if "token" not in call["url"]]
        assert requested == [
            "https://eu1-developer.deyecloud.com/v1.0/device/history",
            "https://eu1-developer.deyecloud.com/v1.0/device/historyRaw",
        ]


class TestOrder:
    def test_battery_parameter_payload(self):
        deye, requestor = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/order/battery/parameter/update": envelope(
                    {"orderId": "123", "collectionTime": 1700000000, "connectionStatus": 1}
                ),
            }
        )
        order = deye.order.battery_parameter(device_sn="2505135714", parameter="BATT_LOW", value=20)
        assert order.order_id == "123"
        body = requestor.calls[-1]["json"]
        assert body == {"deviceSn": "2505135714", "paramterType": "BATT_LOW", "value": 20}

    def test_work_mode_returns_order(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/order/sys/workMode/update": envelope(
                    {"orderId": "123", "collectionTime": 1700000000, "connectionStatus": 1}
                ),
            }
        )
        order = deye.order.work_mode(device_sn="2505135714", work_mode="SELLING_FIRST")
        assert order.order_id == "123"
        assert not order._fetched

    def test_work_mode_validation(self):
        deye, _ = make_deyecloud({"v1.0/account/token": TOKEN})
        with pytest.raises(ClientException):
            deye.order.work_mode(device_sn="2505135714", work_mode="BOGUS")

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
        result = deye.system.system(device_sn="2505135714")
        assert result["systemWorkMode"] == "SELLING_FIRST"


class TestStrategy:
    def test_dynamic_control_read(self):
        deye, _ = make_deyecloud(
            {
                "v1.0/account/token": TOKEN,
                "v1.0/strategy/dynamicControl/read": envelope({"orderId": "9"}),
            }
        )
        order = deye.strategy.read(device_sn="2505135714")
        assert order.order_id == "9"


class TestStream:
    def _stream_deye(self, snapshots):
        from deyecloud.models import Station

        queue = list(reversed(snapshots))
        deye, _ = make_deyecloud({"v1.0/account/token": TOKEN})
        station = Station(deye, _data={"station_id": 322})
        original = deyecloud.DeyeCloud.request

        def fake_request(*, method="", path="", **kwargs):
            if path == "v1.0/station/latest":
                return queue.pop()
            return original(self, method=method, path=path, **kwargs)

        deye.request = fake_request  # type: ignore[method-assign]
        return station

    def test_station_stream_yields_snapshots(self):
        snapshots = [
            {"generationPower": 100, "batterySOC": 50, "lastUpdateTime": 1},
            {"generationPower": 200, "batterySOC": 50, "lastUpdateTime": 2},
            {"generationPower": 300, "batterySOC": 50, "lastUpdateTime": 3},
        ]
        station = self._stream_deye(snapshots)

        import itertools

        yielded = list(itertools.islice(station.stream.latest(), 3))
        assert [item.generation_power for item in yielded] == [100, 200, 300]

    def test_station_stream_skip_existing(self):
        snapshots = [
            {"generationPower": 100, "batterySOC": 50, "lastUpdateTime": 1},
            {"generationPower": 200, "batterySOC": 50, "lastUpdateTime": 2},
        ]
        station = self._stream_deye(snapshots)

        import itertools

        yielded = list(itertools.islice(station.stream.latest(skip_existing=True), 1))
        assert len(yielded) == 1
        assert yielded[0].generation_power == 200


class TestStreamGenerator:
    def test_dedupes_by_attribute(self):
        from types import SimpleNamespace

        from deyecloud.models import stream_generator

        responses = [[1], [1, 2], [2, 3]]

        class _Stop(Exception):
            pass

        def fake(**kwargs):
            if not responses:
                raise _Stop
            return [SimpleNamespace(collection_time=value) for value in responses.pop(0)]

        yielded = []
        try:
            for item in stream_generator(fake):
                yielded.append(item.collection_time)
        except _Stop:
            pass
        assert yielded == [1, 2, 3]

    def test_skip_existing(self):
        from types import SimpleNamespace

        from deyecloud.models import stream_generator

        responses = [[1], [2]]

        class _Stop(Exception):
            pass

        def fake(**kwargs):
            if not responses:
                raise _Stop
            return [SimpleNamespace(collection_time=value) for value in responses.pop(0)]

        yielded = []
        try:
            for item in stream_generator(fake, skip_existing=True):
                yielded.append(item.collection_time)
        except _Stop:
            pass
        assert yielded == [2]
