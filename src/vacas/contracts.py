"""Contratos canônicos da v4.

Os contratos carregam proveniência e qualidade para que nenhum módulo precise
adivinhar a origem, unidade ou completude de um valor.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Mapping
import math
from .coordinates import validate_coordinate


@dataclass(frozen=True)
class DataQuality:
    status: str = "unknown"  # complete, partial, missing, unavailable, estimated
    score: float | None = None
    uncertain: bool = True
    note: str | None = None

    def __post_init__(self):
        if self.status not in {'unknown', 'complete', 'partial', 'missing', 'unavailable', 'estimated'}:
            raise ValueError('status de qualidade inválido')
        if self.score is not None and (not math.isfinite(self.score) or not 0 <= self.score <= 1):
            raise ValueError('qualidade deve estar entre 0 e 1')
        if not isinstance(self.uncertain, bool):
            raise ValueError('uncertain deve ser booleano')


@dataclass(frozen=True)
class Measurement:
    value: Any
    unit: str
    source: str
    version: str
    period: str | None = None
    depth: str | None = None
    quality: DataQuality = field(default_factory=DataQuality)
    missing: bool = False
    lower: float | None = None
    upper: float | None = None

    def __post_init__(self):
        if not all(isinstance(x, str) and x.strip() for x in (self.unit, self.source, self.version)):
            raise ValueError('unidade, fonte e versão são obrigatórias')
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError('valor deve ser finito')
        if self.value is None:
            object.__setattr__(self, 'missing', True)
            if self.quality.status in {'complete', 'unknown', 'estimated'}:
                object.__setattr__(self, 'quality', DataQuality('missing', uncertain=True, note=self.quality.note))
        elif self.missing:
            raise ValueError('valor disponível não pode ser marcado como ausente')
        if self.lower is not None and self.upper is not None and self.lower > self.upper:
            raise ValueError('intervalo de incerteza invertido')
        if any(v is not None and not math.isfinite(v) for v in (self.lower, self.upper)):
            raise ValueError('intervalo deve ser finito')


@dataclass(frozen=True)
class AssessmentRequest:
    latitude: float
    longitude: float
    start_year: int = 1991
    end_year: int = 2020
    future_until: int = 2050
    crops: tuple[str, ...] = ()
    scenario: str = "baseline"
    irrigation: bool | None = None

    def __post_init__(self):
        coord = validate_coordinate(self.latitude, self.longitude)
        object.__setattr__(self, 'latitude', coord.latitude)
        object.__setattr__(self, 'longitude', coord.longitude)
        if not all(type(y) is int for y in (self.start_year,self.end_year,self.future_until)) or not 1900 <= self.start_year <= self.end_year <= self.future_until <= 2050:
            raise ValueError('anos devem estar ordenados entre 1900 e 2050')


@dataclass
class ClimateDataset:
    latitude: float
    longitude: float
    variables: dict[str, list[Measurement]] = field(default_factory=dict)
    source: str = "unknown"
    version: str = "unknown"
    quality: DataQuality = field(default_factory=DataQuality)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        c = validate_coordinate(self.latitude, self.longitude)
        self.latitude, self.longitude = c.latitude, c.longitude


@dataclass
class SoilProfile:
    latitude: float
    longitude: float
    layers: dict[str, dict[str, Measurement]] = field(default_factory=dict)
    source: str = "unknown"
    version: str = "unknown"
    quality: DataQuality = field(default_factory=DataQuality)

    def __post_init__(self):
        c = validate_coordinate(self.latitude, self.longitude)
        self.latitude, self.longitude = c.latitude, c.longitude


@dataclass(frozen=True)
class CropProfile:
    crop_id: str
    scientific_name: str
    requirements: Mapping[str, Measurement]
    source: str
    version: str
    quality: DataQuality = field(default_factory=DataQuality)

    def __post_init__(self):
        if not self.crop_id or not self.scientific_name or not self.requirements:
            raise ValueError('perfil de cultura vazio ou sem identificação')


@dataclass(frozen=True)
class CultivationScenario:
    crop_id: str
    planting_date: date | None = None
    harvest_date: date | None = None
    irrigated: bool = False
    variety: str | None = None
    interventions: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.crop_id:
            raise ValueError('cultura obrigatória')
        if self.planting_date and self.harvest_date and self.harvest_date < self.planting_date:
            raise ValueError('colheita anterior ao plantio')


@dataclass(frozen=True)
class SuitabilityResult:
    crop_id: str
    adequacy_percent: float | None
    status: str
    components: Mapping[str, float | None]
    limitations: tuple[str, ...]
    missing_data: tuple[str, ...]
    quality: DataQuality

    def __post_init__(self):
        if self.status not in {'complete', 'partial', 'restricted', 'unavailable'}:
            raise ValueError('status de avaliação inválido')
        if self.adequacy_percent is not None and (not math.isfinite(self.adequacy_percent) or not 0 <= self.adequacy_percent <= 100):
            raise ValueError('adequação deve estar entre 0 e 100')
        if self.status in {'partial', 'unavailable'} and self.adequacy_percent is not None:
            raise ValueError('avaliação incompleta não deve ter percentual final')
        for value in self.components.values():
            if value is not None and (not math.isfinite(value) or not 0 <= value <= 1):
                raise ValueError('componentes devem estar entre 0 e 1')


@dataclass(frozen=True)
class AssessmentReport:
    request: AssessmentRequest
    results: tuple[SuitabilityResult, ...]
    datasets: Mapping[str, str]
    generated_at: str
    quality: DataQuality

    def __post_init__(self):
        from datetime import datetime
        datetime.fromisoformat(self.generated_at.replace('Z', '+00:00'))
