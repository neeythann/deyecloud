# Devices

A *device* is a piece of equipment registered with Deye Cloud (an inverter, datalogger,
meter, etc.), identified by its serial number (`device_sn`).

## Latest telemetry

Fetch the latest data for one or more devices (max 10 per request):

```python
# A single device
device = deye.device.latest("12583SS")
print(device.device_sn, device.device_state)

# Several devices at once
devices = deye.device.latest(["12583SS", "2401110313"])

# Disambiguate with a device type
device = deye.device.latest("12583SS", device_type="INVERTER")
```

## Lazy instances

`deye.device(sn)` returns a lightweight instance that fetches its data from
`device/latest` on the first attribute access:

```python
device = deye.device("12583SS")
print(device.device_type)   # triggers the fetch
```

## Measure points

Each device exposes a set of *measure points* that can be queried historically:

```python
points = deye.device.measure_points("12583SS")
print(points["measurePoints"])
```

## History

```python
# Day granularity for a single date
device.history("day", measure_points=["SOC"], date="2024-01-01")

# Day-range (up to 31 days)
device.history("day_range", measure_points=["SOC"], start_date="2024-01-01", end_date="2024-01-31")

# Month-range (up to 12 months) or year granularity
device.history("month_range", measure_points=["SOC"], start_date="2024-01-01", end_date="2024-06-30")

# Raw history within a Unix timestamp range (max 5 days)
device.history_raw(1700000000, 1700001000)
```

## Alerts

```python
for alert in device.alerts(1700000000, 1700001000):
    print(alert.alert_code, alert.description)
```

## Managing devices

```python
# Business members: list devices, add/remove loggers
for device in deye.device.list():
    print(device.device_sn)

deye.device.add_logger("12583SS")
deye.device.delete_logger(["12583SS", "2401110313"])

# Register a datalogger into a station
deye.device.register(device_sn="12583SS", gateway_sn="GATEWAY1", station_id=322)
```
