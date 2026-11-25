"""Cache versionado, com expiração e gravação atômica."""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path


class CacheStore:
    def __init__(self, directory: Path, ttl: float, schema: int = 1):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.ttl, self.schema = ttl, schema

    def path(self, version, url, params):
        key = hashlib.sha256(json.dumps([version, self.schema, url, params],
                                        sort_keys=True, default=str).encode()).hexdigest()
        return self.directory / f'{key}.json'

    def read(self, path, validator=None):
        try:
            envelope = json.loads(path.read_text(encoding='utf-8'))
            payload = envelope['payload']
            if not isinstance(payload, dict) or (validator is not None and not validator(payload)):
                return None, False
            age = time.time() - envelope['created_at']
            if age < 0:
                return None, False
            # TTL zero representa cache vencido imediatamente; evita tratar a
            # mesma leitura como atual por diferenças de relógio muito pequenas.
            return payload, self.ttl > 0 and age < self.ttl
        except (OSError, ValueError, KeyError, TypeError):
            return None, False

    def write(self, path, payload):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.directory,
                                             prefix='cache-', suffix='.tmp', delete=False) as handle:
                temporary = Path(handle.name)
                json.dump({'created_at': time.time(), 'payload': payload}, handle,
                          ensure_ascii=False, allow_nan=False)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
