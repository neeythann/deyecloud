# deyecloud

A Python wrapper for the [Deye Cloud API](https://eu1-developer.deyecloud.com/v2/api-docs),
modeled after [PRAW](https://github.com/praw-dev/praw).

Like PRAW is to Reddit, this library provides an object-oriented, lazy interface to the
Deye Cloud API: a central `DeyeCloud` instance issues authenticated requests, an
`Objector` turns JSON responses into model objects, and helper classes expose stations,
devices, control commands, and strategies.

See the [README](https://github.com/neeythann/deyecloud/blob/main/README.md) for the full
quickstart and usage examples.

## Quickstart

```python
import deyecloud

deye = deyecloud.DeyeCloud(
    app_id="201911067156002",
    app_secret="APPSECRET",
    email="user@example.com",
    password="PASSWORD",
)

for station in deye.station.list():
    print(station.station_name, station.battery_soc)
```

## Key features

- **Authentication** — token-based auth via `POST /v1.0/account/token` with automatic
  refresh.
- **Lazy loading** — `deye.station(id)` / `deye.device(sn)` / `deye.order(id)` fetch
  their data on first attribute access.
- **Pagination** — list endpoints use a `PageGenerator` that transparently requests
  successive pages.
- **Streaming** — `station.stream.latest()` / `device.stream.latest()` yield live
  telemetry snapshots as they arrive.
- **Control commands** — asynchronous commands return an `Order` whose result can be
  polled.
