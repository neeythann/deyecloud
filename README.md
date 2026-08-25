# deyecloud

A Python wrapper for the [Deye Cloud API](https://eu1-developer.deyecloud.com/v2/api-docs),
modeled after [PRAW](https://github.com/praw-dev/praw).

Like PRAW is to Reddit, this library provides an object-oriented, lazy interface to the
Deye Cloud API: a central [`DeyeCloud`](./deyecloud/deyecloud.py) instance issues
authenticated requests, an [`Objector`](./deyecloud/objector.py) turns JSON responses
into model objects, and helper classes expose stations, devices, control commands, and
strategies.

## Install

From PyPI:

```bash
pip install deyecloud
```

For development, install in editable mode with test dependencies:

```bash
pip install -e ".[test]"
```

## Quickstart

```python
import deyecloud

deye = deyecloud.DeyeCloud(
    app_id="201911067156002",   # developer application id
    app_secret="APPSECRET",     # paired secret
    email="user@example.com",   # or mobile=... with country_code, or username=...
    password="PASSWORD",
)
```

Credentials may instead come from a `deye.ini` file (see
[`deyecloud/deye.ini`](./deyecloud/deye.ini)) or environment variables prefixed with
`deye_` (e.g. `deye_app_id`). Pass `site_name="..."` to select a named section.

### Stations

```python
# Iterate all stations (paginated under the hood)
for station in deye.station.list():
    print(station.station_id, station.station_name, station.battery_soc)

# Latest telemetry for specific stations
stations = deye.station.latest([322, 323])

# Lazy instance: data is fetched from station/latest on first attribute access
station = deye.station(322)
print(station.generation_power)

# History, alerts, devices
station.history("day", start_date="2024-01-01", end_date="2024-01-31")
for alert in station.alerts(1700000000, 1700001000):
    print(alert.alert_code)

# Create a station
deye.station.create(
    station_name="My Plant",
    country_code="DE",
    timezone="Europe/Berlin",
    currency="EUR",
    capacity=10,
)
```

### Devices

```python
for device in deye.device.latest(["12583SS", "2401110313"]):
    print(device.device_sn, device.device_state)

device = deye.device("12583SS")  # lazy
print(device.measure_points())   # or device.measure_points()

device.history("day", measure_points=["SOC"], date="2024-01-01")
device.history_raw(1700000000, 17000086400)
```

### Control commands

Control commands are asynchronous: they return an [`Order`](./deyecloud/models/order.py)
carrying an `order_id`, and the result is fetched via `GET /v1.0/order/{order_id}`.

```python
order = deye.order.work_mode(device_sn="12583SS", work_mode="SELLING_FIRST")
order = order.refresh()
print(order.order_id, order.status_name, order.succeeded)

# More commands
deye.order.battery_mode(device_sn="...", charge_mode="GRID_CHARGE", enable=True)
deye.order.battery_parameter(device_sn="...", parameter="MAX_CHARGE_CURRENT", value=20)
deye.order.power(device_sn="...", power="MAX_SELL_POWER", value=5000)
deye.order.tou_update(device_sn="...", intervals=[...six intervals...])
deye.order.custom_control(device_sn="...", content="0103000102ABCD")
```

### Configuration and strategies

```python
deye.system.battery(device_sn="...")
deye.system.system(device_sn="...")
deye.system.tou(device_sn="...")

order = deye.strategy.read(device_sn="...")
result = deye.strategy.read_result(order.order_id)
```

### Streaming telemetry

The Deye Cloud API is pull-based, so streams poll the latest telemetry and yield a
snapshot whenever a new sample arrives (identified by its timestamp). This mirrors
PRAW's stream pattern, including exponential backoff, `skip_existing`, `pause_after`,
and `exception_handler`.

```python
# Monitor a station's live telemetry
station = deye.station(322)
for snapshot in station.stream.latest():
    print(snapshot.generation_power, snapshot.battery_soc)

# Only report changes after the stream is created
for snapshot in station.stream.latest(skip_existing=True):
    print(snapshot.last_update_time)

# Stop after 6 polls with no change, then break
for snapshot in station.stream.latest(pause_after=6):
    if snapshot is None:
        break
    print(snapshot.generation_power)

# Keep the stream alive across transient errors
def log_exception(exception):
    print(f"Stream error, retrying: {exception}")

for snapshot in station.stream.latest(exception_handler=log_exception):
    print(snapshot.generation_power)

# Devices work the same way
device = deye.device("12583SS")
for snapshot in device.stream.latest():
    print(snapshot.device_state)
```

## Architecture

The layout intentionally mirrors PRAW:

| PRAW                 | This project             |
|----------------------|--------------------------|
| `praw.Reddit`        | `deyecloud.DeyeCloud`    |
| `prawcore` (auth/session) | `deyecloud.core`    |
| `praw.config`        | `deyecloud.config`       |
| `praw.endpoints`     | `deyecloud.endpoints`    |
| `praw.objector`      | `deyecloud.objector`     |
| `praw.models.base`   | `deyecloud.models.base`  |
| `praw.models.helpers`| `deyecloud.models.helpers` |
| `ListingGenerator`   | `deyecloud.models.listing.PageGenerator` |

- **Authentication** — a bearer token is acquired from `POST /v1.0/account/token`
  (with the password SHA-256 hashed) and attached as `authorization: Bearer ...` to
  every subsequent request; tokens are re-acquired when near expiry.
- **Response envelope** — every response is validated against the `success`/`code`/`msg`
  envelope; business errors raise [`DeyeCloudAPIException`](./deyecloud/exceptions.py).
- **Lazy loading** — `deye.station(id)` / `deye.device(sn)` / `deye.order(id)` return
  lightweight instances that fetch their data on first attribute access, mirroring
  PRAW's `RedditBase`.
- **Pagination** — list endpoints use a `PageGenerator` that transparently requests
  successive pages.
- **Streaming** — `station.stream.latest()` / `device.stream.latest()` poll the latest
  telemetry and yield new snapshots as they arrive, mirroring PRAW's
  `stream_generator` (exponential backoff, dedup, `skip_existing`, `pause_after`,
  `exception_handler`).
- **Snake case** — response keys are normalized from camelCase to snake_case, so
  `batterySOC` becomes `station.battery_soc`.

## Notes / assumptions

The pagination envelopes are assumed to use `page` / `size` / `total` / `records`
(a common Deye convention). Response container keys (`deviceDataList`, `dataList`, ...)
are unwrapped heuristically. If a live response differs, adjust the container key
handling in [`objector.py`](./deyecloud/objector.py) and
[`models/listing.py`](./deyecloud/models/listing.py).

## Tests

```bash
pytest
```

Tests use a fake HTTP layer (`tests/conftest.py`) and do not require network access.
