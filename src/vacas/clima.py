"""Coleta de clima histórico, projeção e NASA POWER para a triagem de monta."""
from __future__ import annotations

from datetime import date, timedelta

from .config import Settings
from .connectors.climate import HistoricalClimateConnector, ProjectionClimateConnector
from .connectors.nasa import NasaPowerConnector
from .contracts import ClimateDataset

NASA_PUBLICATION_LAG = timedelta(days=7)


def merge_observed_climate(projected: ClimateDataset | None,
                           observed: ClimateDataset | None) -> ClimateDataset | None:
    """Substitui dias sobrepostos da projeção por observações NASA válidas, por variável e data."""
    if projected is None or observed is None:
        return projected
    observed_by_variable = {}
    for variable, values in observed.variables.items():
        indexed = {}
        for item in values:
            try:
                day = date.fromisoformat(item.period)
            except (TypeError, ValueError):
                continue
            if not item.missing:
                indexed[day] = item
        if indexed:
            observed_by_variable[variable] = indexed
    if not observed_by_variable:
        return projected

    variables, replaced, used_variables = {}, 0, set()
    for variable, values in projected.variables.items():
        merged = []
        observed_values = observed_by_variable.get(variable, {})
        for item in values:
            try:
                day = date.fromisoformat(item.period)
            except (TypeError, ValueError):
                merged.append(item)
                continue
            replacement = observed_values.get(day)
            if replacement is not None and replacement.unit == item.unit:
                merged.append(replacement)
                replaced += 1
                used_variables.add(variable)
            else:
                merged.append(item)
        variables[variable] = merged
    metadata = dict(projected.metadata)
    metadata['observed_source'] = observed.source
    metadata['observed_variables'] = sorted(used_variables)
    metadata['observed_measurements_used'] = replaced
    metadata['source_mix'] = 'NASA POWER observations overlaid on projected climate where dates overlap'
    return ClimateDataset(projected.latitude, projected.longitude, variables,
                          projected.source, projected.version, projected.quality, metadata)


def collect_climate(settings: Settings, latitude: float, longitude: float, start_year: int,
                    end_year: int, future_until: int) -> dict:
    """Busca histórico, projeção e NASA; falha de uma fonte não derruba as outras."""
    cache, timeout, ttl = settings.cache_dir, settings.timeout, settings.cache_ttl
    nasa_end = min(date.today() - NASA_PUBLICATION_LAG, date(future_until, 12, 31)).isoformat()
    jobs = {
        'historical': lambda: HistoricalClimateConnector(cache, timeout, ttl).fetch(
            latitude, longitude, f'{start_year}-01-01', f'{min(end_year, 2020)}-12-31'),
        'future': lambda: ProjectionClimateConnector(cache, timeout, ttl).fetch(
            latitude, longitude, '2021-01-01', f'{min(future_until, end_year)}-12-31'),
        'nasa_power': lambda: NasaPowerConnector(cache, timeout, ttl).fetch(
            latitude, longitude, f'{max(2021, start_year)}-01-01', nasa_end),
    }
    datasets, errors = {}, {}
    for name, job in jobs.items():
        try:
            datasets[name] = job()
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            datasets[name] = None
            errors[name] = f'{type(exc).__name__}: {exc}'
    datasets['errors'] = errors
    return datasets
