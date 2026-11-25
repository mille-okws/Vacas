from datetime import date, datetime, timedelta, timezone

import pytest

from vacas import ciclo

INICIO = date(2026, 10, 7)
REBANHO = {'vacas': 300, 'primiparas': 60, 'novilhas': 40}


def _lote(plan, id_):
    return next(l for l in plan['lotes'] if l['id'] == id_)


def test_datas_da_estacao_seguem_gestacao_e_duracao():
    lote = _lote(ciclo.plano(INICIO, 'nelore', REBANHO), 'vacas')
    assert lote['monta'] == {'inicio': INICIO, 'fim': INICIO + timedelta(days=89)}
    assert lote['partos']['primeiro'] == INICIO + timedelta(days=292)           # nelore: 292 d (DOC 299)
    assert lote['partos']['ultimo'] == INICIO + timedelta(days=89 + 292)         # fim da monta + gestação
    assert lote['partos']['mediano'] == INICIO + timedelta(days=45 + 292)
    assert lote['desmama'] == lote['partos']['mediano'] + timedelta(days=209)    # 210 dias de amamentação


def test_raca_muda_a_gestacao():
    nelore = ciclo.plano(INICIO, 'nelore', REBANHO)['lotes'][0]['partos']['primeiro']
    taurino = ciclo.plano(INICIO, 'taurino', REBANHO)['lotes'][0]['partos']['primeiro']
    assert (nelore - taurino).days == 12  # 292 contra 280


def test_novilhas_comecam_um_mes_antes_e_por_ate_45_dias():
    nov = _lote(ciclo.plano(INICIO, 'nelore', REBANHO), 'novilhas')
    assert nov['monta']['inicio'] == INICIO - timedelta(days=30)
    assert nov['monta']['fim'] - nov['monta']['inicio'] == timedelta(days=44)


def test_lotes_vazios_nao_aparecem():
    plan = ciclo.plano(INICIO, 'nelore', {'vacas': 100, 'primiparas': 0, 'novilhas': 0})
    assert [l['id'] for l in plan['lotes']] == ['vacas']


def test_diagnostico_e_pre_parto_saem_do_fim_da_monta_e_do_primeiro_parto():
    lote = _lote(ciclo.plano(INICIO, 'nelore', REBANHO), 'vacas')
    assert lote['diagnostico']['ultrassom'] == lote['monta']['fim'] + timedelta(days=30)
    assert lote['diagnostico']['palpacao'] == lote['monta']['fim'] + timedelta(days=45)
    assert lote['pre_parto']['inicio'] == lote['partos']['primeiro'] - timedelta(days=60)
    assert lote['pre_parto']['fim'] == lote['partos']['primeiro'] - timedelta(days=1)


def test_exames_terminam_antes_do_primeiro_lote_a_entrar():
    plan = ciclo.plano(INICIO, 'nelore', REBANHO)
    assert plan['exames']['fim'] == INICIO - timedelta(days=31)  # novilhas entram 30 dias antes
    assert plan['exames']['fim'] - plan['exames']['inicio'] == timedelta(days=59)


@pytest.mark.parametrize('femeas,minimo,maximo', [(400, 14, 16), (300, 10, 12), (25, 1, 1), (31, 2, 2)])
def test_touros_25_a_30_vacas_cada(femeas, minimo, maximo):
    plan = ciclo.plano(INICIO, 'nelore', {'vacas': femeas, 'primiparas': 0, 'novilhas': 0})
    assert (plan['touros']['minimo'], plan['touros']['maximo']) == (minimo, maximo)


def test_exposicao_a_proxima_monta_e_os_ultimos_partos_ficam_curtos():
    lote = _lote(ciclo.plano(INICIO, 'nelore', REBANHO), 'vacas')
    prox_fim = lote['proxima_monta']['fim']
    esperado = (prox_fim - (lote['partos']['ultimo'] + timedelta(days=60))).days + 1
    assert lote['exposicao']['ultimos'] == esperado == 14
    assert lote['exposicao']['primeiros'] > lote['exposicao']['medianos'] > lote['exposicao']['ultimos']
    assert lote['exposicao_curta'] == ['ultimos']  # menos de um ciclo estral (21 dias)


def test_ordem_dos_eventos_e_sem_evento_antes_dos_exames():
    eventos = ciclo.plano(INICIO, 'nelore', REBANHO)['eventos']
    assert eventos[0]['chave'] == 'exames'
    assert [e['inicio'] for e in eventos] == sorted(e['inicio'] for e in eventos)


@pytest.mark.parametrize('entrada', [
    {'inicio': '2026-10-07', 'rebanho': {'vacas': -1}},
    {'inicio': '2026-10-07', 'rebanho': {'vacas': True}},
    {'inicio': '2026-10-07', 'rebanho': {'vacas': 12.5}},
    {'inicio': '2026-10-07', 'rebanho': {'vacas': 10**9}},
    {'inicio': '2026-10-07', 'rebanho': {}},
    {'inicio': '2026-10-07', 'rebanho': 'muitas'},
    {'inicio': '2026-10-07', 'rebanho': {'vacas': 10}, 'raca': 'marciana'},
    {'inicio': '07/10/2026', 'rebanho': {'vacas': 10}},
    {'inicio': '1999-01-01', 'rebanho': {'vacas': 10}},
    {'rebanho': {'vacas': 10}},
    [],
])
def test_entradas_invalidas_viram_valueerror(entrada):
    with pytest.raises(ValueError):
        ciclo.calcular(entrada)


