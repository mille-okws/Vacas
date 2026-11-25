# Validação do modelo com estudos

Método: li o texto de documentos abertos da Embrapa (baixados e extraídos; não só resumos de busca), cruzei duas fontes de clima e testei a sensibilidade dos parâmetros. Não usei dados da fazenda: o modelo **não foi validado contra prenhez ou partos reais**. Onde o estudo contradisse o modelo, corrigi o modelo (seção "O que mudou").

Local de teste: -16,5; -49,5 (Goiás), 1991–2050. Reproduzir: `python tools/validacao.py -16.5 -49.5` (com `$env:PYTHONPATH = "src"`).

## Veredito por parâmetro

| Parâmetro no modelo | O que os estudos dizem | Veredito |
|---|---|---|
| Monta começa após **80–100 mm** acumulados no início das águas (usa 90) | CT 134 (2017) recomenda iniciar logo após 80–100 mm; pode ser dispensado se as matrizes estão em boa condição corporal. Variar de 80 a 100 mm move o início em 2–3 dias. | **Confirmado** |
| Monta de **90 dias** | CT 134: três meses, e quanto mais perto de 90 dias maior o ganho de concentração de partos. DOC 299: 90 dias (novilhas até 45). A estação tradicional do Brasil Central (out–mar) é de 6 meses e deve ser encurtada aos poucos. | **Confirmado** |
| **Gestação nelore 292 d**, taurino 280 d | DOC 299: zebuínos ~292 d e europeus ~280 d. Estudo Embrapa com 4.463 vacas Nelore (Oeste de SP): 287,6 d. O mesmo artigo cita 293,6 d em outro trabalho. Rebanhos do Norte/Nordeste: 295,0 d. Muda com mês do parto e sexo do bezerro. | **Confirmado como faixa 287,6–295**; 292 é o valor da Embrapa |
| Partos em jul–dez e desmama em abril–junho | CT 134: partos de julho ao fim de dezembro, mais frequentes de agosto a outubro; desmama de abril a junho; lactação em pasto bom. O modelo dá partos de meados de ago a nov e desmama em meados/fim de abril. | **Confirmado** |
| Início das águas ~25 de outubro | Heinemann et al. (29 estações de Goiás, 1980–2013): início médio em 25 de outubro (faixa de início de outubro a início de novembro), fim em 2 de abril, 159 dias, 1.254 mm. Modelo (ERA5): início mediano 25/10 em 1991–2020. | **Confirmado** |
| 12 meses entre partos é apertado | DOC 299: com 290 d de gestação sobram 75 d para involução uterina (~30 d), retorno à ciclicidade e nova prenhez; em zebuínos 73 d (contra 85 d nos europeus). Rebanhos do Norte/Nordeste sem estação de monta: intervalo de partos de 465,6 d e período de serviço de 165,8 d (ideal 60–90 d). | **Confirmado** (é o achado central do painel) |
| Ciclo estral de **21 dias** | DOC 299: varia de 18 a 24 dias; 21 d é o padrão para definir manejos. | **Confirmado** |
| Descanso pós-parto de **60 dias** | DOC 299: involução uterina ~30 d; IATF entre 30 e 60 d pós-parto, com prenhez de 46–65%; anestro prolongado é comum a pasto e com nutrição ruim. Primíparas Nelore em Campo Grande: estro ~68% e prenhez 47–61%. | **Parcial**: dentro da faixa, mas a pasto pode ser maior |
| **Veranico** só na estação chuvosa, máx. 15 d | Embrapa Cerrados (Planaltina, 1974–2013): em jan e fev, sequências secas de até 10 dias têm 35% e 45% de probabilidade; as de até 15 dias, 8% e 2% (o texto não deixa claro se "até" inclui as mais curtas). Ou seja, 15 dias já é raro. | **Definição corrigida e coerente**; o limite de 15 d é premissa |
| Chuva mínima na amamentação **1.000 mm** | Chuva da estação chuvosa em Goiás: média 1.254 mm (1.038–1.405 por estação). Modelo: mediana 1.173 mm (902–1.421). Nenhum estudo lido liga esse total a desempenho do rebanho. | **Sem validação**; é o parâmetro que mais move o resultado |
| **210 dias** de parto à desmama | CT 134 só dá a janela de abril a junho. Um estudo ajusta pesos a 270 dias de idade. Não achei estudo para 210 d. | **Sem validação** |
| Fração de dias secos máx. 35% | Em Goiás a média é de 69 dias secos (<0,1 mm) em 159 de estação chuvosa, ou 43%. O limite de 35% reprovaria o ano típico. | **Contradito**: virou só informativo |
| Seca = chuva de 30 dias abaixo de 30 mm | Definição minha, só para exibição. Planaltina (Embrapa Cerrados): seis meses chuvosos e seis secos. Um boletim do CEMPA/UFG apareceu na busca dizendo seca de maio a setembro (só vi o resumo). Heinemann: águas de 159 d (seca complementar ~206 d, outro critério). | **Coerente**, mas não comparável diretamente |
| ~80% da forragem produzida nas águas | Só uma matéria da Revista Cultivar; não li estudo de medição. | **Não verificado** (o modelo não usa esse número) |

## Checagem dos dados: Open-Meteo (ERA5) × NASA POWER, 1991–2020 (29 anos)

