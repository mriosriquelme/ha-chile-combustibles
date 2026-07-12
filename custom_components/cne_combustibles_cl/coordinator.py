"""Data update coordinator for Chile Combustibles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from math import asin, cos, radians, sin, sqrt
from statistics import fmean
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CNEApiClient
from .const import (
    CONF_INCLUDE_ASSISTED,
    CONF_INCLUDE_SELF_SERVICE,
    CONF_RADIUS_KM,
    CONF_TANK_CAPACITY_L,
    CONF_TOP_STATIONS,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_INCLUDE_ASSISTED,
    DEFAULT_INCLUDE_SELF_SERVICE,
    DEFAULT_RADIUS_KM,
    DEFAULT_TANK_CAPACITY_L,
    DEFAULT_TOP_STATIONS,
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
    nearest_offers: dict[str, FuelOffer | None]
    top_offers: dict[str, list[FuelOffer]]
    average_prices: dict[str, float | None]
    nearest_station: StationSummary | None
    nearby_stations: list[StationSummary]
    stations_in_radius: int
    total_stations: int
    tank_capacity_l: float


class CNECombustiblesCoordinator(DataUpdateCoordinator[CNECoordinatorData]):
    """Coordinate fetching and processing CNE station data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: CNEApiClient) -> None:
        self.entry = entry
        self.client = client
        self.home_latitude = float(hass.config.latitude)
        self.home_longitude = float(hass.config.longitude)
        interval_hours = int(entry.options.get(
            CONF_UPDATE_INTERVAL_HOURS,
            entry.data.get(CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS),
        ))
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=interval_hours),
            always_update=False,
            config_entry=entry,
        )

    async def _async_update_data(self) -> CNECoordinatorData:
        try:
            stations = await self.client.async_get_stations()
        except CNEAuthenticationError as err:
            self.entry.async_start_reauth(self.hass)
            raise UpdateFailed("Autenticación CNE inválida") from err
        except CNEError as err:
            raise UpdateFailed(str(err)) from err
        return self._process_stations(stations)

    def _process_stations(self, stations: list[dict[str, Any]]) -> CNECoordinatorData:
        radius_km = float(self.entry.options.get(
            CONF_RADIUS_KM, self.entry.data.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
        ))
        include_assisted = bool(self.entry.options.get(
            CONF_INCLUDE_ASSISTED,
            self.entry.data.get(CONF_INCLUDE_ASSISTED, DEFAULT_INCLUDE_ASSISTED),
        ))
        include_self_service = bool(self.entry.options.get(
            CONF_INCLUDE_SELF_SERVICE,
            self.entry.data.get(CONF_INCLUDE_SELF_SERVICE, DEFAULT_INCLUDE_SELF_SERVICE),
        ))
        top_limit = int(self.entry.options.get(
            CONF_TOP_STATIONS, self.entry.data.get(CONF_TOP_STATIONS, DEFAULT_TOP_STATIONS)
        ))
        tank_capacity_l = float(self.entry.options.get(
            CONF_TANK_CAPACITY_L,
            self.entry.data.get(CONF_TANK_CAPACITY_L, DEFAULT_TANK_CAPACITY_L),
        ))

        offers: dict[str, list[FuelOffer]] = {key: [] for key in FUEL_DEFINITIONS}
        station_summaries: list[StationSummary] = []

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
                self.home_latitude, self.home_longitude, latitude, longitude
            )
            distributor = station.get("distribuidor")
            brand = (
                str(distributor.get("marca") or "Sin marca")
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
                brand=brand,
                address=address,
                latitude=latitude,
                longitude=longitude,
                distance_km=round(distance, 2),
                prices=prices,
            )
            station_summaries.append(summary)

            if distance > radius_km:
                continue

            for fuel_key, definition in FUEL_DEFINITIONS.items():
                key_groups: list[tuple[tuple[str, ...], str]] = []
                if include_assisted:
                    key_groups.append((definition["assisted_keys"], "Asistido"))
                if include_self_service:
                    key_groups.append((definition["self_service_keys"], "Autoservicio"))

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
                        date = offer_data.get("fecha_actualizacion")
                        time = offer_data.get("hora_actualizacion")
                        updated_at = (
                            f"{date} {time}" if date and time else str(date) if date else None
                        )
                        offers[fuel_key].append(FuelOffer(
                            fuel_key=fuel_key,
                            price=price,
                            station_code=station_code,
                            brand=brand,
                            address=address,
                            latitude=latitude,
                            longitude=longitude,
                            distance_km=round(distance, 2),
                            service_type=str(offer_data.get("tipo_atencion") or fallback_service_type),
                            updated_at=updated_at,
                            unit=offer_data.get("unidad_cobro"),
                        ))

        station_summaries.sort(key=lambda item: item.distance_km)
        by_price = {
            key: sorted(values, key=lambda item: (item.price, item.distance_km))
            for key, values in offers.items()
        }
        by_distance = {
            key: sorted(values, key=lambda item: (item.distance_km, item.price))
            for key, values in offers.items()
        }
        cheapest = {key: values[0] if values else None for key, values in by_price.items()}
        nearest_offers = {
            key: values[0] if values else None for key, values in by_distance.items()
        }
        averages = {
            key: round(fmean(item.price for item in values), 1) if values else None
            for key, values in by_price.items()
        }
        in_radius = [item for item in station_summaries if item.distance_km <= radius_km]

        return CNECoordinatorData(
            cheapest=cheapest,
            nearest_offers=nearest_offers,
            top_offers={key: values[:top_limit] for key, values in by_price.items()},
            average_prices=averages,
            nearest_station=station_summaries[0] if station_summaries else None,
            nearby_stations=in_radius[:top_limit],
            stations_in_radius=len(in_radius),
            total_stations=len(stations),
            tank_capacity_l=tank_capacity_l,
        )


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0088
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    a = sin(d_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(d_lon / 2) ** 2
    return 2 * earth_radius_km * asin(sqrt(a))
