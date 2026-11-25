import logging
import math
from pathlib import Path
import requests
from ..cache_store import CacheStore
from ..http_transport import HttpTransport


class ConnectorError(RuntimeError):
    pass


class BaseConnector:
    source = 'unknown'
    version = 'unknown'
    cache_schema = 3

    def __init__(self, cache_dir: Path, timeout: float = 20, ttl: float = 86400):
        if not math.isfinite(timeout) or not math.isfinite(ttl) or timeout <= 0 or ttl < 0:
            raise ValueError('timeout deve ser positivo; TTL não negativo')
        self.cache_dir = Path(cache_dir) / self.source.replace('/', '_')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout, self.ttl = timeout, ttl
        self.cache = CacheStore(self.cache_dir, ttl, self.cache_schema)
        self.http = HttpTransport(timeout)

    def _cache_path(self, url, params):
        return self.cache.path(self.version, url, params)

    def cached_call(self, url, params, loader, allow_cache=True, validator=None):
        path = self._cache_path(url, params)
        stale = None
        if allow_cache:
            stale, current = self.cache.read(path, validator)
            if current:
                return stale, True, None
        try:
            payload = loader()
            if not isinstance(payload, dict) or payload.get('error') or (validator is not None and not validator(payload)):
                raise ConnectorError('resposta inválida ou erro da fonte')
        except (requests.RequestException, ValueError, OSError, ConnectorError) as exc:
            if stale is not None:
                return stale, True, f'cache expirado; fonte indisponível: {exc}'
            return None, False, str(exc)
        try:
            self.cache.write(path, payload)
        except (OSError, ValueError) as exc:
            logging.getLogger('safra_v4').warning('cache não gravado: %s', exc)
        return payload, False, None

    def get_json(self, url, params, allow_cache=True, validator=None):
        return self.cached_call(url, params,
                                lambda: self.http.get_json(url, params), allow_cache, validator)
