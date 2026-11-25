import json
import re
from datetime import date, timedelta

import pytest

from vacas.contracts import ClimateDataset, Measurement
from vacas.pecuaria import (BREEDS, build_breeding_calendar, build_plan, find_dry_season, find_onset,
                            render_dashboard, resolve_parameters)


def _dataset(start: date, days: int, rain, tmax: float = 30.0, skip=()):
    """`rain` é um número (mm/dia) ou função data -> mm."""
    fn = rain if callable(rain) else (lambda day: rain)
    rows = {'precipitation_sum': [], 'temperature_2m_max': []}
    for offset in range(days):
        day = start + timedelta(days=offset)
        if day in skip:
            continue
        rows['precipitation_sum'].append(Measurement(fn(day), 'mm', 'test', 'v1', day.isoformat()))
        rows['temperature_2m_max'].append(Measurement(tmax, 'C', 'test', 'v1', day.isoformat()))
    return ClimateDataset(-16.0, -49.0, rows, 'test', 'v1', metadata={})


def _row(result, monta: str):
    return next(row for row in result['rows'] if row['monta_start'] == monta)


def test_estacao_de_monta_espalha_os_partos_pela_gestacao_da_raca():
    start = date(2001, 1, 1)
    result = build_breeding_calendar(None, _dataset(date(2000, 1, 1), 1800, 6.0), start_year=2001, end_year=2001)
    row = _row(result, '2001-01-01')
    g = BREEDS['nelore']['gestation_days']
    assert row['calving_first'] == (start + timedelta(days=g)).isoformat()
    assert row['calving_last'] == (start + timedelta(days=89 + g)).isoformat()  # fim da monta + gestação
    assert row['calving_first'] < row['calving_mid'] < row['calving_last']
    assert row['weaning_date'] == (date.fromisoformat(row['calving_mid']) + timedelta(days=209)).isoformat()


def test_raca_define_a_gestacao():
    assert resolve_parameters('nelore')['gestation_days'] == BREEDS['nelore']['gestation_days'] == 292  # Embrapa DOC 299
    assert resolve_parameters('taurino')['gestation_days'] == 280  # Embrapa DOC 299
    assert resolve_parameters('nelore', {'gestation_days': 290})['gestation_days'] == 290
    with pytest.raises(ValueError):
        resolve_parameters('marciana')


def test_chuva_suficiente_e_favoravel():
    row = _row(build_breeding_calendar(None, _dataset(date(2000, 1, 1), 1800, 6.0), start_year=2001, end_year=2001),
               '2001-01-01')
    assert row['status'] == 'favorable' and row['reasons'] == []


def test_sem_chuva_antes_da_monta_bloqueia_em_mes_fixo():
    # chuva só depois de 2001-02-01: a monta de 1º/fev não teve águas antes
    data = _dataset(date(2000, 1, 1), 1800, lambda d: 6.0 if d >= date(2001, 2, 1) else 0.0)
    result = build_breeding_calendar(None, data, start_year=2001, end_year=2001)
    row = _row(result, '2001-02-01')
    assert row['status'] == 'unfavorable'
    assert 'chuva antes da monta abaixo do início das águas' in row['reasons']


def test_veranico_so_conta_na_estacao_chuvosa():
    # monta em 1º/jan/2001: parto mediano em dez/2001 e amamentação até ~jun/2002
    seca_de_fim_de_janela = {date(2002, 5, 25) + timedelta(days=i) for i in range(30)}  # mai–jun: não é veranico
    veranico_em_fevereiro = {date(2002, 2, 1) + timedelta(days=i) for i in range(20)}
    ok = build_breeding_calendar(None, _dataset(date(2000, 1, 1), 1800, lambda d: 0.0 if d in seca_de_fim_de_janela else 6.0),
                                 start_year=2001, end_year=2001)
    assert _row(ok, '2001-01-01')['status'] == 'favorable'
    ruim = build_breeding_calendar(None, _dataset(date(2000, 1, 1), 1800, lambda d: 0.0 if d in veranico_em_fevereiro else 6.0),
                                   start_year=2001, end_year=2001)
    row = _row(ruim, '2001-01-01')
    assert row['status'] == 'unfavorable' and row['longest_dry_spell_days'] == 20
    assert any('veranico' in reason for reason in row['reasons'])


def test_indice_de_adequacao_e_o_menor_entre_os_criterios():
    # 2,5 mm/dia: amamentação 525 mm (52,5% de 1000) e chuva antes da monta 75 mm (83% de 90)
    data = _dataset(date(2000, 1, 1), 1800, 2.5)
    row = _row(build_breeding_calendar(None, data, start_year=2001, end_year=2001), '2001-01-01')
    assert row['adequacy_percent'] == 52 and row['limiting'] == 'chuva na amamentação'
    ok = _row(build_breeding_calendar(None, _dataset(date(2000, 1, 1), 1800, 6.0), start_year=2001, end_year=2001), '2001-01-01')
    assert ok['adequacy_percent'] == 100 and ok['limiting'] is None
    indeterminado = _row(build_breeding_calendar(None, _dataset(date(2000, 1, 1), 500, 6.0), start_year=2001, end_year=2001), '2001-01-01')
    assert 'adequacy_percent' not in indeterminado  # dado ausente nunca vira nota


