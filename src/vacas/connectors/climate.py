from datetime import date, timedelta
import math
from ..coordinates import validate_coordinate
from ..contracts import ClimateDataset, DataQuality, Measurement
from .base import BaseConnector

UNITS = {'temperature_2m_mean': '°C', 'temperature_2m_max': '°C', 'temperature_2m_min': '°C', 'precipitation_sum': 'mm'}


class HistoricalClimateConnector(BaseConnector):
    source = 'open-meteo-archive'
    version = 'archive-api-v1/parser-3'
    url = 'https://archive-api.open-meteo.com/v1/archive'
    model = None

    def fetch(self, latitude, longitude, start, end):
        c = validate_coordinate(latitude, longitude)
        first, last = date.fromisoformat(start), date.fromisoformat(end)
        if first > last:
            raise ValueError('período invertido')
        if self.model and not 1950 <= first.year <= last.year <= 2050:
            raise ValueError('projeção disponível entre 1950 e 2050')
        params = {'latitude': c.latitude, 'longitude': c.longitude, 'start_date': start, 'end_date': end,
                  'daily': ','.join(UNITS), 'timezone': 'UTC', 'temperature_unit': 'celsius', 'precipitation_unit': 'mm'}
        if self.model:
            params['models'] = self.model
        payload, cached, error = self.get_json(self.url, params,
            validator=lambda p: isinstance(p.get('daily'), dict) and isinstance(p.get('daily_units'), dict))
        daily = payload.get('daily', {}) if payload else {}
        units = payload.get('daily_units', {}) if payload else {}
        if not isinstance(daily, dict):
            daily = {}
        if not isinstance(units, dict):
            units = {}
        times = daily.get('time', [])
        if not isinstance(times, list):
            times = []
        index = {d: i for i, d in enumerate(times) if isinstance(d, str)}
        dates = [(first + timedelta(days=i)).isoformat() for i in range((last-first).days+1)]
        variables, notes, count = {}, [], 0
        for name, target in UNITS.items():
            raw_unit = units.get(name)
            values = daily.get(name, [])
            if not isinstance(values, list):
                values = []
            series = []
            for day in dates:
                i = index.get(day)
                value = values[i] if i is not None and i < len(values) else None
                valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                if valid and raw_unit in {'°F', 'F'} and target == '°C':
                    value = (value-32)*5/9
                elif valid and raw_unit == 'inch' and target == 'mm':
                    value *= 25.4
                elif raw_unit != target:
                    valid = False
                if valid and ((target == 'mm' and value < 0) or (target == '°C' and not -100 <= value <= 70)):
                    valid = False
                value = float(value) if valid else None
                count += valid
                series.append(Measurement(value, target, self.source, self.version, period=day,
                    quality=DataQuality('estimated' if valid else 'missing', uncertain=True)))
            variables[name] = series
            if any(v.missing for v in series):
                notes.append(f'{name}: dias ausentes ou inválidos; unidade recebida={raw_unit}')
        total = len(dates)*len(UNITS)
        status = 'complete' if count == total else 'partial' if count else 'unavailable'
        if error and payload is not None:
            status = 'partial'
        quality = DataQuality(status, uncertain=True, note='; '.join(filter(None, (error, *notes))) or None)
        metadata = {'url': self.url, 'cached': cached, 'cache_expired': bool(error and cached),
                    'model': self.model, 'coverage_fraction': count/total,
                    'requested_period': [start, end], 'source_latitude': payload.get('latitude') if payload else None,
                    'source_longitude': payload.get('longitude') if payload else None}
        if self.model:
            metadata['scenario'] = 'HighResMIP, altas emissões; não configurável por SSP nesta API'
        return ClimateDataset(c.latitude, c.longitude, variables, self.source, self.version, quality, metadata)


class ProjectionClimateConnector(HistoricalClimateConnector):
    source = 'open-meteo-climate'
    version = 'climate-api-v1/parser-3'
    url = 'https://climate-api.open-meteo.com/v1/climate'
    model = 'MRI_AGCM3_2_S'

    def fetch(self, latitude, longitude, start='2021-01-01', end='2050-12-31'):
        return super().fetch(latitude, longitude, start, end)
