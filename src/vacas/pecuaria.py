"""Triagem de janelas de monta para bovinos de cria no Cerrado.

Modelo (todos os limiares são parâmetros, listados no resultado):

* A monta é uma estação (`monta_days`, padrão 90 dias), não um dia.
* Início da monta no plano anual: primeiro dia depois que a chuva acumulada
  desde 1º de setembro atinge `onset_rain_mm` (Embrapa: iniciar a monta logo
  após 80 a 100 mm no começo das águas).
* Parto = monta + gestação da raça; os partos se espalham da primeira à
  última data. A amamentação (`suckling_days`) é avaliada a partir do parto
  mediano da estação.
* Dado ausente nunca vira zero nem "favorável": o status é `indeterminate`.

Triagem climática; não substitui zootecnista nem médico veterinário.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from statistics import median

from .contracts import ClimateDataset, Measurement

REQUIRED_VARIABLES = ('precipitation_sum', 'temperature_2m_max')
HORIZON = date(2050, 12, 31)
PERIODS = ((1991, 2020, 'historico'), (2021, 2030, '2021-2030'),
           (2031, 2040, '2031-2040'), (2041, 2050, '2041-2050'))

BREEDS = {
    'nelore': {'gestation_days': 292, 'range_days': (287.6, 295.0),
               'source': 'Embrapa Documentos 299 (2021): zebuínos ~292 d. Faixa em estudos lidos: 287,6 d '
                         '(Nelore, n=4463, Oeste de SP), 293,6 d (Alencar e Bugner, 1987) e 295,0 d '
                         '(rebanhos do Norte/Nordeste); varia com mês do parto, sexo do bezerro e sistema.'},
    'taurino': {'gestation_days': 280, 'range_days': None,
                'source': 'Embrapa Documentos 299 (2021): vacas europeias ~280 d.'},
}
DEFAULT_PARAMETERS = {
    'raca': 'nelore',
    'monta_days': 90,                 # Embrapa: ~90 dias; 60–90 em monta natural
    'suckling_days': 210,             # parto até desmama (~7 meses)
    'onset_rain_mm': 90.0,            # Embrapa: 80–100 mm acumulados no começo das águas
    'onset_days': 30,                 # premissa: janela de chuva antes de uma monta em mês fixo
    'onset_search_month': 9,          # busca o início das águas a partir de 1º de setembro
    'onset_search_days': 150,         # e por até 150 dias
    'min_rain_mm': 1000.0,            # premissa: chuva mínima acumulada na amamentação
    'max_longest_dry_spell_days': 15, # premissa: veranico máximo; Embrapa Cerrados: 15 d já é raro em jan–fev (2–8%)
    'veranico_months': (11, 12, 1, 2, 3),  # veranico só conta na estação chuvosa (não na cauda da seca)
    'max_dry_fraction': None,         # sem limite validado: a fração de dias secos só é informativa
    'heat_day_c': 35.0,               # dia de calor extremo (informativo)
    'min_years_share': 0.7,           # anos avaliados mínimos para destacar um mês
    'postpartum_rest_days': 60,       # premissa: descanso mínimo parto → próxima monta
    'estrous_cycle_days': 21,         # premissa a confirmar: ciclo estral; exposição menor = sem nova chance
    'dry_season_window_days': 30,     # definição de seca: chuva dos últimos 30 dias...
    'dry_season_rain_mm': 30.0,       # ...abaixo de 30 mm (~1 mm/dia); só para exibição
    'dry_season_search_month': 4,     # procura o começo da seca a partir de 1º de abril
}
_POSITIVE_INTS = ('gestation_days', 'monta_days', 'suckling_days', 'onset_days', 'onset_search_days',
                  'estrous_cycle_days', 'dry_season_window_days')
PARAMETER_NOTE = ('Confirmados em textos da Embrapa: início da monta após 80–100 mm, monta de 90 dias, gestação '
                  'de zebuínos ~292 d, ciclo estral de 21 d. Premissas não calibradas: chuva mínima na '
                  'amamentação, veranico máximo, descanso pós-parto e os 210 dias até a desmama. '
                  'Ver docs/VALIDACAO.md.')


def resolve_parameters(raca: str = 'nelore', overrides: dict | None = None) -> dict:
    if raca not in BREEDS:
        raise ValueError(f'raça desconhecida: {raca}; use {sorted(BREEDS)}')
    breed = BREEDS[raca]
    params = {**DEFAULT_PARAMETERS, 'raca': raca, 'gestation_days': breed['gestation_days'],
              'gestation_source': breed['source']}
    params.update(overrides or {})
    for key in _POSITIVE_INTS:
        if type(params[key]) is not int or params[key] <= 0:
            raise ValueError(f'{key} deve ser um inteiro positivo')
    if type(params['postpartum_rest_days']) is not int or params['postpartum_rest_days'] < 0:
        raise ValueError('postpartum_rest_days deve ser um inteiro >= 0')
    for key in ('onset_rain_mm', 'dry_season_rain_mm'):
        if not isinstance(params[key], (int, float)) or params[key] <= 0:
            raise ValueError(f'{key} deve ser maior que zero')
    if type(params['dry_season_search_month']) is not int or not 1 <= params['dry_season_search_month'] <= 12:
        raise ValueError('dry_season_search_month deve estar entre 1 e 12')
    fraction = params['max_dry_fraction']
    if fraction is not None and (not isinstance(fraction, (int, float)) or not 0 < fraction <= 1):
        raise ValueError('max_dry_fraction deve ser None ou estar entre 0 e 1')
    months = tuple(params['veranico_months'])
    if not months or any(type(m) is not int or not 1 <= m <= 12 for m in months):
        raise ValueError('veranico_months deve listar meses de 1 a 12')
    params['veranico_months'] = months
    return params


def _series(dataset: ClimateDataset, variable: str) -> dict[date, Measurement]:
    result, seen = {}, set()
    for item in dataset.variables.get(variable, ()):
        try:
            day = date.fromisoformat(item.period)
        except (TypeError, ValueError):
            continue
        if day in seen:
            raise ValueError(f'data climática duplicada: {variable} {day}')
        seen.add(day)
        if not item.missing:
            result[day] = item
    return result


def _period_name(year: int) -> str | None:
    return next((name for first, last, name in PERIODS if first <= year <= last), None)


def _max_run(values: list[bool]) -> int:
    best = current = 0
    for value in values:
        current = current + 1 if value else 0
        best = max(best, current)
    return best


def _merged_series(datasets, variable: str) -> dict[date, Measurement]:
    """Une histórico e projeção por data; o histórico vence em caso de sobreposição."""
    merged = {}
    for dataset in datasets:
        if dataset is None:
            continue
        for day, item in _series(dataset, variable).items():
            merged.setdefault(day, item)
    return merged


def _days(first: date, count: int) -> list[date]:
    return [first + timedelta(days=offset) for offset in range(count)]


def evaluate_window(monta_start: date, series: dict, parameters: dict, dry_threshold_mm: float,
                    check_onset: bool = True) -> dict:
    p = parameters
    monta_end = monta_start + timedelta(days=p['monta_days'] - 1)
    gestation = timedelta(days=p['gestation_days'])
    calving_mid = monta_start + timedelta(days=p['monta_days'] // 2) + gestation
    suckling = _days(calving_mid, p['suckling_days'])
    monta_span = _days(monta_start, p['monta_days'])
    onset_span = _days(monta_start - timedelta(days=p['onset_days']), p['onset_days'])
    row = {'monta_start': monta_start.isoformat(), 'monta_end': monta_end.isoformat(),
           'calving_first': (monta_start + gestation).isoformat(),
           'calving_mid': calving_mid.isoformat(), 'calving_last': (monta_end + gestation).isoformat(),
           'weaning_date': suckling[-1].isoformat(), 'year': monta_start.year, 'month': monta_start.month,
           'period': _period_name(monta_start.year), 'status': 'indeterminate', 'reasons': [], 'missing': []}
    if suckling[-1] > HORIZON:
        row['missing'].append('clima após 2050')
    needs = {'precipitation_sum': monta_span + suckling + (onset_span if check_onset else []),
             'temperature_2m_max': suckling}
    for variable, days in needs.items():
        gaps = sum(day not in series[variable] for day in days)
        if gaps:
            row['missing'].append(f'{variable}: {gaps} dias')
    if row['missing']:
        return row

    rain = [series['precipitation_sum'][day].value for day in suckling]
    maxima = [series['temperature_2m_max'][day].value for day in suckling]
    total = sum(rain)
    dry = [value < dry_threshold_mm for value in rain]
    # veranico = sequência seca dentro da estação chuvosa; a seca do início/fim da janela não é veranico
    longest = _max_run([flag and day.month in p['veranico_months'] for flag, day in zip(dry, suckling)])
    dry_fraction = sum(dry) / len(dry)
    onset_rain = sum(series['precipitation_sum'][day].value for day in onset_span) if check_onset else None
    reasons = []
    if check_onset and onset_rain < p['onset_rain_mm']:
        reasons.append('chuva antes da monta abaixo do início das águas')
    if total < p['min_rain_mm']:
        reasons.append('chuva da amamentação abaixo do mínimo')
    if longest > p['max_longest_dry_spell_days']:
        reasons.append('veranico longo na estação chuvosa')
    if p['max_dry_fraction'] is not None and dry_fraction > p['max_dry_fraction']:
        reasons.append('fração de dias secos acima do limite')
    # Índice de adequação: o menor entre os critérios de "fração do limite atingida" (não é probabilidade).
    # 100 só quando todos os critérios passam; abaixo disso arredonda para baixo.
    ratios = {}
    if check_onset:
        ratios['chuva antes da monta'] = min(1.0, onset_rain / p['onset_rain_mm'])
    ratios['chuva na amamentação'] = min(1.0, total / p['min_rain_mm']) if p['min_rain_mm'] > 0 else 1.0
    limit = p['max_longest_dry_spell_days']
    ratios['veranico'] = 1.0 if longest <= limit else limit / longest
    if p['max_dry_fraction'] is not None:
        ratios['dias secos'] = 1.0 if dry_fraction <= p['max_dry_fraction'] else p['max_dry_fraction'] / dry_fraction
    weakest = min(ratios, key=ratios.get)
    row['adequacy_percent'] = 100 if ratios[weakest] >= 1.0 else int(100 * ratios[weakest])
    row['limiting'] = None if ratios[weakest] >= 1.0 else weakest
    row.update({'status': 'unfavorable' if reasons else 'favorable', 'reasons': reasons,
                'onset_rain_mm': None if onset_rain is None else round(onset_rain, 1),
                'monta_rain_mm': round(sum(series['precipitation_sum'][day].value for day in monta_span), 1),
                'rainfall_mm': round(total, 1), 'dry_days': sum(dry), 'longest_dry_spell_days': longest,
                'dry_fraction': round(dry_fraction, 3),
                'hot_days': sum(value >= p['heat_day_c'] for value in maxima)})
    return row


def find_onset(year: int, series: dict, parameters: dict) -> tuple[date | None, str]:
    """Primeiro dia após a chuva acumulada desde a data de busca atingir `onset_rain_mm`."""
    first = date(year, parameters['onset_search_month'], 1)
    total = 0.0
    for day in _days(first, parameters['onset_search_days']):
        item = series['precipitation_sum'].get(day)
        if item is None:
            return None, 'indeterminate'
        total += item.value
        if total >= parameters['onset_rain_mm']:
            return day + timedelta(days=1), 'found'
    return None, 'not_reached'


def find_dry_season(year: int, series: dict, parameters: dict) -> date | None:
    """Primeiro dia (a partir de `dry_season_search_month`) em que a chuva dos últimos N dias fica
    abaixo do limite. Dia sem dado na janela → None (indeterminado), não seca."""
    rain = series['precipitation_sum']
    window, limit = parameters['dry_season_window_days'], parameters['dry_season_rain_mm']
    for day in _days(date(year, parameters['dry_season_search_month'], 1), 183):
        span = _days(day - timedelta(days=window - 1), window)
        if any(d not in rain for d in span):
            return None
        if sum(rain[d].value for d in span) < limit:
            return day
    return None


def build_plan(series: dict, parameters: dict, dry_threshold_mm: float, years: range) -> list[dict]:
    """Uma estação de monta por ano pecuário, iniciada pelas águas; sem sobreposição entre anos."""
    plan = []
    for year in years:
        start, state = find_onset(year, series, parameters)
        if start is None:
            status = 'indeterminate' if state == 'indeterminate' else 'unfavorable'
            reason = ('dia sem dado de chuva antes de atingir o início das águas' if state == 'indeterminate'
                      else f"chuva acumulada não atingiu {parameters['onset_rain_mm']:g} mm em "
                           f"{parameters['onset_search_days']} dias")
            plan.append({'year': year, 'onset_state': state, 'status': status, 'reasons': [reason],
                         'missing': [reason] if status == 'indeterminate' else [], 'dry_season': None})
            continue
        window = evaluate_window(start, series, parameters, dry_threshold_mm, check_onset=False)
        first = date(year, parameters['onset_search_month'], 1)
        cumulative = sum(series['precipitation_sum'][d].value for d in _days(first, (start - first).days))
        dry_start = find_dry_season(year, series, parameters)
        dry = ({'start': dry_start.isoformat(), 'end': start.isoformat(), 'days': (start - dry_start).days}
               if dry_start and dry_start < start else None)
        plan.append({**window, 'year': year, 'onset_state': state, 'trigger': 'chuva acumulada',
                     'onset_rain_mm': round(cumulative, 1), 'dry_season': dry})
    dated = [row for row in plan if row.get('monta_start')]
    for current, following in zip(dated, dated[1:]):
        if following['year'] != current['year'] + 1:
            continue
        # dias em que a vaca, já recuperada do parto, ainda pega a estação seguinte
        next_end = date.fromisoformat(following['monta_end'])
        rest = timedelta(days=parameters['postpartum_rest_days'])
        exposed = {name: max(0, (next_end - (date.fromisoformat(current[f'calving_{name}']) + rest)).days + 1)
                   for name in ('first', 'mid', 'last')}
        current['days_exposed_next_monta'] = exposed
        current['short_exposure_cohorts'] = [name for name, days in exposed.items()
                                             if days < parameters['estrous_cycle_days']]
    return plan


def build_breeding_calendar(historical, future, *, start_year: int = 1991, end_year: int = 2050,
                            dry_threshold_mm: float = 1.0, raca: str = 'nelore',
                            parameters: dict | None = None) -> dict:
    if not 1900 <= start_year <= end_year <= 2050:
        raise ValueError('anos devem estar entre 1900 e 2050')
    p = resolve_parameters(raca, parameters)
    series = {name: _merged_series((historical, future), name) for name in REQUIRED_VARIABLES}
    if not series['precipitation_sum']:
        raise ValueError('sem série diária de precipitação para a triagem')
    rows = [evaluate_window(date(year, month, 1), series, p, dry_threshold_mm)
            for year in range(start_year, end_year + 1) for month in range(1, 13)]
    plan = build_plan(series, p, dry_threshold_mm, range(start_year, end_year))

    summaries, best = [], []
    for _, _, period in PERIODS:
        for month in range(1, 13):
            candidates = [row for row in rows if row['period'] == period and row['month'] == month]
            if not candidates:
                continue
            evaluated = [row for row in candidates if row['status'] in ('favorable', 'unfavorable')]
            favorable = [row for row in evaluated if row['status'] == 'favorable']
            share = len(favorable) / len(evaluated) if evaluated else None
            summaries.append({'period': period, 'month': month, 'years_expected': len(candidates),
                              'years_evaluated': len(evaluated),
                              'favorable_share': round(share, 3) if share is not None else None,
                              'status': 'estimated' if evaluated else 'indeterminate',
                              'median_rainfall_mm': round(median(r['rainfall_mm'] for r in evaluated), 1) if evaluated else None,
                              'median_longest_dry_spell_days': median(r['longest_dry_spell_days'] for r in evaluated) if evaluated else None})
    for _, _, period in PERIODS:
        choices = [s for s in summaries if s['period'] == period and s['favorable_share'] is not None
                   and s['years_evaluated'] / s['years_expected'] >= p['min_years_share']]
        if not choices:
            continue
        top = max(s['favorable_share'] for s in choices)
        if top < p['min_years_share']:
            continue
        best.append({'period': period, 'months': [s['month'] for s in choices if s['favorable_share'] == top],
                     'favorable_share': top})

    rain = series['precipitation_sum']
    first_day, last_day = min(rain), max(rain)
    climate = {'start': first_day.isoformat(),  # chuva diária (mm) para os gráficos; null = sem dado
               'rain': [round(rain[d].value, 1) if d in rain else None
                        for d in _days(first_day, (last_day - first_day).days + 1)]}
    return {'method': 'breeding-season-screen-v3', 'parameters': p, 'parameter_note': PARAMETER_NOTE,
            'climate': climate,
            'dry_day_definition': f'precipitação diária < {dry_threshold_mm:g} mm',
            'monta_meaning': ('estação de monta de monta_days dias; parto = monta + gestação da raça; '
                              'amamentação avaliada a partir do parto mediano; grade = início no dia 1 de cada mês; '
                              'plano = início quando a chuva acumulada desde 1º de setembro atinge o limiar'),
            'eligibility': 'indeterminate', 'evidence_level': 'experimental',
            'unknowns': ['pasto_disponivel_kg_ms_ha', 'lotacao', 'escore_corporal', 'manejo_desmama'],
            'sources': {'historical': historical.source if historical else None,
                        'future': future.source if future else None},
            'rows': rows, 'plan': plan, 'summary': summaries, 'best_months': best}


def render_dashboard(result: dict, meta: dict, folder: Path) -> Path:
    """Painel HTML autocontido (sem rede) a partir do resultado e dos metadados do local."""
    template = (Path(__file__).parent / 'resources' / 'dashboard.html').read_text(encoding='utf-8')
    payload = json.dumps({**result, 'meta': meta}, ensure_ascii=False).replace('<', '\\u003c')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'painel_vacas.html'
    path.write_text(template.replace('__DATA__', payload), encoding='utf-8')
    return path


def write_breeding(result: dict, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'breeding_windows.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return path