def test_adequacao_100_se_e_somente_se_favoravel():
    seasonal = lambda d: 12.0 if d.month in (10, 11, 12, 1, 2, 3) and d.day % 3 else (0.0 if d.month in (6, 7, 8) else 3.0)
    result = build_breeding_calendar(None, _dataset(date(1999, 1, 1), 2600, seasonal), start_year=2000, end_year=2004,
                                     parameters={'max_dry_fraction': .35})
    evaluated = [r for r in result['rows'] if r['status'] != 'indeterminate']
    assert evaluated and {r['status'] == 'favorable' for r in evaluated if r['adequacy_percent'] == 100} == {True}
    assert all(r['adequacy_percent'] < 100 for r in evaluated if r['status'] == 'unfavorable')
    assert all(0 <= r['adequacy_percent'] <= 100 for r in evaluated)


def test_fracao_de_dias_secos_e_so_informativa_por_padrao():
    # chuva só em dias alternados: 50% de dias secos, mas sem veranico e com chuva total suficiente
    data = _dataset(date(2000, 1, 1), 1800, lambda d: 12.0 if d.toordinal() % 2 else 0.0)
    row = _row(build_breeding_calendar(None, data, start_year=2001, end_year=2001), '2001-01-01')
    assert row['dry_fraction'] > .45 and row['status'] == 'favorable'
    strict = build_breeding_calendar(None, data, start_year=2001, end_year=2001, parameters={'max_dry_fraction': .35})
    assert 'fração de dias secos acima do limite' in _row(strict, '2001-01-01')['reasons']


def test_veranico_longo_bloqueia_com_motivo():
    start = date(2001, 1, 1)
    mid = start + timedelta(days=45 + 292 + 50)
    dry = {mid + timedelta(days=i) for i in range(60)}
    data = _dataset(date(2000, 1, 1), 1800, lambda d: 0.0 if d in dry else 6.0)
    row = _row(build_breeding_calendar(None, data, start_year=2001, end_year=2001), '2001-01-01')
    assert row['status'] == 'unfavorable'
    assert any('veranico' in reason for reason in row['reasons'])


def test_dado_ausente_nao_vira_zero_nem_favoravel():
    data = _dataset(date(2000, 1, 1), 500, 6.0)  # termina antes da amamentação
    row = _row(build_breeding_calendar(None, data, start_year=2001, end_year=2001), '2001-01-01')
    assert row['status'] == 'indeterminate' and row['missing']


def test_inicio_das_aguas_e_o_dia_apos_acumular_o_limiar():
    p = resolve_parameters('nelore')  # 90 mm
    rain = lambda d: 10.0 if d >= date(2000, 10, 1) else 0.0  # 10 mm/dia desde 1º/out
    series = {'precipitation_sum': {d.date() if hasattr(d, 'date') else d: m for d, m in
                                    ((date.fromisoformat(i.period), i) for i in
                                     _dataset(date(2000, 9, 1), 200, rain).variables['precipitation_sum'])}}
    start, state = find_onset(2000, series, p)
    assert state == 'found'
    assert start == date(2000, 10, 10)  # 9 dias x 10 mm = 90 mm em 1–9/out → monta no dia seguinte


def test_inicio_das_aguas_com_dia_sem_dado_e_indeterminado():
    p = resolve_parameters('nelore')
    data = _dataset(date(2000, 9, 1), 200, 0.0, skip={date(2000, 9, 5)})
    series = {'precipitation_sum': {date.fromisoformat(i.period): i for i in data.variables['precipitation_sum']}}
    assert find_onset(2000, series, p) == (None, 'indeterminate')


@pytest.mark.parametrize('override', [{'monta_days': 0}, {'gestation_days': -5}, {'suckling_days': 0},
                                      {'onset_rain_mm': -1}, {'monta_days': 90.5}, {'max_dry_fraction': 1.5},
                                      {'veranico_months': ()}, {'veranico_months': (0, 13)}])
def test_parametros_invalidos_viram_valueerror(override):
    with pytest.raises(ValueError):
        resolve_parameters('nelore', override)


def test_plano_nao_sobrepoe_estacoes_e_mede_exposicao_a_proxima_monta():
    data = _dataset(date(1999, 1, 1), 3000, lambda d: 10.0 if 10 <= d.month or d.month <= 4 else 0.0)
    series = {'precipitation_sum': {date.fromisoformat(i.period): i for i in data.variables['precipitation_sum']},
              'temperature_2m_max': {date.fromisoformat(i.period): i for i in data.variables['temperature_2m_max']}}
    p = resolve_parameters('nelore')
    plan = build_plan(series, p, 1.0, range(2000, 2004))
    dated = [r for r in plan if r.get('monta_start')]
    assert len(dated) >= 2
    for a, b in zip(dated, dated[1:]):
        assert date.fromisoformat(a['monta_end']) < date.fromisoformat(b['monta_start'])
    # exposição = fim da monta seguinte − (parto + descanso); quem pare por último sobra com poucos dias
    first = dated[0]
    exposed = first['days_exposed_next_monta']
    assert exposed['first'] > exposed['mid'] > exposed['last'] >= 0
    next_end = date.fromisoformat(dated[1]['monta_end'])
    ready = date.fromisoformat(first['calving_mid']) + timedelta(days=p['postpartum_rest_days'])
    assert exposed['mid'] == max(0, (next_end - ready).days + 1)
    assert 'last' in first['short_exposure_cohorts']


