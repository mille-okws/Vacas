# Vacas: proposta de escopo para planejar o nascimento dos bezerros

Documento de proposta. Nada aqui foi implementado além do que a seção 9 diz que já existe. Esforço: **P** até 1 dia, **M** 2 a 4 dias, **G** 1 a 2 semanas (estimativa minha, uma pessoa, sem revisão externa). Evidência: **✓** lido no texto da Embrapa, **○** visto só em resumo de busca (conferir), **✗** decisão de produto.

## 1. A proposta

**Promessa:** dado o local e o rebanho, planejar o ano reprodutivo para que os bezerros nasçam **concentrados na melhor época** e o ciclo se repita a cada 12 meses.

**A ideia central:** tudo parte de **uma data, o início da estação de monta**. Dela saem, em sequência, o diagnóstico de gestação, os partos, a desmama e a monta seguinte. O clima (a chuva) escolhe a data; o rebanho (categorias, touros, condição corporal) define quanto e quem; o calendário amarra as consequências.

Hoje o app resolve a primeira metade dessa frase (a data e o que ela implica em partos e desmama). Para ser um **planejamento completo**, falta cobrir o que o produtor decide *antes* (lotes, touros, exames) e *depois* (diagnóstico, descarte, pré-parto, próxima monta), e permitir que ele leve e acompanhe o calendário.

## 2. Para quem e qual decisão (a confirmar)

Hipótese: **pecuarista ou técnico de cria no Cerrado** que decide, todo ano, *quando abrir a estação de monta* e *como organizar o rebanho até a desmama*. Se o público for pesquisa ou ensino, o desenho continua valendo, mas o peso passa para transparência e exportação (seção 10).

## 3. O ano reprodutivo que o app planejaria

Exemplo real do modelo (Goiás, nelore, plano pelas águas de 2048). **Negrito** = calculado pelo app hoje; o restante vem de regra prática da Embrapa e passaria a ser calculado a partir da data de início.

| Fase | Quando (exemplo) | Decisão do produtor | O que o app entregaria | Base |
|---|---|---|---|---|
| 1. Preparar | 24 ago – 23 set (laudo com até 60 dias antes da monta) | Exame ginecológico das vacas e andrológico dos touros; formar lotes por categoria; definir quantos touros | Datas dos exames, lista de lotes e **número de touros** (25 a 30 vacas por touro) | ✓ CT 134; ✓ DOC 299 |
| 2. Decidir o início | out | Esperar 80–100 mm de chuva acumulada; novilhas começam um mês antes e por menos tempo (até 45 d); monta natural ou IATF | **Início recomendado: 23 out**; adequação 100/100; chuva acumulada até lá; datas por lote | ✓ CT 134; ✓ DOC 299 |
| 3. Estação de monta | **23 out 2048 – 20 jan 2049** (90 dias) | Conduzir a monta; repasse após IATF | **Calendário da estação**; com IATF, 40–60% das vacas podem emprenhar no primeiro dia | ✓ CT 134; ✓ DOC 299 |
| 4. Diagnóstico e descarte | 19 fev (ultrassom, +30 d) ou 6 mar (palpação, +45 d) | Descartar as vazias ainda em boa condição e antes da seca; repor com novilhas prenhes (no máximo 30% do rebanho) | Datas do diagnóstico, janela de descarte e **teto de reposição** | ✓ CT 134 |
| 5. Seca e pré-parto | **seca de 5 mai a 23 out** (171 dias); últimos 2 meses de gestação: 12 jun – 11 ago | Reservar o melhor pasto para primíparas; prever suplementação para parir com boa condição corporal | **Duração da seca**; janela crítica do pré-parto; alerta de condição corporal | ✓ DOC 299; ○ condição corporal × prenhez |
| 6. Partos | **11 ago – 8 nov 2049** (parto mediano em 25 set) | Organizar maternidade e manejo dos bezerros | **Calendário de partos** por grupo (primeiros, medianos, últimos) | ✓ gestação 292 d (DOC 299) |
| 7. Amamentação e desmama | **22 abr 2050** (parto mediano + 210 d); janela da Embrapa: abril a junho | Desmamar no início da seca; descartar matrizes com bezerro fraco | **Data de desmama**; peso padronizado aos 210 dias | ✓ CT 134; ○ 210 d |
| 8. Próxima estação | out 2049 | Repetir o ciclo; recuperar as vacas do parto | **Exposição à próxima monta**: neste exemplo, os últimos partos sobram com 1 dia (precisam de 21) | ✓ DOC 299 (73 d para emprenhar de novo) |

