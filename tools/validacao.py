"""Checagens de dados e sensibilidade do plano de monta (reexecutável, usa o cache de clima).

    $env:PYTHONPATH = "src"; python tools/validacao.py -16.5 -49.5

A: Open-Meteo (ERA5) x NASA POWER no início das águas e na seca, 1991-2020.
B: o que bloqueia o plano e onde cai o maior veranico dentro da amamentação.
C: sensibilidade do plano aos parâmetros.
"""
import sys
from datetime import date, timedelta
from statistics import median

from vacas.clima import collect_climate
from vacas.config import load_settings
from vacas.connectors.nasa import NasaPowerConnector
from vacas.pecuaria import (_days, _max_run, _merged_series, _series, build_plan, find_dry_season, find_onset,
                            resolve_parameters)

lat, lon = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (-16.5, -49.5)
settings = load_settings()
src = collect_climate(settings, lat, lon, 1991, 2050, 2050)
series = {k: _merged_series((src['historical'], src['future']), k) for k in ('precipitation_sum', 'temperature_2m_max')}
P = resolve_parameters('nelore')
iso = lambda d: d.strftime('%d/%m')
doy = lambda d, y: (d - date(y, 9, 1)).days  # dias desde 1º de setembro


def pearson(a, b):
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** .5
    return num / den if den else float('nan')


print('== A. Open-Meteo (ERA5) x NASA POWER, 1991-2020')
nasa = NasaPowerConnector(settings.cache_dir, settings.timeout, settings.cache_ttl).fetch(lat, lon, '1991-01-01', '2020-12-31')
ns = {'precipitation_sum': _series(nasa, 'precipitation_sum')}
om_on, na_on, om_dry, na_dry, annual_om, annual_na = [], [], [], [], [], []
for y in range(1991, 2020):
    a, sa = find_onset(y, series, P)
    b, sb = find_onset(y, ns, P)
    if a and b:
        om_on.append(doy(a, y)); na_on.append(doy(b, y))
    da, db = find_dry_season(y, series, P), find_dry_season(y, ns, P)
    if a and b and da and db:
        om_dry.append((a - da).days); na_dry.append((b - db).days)
    days = _days(date(y, 1, 1), 365)
    if all(d in series['precipitation_sum'] and d in ns['precipitation_sum'] for d in days):
        annual_om.append(sum(series['precipitation_sum'][d].value for d in days))
        annual_na.append(sum(ns['precipitation_sum'][d].value for d in days))
n = len(om_on)
diff = [abs(x - y) for x, y in zip(om_on, na_on)]
print(f'anos comparáveis (início das águas): {n}')
print(f'início mediano: ERA5 {iso(date(2001, 9, 1) + timedelta(days=median(om_on)))} | NASA {iso(date(2001, 9, 1) + timedelta(days=median(na_on)))}')
print(f'diferença absoluta mediana {median(diff):.0f} d; média {sum(diff)/n:.1f} d; máx {max(diff)} d; correlação {pearson(om_on, na_on):.2f}')
if om_dry:
    print(f'seca (dias): ERA5 mediana {median(om_dry):.0f} | NASA mediana {median(na_dry):.0f}; correlação {pearson(om_dry, na_dry):.2f}  (n={len(om_dry)})')
if annual_om:
    print(f'chuva anual (mm): ERA5 mediana {median(annual_om):.0f} | NASA mediana {median(annual_na):.0f}  (n={len(annual_om)})')

print('\n== B. O que o modelo bloqueia (plano pelas águas, 1991-2020) e onde cai o veranico')
plan = build_plan(series, P, 1.0, range(1991, 2021))
ev = [r for r in plan if r['status'] in ('favorable', 'unfavorable')]
print(f'avaliados {len(ev)}; favoráveis {sum(r["status"] == "favorable" for r in ev)}')
reasons = {}
for r in ev:
    for x in r['reasons']:
        reasons[x] = reasons.get(x, 0) + 1
for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
    print(f'  {v:>3} anos: {k}')
rain = series['precipitation_sum']
stats = {'toda a janela': [], 'só nov-mar': []}
rain_amam, cum_wet = [], []
for r in ev:
    mid = date.fromisoformat(r['calving_mid'])
    window = _days(mid, P['suckling_days'])
    flags = [rain[d].value < 1.0 for d in window]
    stats['toda a janela'].append(_max_run(flags))
    stats['só nov-mar'].append(_max_run([f and d.month in (11, 12, 1, 2, 3) for f, d in zip(flags, window)]))
    rain_amam.append(r['rainfall_mm'])
for k, v in stats.items():
    print(f'maior veranico ({k}): mediana {median(v):.0f} d; >10 d em {sum(x > 10 for x in v)}/{len(v)}; '
          f'>15 d em {sum(x > 15 for x in v)}/{len(v)}; >30 d em {sum(x > 30 for x in v)}/{len(v)}')
print(f'chuva na amamentação (mm): mediana {median(rain_amam):.0f}; mín {min(rain_amam):.0f}; máx {max(rain_amam):.0f}')

print('\n== C. Sensibilidade (plano 1991-2049; % favorável entre os avaliados; exposição mediana, dias)')
def run(**over):
    p = resolve_parameters('nelore', over)
    pl = build_plan(series, p, 1.0, range(1991, 2050))
    ev = [r for r in pl if r['status'] in ('favorable', 'unfavorable')]
    fav = 100 * sum(r['status'] == 'favorable' for r in ev) / len(ev)
    ex = [r['days_exposed_next_monta'] for r in pl if r.get('days_exposed_next_monta')]
    on = [doy(date.fromisoformat(r['monta_start']), r['year']) for r in pl if r.get('monta_start')]
    return (f'{fav:5.1f}% fav | início mediano {iso(date(2001, 9, 1) + timedelta(days=median(on)))} | '
            f'exposição 1ºs/med/últ {median(e["first"] for e in ex):.0f}/{median(e["mid"] for e in ex):.0f}/{median(e["last"] for e in ex):.0f}')
cases = [('base (nelore 292 d, 90 mm, monta 90 d, rest 60 d)', {}),
         ('gestação 287', {'gestation_days': 287}),
         ('gestação 295', {'gestation_days': 295}), ('gestação 280 (taurino)', {'gestation_days': 280}),
         ('início das águas 80 mm', {'onset_rain_mm': 80.0}), ('início das águas 100 mm', {'onset_rain_mm': 100.0}),
         ('monta 60 d', {'monta_days': 60}), ('descanso pós-parto 30 d', {'postpartum_rest_days': 30}),
         ('descanso pós-parto 90 d', {'postpartum_rest_days': 90}),
         ('chuva mín. amamentação 800', {'min_rain_mm': 800.0}), ('chuva mín. amamentação 1200', {'min_rain_mm': 1200.0}),
         ('veranico máx. 10 d', {'max_longest_dry_spell_days': 10}), ('veranico máx. 30 d', {'max_longest_dry_spell_days': 30}),
         ('dias secos ligado a 25%', {'max_dry_fraction': .25}), ('dias secos ligado a 35%', {'max_dry_fraction': .35}),
         ('dias secos ligado a 45%', {'max_dry_fraction': .45})]
for label, over in cases:
    print(f'{label:<52} {run(**over)}')
