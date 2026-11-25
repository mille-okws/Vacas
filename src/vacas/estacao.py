"""Estação das águas: chuva acumulada da estação em curso e histórico do início das águas.

As duas séries vêm da mesma fonte (Open-Meteo, reanálise ERA5), para que "faltam X mm" e o histórico
sejam comparáveis. A NASA POWER não entra aqui: no mesmo ponto ela dá totais bem diferentes da ERA5.
"""
from __future__ import annotations

from datetime import date, timedelta
from types import SimpleNamespace

from .connectors.climate import HistoricalClimateConnector
from .pecuaria import find_onset, resolve_parameters

ANOS_HISTORICO = range(1991, 2020)  # o ano de 2019 usa chuva até janeiro de 2020


def _quantil(valores: list[float], fracao: float) -> float:
    ordenados = sorted(valores)
    pos = (len(ordenados) - 1) * fracao
    i = int(pos)
    return ordenados[i] + (ordenados[min(i + 1, len(ordenados) - 1)] - ordenados[i]) * (pos - i)


def _como_serie(chuva: dict) -> dict:
    return {'precipitation_sum': {dia: SimpleNamespace(value=mm) for dia, mm in chuva.items()}}


def ddmm(deslocamento_dias: float, mes_base: int = 9) -> str:
    return (date(2001, mes_base, 1) + timedelta(days=round(deslocamento_dias))).strftime('%d/%m')


def historico_aguas(chuva: dict, parametros: dict, anos=ANOS_HISTORICO) -> dict:
    """Quando a monta começaria em cada ano pela regra de chuva acumulada (dias desde 1º de setembro)."""
    serie = _como_serie(chuva)
    mes = parametros['onset_search_month']
    deslocamentos = []
    for ano in anos:
        inicio, estado = find_onset(ano, serie, parametros)
        if estado == 'found':
            deslocamentos.append((inicio - date(ano, mes, 1)).days)
    if not deslocamentos:
        return {'anos_avaliados': 0, 'p10': None, 'p50': None, 'p90': None}
    r = {'anos_avaliados': len(deslocamentos)}
    for nome, f in (('p10', .1), ('p50', .5), ('p90', .9)):
        d = _quantil(deslocamentos, f)
        r[nome] = {'deslocamento_dias': d, 'data': ddmm(d, mes)}
    return r


def estacao_atual(chuva: dict, hoje: date, parametros: dict) -> dict:
    """Chuva acumulada desde 1º de setembro e dia em que cruzou o limite (a monta começa no dia seguinte)."""
    mes, limite = parametros['onset_search_month'], parametros['onset_rain_mm']
    ano = hoje.year if hoje.month >= mes else hoje.year - 1
    desde = date(ano, mes, 1)
    total, ultimo, cruzou, serie = 0.0, None, None, []
    dia = desde
    # só chuva já ocorrida e sem buracos: a primeira data sem dado encerra o acumulado
    while dia < hoje and dia in chuva and dia <= desde + timedelta(days=parametros['onset_search_days'] - 1):
        total += chuva[dia]
        ultimo = dia
        if cruzou is None and total >= limite:
            cruzou = dia
        serie.append([dia.isoformat(), round(total, 1)])
        dia += timedelta(days=1)
    return {'ano': ano, 'desde': desde.isoformat(), 'encerrada': hoje.month < mes,
            'observado_ate': ultimo.isoformat() if ultimo else None, 'acumulado_mm': round(total, 1),
            'limite_mm': limite, 'faixa_embrapa_mm': [80, 100], 'faltam_mm': round(max(0.0, limite - total), 1),
            'cruzou_em': cruzou.isoformat() if cruzou else None,
            'inicio_monta': (cruzou + timedelta(days=1)).isoformat() if cruzou else None, 'serie': serie}


class FonteChuva:
    """Busca a chuva diária na Open-Meteo (ERA5). Fica separada das regras para os testes poderem trocá-la."""

    nome = 'Open-Meteo (ERA5)'

    def __init__(self, settings):
        self.conector = HistoricalClimateConnector(settings.cache_dir, settings.timeout, settings.cache_ttl)

    def _buscar(self, lat: float, lon: float, inicio: date, fim: date) -> tuple[dict, str | None]:
        dados = self.conector.fetch(lat, lon, inicio.isoformat(), fim.isoformat())
        chuva = {date.fromisoformat(m.period): m.value for m in dados.variables['precipitation_sum'] if not m.missing}
        if not chuva:
            raise RuntimeError(f'sem dado de chuva da {self.nome} para este ponto: {dados.quality.note or "fonte indisponível"}')
        return chuva, dados.quality.note

    def historica(self, lat, lon):
        return self._buscar(lat, lon, date(1991, 1, 1), date(2020, 12, 31))

    def atual(self, lat, lon, hoje: date):
        mes = resolve_parameters('nelore')['onset_search_month']
        ano = hoje.year if hoje.month >= mes else hoje.year - 1
        return self._buscar(lat, lon, date(ano, mes, 1), hoje - timedelta(days=1))


def estacao(fonte, lat: float, lon: float, hoje: date | None = None, raca: str = 'nelore') -> dict:
    hoje = hoje or date.today()
    p = resolve_parameters(raca)
    avisos = []
    historica, nota_h = fonte.historica(lat, lon)
    atual_chuva, nota_a = fonte.atual(lat, lon, hoje)
    avisos += [n for n in (nota_h, nota_a) if n]
    hist = historico_aguas(historica, p)
    atual = estacao_atual(atual_chuva, hoje, p)
    if hist['p50']:
        atual['inicio_esperado'] = (date(atual['ano'], p['onset_search_month'], 1)
                                    + timedelta(days=round(hist['p50']['deslocamento_dias']))).isoformat()
    return {'historico': hist, 'atual': atual, 'hoje': hoje.isoformat(),
            'fonte': {'nome': fonte.nome, 'historico': '1991–2020', 'avisos': avisos}}