Nota sobre a fase 1: o DOC 299 e o CT 134 pedem os exames antes da monta, mas só fixam um prazo para touros **comprados** (laudo com até 60 dias). Usei os 60 dias como referência também para o rebanho próprio; a data exata seria uma premissa editável.

A fase 8 é a que mais ensina: com gestação de zebuíno (292 d) e monta de 90 dias, **quem emprenha no fim da estação dificilmente emprenha de novo no ciclo seguinte**. Por isso o plano precisa conectar um ano ao outro, e não só calcular partos.

## 4. Módulos do produto completo

| # | Módulo | Responde | Entradas | Saídas | Hoje | Base |
|---|---|---|---|---|---|---|
| M1 | **Local e clima** | Quando as águas chegam? Quanto dura a seca? | Ponto no mapa | Início das águas, seca, cenários 1991–2050, **acompanhamento da estação em curso** ("faltam X mm") | Parcial: falta acompanhar a estação atual | ✓ CT 134 |
| M2 | **Rebanho e lotes** | Quem entra na monta? | Raça, nº de vacas, primíparas e novilhas, nº de touros, condição corporal (opcional) | Lotes por categoria, nº de touros necessário | **Novo** | ✓ DOC 299 |
| M3 | **Estação de monta** | Quando começar, quanto durar, como cobrir? | Duração, monta natural ou IATF, regime atual | Datas por lote (novilhas antes e mais curtas); plano de **transição** de estação longa para 90 dias | Parcial: só vacas, só monta natural | ✓ CT 134 (duas estratégias de transição); ✓ DOC 299 |
| M4 | **Gestação e partos** | Quando nascem os bezerros? | (herda de M3) | Calendário de partos por grupo, diagnóstico de gestação (30/45 d), janela do pré-parto | Parcial: partos prontos; faltam diagnóstico e pré-parto | ✓ |
| M5 | **Amamentação e desmama** | Quando desmamar? | (herda) | Data de desmama, peso aos 210 d, alerta de seca no desmame | Parcial | ✓ CT 134; ○ 210 d |
| M6 | **Próxima estação, descarte e reposição** | O ciclo fecha em 12 meses? Quem sai e quem entra? | Resultado do diagnóstico (opcional) | Exposição à próxima monta, critérios de descarte (vazia, bezerro fraco), teto de reposição de 30% | Parcial: exposição pronta | ✓ DOC 299; ✓ CT 134 |
| M7 | **Pasto e nutrição** | Há pasto e condição corporal para sustentar o plano? | Área de pasto, cultivar, condição corporal | Oferta de forragem (kg MS/ha/dia), suplementação prevista | **Novo**, depende de estudos | ○ forragem; ○ condição corporal |
| M8 | **Calendário e acompanhamento** | Como levo isso para a fazenda e vejo se deu certo? | Datas reais de parto e diagnóstico | Exportar **CSV e .ics**, relatório de uma página, **planejado × realizado** | **Novo** | ✗ |
| M9 | **Confiança** | Posso confiar neste plano? | — | Premissas editáveis e rotuladas, fontes, reprodutibilidade, validação com histórico de fazenda | Parcial | ✓ (`docs/VALIDACAO.md`) |

**Transversais** (não são módulos, mas todo módulo depende): formulário de entrada no painel (hoje só linha de comando), escolha de local com aviso se estiver fora do Cerrado, parâmetros editáveis com recálculo, glossário curto (estação de monta, IATF, condição corporal, índice de adequação), proveniência de cada dado, testes de navegador.

**Fora de M1–M9, adiado:** sanidade reprodutiva (a única vacina obrigatória é a da brucelose; outras dependem do veterinário), viabilidade econômica das estratégias (o DOC 299 tem uma seção só sobre isso), calor (ITU), genética de touros, vários locais, versão hospedada.

## 5. Jornada do usuário

