import argparse
import json
import sys
from datetime import datetime, timezone

from .clima import collect_climate, merge_observed_climate
from .config import load_settings
from .coordinates import validate_coordinate
from .pecuaria import BREEDS, build_breeding_calendar, render_dashboard, write_breeding


def coordinate_folder(latitude: float, longitude: float) -> str:
    return f'{latitude:.5f}_{longitude:.5f}'.replace('-', 'm').replace('.', '_')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='vacas', description='Vacas · janelas de monta para bovinos de cria')
    sub = parser.add_subparsers(dest='command', required=True)
    monta = sub.add_parser('monta', help='plano anual de monta, parto e desmama pelas chuvas; gera JSON e painel HTML')
    monta.add_argument('--lat', type=float, required=True)
    monta.add_argument('--lon', type=float, required=True)
    monta.add_argument('--raca', choices=sorted(BREEDS), default='nelore', help='define a gestação (padrão: nelore)')
    monta.add_argument('--gestation-days', type=int, help='substitui a gestação da raça')
    monta.add_argument('--monta-days', type=int, help='duração da estação de monta (padrão: 90)')
    monta.add_argument('--onset-rain-mm', type=float, help='chuva acumulada que inicia a monta (padrão: 90; Embrapa 80–100)')
    monta.add_argument('--start-year', type=int, help='padrão: 1991')
    monta.add_argument('--end-year', type=int, help='padrão: 2050')
    monta.add_argument('--future-until', type=int, help='padrão: 2050')
    monta.add_argument('--dry-threshold', type=float, default=1.0,
                       help='dia seco se chuva diária for menor que este valor em mm')
    app = sub.add_parser('app', help='abre o app da V2 (planejamento do nascimento dos bezerros) no navegador')
    app.add_argument('--port', type=int, default=8790)
    app.add_argument('--no-browser', action='store_true', help='não abre o navegador automaticamente')
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    args = build_parser().parse_args(argv)
    if args.command == 'app':
        from .servidor import servir
        return servir(args.port, not args.no_browser)
    try:
        coordinate = validate_coordinate(args.lat, args.lon)
        settings = load_settings()
        start_year = 1991 if args.start_year is None else args.start_year
        end_year = 2050 if args.end_year is None else args.end_year
        future_until = settings.future_until if args.future_until is None else args.future_until
        if end_year > 2050 or future_until < 2021:
            raise ValueError('use projeção de 2021 até 2050')
        overrides = {key: value for key, value in (('gestation_days', args.gestation_days),
                                                    ('monta_days', args.monta_days),
                                                    ('onset_rain_mm', args.onset_rain_mm)) if value is not None}
        sources = collect_climate(settings, coordinate.latitude, coordinate.longitude,
                                  start_year, end_year, future_until)
        historical = sources['historical']
        future = merge_observed_climate(sources['future'], sources['nasa_power'])
        if historical is None and future is None:
            raise RuntimeError(f"não foi possível coletar clima: {sources['errors']}")
        result = build_breeding_calendar(historical, future, start_year=start_year, end_year=end_year,
                                         dry_threshold_mm=args.dry_threshold, raca=args.raca, parameters=overrides)
        result['source_errors'] = sources['errors']
        folder = settings.output_dir / coordinate_folder(coordinate.latitude, coordinate.longitude)
        meta = {'latitude': coordinate.latitude, 'longitude': coordinate.longitude,
                'generated': datetime.now(timezone.utc).isoformat(), 'source_errors': sources['errors']}
        json_path = write_breeding(result, folder)
        html_path = render_dashboard(result, meta, folder)
        plan = result['plan']
        print(json.dumps({'files': {'json': str(json_path), 'dashboard': str(html_path)},
                          'plan_years': len(plan),
                          'plan_status': {s: sum(row['status'] == s for row in plan)
                                          for s in ('favorable', 'unfavorable', 'indeterminate')},
                          'best_months': result['best_months'], 'source_errors': sources['errors']},
                         ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
