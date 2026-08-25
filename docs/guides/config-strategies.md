# Configuration and strategies

## Reading device configuration

The `system` helper exposes read-only configuration endpoints.

```python
# Battery parameters
battery = deye.system.battery(device_sn="12583SS")
print(battery.batt_low_capacity)

# System work mode parameters
system = deye.system.system(device_sn="12583SS")
print(system.system_work_mode)

# Time-of-use configuration
tou = deye.system.tou(device_sn="12583SS")
print(tou.time_use_setting_items)
```

## Dynamic control strategies

The `strategy` helper manages comprehensive dynamic control for a device. Sending a
dynamic control command is asynchronous and returns an `Order`.

```python
order = deye.strategy.dynamic_control(
    device_sn="12583SS",
    work_mode="SELLING_FIRST",
    # ... additional settings (TOU, grid charge, sell power, solar sell)
)
print(order.order_id)
```

To read the current dynamic control parameters:

```python
order = deye.strategy.read(device_sn="12583SS")
result = deye.strategy.read_result(order.order_id)
print(result)
```
