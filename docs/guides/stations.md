# Stations

A *station* represents a power station / installation. Stations are identified by a
numeric `station_id`.

## Listing stations

```python
# Iterate all stations (paginated under the hood)
for station in deye.station.list():
    print(station.station_id, station.station_name, station.battery_soc)

# Filter by keyword
for station in deye.station.list(keyword="Home"):
    print(station.station_name)

# Limit the number of results
stations = list(deye.station.list(limit=5))
```

## Latest telemetry

Fetch the latest telemetry for a station:

```python
station = deye.station.latest(322)
print(station.generation_power, station.battery_soc)
```

## Lazy instances

`deye.station(id)` returns a lightweight instance that fetches its data from
`station/latest` on the first attribute access:

```python
station = deye.station(322)
print(station.station_name)   # triggers the fetch
print(station.generation_power)
```

## History

```python
# Day granularity
station.history("day", start_date="2024-01-01", end_date="2024-01-31")

# Frame (power only), month, or year granularity
station.history("month", start_date="2024-01-01", end_date="2024-03-31")

# Power history within a Unix timestamp range (max 12 months)
station.history_power(1700000000, 1700001000)
```

## Alerts

```python
for alert in station.alerts(1700000000, 1700001000):
    print(alert.alert_code, alert.alert_name, alert.level_name)
```

## Devices

```python
for device in station.devices():
    print(device.device_sn, device.device_type)

# Filter by device type
for device in station.devices(device_type="INVERTER"):
    print(device.device_sn)
```

## Creating a station

```python
deye.station.create(
    station_name="My Plant",
    country_code="DE",            # ISO 3166 alpha-2
    timezone="Europe/Berlin",     # IANA timezone
    currency="EUR",               # ISO 4217
    capacity=10,                  # kW
)
```
