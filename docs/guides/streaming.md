# Streaming telemetry

The Deye Cloud API is pull-based, so `deyecloud` implements streaming by polling the
latest telemetry and yielding a snapshot whenever a new sample arrives (identified by
its timestamp). This mirrors PRAW's stream pattern.

## Station stream

```python
station = deye.station(322)

for snapshot in station.stream.latest():
    print(snapshot.generation_power, snapshot.battery_soc)
```

## Device stream

```python
device = deye.device("12583SS")

for snapshot in device.stream.latest():
    print(snapshot.device_state)
```

## Stream options

All options are keyword arguments passed to the underlying stream generator.

### `skip_existing`

Only report changes starting *after* the stream is created:

```python
for snapshot in station.stream.latest(skip_existing=True):
    print(snapshot.last_update_time)
```

### `pause_after`

Yield `None` after a number of polls return no new data, allowing you to break out of
the stream:

```python
for snapshot in station.stream.latest(pause_after=6):
    if snapshot is None:
        break
    print(snapshot.generation_power)
```

### `exception_handler`

Keep the stream alive across transient errors instead of terminating:

```python
def log_exception(exception):
    print(f"Stream error, retrying: {exception}")

for snapshot in station.stream.latest(exception_handler=log_exception):
    print(snapshot.generation_power)
```

Re-raise from the handler to stop the stream for fatal errors.

## Backoff behaviour

Between polls that return no new data, the stream waits an exponentially increasing
delay with jitter, up to a maximum of just over 16 seconds. When new data is found, the
delay resets. This avoids hammering the API when telemetry is static.