| | ERA5 | NASA POWER |
|---|---|---|
| Início das águas, mediana | 25/10 | 17/10 |
| Seca, mediana (dias) | 164 | 152 |
| Chuva anual, mediana (mm) | 1.227 | 1.449 |

A diferença absoluta do início das águas é de 5 dias na mediana (média 9,4; máx. 36), com correlação 0,76. Conclusão: a incerteza da fonte de clima é de cerca de **uma semana no início** e **12 dias na seca**. Para comparação, o ERA5 bate com a média observada em estações (25/10); o NASA POWER antecipa.

## Sensibilidade (plano 1991–2049, depois das correções)

| Mudança | % de anos favoráveis | Exposição mediana à próxima monta (1ºs / medianos / últimos partos) |
|---|---|---|
| Base (nelore 292 d, 90 mm, monta 90 d, descanso 60 d) | 94,8% | 104 / 58 / 14 dias |
| Gestação 287 d / 295 d | 94,8% / 94,8% | 108/64/20 e 100/56/12 |
| Gestação 280 d (taurino) | 93,1% | 116 / 70 / 26 |
| Início das águas 80 mm / 100 mm | 93,1% / 94,8% | início 18/10 e 21/10 |
| Monta de 60 d | 93,1% | 74 / 44 / 14 |
| Descanso pós-parto 30 d / 90 d | 94,8% / 94,8% | 134/88/44 e 74/28/0 |
| **Chuva mínima 800 / 1.000 / 1.200 mm** | **100% / 94,8% / 56,9%** | igual |
| Veranico máx. 10 d / 30 d | 84,5% / 94,8% | igual |
| Dias secos ligado a 25% / 35% / 45% | 13,8% / 62,1% / 93,1% | igual |

O que isso diz:
- **Início das águas e gestação** pouco mexem no veredito: o resultado é robusto a eles.
- A **exposição à próxima monta** depende da gestação e do descanso pós-parto (de 14 para 0 dias nos últimos partos se o descanso for 90 d). O achado "os últimos partos ficam sem chance" vale em toda a faixa testada.
- O veredito de "favorável" depende quase só da **chuva mínima na amamentação**, que é premissa.

## O que mudou no modelo por causa dos estudos

1. Gestação: nelore 293 → **292** e taurino 283 → **280** (Embrapa DOC 299).
2. Veranico: antes contava qualquer sequência seca na janela de 210 dias, e a mediana era 14 dias, porque a janela inclui a cauda da seca. Agora só conta de novembro a março (mediana 7 dias; nenhum ano passou de 15 dias). Limite de 30 → **15 dias**.
3. Dias secos: o limite de 35% **deixou de decidir** (bloqueava 17 dos 30 anos de 1991–2020 e contradiz a média regional de 43%). O medidor continua no painel, sem veredito.
4. Efeito: anos favoráveis no plano 1991–2049 foram de 36 para **53 de 59**.

## Limites que ficam

- **Nada aqui prova que o modelo prevê prenhez.** Os estudos confirmam as peças (datas, ciclo, gestação, intervalo), não a regra de aprovação.
- A chuva mínima na amamentação, o veranico máximo, o descanso de 60 d e os 210 d seguem como premissas. O caminho para validar é cruzar, na própria fazenda, datas de parto, taxa de prenhez e intervalo entre partos com a chuva de cada ano.
- O **índice de adequação** do calendário (0–100 = o menor, entre chuva até a monta, chuva na amamentação e veranico, da fração do limite atingida) é uma construção do modelo: 100 equivale a "favorável", mas os tons intermediários herdam as mesmas premissas e não foram validados contra nenhum desfecho.
- Um único ponto (-16,5; -49,5) e dois conjuntos de clima de grade, sem pluviômetro local.
- Não li a revisão de Baruselli et al. sobre ciclo estral em zebuínos nem os dados de intervalo de partos da Embrapa Meio-Norte (só resumos de busca); não usei esses números.

## Fontes lidas

- Embrapa Gado de Corte, Comunicado Técnico 134, [Estação de monta em rebanhos de gado de corte](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1072647/1/Estacaodemontaemrebanhos.pdf) (2017)
- Embrapa Gado de Corte, Documentos 299, [Estação de monta em gado de corte](https://www.infoteca.cnptia.embrapa.br/infoteca/bitstream/doc/1137902/1/DOC-299-Final-em-alta.pdf) (2021)
- Alencar et al., [Peso ao parto, período de gestação e desempenho produtivo de vacas Nelore e cruzadas](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/43372/1/PesoPartoPeriodoGestacao.pdf)
- Amaral et al., [Intervalo parto-primeiro cio... de vacas Nelore primíparas](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/326508/1/Intervalo-parto-primeiro-cio-2006.pdf) (SBZ, 2006)
- Azevêdo, [Desempenho reprodutivo de vacas Nelore do Norte e Nordeste: intervalo de partos](https://www.agrolink.com.br/colunistas/a-pecuaria-de-corte-no-brasil--intervalo-de-partos-na-raca-nelore_385149.html) (2007)
- Heinemann et al., [Estabelecimento da estação chuvosa em Goiás](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1109037/1/CNPAF2018cbmetabh.pdf) (CBMET, 2018)
- Heinemann et al., [Precipitação pluvial no período das águas no Brasil Central](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1114348/1/CNPAF2019cbagro.pdf)
- Silva et al., [Ocorrência de veranicos no município de Planaltina-DF](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/1038975/1/S2086.pdf) (CBAgro, 2015)