def _series_of(data):
    return {name: {date.fromisoformat(i.period): i for i in data.variables[name]} for name in data.variables}


def _wet_dry_wet(day):  # águas até 30/abr, seca de maio a agosto, águas de volta em 1º/set
    return 0.0 if 5 <= day.month <= 8 else 10.0


def test_seca_comeca_quando_a_chuva_de_30_dias_cai_abaixo_do_limite():
    series = _series_of(_dataset(date(1999, 1, 1), 1200, _wet_dry_wet))
    p = resolve_parameters('nelore')
    # 28 dias secos deixam 2 x 10 = 20 mm nos últimos 30 dias: 28/mai
    assert find_dry_season(2000, series, p) == date(2000, 5, 28)


def test_seca_com_dia_sem_dado_e_indeterminada():
    series = _series_of(_dataset(date(1999, 1, 1), 1200, _wet_dry_wet, skip={date(2000, 3, 20)}))
    assert find_dry_season(2000, series, resolve_parameters('nelore')) is None


def test_plano_traz_duracao_da_seca_e_chuva_ate_a_monta():
    series = _series_of(_dataset(date(1999, 1, 1), 1800, _wet_dry_wet))
    plan = build_plan(series, resolve_parameters('nelore'), 1.0, range(2000, 2001))
    row = plan[0]
    assert row['monta_start'] == '2000-09-10'  # 9 dias x 10 mm = 90 mm desde 1º/set
    assert row['onset_rain_mm'] == 90.0
    assert row['dry_season'] == {'start': '2000-05-28', 'end': '2000-09-10', 'days': 105}


def test_resultado_traz_serie_diaria_de_chuva_para_os_graficos():
    data = _dataset(date(2000, 1, 1), 1800, 6.0, skip={date(2000, 1, 5)})
    result = build_breeding_calendar(None, data, start_year=2001, end_year=2001)
    clim = result['climate']
    assert clim['start'] == '2000-01-01'
    assert clim['rain'][0] == 6.0 and clim['rain'][4] is None  # dia ausente = null, nunca 0


def test_painel_html_autocontido(tmp_path):
    result = build_breeding_calendar(None, _dataset(date(2000, 1, 1), 1800, 6.0), start_year=2001, end_year=2001)
    path = render_dashboard(result, {'latitude': -16.5, 'longitude': -49.5, 'generated': '2026-11-19T00:00:00+00:00',
                                     'source_errors': {}}, tmp_path)
    html = path.read_text(encoding='utf-8')
    payload = re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S).group(1)
    assert json.loads(payload)['meta']['latitude'] == -16.5
    assert '__DATA__' not in html
    assert not re.search(r'(src|href)="https?://', html)  # sem recursos externos


def test_painel_expoe_barra_de_cenario_faixa_p10_p90_e_evolucao_por_decada(tmp_path):
    result = build_breeding_calendar(None, _dataset(date(2000, 1, 1), 1800, 6.0), start_year=2001, end_year=2001)
    html = render_dashboard(result, {'latitude': -16.5, 'longitude': -49.5, 'generated': '2026-11-20T00:00:00+00:00',
                                     'source_errors': {}}, tmp_path).read_text(encoding='utf-8')
    for marcador in ('id="yr"', 'id="chips"', 'role="radiogroup"',  # cenário: ano (deslizador) + mês de início
                     'P10', 'P90',                                  # faixa de percentis no início das águas
                     'drawEvolution', 'drawDelta', '--d6:'):        # chuva por década e mudança por mês
        assert marcador in html, marcador
    assert 'id="year"' not in html and 'id="reset"' not in html  # controles antigos escondidos saíram
    assert 'id="src"' in html and 'mediana ${' in html  # rodapé com fontes e indicadores com comparação
    for titulo in ('t-tl', 't-why', 't-expo', 't-cal', 't-onset', 't-seca', 't-evo'):  # títulos que dizem a conclusão
        assert f'id="{titulo}"' in html, titulo
    assert 'renderTitles' in html
    # veredito é sobre o clima; a exposição à próxima monta é um aviso informativo, não um limite
    assert 'Clima favorável' in html and 'Ponto de atenção' in html and 'não entra no índice' in html
    assert 'todos os limites foram atingidos' not in html
    assert ".lgb{" in html and "className='lgb'" in html and 'EVO' in html  # décadas ligadas e desligadas pela legenda
