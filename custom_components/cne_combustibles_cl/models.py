"""Data models for CNE Combustibles Chile."""

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


@dataclass(frozen=True, slots=True)
class StationSummary:
    """Normalized nearest station information."""

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
