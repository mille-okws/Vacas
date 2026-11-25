from datetime import date, timedelta

from vacas import estacao
from vacas.pecuaria import resolve_parameters

P = resolve_parameters('nelore')  # 90 mm desde 1º de setembro


def _chuva(inicio: date, fim: date, mm: float = 10.0, sem=()):
    dia, serie = inicio, {}
    while dia <= fim:
        if dia not in sem:
            serie[dia] = mm
        dia += timedelta(days=1)
    return serie


def test_cruza_o_limite_no_dia_em_que_acumula_90_mm_e_a_monta_comeca_no_seguinte():
    chuva = _chuva(date(2026, 9, 1), date(2026, 11, 19))
    r = estacao.estacao_atual(chuva, date(2026, 11, 20), P)
    assert r['cruzou_em'] == '2026-09-09' and r['inicio_monta'] == '2026-09-10'  # 9 dias x 10 mm
    assert r['faltam_mm'] == 0.0 and r['acumulado_mm'] == 800.0  # 80 dias de 1º/set a 19/nov
    assert r['observado_ate'] == '2026-11-19' and r['encerrada'] is False


def test_antes_de_cruzar_mostra_quanto_falta():
    r = estacao.estacao_atual(_chuva(date(2026, 9, 1), date(2026, 9, 4)), date(2026, 9, 5), P)
    assert r['acumulado_mm'] == 40.0 and r['faltam_mm'] == 50.0
    assert r['cruzou_em'] is None and r['inicio_monta'] is None


def test_hoje_nao_entra_no_acumulado_nem_dias_futuros():
    chuva = _chuva(date(2026, 9, 1), date(2026, 9, 30))
    r = estacao.estacao_atual(chuva, date(2026, 9, 3), P)
    assert r['acumulado_mm'] == 20.0 and r['observado_ate'] == '2026-09-02'


def test_dia_sem_dado_encerra_o_acumulado_e_nunca_vira_zero():
    chuva = _chuva(date(2026, 9, 1), date(2026, 9, 20), sem={date(2026, 9, 3)})
    r = estacao.estacao_atual(chuva, date(2026, 9, 21), P)
    assert r['acumulado_mm'] == 20.0 and r['observado_ate'] == '2026-09-02'
    assert r['cruzou_em'] is None  # não afirma início sem a série completa


def test_antes_de_setembro_a_estacao_e_a_do_ano_anterior_e_encerrada():
    chuva = _chuva(date(2026, 9, 1), date(2027, 2, 28))
    r = estacao.estacao_atual(chuva, date(2027, 3, 1), P)
    assert r['ano'] == 2026 and r['encerrada'] is True and r['desde'] == '2026-09-01'


def test_sem_nenhum_dado_nao_quebra():
    r = estacao.estacao_atual({}, date(2026, 11, 20), P)
    assert r['acumulado_mm'] == 0.0 and r['observado_ate'] is None and r['serie'] == []


def test_historico_das_aguas_em_percentis():
    chuva = _chuva(date(1991, 9, 1), date(1994, 1, 31))
    h = estacao.historico_aguas(chuva, P, anos=range(1991, 1994))
    assert h['anos_avaliados'] == 3
    assert h['p10']['data'] == h['p50']['data'] == h['p90']['data'] == '10/09'


def test_historico_ignora_anos_sem_dado_completo():
    chuva = _chuva(date(1991, 9, 1), date(1992, 1, 31))
    h = estacao.historico_aguas(chuva, P, anos=range(1991, 1994))
    assert h['anos_avaliados'] == 1


class FonteFalsa:
    nome = 'fonte de teste'

    def historica(self, lat, lon):
        return _chuva(date(1991, 9, 1), date(2020, 1, 31)), None

    def atual(self, lat, lon, hoje):
        return _chuva(date(2026, 9, 1), hoje - timedelta(days=1), mm=2.0), 'atraso de 1 dia'


def test_estacao_junta_historico_atual_e_inicio_esperado():
    r = estacao.estacao(FonteFalsa(), -16.5, -49.5, hoje=date(2026, 10, 1))
    assert r['atual']['acumulado_mm'] == 60.0 and r['atual']['faltam_mm'] == 30.0
    assert r['historico']['p50']['data'] == '10/09'
    assert r['atual']['inicio_esperado'] == '2026-09-10'
    assert r['fonte']['avisos'] == ['atraso de 1 dia'] and r['hoje'] == '2026-10-01'