1. **Configurar:** escolhe o local, a raça e o rebanho (categorias, touros). Uma vez por fazenda.
2. **Ver a recomendação:** início da monta, adequação, ponto de atenção e a seca (o que o painel já mostra no topo).
3. **Ajustar:** muda duração, monta natural × IATF, antecipação das novilhas; compara com "e se o início for em outro mês?".
4. **Levar o calendário:** exporta datas de exames, monta, diagnóstico, pré-parto, partos e desmama para a agenda.
5. **Acompanhar:** na estação, vê a chuva acumulada contra os 80–100 mm; depois registra diagnóstico e partos reais e compara com o plano.
6. **Fechar o ciclo:** o resultado do diagnóstico alimenta o ano seguinte (descarte, reposição, exposição).

## 6. O que entra em cada versão

| Versão | Conteúdo | Esforço (soma aproximada) |
|---|---|---|
| **Hoje** | Plano pelas águas (vacas, monta natural), painel em gráficos, validação com estudos, execução por linha de comando | — |
| **MVP: planejamento do nascimento** | M1 com acompanhamento da estação; M2 básico (categorias, nº de vacas e touros); M3 (início, duração, **novilhas antes**, natural × IATF); M4 (partos, diagnóstico, pré-parto); M5 (desmama); M6 básico (exposição, teto de reposição, critérios de descarte como lista); M8 (CSV, .ics, resumo); M9 (premissas editáveis, revisão por técnico); formulário de entrada e escolha de local | de 5 a 9 semanas de uma pessoa (M1, M2, M4, M6, M8: M cada; M3: M a G; formulário: G; M5 e M9: P a M) |
| **v1** | M7 (condição corporal e forragem), planejado × realizado, comparação de dois cenários, relatório em PDF, teste contra histórico de uma fazenda | mais 3 a 5 semanas |
| **Depois** | Calor (ITU), economia, sanidade, vários locais, versão hospedada, outras regiões | — |

Por que este corte: o MVP entrega o **calendário completo e levável**, que é a promessa da seção 1, usando só o que tem estudo lido (✓). O que depende de estudo ainda só visto em resumo (condição corporal, forragem) fica para a v1, depois da leitura.

## 7. O que o usuário informa e o que o app estima

| O usuário informa | O app calcula |
|---|---|
| Local, raça, nº de vacas, primíparas, novilhas e touros | Início da monta, duração, datas por lote |
| Monta natural ou IATF | Datas dos protocolos e do repasse |
| Resultado do diagnóstico (opcional) | Vazias, descarte, reposição, exposição à próxima monta |
| Datas reais de parto (opcional) | Planejado × realizado |
| Condição corporal e taxa de prenhez histórica (opcional) | Avisos de pré-parto; **nº de bezerros esperado só se a taxa for informada** |

O app **não inventa taxa de prenhez**. Sem dado da fazenda, ele mostra datas e riscos, não uma previsão de quantos bezerros nascerão.

## 8. Fora do escopo

Produtividade (peso do bezerro, ganho de peso), economia e custos, prescrição sanitária ou nutricional, seleção genética, fertilidade do touro além do número de touros, outras regiões e biomas, outras espécies, lavoura (ZARC, solo, rotação, do safra original).

## 9. O que já existe

| Item | Estado |
|---|---|
| Plano anual pelas águas (início por 90 mm acumulados desde 1º/set, monta de 90 d, gestação por raça, partos, desmama) | Pronto e testado |
| Raças nelore (292 d) e taurino (280 d); `--gestation-days` | Pronto |
| Critérios (chuva até a monta, chuva na amamentação, veranico só nov–mar) e índice de adequação 0–100 | Pronto; limiares são premissas |
| Exposição à próxima monta e ponto de atenção (informativo) | Pronto |
| Duração da seca, evolução da chuva por década, faixa P10–P90 do início das águas | Pronto |
| Painel offline: barra de cenário, títulos com a conclusão, calendário em gradiente, claro/escuro, celular | Pronto |
| Validação com estudos (`docs/VALIDACAO.md`) e `tools/validacao.py` | Pronto |
| 29 testes automáticos | Passando |

## 10. Critérios de aceite do planejamento completo

1. Dado o local, a raça e o rebanho, gera o calendário **das fases 1 a 8** sem editar código nem usar linha de comando.
2. As datas de exames, diagnóstico e pré-parto saem da data de início da monta pelas regras da Embrapa, com a fonte visível.
3. Novilhas e vacas têm datas diferentes (novilhas um mês antes e por até 45 dias).
4. Toda premissa aparece como **confirmada** ou **premissa** e pode ser editada com recálculo.
5. A mesma entrada gera o mesmo resultado (identificador e hash dos parâmetros).
6. Exporta CSV e calendário (.ics) com todas as datas.
7. Dado ausente aparece como "sem dado", nunca como favorável ou zero; nenhuma previsão de nº de bezerros sem taxa informada.
8. Revisão por zootecnista ou veterinário registrada; teste contra histórico de pelo menos uma fazenda, ou a tela declara que não foi validado.

