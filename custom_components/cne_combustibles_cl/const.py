"""Constants for Chile Combustibles."""

from __future__ import annotations

DOMAIN = "cne_combustibles_cl"
NAME = "Chile Combustibles"
MANUFACTURER = "Comisión Nacional de Energía"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_RADIUS_KM = "radius_km"
CONF_UPDATE_INTERVAL_HOURS = "update_interval_hours"
CONF_INCLUDE_ASSISTED = "include_assisted"
CONF_INCLUDE_SELF_SERVICE = "include_self_service"
CONF_TOP_STATIONS = "top_stations"
CONF_TANK_CAPACITY_L = "tank_capacity_l"

DEFAULT_RADIUS_KM = 20.0
DEFAULT_UPDATE_INTERVAL_HOURS = 6
DEFAULT_INCLUDE_ASSISTED = True
DEFAULT_INCLUDE_SELF_SERVICE = True
DEFAULT_TOP_STATIONS = 5
DEFAULT_TANK_CAPACITY_L = 50
DEFAULT_TIMEOUT = 30

MIN_RADIUS_KM = 1.0
MAX_RADIUS_KM = 200.0
MIN_UPDATE_INTERVAL_HOURS = 1
MAX_UPDATE_INTERVAL_HOURS = 24
MIN_TOP_STATIONS = 1
MAX_TOP_STATIONS = 10
MIN_TANK_CAPACITY_L = 10
MAX_TANK_CAPACITY_L = 200

BASE_URL = "https://api.cne.cl"
LOGIN_ENDPOINT = "/api/login"
STATIONS_ENDPOINT = "/api/v4/estaciones"

PLATFORMS = ["sensor"]

UNIT_CLP_PER_LITRE = "CLP/L"
UNIT_STATIONS = "estaciones"

# Home Assistant rejects entity states longer than 255 characters.
MAX_STATE_LENGTH = 255

# Display names live in strings.json / translations and icons in icons.json,
# keyed by the sensor translation_key (fuel_<key> and fuel_<key>_location).
FUEL_DEFINITIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "93": {
        "assisted_keys": ("93",),
        "self_service_keys": ("A93",),
    },
    "95": {
        "assisted_keys": ("95",),
        "self_service_keys": ("A95",),
    },
    "97": {
        "assisted_keys": ("97",),
        "self_service_keys": ("A97",),
    },
    "diesel": {
        "assisted_keys": ("DI",),
        "self_service_keys": ("ADI",),
    },
    "kerosene": {
        "assisted_keys": ("KE",),
        "self_service_keys": ("AKE",),
    },
}
