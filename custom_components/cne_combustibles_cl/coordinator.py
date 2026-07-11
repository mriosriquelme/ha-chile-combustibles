"""Data update coordinator for CNE Combustibles Chile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from math import asin, cos, radians, sin, sqrt
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CNEApiClient
from .const import (
    CONF_INCLUDE_ASSISTED,
    CONF_INCLUDE_SELF_SERVICE,
    CONF_RADIUS_KM,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_INCLUDE_ASSISTED,
    DEFAULT_INCLUDE_SELF_SERVICE,
    DEFAULT_RADIUS_KM,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
    FUEL_DEFINITIONS,
)
from .exceptions import CNEAuthenticationError, CNEError
from .models import FuelOffer, StationSummary

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CNECoordinatorData:
    """Processed coordinator data."""

    cheapest: dict[str, FuelOffer | None]
    nearest_station: StationSummary | None
    stations_in_radius: int
    total_stations: int


class CNECombustiblesCoordinator(DataUpdateCoordinator[CNECoordinatorData]):
    """Coordinate fetching and processing CNE station data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: CNEApiClient,
    ) -> None:
        self.entry = entry
        self.client = client
        self.home_latitude = float(hass.config.latitude)
        self.home_longitude = float(hass.config.longitude)

        interval_hours = int(
            entry.options.get(
                CONF_UPDATE_INTERVAL_HOURS,
                entry.data.get(
                    CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS
                ),
            )
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=interval_hours),
            always_update=False,
        )

    async def _async_update_data(self) -> CNECoordinatorData:
        """Fetch and normalize stations."""
        try:
            stations = await self.client.async_get_stations()
        except CNEAuthenticationError:
            self.entry.async_start_reauth(self.hass)
            raise UpdateFailed("Autenticación CNE inválida")
        except CNEError as err:
            raise UpdateFailed(str(err)) from err

        return self._process_stations(stations)

    def _process_stations(
        self, stations: list[dict[str, Any]]
    ) -> CNECoordinatorData:
        radius_km = float(
            self.entry.options.get(
                CONF_RADIUS_KM,
                self.entry.data.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM),
            )
        )
        include_assisted = bool(
            self.entry.options.get(
                CONF_INCLUDE_ASSISTED,
                self.entry.data.get(
                    CONF_INCLUDE_ASSISTED, DEFAULT_INCLUDE_ASSISTED
                ),
            )
        )
        include_self_service = bool(
            self.entry.options.get(
                CONF_INCLUDE_SELF_SERVICE,
                self.entry.data.get(
                    CONF_INCLUDE_SELF_SERVICE, DEFAULT_INCLUDE_SELF_SERVICE
                ),
            )
        )

        cheapest: dict[str, FuelOffer | None] = {
            key: None for key in FUEL_DEFINITIONS
        }
        nearest: StationSummary | None = None
        stations_in_radius = 0

        for station in stations:
            location = station.get("ubicacion")
            if not isinstance(location, dict):
                continue

            try:
                latitude = float(location.get("latitud"))
                longitude = float(location.get("longitud"))
            except (TypeError, ValueError):
                continue

            distance = _haversine_km(
                self.home_latitude,
                self.home_longitude,
                latitude,
                longitude,
            )

            distributor = station.get("distribuidor")
            brand = (
                distributor.get("marca", "Sin marca")
                if isinstance(distributor, dict)
                else "Sin marca"
            )
            address = str(location.get("direccion") or "Sin dirección")
            station_code = str(station.get("codigo") or "desconocido")
            prices = station.get("precios")
            if not isinstance(prices, dict):
                prices = {}

            summary = StationSummary(
                station_code=station_code,
                brand=str(brand),
                address=address,
                latitude=latitude,
                longitude=longitude,
                distance_km=round(distance, 2),
                prices=prices,
            )
            if nearest is None or distance < nearest.distance_km:
                nearest = summary

            if distance > radius_km:
                continue
            stations_in_radius += 1

            for fuel_key, definition in FUEL_DEFINITIONS.items():
                key_groups: list[tuple[tuple[str, ...], str]] = []
                if include_assisted:
                    key_groups.append((definition["assisted_keys"], "Asistido"))
                if include_self_service:
                    key_groups.append(
                        (definition["self_service_keys"], "Autoservicio")
                    )

                for api_keys, fallback_service_type in key_groups:
                    for api_key in api_keys:
                        offer_data = prices.get(api_key)
                        if not isinstance(offer_data, dict):
                            continue
                        try:
                            price = float(offer_data.get("precio"))
                        except (TypeError, ValueError):
                            continue
                        if price <= 0:
                            continue

                        service_type = str(
                            offer_data.get("tipo_atencion")
                            or fallback_service_type
                        )
                        date = offer_data.get("fecha_actualizacion")
                        time = offer_data.get("hora_actualizacion")
                        updated_at = None
                        if date and time:
                            updated_at = f"{date} {time}"
                        elif date:
                            updated_at = str(date)

                        offer = FuelOffer(
                            fuel_key=fuel_key,
                            price=price,
                            station_code=station_code,
                            brand=str(brand),
                            address=address,
                            latitude=latitude,
                            longitude=longitude,
                            distance_km=round(distance, 2),
                            service_type=service_type,
                            updated_at=updated_at,
                            unit=offer_data.get("unidad_cobro"),
                        )

                        current = cheapest[fuel_key]
                        if current is None or (
                            offer.price,
                            offer.distance_km,
                        ) < (
                            current.price,
                            current.distance_km,
                        ):
                            cheapest[fuel_key] = offer

        return CNECoordinatorData(
            cheapest=cheapest,
            nearest_station=nearest,
            stations_in_radius=stations_in_radius,
            total_stations=len(stations),
        )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance in kilometers."""
    earth_radius_km = 6371.0088
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    a = (
        sin(d_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(a))