## 11. Decisões que dependem de você

1. **Público:** produtor, técnico ou pesquisa? Muda a ordem do MVP (entrada simples × transparência).
2. **IATF no MVP:** entra junto com a monta natural, ou só monta natural no início?
3. **Rebanho:** o MVP precisa de novilhas e primíparas (recomendado), ou começa só com vacas adultas?
4. **Touros:** calcular só o número de touros, ou também registrar exames e descarte?
5. **Onde roda:** local (como hoje) ou hospedado (muda privacidade e custo)?
6. **Dados reais:** você tem acesso a um histórico de fazenda (partos, diagnóstico, chuva) para validar?
7. **Economia:** o DOC 299 tem uma seção sobre viabilidade das estratégias; vale um módulo depois do MVP?

## 12. Riscos

- **As premissas movem o resultado.** A chuva mínima na amamentação (1.200 mm → 57% dos anos favoráveis; 800 mm → 100%) é a que mais pesa. "Favorável" não é garantia.
- **O ciclo de 12 meses é apertado por natureza.** Com gestação de zebuíno e monta de 90 dias, os últimos partos ficam sem chance no ciclo seguinte; o app deve mostrar isso, não esconder.
- **Dependência de APIs gratuitas** (Open-Meteo, NASA POWER) sem garantia de serviço; as coordenadas da fazenda são enviadas a elas.
- **Grade ≠ pluviômetro:** diferença de cerca de 1 semana no início das águas e de ~18% na chuva anual entre as duas fontes.
- **Modelo calibrado em Goiás.** Outra região exige revisar meses e limiares.
- **Uma pessoa, sem revisão externa:** os esforços acima podem subir.

## 13. Débitos técnicos conhecidos

`contracts.py` ainda traz tipos de cultura do safra; `pecuaria.py` reúne cálculo e geração do painel (separar quando entrar o formulário); painel de ~595 KB por embutir a chuva diária; gradiente vermelho–verde ruim para daltonismo; quadrados do calendário muito finos no celular; sem testes de navegador; `RODAR.ps1` exige internet na primeira execução.

## Fontes

**Lidas no texto:** Embrapa Gado de Corte, [Comunicado Técnico 134](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1072647/1/Estacaodemontaemrebanhos.pdf) (lotes, exames, novilhas, diagnóstico de gestação, descarte, reposição, IATF, transição de regime) e [Documentos 299](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1137902/1/DOC-299-Final-em-alta.pdf) (relação touro:vaca, exame andrológico, janela de 73 dias, pré-parto, categorias); [Alencar et al.](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/43372/1/PesoPartoPeriodoGestacao.pdf); [Amaral et al.](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/326508/1/Intervalo-parto-primeiro-cio-2006.pdf); [Azevêdo](https://www.agrolink.com.br/colunistas/a-pecuaria-de-corte-no-brasil--intervalo-de-partos-na-raca-nelore_385149.html); [Heinemann et al. (Goiás)](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1109037/1/CNPAF2018cbmetabh.pdf); [Silva et al. (veranicos)](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1038975/1/S2086.pdf).

**Só em resumo de busca (conferir):** [condição corporal e prenhez em Nelore](https://www.scielo.br/j/rbz/a/9hwHMbJctNpgjpQBT5tZ84G/?lang=pt); [comunicado da Embrapa Rondônia](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1136161/1/cpafro-18613.pdf); [produção de forragem de cultivares](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/570329/1/Producao-de-forragem-de-cultivares.pdf); [Boletim 81, Embrapa Cerrados](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/567959/1/bolpd81.pdf); [Comunicado Técnico 118](https://ainfo.cnptia.embrapa.br/digital/bitstream/doc/1174002/1/2025-cppse-com-tec-118-jcpp-coeficiente-culturas-forrageiras-brasil-aplicacao-calculo-necessidade-irrigacao.pdf); [cenários agrícolas futuros](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1136396/1/CenariosAgricolasFuturos.pdf); [ITU em vacas zebuínas](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6081557/).
