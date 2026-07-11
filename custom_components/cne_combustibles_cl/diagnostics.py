"""Diagnostics support for Chile Combustibles."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_EMAIL, CONF_PASSWORD
from .coordinator import CNECombustiblesCoordinator

TO_REDACT = {CONF_EMAIL, CONF_PASSWORD, "latitude", "longitude", "google_maps_url"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics."""
    coordinator: CNECombustiblesCoordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "options": dict(entry.options)}, TO_REDACT
        ),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "stations_in_radius": data.stations_in_radius,
            "total_stations": data.total_stations,
            "available_fuels": [
                key for key, offer in data.cheapest.items() if offer is not None
            ],
        },
    }
