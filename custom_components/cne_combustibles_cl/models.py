"""Data models for Chile Combustibles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FuelOffer:
    """Normalized fuel offer."""

    fuel_key: str
    price: float
    station_code: str
    brand: str
    address: str
    latitude: float
    longitude: float
    distance_km: float
    service_type: str
    updated_at: str | None
    unit: str | None

    @property
    def maps_url(self) -> str:
        """Return a Google Maps directions URL."""
        return (
            "https://www.google.com/maps/dir/?api=1&destination="
            f"{self.latitude},{self.longitude}"
        )

    def as_attribute_dict(self) -> dict[str, Any]:
        """Return a safe representation for entity attributes."""
        return {
            "price": round(self.price),
            "brand": self.brand,
            "address": self.address,
            "distance_km": self.distance_km,
            "service_type": self.service_type,
            "last_price_update": self.updated_at,
            "station_code": self.station_code,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "google_maps_url": self.maps_url,
        }


@dataclass(frozen=True, slots=True)
class StationSummary:
    """Normalized station information."""

    station_code: str
    brand: str
    address: str
    latitude: float
    longitude: float
    distance_km: float
    prices: dict[str, Any]

    @property
    def maps_url(self) -> str:
        """Return a Google Maps directions URL."""
        return (
            "https://www.google.com/maps/dir/?api=1&destination="
            f"{self.latitude},{self.longitude}"
        )

    def as_attribute_dict(self) -> dict[str, Any]:
        """Return a safe representation for entity attributes."""
        return {
            "station_code": self.station_code,
            "brand": self.brand,
            "address": self.address,
            "distance_km": self.distance_km,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "google_maps_url": self.maps_url,
        }
