"""Sensor platform for Chile Combustibles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
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

STATIONS_COUNT_SENSOR = SensorEntityDescription(
    key="stations_in_radius",
    translation_key="stations_in_radius",
    name="Estaciones en el radio",
    icon="mdi:map-marker-radius",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Chile Combustibles sensors."""
    coordinator: CNECombustiblesCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        CNEFuelSensor(coordinator, entry, description)
        for description in FUEL_SENSORS
    ]
    entities.extend(
        (
            CNENearestStationSensor(coordinator, entry, NEAREST_SENSOR),
            CNEStationsCountSensor(coordinator, entry, STATIONS_COUNT_SENSOR),
        )
    )
    async_add_entities(entities)


class CNEBaseSensor(CoordinatorEntity[CNECombustiblesCoordinator], SensorEntity):
    """Base sensor for Chile Combustibles."""

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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer=MANUFACTURER,
            model="API Combustibles",
            configuration_url="https://api.cne.cl",
        )


class CNEFuelSensor(CNEBaseSensor):
    """Sensor exposing the cheapest fuel offer."""

    entity_description: CNEFuelSensorDescription

    @property
    def native_value(self) -> float | None:
        offer = self._offer
        return round(offer.price) if offer else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        offer = self._offer
        attrs: dict[str, Any] = {
            "average_price": self.coordinator.data.average_prices.get(
                self.entity_description.fuel_key
            ),
            "stations_in_radius": self.coordinator.data.stations_in_radius,
            "total_stations": self.coordinator.data.total_stations,
            "top_stations": [
                item.as_attribute_dict()
                for item in self.coordinator.data.top_offers.get(
                    self.entity_description.fuel_key, []
                )
            ],
        }
        if offer:
            attrs.update(offer.as_attribute_dict())
        return attrs

    @property
    def _offer(self) -> FuelOffer | None:
        return self.coordinator.data.cheapest.get(self.entity_description.fuel_key)


class CNENearestStationSensor(CNEBaseSensor):
    """Nearest station sensor."""

    @property
    def native_value(self) -> float | None:
        station = self.coordinator.data.nearest_station
        return station.distance_km if station else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        station = self.coordinator.data.nearest_station
        attrs: dict[str, Any] = {
            "nearby_stations": [
                item.as_attribute_dict()
                for item in self.coordinator.data.nearby_stations
            ]
        }
        if station:
            attrs.update(station.as_attribute_dict())
            attrs["prices"] = station.prices
        return attrs


class CNEStationsCountSensor(CNEBaseSensor):
    """Number of stations inside the configured radius."""

    @property
    def native_value(self) -> int:
        return self.coordinator.data.stations_in_radius

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"total_stations": self.coordinator.data.total_stations}
