"""Regras do ciclo reprodutivo: lotes, datas, touros, diagnóstico, exposição e calendário (.ics).

Todas as regras ficam aqui. A interface só mostra o que `calcular` devolve, sem refazer conta de data.
Fontes: Embrapa Gado de Corte, Comunicado Técnico 134 (CT 134) e Documentos 299 (DOC 299); a gestação
e a duração da monta vêm de `pecuaria.resolve_parameters`. Itens marcados "premissa" não vêm de estudo.
"""
from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone

from .pecuaria import BREEDS, resolve_parameters

MAX_ANIMAIS = 100_000
EXAME_ANTES_DIAS = 60           # premissa: DOC 299 limita em 60 dias o laudo de touro comprado
NOVILHA_ANTECIPA_DIAS = 30      # CT 134: novilhas começam um mês antes das vacas
NOVILHA_MONTA_DIAS = 45         # DOC 299: estação das novilhas de até 45 dias
VACAS_POR_TOURO = (25, 30)      # DOC 299
DG_ULTRASSOM_DIAS = 30          # CT 134: diagnóstico 30 dias após o fim da monta (ultrassom)...
DG_PALPACAO_DIAS = 45           # ...ou 45 dias (palpação retal)
PRE_PARTO_DIAS = 60             # DOC 299: os dois últimos meses da gestação são críticos
TETO_REPOSICAO = 0.30           # CT 134: reposição de matrizes de no máximo 30%
CATEGORIAS = (('vacas', 'Vacas adultas'), ('primiparas', 'Primíparas'), ('novilhas', 'Novilhas'))


def _contagem(valor, nome: str) -> int:
    if type(valor) is not int or not 0 <= valor <= MAX_ANIMAIS:
        raise ValueError(f'{nome} deve ser um número inteiro entre 0 e {MAX_ANIMAIS}')
    return valor


def _data(texto, nome: str) -> date:
    try:
        dia = date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ValueError(f'{nome} deve ser uma data no formato AAAA-MM-DD') from None
    if not date(2000, 1, 1) <= dia <= date(2100, 12, 31):
        raise ValueError(f'{nome} fora do intervalo 2000–2100')
    return dia


def validar_rebanho(rebanho) -> dict:
    if not isinstance(rebanho, dict):
        raise ValueError('rebanho deve ser um objeto com vacas, primiparas e novilhas')
    limpo = {chave: _contagem(rebanho.get(chave, 0), chave) for chave, _ in CATEGORIAS}
    if sum(limpo.values()) == 0:
        raise ValueError('informe ao menos um animal no rebanho')
    return limpo


def lotes_do_rebanho(rebanho: dict, parametros: dict) -> list[dict]:
    """Um lote por categoria com animais. Novilhas: um mês antes e por no máximo 45 dias (regra Embrapa)."""
    lotes = []
    for chave, nome in CATEGORIAS:
        if rebanho[chave] == 0:
            continue
        nov = chave == 'novilhas'
        lotes.append({'id': chave, 'nome': nome, 'animais': rebanho[chave],
                      'offset': -NOVILHA_ANTECIPA_DIAS if nov else 0,
                      'duracao': NOVILHA_MONTA_DIAS if nov else parametros['monta_days']})
    return lotes


def _iso(valor):
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: _iso(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_iso(v) for v in valor]
    return valor


