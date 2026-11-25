from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Coordinate:
    latitude: float
    longitude: float


def validate_coordinate(latitude: float, longitude: float) -> Coordinate:
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError) as exc:
        raise ValueError("latitude e longitude devem ser números") from exc
    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValueError("latitude e longitude devem ser finitas")
    if not -90 <= lat <= 90:
        raise ValueError("latitude deve estar entre -90 e 90 graus")
    if not -180 <= lon <= 180:
        raise ValueError("longitude deve estar entre -180 e 180 graus")
    if lon == 180:
        lon = -180.0
    return Coordinate(lat, lon)