def test_diagnostico_conta_prenhes_descarte_e_teto_de_30_por_cento():
    plan = ciclo.plano(INICIO, 'nelore', REBANHO)
    d = ciclo.diagnostico(plan, {'vacas': 45, 'primiparas': 20, 'novilhas': 5})
    assert d['prenhes'] == 330 and d['bezerros_esperados'] == 330 and d['vazias'] == 70
    assert d['matrizes'] == 360 and d['teto_reposicao'] == 108          # 30% de 360
    assert d['descarte_sugerido'] == 65                                  # novilhas vazias não entram
    assert d['reposicao_acima_do_teto'] is False
    assert d['taxa_prenhez'] == pytest.approx(330 / 400)


def test_diagnostico_avisa_quando_o_descarte_passa_do_teto():
    plan = ciclo.plano(INICIO, 'nelore', {'vacas': 100, 'primiparas': 0, 'novilhas': 0})
    assert ciclo.diagnostico(plan, {'vacas': 31})['reposicao_acima_do_teto'] is True
    assert ciclo.diagnostico(plan, {'vacas': 30})['reposicao_acima_do_teto'] is False


def test_diagnostico_recusa_mais_vazias_que_animais():
    plan = ciclo.plano(INICIO, 'nelore', {'vacas': 10, 'primiparas': 0, 'novilhas': 0})
    with pytest.raises(ValueError):
        ciclo.diagnostico(plan, {'vacas': 11})


def test_sem_diagnostico_nao_ha_previsao_de_bezerros():
    r = ciclo.calcular({'inicio': '2026-10-07', 'rebanho': REBANHO})
    assert r['diagnostico'] is None


# ---------- .ics: o que costuma quebrar a importação no Google e no Outlook ----------

AGORA = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def _ics(nome='Fazenda'):
    return ciclo.para_ics(ciclo.plano(INICIO, 'nelore', REBANHO), nome, AGORA)


def _desdobrar(texto):
    return texto.replace('\r\n ', '')


def test_ics_usa_crlf_em_todas_as_linhas():
    texto = _ics()
    assert texto.endswith('\r\n') and '\n' not in texto.replace('\r\n', '')
    assert texto.startswith('BEGIN:VCALENDAR\r\n') and texto.endswith('END:VCALENDAR\r\n')


def test_ics_tem_uid_e_dtstamp_em_todo_evento_e_uids_unicos():
    texto = _ics()
    n = texto.count('BEGIN:VEVENT')
    assert n == texto.count('END:VEVENT') == texto.count('DTSTAMP:20261120T120000Z') > 5
    uids = [l for l in texto.split('\r\n') if l.startswith('UID:')]
    assert len(uids) == n and len(set(uids)) == n


def test_ics_dtend_de_dia_inteiro_e_exclusivo():
    plan = ciclo.plano(INICIO, 'nelore', {'vacas': 10, 'primiparas': 0, 'novilhas': 0})
    texto = ciclo.para_ics(plan, 'F', AGORA)
    monta = plan['lotes'][0]['monta']
    assert f'DTSTART;VALUE=DATE:{monta["inicio"]:%Y%m%d}' in texto
    assert f'DTEND;VALUE=DATE:{monta["fim"] + timedelta(days=1):%Y%m%d}' in texto
    desmama = plan['lotes'][0]['desmama']  # evento de um dia: termina no dia seguinte
    assert f'DTSTART;VALUE=DATE:{desmama:%Y%m%d}\r\nDTEND;VALUE=DATE:{desmama + timedelta(days=1):%Y%m%d}' in texto


def test_ics_escapa_virgula_ponto_e_virgula_e_barra():
    texto = _desdobrar(_ics('Fazenda São João, Goiás; lote A\\B'))
    assert 'X-WR-CALNAME:Monta: Fazenda São João\\, Goiás\\; lote A\\\\B' in texto


def test_ics_dobra_linhas_em_75_octetos_sem_partir_acentos_e_preserva_o_texto():
    nome = 'Fazenda ' + 'Ação ' * 40
    texto = _ics(nome)
    for linha in texto.split('\r\n'):
        assert len(linha.encode('utf-8')) <= 75
    desdobrado = _desdobrar(texto)
    assert 'Ação ' * 40 in desdobrado
    texto.encode('utf-8').decode('utf-8')  # nenhum caractere partido ao meio


def test_calcular_devolve_plano_com_datas_em_iso_e_ics():
    r = ciclo.calcular({'inicio': '2026-10-07', 'raca': 'nelore', 'rebanho': REBANHO, 'nome': 'Fazenda X'}, AGORA)
    assert r['plano']['inicio'] == '2026-10-07'
    assert r['plano']['lotes'][0]['monta']['inicio'] == '2026-10-07'
    assert r['ics'].startswith('BEGIN:VCALENDAR')
