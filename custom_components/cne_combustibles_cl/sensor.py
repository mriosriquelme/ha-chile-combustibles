"""Sensor platform for Chile Combustibles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    FUEL_DEFINITIONS,
    MANUFACTURER,
    MAX_STATE_LENGTH,
    NAME,
    UNIT_CLP_PER_LITRE,
    UNIT_STATIONS,
)
from .coordinator import CNECombustiblesCoordinator
from .models import FuelOffer

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class CNEFuelSensorDescription(SensorEntityDescription):
    """Description for a fuel sensor."""

    fuel_key: str


FUEL_SENSORS = tuple(
    CNEFuelSensorDescription(
        key=fuel_key,
        translation_key=f"fuel_{fuel_key}",
        native_unit_of_measurement=UNIT_CLP_PER_LITRE,
        suggested_display_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        fuel_key=fuel_key,
    )
    for fuel_key in FUEL_DEFINITIONS
)

# Text sensors must not declare a unit, a state class or a display precision:
# any of those makes Home Assistant treat the state as numeric.
LOCATION_SENSORS = tuple(
    CNEFuelSensorDescription(
        key=f"fuel_{fuel_key}_location",
        translation_key=f"fuel_{fuel_key}_location",
        fuel_key=fuel_key,
    )
    for fuel_key in FUEL_DEFINITIONS
)

NEAREST_SENSOR = SensorEntityDescription(
    key="nearest_station",
    translation_key="nearest_station",
    native_unit_of_measurement=UnitOfLength.KILOMETERS,
    suggested_display_precision=2,
    state_class=SensorStateClass.MEASUREMENT,
)

STATIONS_COUNT_SENSOR = SensorEntityDescription(
    key="stations_in_radius",
    translation_key="stations_in_radius",
    native_unit_of_measurement=UNIT_STATIONS,
    state_class=SensorStateClass.MEASUREMENT,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Chile Combustibles sensors."""
    coordinator: CNECombustiblesCoordinator = entry.runtime_data

    entities: list[SensorEntity] = [
        CNEFuelSensor(coordinator, entry, description) for description in FUEL_SENSORS
    ]

    entities.extend(
        CNEFuelLocationSensor(coordinator, entry, description)
        for description in LOCATION_SENSORS
    )

    entities.extend(
        (
            CNENearestStationSensor(coordinator, entry, NEAREST_SENSOR),
            CNEStationsCountSensor(coordinator, entry, STATIONS_COUNT_SENSOR),
        )
    )

    async_add_entities(entities)


class CNEBaseSensor(
    CoordinatorEntity[CNECombustiblesCoordinator],
    SensorEntity,
):
    """Base sensor for Chile Combustibles."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CNECombustiblesCoordinator,
        entry: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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

    @property
    def _has_data(self) -> bool:
        """Return whether this sensor has a value to report."""
        return True

    @property
    def available(self) -> bool:
        """Return True when the coordinator succeeded and data is present."""
        return super().available and self._has_data


class CNEFuelFamilySensor(CNEBaseSensor):
    """Base for sensors bound to a single fuel type."""

    entity_description: CNEFuelSensorDescription

    @property
    def _offer(self) -> FuelOffer | None:
        """Return the cheapest offer for this fuel."""
        return self.coordinator.data.cheapest.get(self.entity_description.fuel_key)

    @property
    def _has_data(self) -> bool:
        """Return whether an offer was found for this fuel."""
        return self._offer is not None


class CNEFuelSensor(CNEFuelFamilySensor):
    """Sensor for the cheapest fuel price."""

    @property
    def native_value(self) -> float | None:
        """Return the cheapest fuel price."""
        offer = self._offer
        return round(offer.price) if offer else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional fuel attributes."""
        fuel_key = self.entity_description.fuel_key
        offer = self._offer
        nearest = self.coordinator.data.nearest_offers.get(fuel_key)

        attrs: dict[str, Any] = {
            "average_price": self.coordinator.data.average_prices.get(fuel_key),
            "stations_in_radius": self.coordinator.data.stations_in_radius,
            "total_stations": self.coordinator.data.total_stations,
            "tank_capacity_l": self.coordinator.data.tank_capacity_l,
            "top_stations": [
                item.as_attribute_dict()
                for item in self.coordinator.data.top_offers.get(fuel_key, [])
            ],
        }

        if offer:
            attrs.update(offer.as_attribute_dict())
            attrs["estimated_full_tank_cost"] = round(
                offer.price * self.coordinator.data.tank_capacity_l
            )

        if offer and nearest:
            difference = round(nearest.price - offer.price)

            attrs.update(
                {
                    "nearest_station_brand": nearest.brand,
                    "nearest_station_address": nearest.address,
                    "nearest_station_distance_km": nearest.distance_km,
                    "nearest_station_price": round(nearest.price),
                    "price_difference_vs_nearest": difference,
                    "estimated_savings_full_tank": round(
                        max(0, difference) * self.coordinator.data.tank_capacity_l
                    ),
                }
            )

        return attrs


class CNEFuelLocationSensor(CNEFuelFamilySensor):
    """Human-readable recommendation showing where to refuel."""

    @property
    def native_value(self) -> str | None:
        """Return the recommended station, capped to the HA state length limit."""
        offer = self._offer
        if offer is None:
            return None
        return f"{offer.brand} · {offer.address}"[:MAX_STATE_LENGTH]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the recommended station attributes."""
        offer = self._offer
        return offer.as_attribute_dict() if offer else {}


class CNENearestStationSensor(CNEBaseSensor):
    """Sensor for the nearest station."""

    @property
    def _has_data(self) -> bool:
        """Return whether a nearest station was found."""
        return self.coordinator.data.nearest_station is not None

    @property
    def native_value(self) -> float | None:
        """Return the distance to the nearest station."""
        station = self.coordinator.data.nearest_station
        return station.distance_km if station else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return nearest and nearby station attributes."""
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
    """Sensor for stations inside the configured radius."""

    @property
    def native_value(self) -> int:
        """Return the number of stations inside the radius."""
        return self.coordinator.data.stations_in_radius

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the total number of stations."""
        return {
            "total_stations": self.coordinator.data.total_stations,
        }
