"""Transporte HTTP limitado por timeout, tentativas e resposta de 429."""
import time
import requests


class HttpTransport:
    def __init__(self, timeout: float, attempts: int = 3):
        self.timeout, self.attempts = timeout, attempts

    def get_json(self, url, params):
        for attempt in range(self.attempts):
            try:
                response = requests.get(url, params=params,
                                        timeout=(min(5, self.timeout), self.timeout))
                if response.status_code not in (429, 500, 502, 503, 504) or attempt == self.attempts-1:
                    response.raise_for_status()
                    return response.json()
                wait = min(4, 2 ** attempt)
                if response.status_code == 429:
                    try:
                        wait = min(10, max(wait, float(response.headers.get('Retry-After', wait))))
                    except (ValueError, TypeError):
                        pass
            except (requests.HTTPError, requests.exceptions.JSONDecodeError):
                raise
            except requests.RequestException:
                if attempt == self.attempts-1:
                    raise
                wait = min(4, 2 ** attempt)
            time.sleep(wait)
        raise RuntimeError('tentativas esgotadas')
