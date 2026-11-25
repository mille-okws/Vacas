import http.client
import json
import threading
from datetime import date, timedelta

import pytest

from vacas.servidor import Aplicacao, criar_servidor


class FonteFalsa:
    nome = 'fonte de teste'
    falhar = False

    def historica(self, lat, lon):
        if self.falhar:
            raise RuntimeError('fonte indisponível')
        dia, serie = date(1991, 9, 1), {}
        while dia <= date(2020, 1, 31):
            serie[dia] = 10.0
            dia += timedelta(days=1)
        return serie, None

    def atual(self, lat, lon, hoje):
        return {date(2026, 9, 1) + timedelta(days=i): 5.0 for i in range(10)}, None


@pytest.fixture
def servidor(tmp_path):
    (tmp_path / 'index.html').write_text('<h1>vacas</h1>', encoding='utf-8')
    (tmp_path / 'app.js').write_text('console.log(1)', encoding='utf-8')
    (tmp_path.parent / 'segredo.txt').write_text('não pode sair', encoding='utf-8')
    fonte = FonteFalsa()
    srv = criar_servidor(Aplicacao(fonte, hoje=lambda: date(2026, 9, 20)), porta=0, raiz=tmp_path)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1], fonte
    srv.shutdown()
    srv.server_close()


def _pedir(porta, metodo, caminho, corpo=None, host=None, cabecalhos=None):
    conexao = http.client.HTTPConnection('127.0.0.1', porta, timeout=10)
    cab = {'Host': host or f'127.0.0.1:{porta}', **(cabecalhos or {})}
    dados = None
    if corpo is not None:
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
        cab['Content-Type'] = 'application/json'
    conexao.request(metodo, caminho, body=dados, headers=cab)
    resposta = conexao.getresponse()
    texto = resposta.read().decode('utf-8')
    conexao.close()
    return resposta.status, texto


PLANO = {'inicio': '2026-10-07', 'raca': 'nelore', 'rebanho': {'vacas': 100, 'primiparas': 10, 'novilhas': 5}, 'nome': 'Fazenda X'}


def test_interface_compilada_acompanha_o_projeto():
    from vacas.servidor import WEB
    html = (WEB / 'index.html').read_text(encoding='utf-8')
    assert 'id="root"' in html and 'assets/' in html
    assert list((WEB / 'assets').glob('*.js')) and list((WEB / 'assets').glob('*.css'))


def test_entrega_a_interface_e_nao_sai_da_pasta(servidor):
    porta, _ = servidor
    assert _pedir(porta, 'GET', '/') == (200, '<h1>vacas</h1>')
    status, _ = _pedir(porta, 'GET', '/app.js')
    assert status == 200
    assert _pedir(porta, 'GET', '/../segredo.txt')[0] == 404
    assert _pedir(porta, 'GET', '/%2e%2e/segredo.txt')[0] == 404
    assert _pedir(porta, 'GET', '/nao-existe.js')[0] == 404


def test_estacao_devolve_historico_e_estacao_atual(servidor):
    porta, _ = servidor
    status, texto = _pedir(porta, 'GET', '/api/estacao?lat=-16.5&lon=-49.5')
    corpo = json.loads(texto)
    assert status == 200
    assert corpo['atual']['acumulado_mm'] == 50.0 and corpo['atual']['faltam_mm'] == 40.0
    assert corpo['historico']['p50']['data'] == '10/09' and corpo['fonte']['nome'] == 'fonte de teste'


@pytest.mark.parametrize('consulta', ['', '?lat=-16.5', '?lat=abc&lon=1', '?lat=95&lon=0', '?lat=0&lon=200', '?lat=nan&lon=0'])
def test_estacao_valida_coordenadas(servidor, consulta):
    porta, _ = servidor
    status, texto = _pedir(porta, 'GET', '/api/estacao' + consulta)
    assert status == 400 and 'erro' in json.loads(texto)


def test_fonte_indisponivel_vira_502_com_mensagem(servidor):
    porta, fonte = servidor
    fonte.falhar = True
    status, texto = _pedir(porta, 'GET', '/api/estacao?lat=-16.5&lon=-49.5')
    assert status == 502 and 'indisponível' in json.loads(texto)['erro']


def test_plano_devolve_calendario_e_ics(servidor):
    porta, _ = servidor
    status, texto = _pedir(porta, 'POST', '/api/plano', PLANO)
    corpo = json.loads(texto)
    assert status == 200
    assert corpo['plano']['touros']['maximo'] == 5 and corpo['diagnostico'] is None
    assert corpo['ics'].startswith('BEGIN:VCALENDAR\r\n')


def test_plano_com_diagnostico(servidor):
    porta, _ = servidor
    status, texto = _pedir(porta, 'POST', '/api/plano', {**PLANO, 'vazias': {'vacas': 20}})
    assert status == 200 and json.loads(texto)['diagnostico']['prenhes'] == 95


@pytest.mark.parametrize('corpo', [b'isto nao e json', b'[]', b'', json.dumps({**PLANO, 'rebanho': {'vacas': -3}}).encode(),
                                   json.dumps({**PLANO, 'inicio': 'ontem'}).encode(),
                                   json.dumps({**PLANO, 'vazias': {'vacas': 999}}).encode()])
def test_plano_rejeita_entrada_invalida_com_400(servidor, corpo):
    porta, _ = servidor
    status, texto = _pedir(porta, 'POST', '/api/plano', corpo)
    assert status == 400 and 'erro' in json.loads(texto)


def test_plano_rejeita_corpo_maior_que_64_kb(servidor):
    porta, _ = servidor
    status, texto = _pedir(porta, 'POST', '/api/plano', b'x' * 70_000)
    assert status == 400 and 'erro' in json.loads(texto)


def test_rotas_desconhecidas_dao_404(servidor):
    porta, _ = servidor
    assert _pedir(porta, 'GET', '/api/outra')[0] == 404
    assert _pedir(porta, 'POST', '/api/outra', {})[0] == 404


def test_recusa_host_que_nao_e_local(servidor):
    porta, _ = servidor
    assert _pedir(porta, 'GET', '/api/estacao?lat=-16.5&lon=-49.5', host='malicioso.example')[0] == 403
    assert _pedir(porta, 'POST', '/api/plano', PLANO, host='malicioso.example')[0] == 403
    assert _pedir(porta, 'GET', '/', host='malicioso.example')[0] == 403
    assert _pedir(porta, 'GET', '/', host=f'localhost:{porta}')[0] == 200


def test_respostas_json_nao_vao_para_o_cache_do_navegador(servidor):
    porta, _ = servidor
    conexao = http.client.HTTPConnection('127.0.0.1', porta, timeout=10)
    conexao.request('GET', '/api/estacao?lat=-16.5&lon=-49.5', headers={'Host': f'127.0.0.1:{porta}'})
    resposta = conexao.getresponse()
    assert resposta.getheader('Cache-Control') == 'no-store' and resposta.getheader('X-Content-Type-Options') == 'nosniff'
    resposta.read()
    conexao.close()
