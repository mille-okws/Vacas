from dataclasses import dataclass
from pathlib import Path
import os
import math
import yaml


@dataclass(frozen=True)
class Settings:
    root: Path
    log_level: str = 'INFO'
    timeout: float = 20
    cache_ttl: float = 86400
    reference_years: tuple[int, int] = (1991, 2020)
    future_until: int = 2050

    @property
    def config_dir(self):
        return self.root / 'configs'

    @property
    def cache_dir(self):
        return self.root / 'cache'

    @property
    def output_dir(self):
        return self.root / 'outputs'

    def ensure_directories(self):
        for name in ('cache', 'outputs'):
            (self.root / name).mkdir(parents=True, exist_ok=True)


def load_settings(root=None):
    base = Path(root or os.getenv('VACAS_ROOT') or Path(__file__).resolve().parents[2]).resolve()
    path = base / 'configs' / 'default.yaml'
    try:
        raw = yaml.safe_load(path.read_text(encoding='utf-8')) if path.exists() else {}
    except yaml.YAMLError as exc:
        raise ValueError(f'YAML inválido: {exc}') from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError('configuração deve ser um objeto YAML')
    assessment = raw.get('assessment', {})
    connection = raw.get('connectors', {})
    if not isinstance(assessment, dict) or not isinstance(connection, dict):
        raise ValueError('assessment e connectors devem ser objetos')
    level = os.getenv('SAFRA_V5_LOG_LEVEL', raw.get('log_level', 'INFO'))
    if not isinstance(level, str) or level.upper() not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
        raise ValueError('log_level inválido')
    level = level.upper()
    years = tuple(assessment.get('reference_years', [1991, 2020]))
    until = assessment.get('future_until', 2050)
    if len(years) != 2 or not all(type(y) is int for y in (*years, until)) or not 1900 <= years[0] <= years[1] <= until <= 2050:
        raise ValueError('períodos de configuração inválidos')
    timeout, ttl = float(connection.get('timeout', 20)), float(connection.get('cache_ttl', 86400))
    if not math.isfinite(timeout) or not math.isfinite(ttl) or timeout <= 0 or ttl < 0:
        raise ValueError('timeout/TTL inválidos')
    settings = Settings(base, level, timeout, ttl, years, until)
    settings.ensure_directories()
    return settings
