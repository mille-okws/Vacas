"""Servidor local da V2: entrega a interface (pasta web/) e duas rotas JSON.

    GET  /api/estacao?lat=&lon=   chuva da estação em curso e histórico do início das águas
    POST /api/plano               calendário do ano reprodutivo (e diagnóstico, se informado) + texto .ics

Escuta só em 127.0.0.1 e aceita apenas pedidos com Host local (contra DNS rebinding).
"""
from __future__ import annotations

import json
import mimetypes
import sys
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import ciclo, estacao
from .config import load_settings
from .coordinates import validate_coordinate

WEB = Path(__file__).parent / 'web'
MAX_CORPO = 64 * 1024
LIMITE_LEITURA = 1_000_000  # corpos maiores que isso nem são lidos; a resposta de erro segue igual
TIPOS = {'.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
         '.html': 'text/html; charset=utf-8', '.svg': 'image/svg+xml', '.json': 'application/json; charset=utf-8',
         '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.png': 'image/png', '.ico': 'image/x-icon'}


class Aplicacao:
    def __init__(self, fonte, hoje=date.today):
        self.fonte, self.hoje = fonte, hoje

    def estacao(self, lat: float, lon: float) -> dict:
        c = validate_coordinate(lat, lon)
        return estacao.estacao(self.fonte, c.latitude, c.longitude, self.hoje())

    def plano(self, entrada: dict) -> dict:
        return ciclo.calcular(entrada)


def _numero(consulta: dict, nome: str) -> float:
    try:
        return float(consulta[nome][0])
    except (KeyError, IndexError, ValueError):
        raise ValueError(f'informe {nome} como número') from None


def criar_servidor(app: Aplicacao, host: str = '127.0.0.1', porta: int = 8790, raiz: Path = WEB) -> ThreadingHTTPServer:
    raiz = raiz.resolve()

    class Manipulador(BaseHTTPRequestHandler):
        def log_message(self, *args):  # sem ruído no terminal
            pass

        def _responder(self, status: int, corpo: bytes, tipo: str, extra=None):
            self.send_response(status)
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(corpo)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cache-Control', 'no-store')
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(corpo)

        def _json(self, status: int, dados: dict):
            self._responder(status, json.dumps(dados, ensure_ascii=False).encode('utf-8'), 'application/json; charset=utf-8')

        def _host_local(self) -> bool:
            host_pedido = (self.headers.get('Host') or '').rsplit(':', 1)[0].strip('[]')
            return host_pedido in ('127.0.0.1', 'localhost', '::1')

        def _tratar(self, funcao):
            if not self._host_local():
                return self._json(403, {'erro': 'host não permitido'})
            try:
                return self._json(200, funcao())
            except ValueError as erro:  # entrada inválida do usuário
                return self._json(400, {'erro': str(erro)})
            except RuntimeError as erro:  # fonte de dados indisponível
                return self._json(502, {'erro': str(erro)})
            except Exception as erro:  # nunca derruba o servidor
                print(f'erro interno: {type(erro).__name__}: {erro}', file=sys.stderr)
                return self._json(500, {'erro': 'erro interno; veja o terminal'})

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == '/api/estacao':
                consulta = parse_qs(url.query)
                return self._tratar(lambda: app.estacao(_numero(consulta, 'lat'), _numero(consulta, 'lon')))
            if url.path.startswith('/api/'):
                return self._json(404, {'erro': 'rota não encontrada'})
            if not self._host_local():
                return self._json(403, {'erro': 'host não permitido'})
            alvo = (raiz / ('index.html' if url.path in ('', '/') else url.path.lstrip('/'))).resolve()
            if raiz not in alvo.parents or not alvo.is_file():
                return self._json(404, {'erro': 'arquivo não encontrado'})
            tipo = TIPOS.get(alvo.suffix.lower()) or mimetypes.guess_type(alvo.name)[0] or 'application/octet-stream'
            return self._responder(200, alvo.read_bytes(), tipo)

        def do_POST(self):
            # Lê o corpo antes de qualquer resposta: responder sem ler derruba a conexão do cliente no Windows.
            try:
                tamanho = int(self.headers.get('Content-Length') or 0)
            except ValueError:
                tamanho = -1
            bruto = self.rfile.read(min(tamanho, LIMITE_LEITURA)) if tamanho > 0 else b''
            if urlparse(self.path).path != '/api/plano':
                return self._json(404, {'erro': 'rota não encontrada'})

            def calcular():
                if not 0 < tamanho <= MAX_CORPO:
                    raise ValueError(f'corpo da requisição deve ter entre 1 e {MAX_CORPO} bytes')
                try:
                    entrada = json.loads(bruto.decode('utf-8'))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    raise ValueError('o corpo deve ser um JSON válido') from None
                return app.plano(entrada)
            return self._tratar(calcular)

    return ThreadingHTTPServer((host, porta), Manipulador)


def servir(porta: int = 8790, abrir_navegador: bool = True) -> int:
    from .estacao import FonteChuva
    if not (WEB / 'index.html').is_file():
        print(json.dumps({'erro': f'interface não encontrada em {WEB}; rode "npm run build" na pasta web'}, ensure_ascii=False), file=sys.stderr)
        return 2
    servidor = criar_servidor(Aplicacao(FonteChuva(load_settings())), porta=porta)
    url = f'http://127.0.0.1:{servidor.server_address[1]}/'
    print(f'Vacas V2 em {url}  (Ctrl+C para sair)')
    if abrir_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0
