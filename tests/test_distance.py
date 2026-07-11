"""Basic unit tests for distance calculations."""

from custom_components.cne_combustibles_cl.coordinator import _haversine_km


def test_same_point_is_zero() -> None:
    assert _haversine_km(-36.6, -72.1, -36.6, -72.1) == 0


def test_distance_is_reasonable() -> None:
    distance = _haversine_km(-36.606, -72.103, -36.616, -72.103)
    assert 1.0 < distance < 1.2
