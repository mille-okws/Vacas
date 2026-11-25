"""Conector NASA POWER para variáveis ambientais diárias e observações de superfície."""
from datetime import date, timedelta
import math
from ..coordinates import validate_coordinate
from ..contracts import ClimateDataset, DataQuality, Measurement
from .base import BaseConnector


class NasaPowerConnector(BaseConnector):
    source = 'nasa-power'
    version = 'power-api-v2.8.0/parser-2'
    url = 'https://power.larc.nasa.gov/api/temporal/daily/point'
    # POWER não publica ET0: estes campos alimentam o Penman-Monteith FAO-56 (safra.science.et0).
    # Máx./mín. têm nomes próprios para não substituir a projeção em merge_observed_climate.
    variables = {'T2M': ('temperature_2m_mean', '°C'), 'PRECTOTCORR': ('precipitation_sum', 'mm'),
                 'ALLSKY_SFC_SW_DWN': ('surface_solar_radiation', 'MJ/m²/day'),
                 'T2M_MAX': ('air_temperature_max', '°C'), 'T2M_MIN': ('air_temperature_min', '°C'),
                 'T2MDEW': ('dew_point_temperature', '°C'), 'WS2M': ('wind_speed_2m', 'm/s')}

    def fetch(self, latitude, longitude, start='2021-01-01', end='2050-12-31'):
        coord = validate_coordinate(latitude, longitude)
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if first > last or last.year > 2050:
            raise ValueError('período NASA POWER inválido')
        params = {'parameters': ','.join(self.variables), 'community': 'AG', 'longitude': coord.longitude,
                  'latitude': coord.latitude, 'start': first.strftime('%Y%m%d'), 'end': last.strftime('%Y%m%d'),
                  'format': 'JSON', 'time-standard': 'UTC'}
        payload, cached, error = self.get_json(self.url, params,
            validator=lambda p: isinstance(p.get('properties'), dict) and isinstance(p['properties'].get('parameter'), dict))
        raw = payload.get('properties', {}).get('parameter', {}) if payload else {}
        dates = [(first + timedelta(days=i)).isoformat() for i in range((last-first).days + 1)]

        def read(name, day):
            values = raw.get(name, {}) if isinstance(raw, dict) else {}
            value = values.get(day.replace('-', '')) if isinstance(values, dict) else None
            valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > -900
            return float(value) if valid else None

        grid = {name: [read(name, day) for day in dates] for name in self.variables}
        # Cada variável tem atraso próprio (radiação ~2 meses): o fim da série é o último dia com todas.
        full = [i for i in range(len(dates)) if all(grid[name][i] is not None for name in grid)]
        if full:
            dates = dates[:full[-1] + 1]
        variables = {}
        valid_count = 0
        for name, (target, unit) in self.variables.items():
            series = []
            for day, value in zip(dates, grid[name]):
                valid_count += value is not None
                series.append(Measurement(value, unit, self.url, self.version, period=day,
                    quality=DataQuality('estimated' if value is not None else 'missing', uncertain=True)))
            variables[target] = series
        total = len(dates) * len(self.variables)
        status = 'complete' if valid_count == total else 'partial' if valid_count else 'unavailable'
        if error and payload is not None: status = 'partial'
        return ClimateDataset(coord.latitude, coord.longitude, variables, self.source, self.version,
            DataQuality(status, uncertain=True, note=error),
            {'url': self.url, 'cached': cached, 'cache_expired': bool(error and cached),
             'requested_period': [start, end], 'observed_until': dates[-1] if full else None,
             'parameters': list(self.variables),
             'elevation_m': _elevation(payload),
             'source': 'NASA Langley Research Center POWER'})


def _elevation(payload):
    coords = (payload or {}).get('geometry', {}).get('coordinates') if isinstance(payload, dict) else None
    value = coords[2] if isinstance(coords, list) and len(coords) == 3 else None
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None
