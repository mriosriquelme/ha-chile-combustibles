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

DEFAULT_RADIUS_KM = 20.0
DEFAULT_UPDATE_INTERVAL_HOURS = 6
DEFAULT_INCLUDE_ASSISTED = True
DEFAULT_INCLUDE_SELF_SERVICE = True
DEFAULT_TOP_STATIONS = 5
DEFAULT_TIMEOUT = 30

MIN_RADIUS_KM = 1.0
MAX_RADIUS_KM = 200.0
MIN_UPDATE_INTERVAL_HOURS = 1
MAX_UPDATE_INTERVAL_HOURS = 24
MIN_TOP_STATIONS = 1
MAX_TOP_STATIONS = 10

BASE_URL = "https://api.cne.cl"
LOGIN_ENDPOINT = "/api/login"
STATIONS_ENDPOINT = "/api/v4/estaciones"

PLATFORMS = ["sensor"]

FUEL_DEFINITIONS: dict[str, dict[str, object]] = {
    "93": {
        "name": "Gasolina 93 más barata",
        "icon": "mdi:gas-station",
        "assisted_keys": ("93",),
        "self_service_keys": ("A93",),
    },
    "95": {
        "name": "Gasolina 95 más barata",
        "icon": "mdi:gas-station",
        "assisted_keys": ("95",),
        "self_service_keys": ("A95",),
    },
    "97": {
        "name": "Gasolina 97 más barata",
        "icon": "mdi:gas-station",
        "assisted_keys": ("97",),
        "self_service_keys": ("A97",),
    },
    "diesel": {
        "name": "Diésel más barato",
        "icon": "mdi:fuel",
        "assisted_keys": ("DI",),
        "self_service_keys": ("ADI",),
    },
    "kerosene": {
        "name": "Kerosene más barato",
        "icon": "mdi:fire",
        "assisted_keys": ("KE",),
        "self_service_keys": ("AKE",),
    },
}