def plano(inicio: date, raca: str, rebanho: dict, parametros: dict | None = None) -> dict:
    """Calendário do ano reprodutivo a partir da data de início da monta das vacas."""
    p = resolve_parameters(raca, parametros)
    rebanho = validar_rebanho(rebanho)
    gestacao = timedelta(days=p['gestation_days'])
    pronta = timedelta(days=p['postpartum_rest_days'])
    lotes, eventos = [], []

    def evento(chave, titulo, ini, fim, lote=None):
        eventos.append({'chave': chave, 'titulo': titulo, 'inicio': ini, 'fim': fim, 'lote': lote})

    for lote in lotes_do_rebanho(rebanho, p):
        ini = inicio + timedelta(days=lote['offset'])
        fim = ini + timedelta(days=lote['duracao'] - 1)
        primeiro, mediano, ultimo = ini + gestacao, ini + timedelta(days=lote['duracao'] // 2) + gestacao, fim + gestacao
        desmama = mediano + timedelta(days=p['suckling_days'] - 1)
        prox_ini = ini + timedelta(days=365)  # premissa: a próxima estação começa no mesmo dia do ano seguinte
        prox_fim = prox_ini + timedelta(days=lote['duracao'] - 1)
        exposicao = {nome: max(0, (prox_fim - (parto + pronta)).days + 1)
                     for nome, parto in (('primeiros', primeiro), ('medianos', mediano), ('ultimos', ultimo))}
        curta = [nome for nome, dias in exposicao.items() if dias < p['estrous_cycle_days']]
        dg_us, dg_pal = fim + timedelta(days=DG_ULTRASSOM_DIAS), fim + timedelta(days=DG_PALPACAO_DIAS)
        antes_da_seca = date(fim.year if fim.month < 5 else fim.year + 1, 5, 1)  # premissa: a seca começa em maio
        pre_ini = primeiro - timedelta(days=PRE_PARTO_DIAS)
        lotes.append({**lote, 'monta': {'inicio': ini, 'fim': fim},
                      'diagnostico': {'ultrassom': dg_us, 'palpacao': dg_pal, 'descartar_antes_de': antes_da_seca},
                      'pre_parto': {'inicio': pre_ini, 'fim': primeiro - timedelta(days=1)},
                      'partos': {'primeiro': primeiro, 'mediano': mediano, 'ultimo': ultimo},
                      'desmama': desmama,
                      'proxima_monta': {'inicio': prox_ini, 'fim': prox_fim},
                      'exposicao': exposicao, 'exposicao_curta': curta})
        nome = lote['nome']
        evento('monta', f'Monta: {nome}', ini, fim, lote['id'])
        evento('diagnostico', f'Diagnóstico de gestação: {nome} (ultrassom a partir de {dg_us:%d/%m}; palpação a partir de {dg_pal:%d/%m})', dg_us, dg_pal, lote['id'])
        evento('pre_parto', f'Pré-parto crítico: {nome}', pre_ini, primeiro - timedelta(days=1), lote['id'])
        evento('partos', f'Partos: {nome}', primeiro, ultimo, lote['id'])
        evento('desmama', f'Desmama (parto mediano + {p["suckling_days"]} dias): {nome}', desmama, desmama, lote['id'])

    primeiro_inicio = min(lote['monta']['inicio'] for lote in lotes)
    exames = {'inicio': primeiro_inicio - timedelta(days=EXAME_ANTES_DIAS), 'fim': primeiro_inicio - timedelta(days=1)}
    evento('exames', 'Exames: ginecológico (vacas) e andrológico (touros)', exames['inicio'], exames['fim'])
    eventos.sort(key=lambda e: (e['inicio'], e['fim'], e['titulo']))
    femeas = sum(lote['animais'] for lote in lotes)
    touros = {'femeas_na_monta': femeas, 'minimo': math.ceil(femeas / VACAS_POR_TOURO[1]),
              'maximo': math.ceil(femeas / VACAS_POR_TOURO[0]), 'vacas_por_touro': list(VACAS_POR_TOURO)}
    return {'inicio': inicio, 'raca': raca, 'gestacao_dias': p['gestation_days'], 'monta_dias': p['monta_days'],
            'desmama_dias': p['suckling_days'], 'ciclo_estral_dias': p['estrous_cycle_days'],
            'descanso_pos_parto_dias': p['postpartum_rest_days'], 'exames': exames, 'touros': touros,
            'lotes': lotes, 'eventos': eventos}


def diagnostico(plan: dict, vazias: dict) -> dict:
    """Resultado do diagnóstico informado pelo usuário: prenhes, descarte e teto de reposição (30%)."""
    if not isinstance(vazias, dict):
        raise ValueError('vazias deve ser um objeto com a contagem por categoria')
    por_lote, prenhes, vazias_total = [], 0, 0
    for lote in plan['lotes']:
        v = _contagem(vazias.get(lote['id'], 0), f'vazias de {lote["nome"]}')
        if v > lote['animais']:
            raise ValueError(f'{lote["nome"]}: vazias ({v}) maior que o número de animais ({lote["animais"]})')
        por_lote.append({'id': lote['id'], 'nome': lote['nome'], 'animais': lote['animais'], 'vazias': v,
                         'prenhes': lote['animais'] - v})
        prenhes += lote['animais'] - v
        vazias_total += v
    matrizes = sum(l['animais'] for l in plan['lotes'] if l['id'] != 'novilhas')
    descarte = sum(l['vazias'] for l in por_lote if l['id'] != 'novilhas')
    teto = math.floor(TETO_REPOSICAO * matrizes)
    total = sum(l['animais'] for l in plan['lotes'])
    return {'lotes': por_lote, 'prenhes': prenhes, 'vazias': vazias_total, 'bezerros_esperados': prenhes,
            'taxa_prenhez': round(prenhes / total, 4) if total else None,
            'matrizes': matrizes, 'descarte_sugerido': descarte, 'teto_reposicao': teto,
            'reposicao_acima_do_teto': descarte > teto}


def _escapar(texto: str) -> str:
    return (texto.replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,')
            .replace('\r\n', '\\n').replace('\n', '\\n'))


def _dobrar(linha: str) -> list[str]:
    """Dobra a linha em até 75 octetos UTF-8 (continuações começam com um espaço), sem partir caracteres."""
    partes, atual, usados, limite = [], '', 0, 75
    for caractere in linha:
        n = len(caractere.encode('utf-8'))
        if usados + n > limite:
            partes.append(atual)
            atual, usados, limite = ' ', 1, 75
        atual += caractere
        usados += n
    partes.append(atual)
    return partes


def para_ics(plan: dict, nome: str = 'Fazenda', agora: datetime | None = None) -> str:
    agora = (agora or datetime.now(timezone.utc)).astimezone(timezone.utc)
    carimbo = agora.strftime('%Y%m%dT%H%M%SZ')
    linhas = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Vacas V2//Planejamento da monta//PT-BR',
              'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', f'X-WR-CALNAME:{_escapar("Monta: " + nome)}']
    for e in plan['eventos']:
        uid = hashlib.sha1(f'{e["chave"]}|{e["lote"]}|{e["inicio"]}|{plan["inicio"]}'.encode()).hexdigest()[:20]
        linhas += ['BEGIN:VEVENT', f'UID:{uid}@vacas-v2', f'DTSTAMP:{carimbo}',
                   f'DTSTART;VALUE=DATE:{e["inicio"]:%Y%m%d}',
                   f'DTEND;VALUE=DATE:{e["fim"] + timedelta(days=1):%Y%m%d}',  # DTEND de dia inteiro é exclusivo
                   f'SUMMARY:{_escapar(e["titulo"])}',
                   f'DESCRIPTION:{_escapar("Plano gerado pelo Vacas V2 a partir do início da monta em " + plan["inicio"].strftime("%d/%m/%Y") + ". Triagem; não substitui zootecnista ou veterinário.")}',
                   'END:VEVENT']
    linhas.append('END:VCALENDAR')
    return ''.join(parte + '\r\n' for linha in linhas for parte in _dobrar(linha))


def calcular(entrada: dict, agora: datetime | None = None) -> dict:
    """Entrada JSON da interface -> plano, diagnóstico (se informado) e texto .ics."""
    if not isinstance(entrada, dict):
        raise ValueError('a entrada deve ser um objeto JSON')
    raca = entrada.get('raca', 'nelore')
    if raca not in BREEDS:
        raise ValueError(f'raça desconhecida: {raca}')
    inicio = _data(entrada.get('inicio'), 'inicio')
    nome = str(entrada.get('nome') or 'Fazenda')[:80]
    plan = plano(inicio, raca, entrada.get('rebanho'))
    diag = diagnostico(plan, entrada['vazias']) if entrada.get('vazias') is not None else None
    return {'plano': _iso(plan), 'diagnostico': diag, 'ics': para_ics(plan, nome, agora)}
