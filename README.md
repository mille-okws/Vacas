# Vacas V2: planejar o nascimento dos bezerros

MVP simples, só para entender o fluxo. Parte da V1 (clima e regras de monta) e acrescenta um app de 8 passos:

**Configurar → Preparar → Ver a chuva → Ver o plano → Levar à agenda → Diagnóstico → Partos → Próximo ciclo**

Tudo parte de uma data, o início da monta das vacas. A chuva escolhe a data (80–100 mm acumulados no início das águas,
Embrapa); as regras da Embrapa (novilhas antes, diagnóstico, pré-parto, touros, reposição) calculam o resto.

## Como rodar (Windows)

```powershell
.\RODAR.ps1
```

Cria `.venv`, instala e abre `http://127.0.0.1:8790/`. A interface já vem compilada em `src/vacas/web`; Node só é
preciso para alterá-la. Direto pelo Python: `$env:PYTHONPATH = "src"; python -m vacas app`.

## O que cada passo faz

| Passo | O que faz | De onde vêm os dados |
|---|---|---|
| Configurar | Local, raça, nº de vacas, primíparas e novilhas | Você |
| Preparar | Exames, lotes, nº de touros (25 a 30 vacas por touro), novilhas um mês antes | Regras Embrapa (CT 134, DOC 299) |
| Ver a chuva | Chuva acumulada desde 1º/set contra 90 mm; dia em que cruzou; histórico P10/P50/P90 | Open-Meteo (ERA5), a mesma fonte do histórico |
| Ver o plano | Monta, partos, desmama e cronograma por lote | Regras do ciclo (`ciclo.py`) |
| Levar à agenda | Baixa o calendário `.ics` | `ciclo.py` |
| Diagnóstico | Você informa as vazias; o app calcula descarte e teto de reposição (30%) | Você + CT 134 |
| Partos | Pré-parto crítico, partos por lote, bezerros esperados (só com o diagnóstico) | `ciclo.py` |
| Próximo ciclo | Exposição à próxima monta de cada grupo de partos | `ciclo.py` |

## Premissas e limites

- **Data de início:** vem da chuva observada se ela já cruzou o limite; senão, da mediana histórica. Você pode mudar.
- **Próxima monta:** premissa de que começa no mesmo dia do ano seguinte.
- **Sem taxa de prenhez inventada:** o número de bezerros só aparece se você informar o diagnóstico.
- **`.ics`:** segue o padrão iCalendar (dias inteiros, UTF-8, CRLF, linhas de até 75 octetos); a importação no Google
  Agenda e no Outlook não foi conferida.
- **Região:** os limiares foram pensados para o Cerrado (Goiás). O app não verifica se o ponto está no Cerrado.
- Triagem; não substitui zootecnista nem veterinário. Validação com estudos: `docs/VALIDACAO.md`.

## Estrutura

- `src/vacas/ciclo.py`: todas as regras (lotes, datas, touros, diagnóstico, exposição, `.ics`). A interface não refaz conta.
- `src/vacas/estacao.py`: chuva da estação em curso e histórico do início das águas.
- `src/vacas/servidor.py`: servidor local (só `127.0.0.1`) com `GET /api/estacao` e `POST /api/plano`.
- `web/`: interface em React com o design system [Astryx](https://github.com/meta/astryx) (`@astryxdesign/core`, tema neutro).
  Recompilar: `cd web; npm install --ignore-scripts; npm run build` (gera `src/vacas/web`).
- O restante é a V1 (`monta`, painel de clima), que continua funcionando: `python -m vacas monta --lat -16.5 --lon -49.5`.

## Testes

```powershell
$env:PYTHONPATH = "src"
python -m pytest tests -q
```
