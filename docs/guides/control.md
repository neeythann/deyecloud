# Control commands

Control commands let you configure and operate devices (work mode, time-of-use, battery
settings, etc.). Commands are **asynchronous**: the API accepts the command and
immediately returns an [`Order`](../api/order.md) carrying an `order_id`. The actual
result must be fetched later via `GET /v1.0/order/{order_id}`.

## Sending a command

```python
order = deye.order.work_mode(device_sn="12583SS", work_mode="SELLING_FIRST")
print(order.order_id)
```

## Checking the result

```python
order = order.refresh()          # re-fetch the result
print(order.status_name)         # e.g. 'SUCCEEDED'
print(order.succeeded)           # True / False
print(order.failed)              # True / False
```

You can also fetch the result of a previously issued command:

```python
order = deye.order.result("123456")
```

## Available commands

All commands accept a `device_sn` and return an `Order`.

### Work mode

```python
deye.order.work_mode(device_sn="...", work_mode="SELLING_FIRST")
# Options: SELLING_FIRST, ZERO_EXPORT_TO_LOAD, ZERO_EXPORT_TO_CT
# Micro storage: GREEN_POWER_MODE, FULL_CHARGE_MODE, CUSTOMIZED_MODE
```

### Energy pattern

```python
deye.order.energy_pattern(device_sn="...", energy_pattern="BATTERY_FIRST")
# Options: BATTERY_FIRST, LOAD_FIRST
```

### Power limits

```python
deye.order.power(device_sn="...", power="MAX_SELL_POWER", value=5000)
# Options: MAX_SELL_POWER, MAX_SOLAR_POWER, ZERO_EXPORT_POWER
```

### Battery

```python
# Charge mode
deye.order.battery_mode(device_sn="...", charge_mode="GRID_CHARGE", enable=True)
# Options: GRID_CHARGE, GEN_CHARGE

# Parameter
deye.order.battery_parameter(device_sn="...", parameter="MAX_CHARGE_CURRENT", value=20)
# Options: MAX_CHARGE_CURRENT, MAX_DISCHARGE_CURRENT, GRID_CHARGE_AMPERE, BATT_LOW

# Battery type
deye.order.battery_type(device_sn="...", battery_type="LI")
# Options: BATT_V, BATT_SOC, LI, NO_BATTERY
```

### Time-of-use (TOU)

```python
deye.order.tou_switch(device_sn="...", enable=True, days=["MONDAY", "TUESDAY"])

deye.order.tou_update(device_sn="...", intervals=[
    {"time": "02:05", "power": 1000, "soc": 50},
    # ... up to six intervals, in sequence, times in 5-minute steps
])
```

### Grid / solar

```python
deye.order.grid_peak_shaving(device_sn="...", enable=True)
deye.order.solar_sell(device_sn="...", enable=True)
deye.order.smartload(device_sn="...", on_soc=90, off_soc=40)
```

### Limit control (Micro ESS only)

```python
deye.order.limit_control(device_sn="...", limit_control="ZERO_EXPORT_TO_CT")
# Options: SELL_FIRST, ZERO_EXPORT_TO_UPS_LOAD, ZERO_EXPORT_TO_CT, ZERO_EXPORT_TO_WIRELESS_CT
```

### Raw Modbus

```python
deye.order.custom_control(device_sn="...", content="0103000102ABCD", timeout_seconds=60)
```
