"""List of API endpoints the client knows about."""

# fmt: off
API_PATH = {
    "account_token":              "v1.0/account/token",
    "account_info":               "v1.0/account/info",

    "config_battery":             "v1.0/config/battery",
    "config_system":              "v1.0/config/system",
    "config_tou":                 "v1.0/config/tou",

    "device_list":                "v1.0/device/list",
    "device_latest":              "v1.0/device/latest",
    "device_history":             "v1.0/device/history",
    "device_history_raw":         "v1.0/device/historyRaw",
    "device_measure_points":      "v1.0/device/measurePoints",
    "device_alert_list":          "v1.0/device/alertList",
    "device_register":            "v1.0/device/register",
    "device_add_logger":          "v1.0/device/addLogger",
    "device_delete_logger":       "v1.0/device/deleteLogger",

    "order_result":               "v1.0/order/{order_id}",
    "order_custom_control":       "v1.0/order/customControl",
    "order_battery_mode":         "v1.0/order/battery/modeControl",
    "order_battery_parameter":    "v1.0/order/battery/parameter/update",
    "order_battery_type":         "v1.0/order/battery/type/update",
    "order_grid_peak_shaving":    "v1.0/order/gridPeakShaving/control",
    "order_smartload":            "v1.0/order/smartload/update",
    "order_energy_pattern":       "v1.0/order/sys/energyPattern/update",
    "order_limit_control":        "v1.0/order/sys/limitControl",
    "order_power_update":         "v1.0/order/sys/power/update",
    "order_solar_sell":           "v1.0/order/sys/solarSell/control",
    "order_tou_switch":           "v1.0/order/sys/tou/switch",
    "order_tou_update":           "v1.0/order/sys/tou/update",
    "order_work_mode":            "v1.0/order/sys/workMode/update",

    "station_list":               "v1.0/station/list",
    "station_list_with_device":   "v1.0/station/listWithDevice",
    "station_create":             "v1.0/station/create",
    "station_device":             "v1.0/station/device",
    "station_latest":             "v1.0/station/latest",
    "station_history":            "v1.0/station/history",
    "station_history_power":      "v1.0/station/history/power",
    "station_alert_list":         "v1.0/station/alertList",

    "strategy_dynamic_control":     "v1.0/strategy/dynamicControl",
    "strategy_dynamic_control_read": "v1.0/strategy/dynamicControl/read",
    "strategy_dynamic_control_result": "v1.0/strategy/dynamicControl/readResult",
}
# fmt: on
