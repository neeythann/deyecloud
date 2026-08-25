"""Client constants."""

from deyecloud.endpoints import API_PATH  # ruff:ignore[unused-import]

__version__ = "0.3.0"

# The code returned by the Deye Cloud API for a successful response.
SUCCESS_CODE = "1000000"

# Default regional developer base URL.
DEFAULT_BASE_URL = "https://eu1-developer.deyecloud.com"

# Enumerations documented by the API (kept here for reference and reuse).
WORK_MODES = {
    "SELLING_FIRST",
    "ZERO_EXPORT_TO_LOAD",
    "ZERO_EXPORT_TO_CT",
}
MICRO_STORAGE_WORK_MODES = {
    "GREEN_POWER_MODE",
    "FULL_CHARGE_MODE",
    "CUSTOMIZED_MODE",
}
LIMIT_CONTROL_MODES = {
    "SELL_FIRST",
    "ZERO_EXPORT_TO_UPS_LOAD",
    "ZERO_EXPORT_TO_CT",
    "ZERO_EXPORT_TO_WIRELESS_CT",
}
ENERGY_PATTERNS = {"BATTERY_FIRST", "LOAD_FIRST"}
BATTERY_PARAMETERS = {
    "MAX_CHARGE_CURRENT",
    "MAX_DISCHARGE_CURRENT",
    "GRID_CHARGE_AMPERE",
    "BATT_LOW",
}
BATTERY_TYPES = {"BATT_V", "BATT_SOC", "LI", "NO_BATTERY"}
WEEKDAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

# Station history granularity: 1=frame (power only), 2=day, 3=month, 4=year.
STATION_HISTORY_GRANULARITY = {"frame": 1, "day": 2, "month": 3, "year": 4}
# Device history granularity: 1=day, 2=day-range, 3=month-range, 4=year.
DEVICE_HISTORY_GRANULARITY = {"day": 1, "day_range": 2, "month": 3, "year": 4}

# Order status values returned by ``GET /v1.0/order/{orderId}``.
ORDER_STATUS = {
    0: "PENDING",
    100: "SENDING",
    300: "UPGRADING",
    400: "TERMINATED",
    500: "FAILED",
    666: "SUCCEEDED",
}
