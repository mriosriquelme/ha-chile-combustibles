"""Sensor platform for CNE Combustibles Chile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FUEL_DEFINITIONS, MANUFACTURER, NAME
from .coordinator import CNECombustiblesCoordinator
from .models import FuelOffer

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class CNEFuelSensorDescription(SensorEntityDescription):
    """Description for a CNE fuel sensor."""

    fuel_key: str


FUEL_SENSORS = tuple(
    CNEFuelSensorDescription(
        key=fuel_key,
        translation_key=f"fuel_{fuel_key}",
        name=definition["name"],
        icon=definition["icon"],
        native_unit_of_measurement="CLP/L",
        suggested_display_precision=0,
        fuel_key=fuel_key,
    )
    for fuel_key, definition in FUEL_DEFINITIONS.items()
)

NEAREST_SENSOR = SensorEntityDescription(
    key="nearest_station",
    translation_key="nearest_station",
    name="Estación más cercana",
    icon="mdi:map-marker-distance",
    native_unit_of_measurement=UnitOfLength.KILOMETERS,
    suggested_display_precision=2,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up CNE sensors."""
    coordinator: CNECombustiblesCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        CNEFuelSensor(coordinator, entry, description)
        for description in FUEL_SENSORS
    ]
    entities.append(CNENearestStationSensor(coordinator, entry, NEAREST_SENSOR))
    async_add_entities(entities)


class CNEBaseSensor(CoordinatorEntity[CNECombustiblesCoordinator], SensorEntity):
    """Base CNE sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CNECombustiblesCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": NAME,
            "manufacturer": MANUFACTURER,
            "model": "API Combustibles",
            "configuration_url": "https://api.cne.cl/",
        }


class CNEFuelSensor(CNEBaseSensor):
    """Cheapest fuel sensor."""

    entity_description: CNEFuelSensorDescription

    @property
    def native_value(self) -> float | None:
        """Return fuel price."""
        offer = self._offer
        return offer.price if offer else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return station details."""
        offer = self._offer
        if offer is None:
            return {
                "stations_in_radius": self.coordinator.data.stations_in_radius,
                "total_stations": self.coordinator.data.total_stations,
            }

        return {
            "brand": offer.brand,
            "address": offer.address,
            "distance_km": offer.distance_km,
            "service_type": offer.service_type,
            "last_price_update": offer.updated_at,
            "unit": offer.unit,
            "station_code": offer.station_code,
            "latitude": offer.latitude,
            "longitude": offer.longitude,
            "google_maps_url": offer.maps_url,
            "stations_in_radius": self.coordinator.data.stations_in_radius,
            "total_stations": self.coordinator.data.total_stations,
        }

    @property
    def _offer(self) -> FuelOffer | None:
        return self.coordinator.data.cheapest.get(self.entity_description.fuel_key)


class CNENearestStationSensor(CNEBaseSensor):
    """Nearest station sensor."""

    @property
    def native_value(self) -> float | None:
        """Return distance to nearest station."""
        station = self.coordinator.data.nearest_station
        return station.distance_km if station else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return nearest station details."""
        station = self.coordinator.data.nearest_station
        if station is None:
            return {}
        return {
            "brand": station.brand,
            "address": station.address,
            "station_code": station.station_code,
            "latitude": station.latitude,
            "longitude": station.longitude,
            "google_maps_url": station.maps_url,
            "prices": station.prices,
        }
