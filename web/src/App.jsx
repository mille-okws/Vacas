import React, {useEffect, useMemo, useState} from 'react';
import {Stepper, Step} from '@astryxdesign/core/Stepper';
import {Card} from '@astryxdesign/core/Card';
import {Stack} from '@astryxdesign/core/Stack';
import {HStack} from '@astryxdesign/core/HStack';
import {Heading} from '@astryxdesign/core/Heading';
import {Text} from '@astryxdesign/core/Text';
import {Button} from '@astryxdesign/core/Button';
import {Banner} from '@astryxdesign/core/Banner';
import {Badge} from '@astryxdesign/core/Badge';
import {NumberInput} from '@astryxdesign/core/NumberInput';
import {TextInput} from '@astryxdesign/core/TextInput';
import {DateInput} from '@astryxdesign/core/DateInput';
import {SegmentedControl, SegmentedControlItem} from '@astryxdesign/core/SegmentedControl';
import {Table} from '@astryxdesign/core/Table';
import {ProgressBar} from '@astryxdesign/core/ProgressBar';
import Cronograma from './Cronograma.jsx';
import {baixar, fmt, fmtIntervalo, getEstacao, hoje, num, postPlano, situacao} from './api.js';

const PASSOS = ['Configurar', 'Preparar', 'Ver a chuva', 'Ver o plano', 'Levar à agenda', 'Diagnóstico', 'Partos', 'Próximo ciclo'];
const CHAVE = 'vacas-v2';
const PADRAO = {cfg: {nome: 'Minha fazenda', lat: -16.5, lon: -49.5, raca: 'nelore', rebanho: {vacas: 300, primiparas: 60, novilhas: 40}},
                inicio: null, origem: null, vazias: {vacas: 0, primiparas: 0, novilhas: 0}, diagOn: false};

function carregar() {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE));
    return salvo && salvo.cfg ? {...PADRAO, ...salvo, cfg: {...PADRAO.cfg, ...salvo.cfg}} : PADRAO;
  } catch {
    return PADRAO;
  }
}

const SIT = {passou: ['já passou', 'neutral'], andamento: ['em andamento', 'warning'], futuro: ['vai chegar', 'success']};
const Situacao = ({inicio, fim}) => <Badge variant={SIT[situacao(inicio, fim)][1]} label={SIT[situacao(inicio, fim)][0]} />;
const Titulo = ({children, sub}) => (
  <Stack gap={1}>
    <Heading level={2}>{children}</Heading>
    {sub && <Text color="secondary">{sub}</Text>}
  </Stack>
);
const Numero = ({rotulo, valor, sub}) => (
  <Card padding={3} variant="muted">
    <Stack gap={0.5}>
      <Text type="supporting">{rotulo}</Text>
      <Heading level={3}>{valor}</Heading>
      {sub && <Text type="supporting">{sub}</Text>}
    </Stack>
  </Card>
);

export default function App() {
  const inicial = useMemo(carregar, []);
  const [cfg, setCfg] = useState(inicial.cfg);
  const [inicio, setInicio] = useState(inicial.inicio);
  const [origem, setOrigem] = useState(inicial.origem);
  const [vazias, setVazias] = useState(inicial.vazias);
  const [diagOn, setDiagOn] = useState(inicial.diagOn);
  const [passo, setPasso] = useState(0);
  const [estacao, setEstacao] = useState(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [erroPlano, setErroPlano] = useState(null);

  useEffect(() => {
    try {
      localStorage.setItem(CHAVE, JSON.stringify({cfg, inicio, origem, vazias, diagOn}));
    } catch {
      /* armazenamento indisponível: o app continua funcionando sem lembrar */
    }
  }, [cfg, inicio, origem, vazias, diagOn]);

  useEffect(() => {
    if (!inicio) return undefined;
    const ctl = new AbortController();
    const espera = setTimeout(() => {
      postPlano({inicio, raca: cfg.raca, rebanho: cfg.rebanho, nome: cfg.nome, ...(diagOn ? {vazias} : {})}, ctl.signal)
        .then((r) => { setResultado(r); setErroPlano(null); })
        .catch((e) => { if (e.name !== 'AbortError') setErroPlano(e.message); });
    }, 200);
    return () => { clearTimeout(espera); ctl.abort(); };
  }, [inicio, cfg.raca, cfg.rebanho, cfg.nome, vazias, diagOn]);

  const plano = resultado && resultado.plano;
  const diag = resultado && resultado.diagnostico;

  async function continuar() {
    setCarregando(true);
    setErro(null);
    try {
      const e = await getEstacao(cfg.lat, cfg.lon);
      setEstacao(e);
      if (!inicio) {
        const sugerido = e.atual.inicio_monta || e.atual.inicio_esperado;
        setInicio(sugerido);
        setOrigem(e.atual.inicio_monta ? 'chuva observada' : 'início esperado (mediana histórica)');
      }
      setPasso(1);
    } catch (e) {
      setErro(e.message);
    } finally {
      setCarregando(false);
    }
  }

  const usarInicio = (data, nome) => { setInicio(data); setOrigem(nome); };
  const mudarRebanho = (k) => (v) => setCfg((c) => ({...c, rebanho: {...c.rebanho, [k]: v ?? 0}}));
  const total = cfg.rebanho.vacas + cfg.rebanho.primiparas + cfg.rebanho.novilhas;
  const semPlano = !plano && (
    <Banner status="info" title="Ainda não há plano" description="Preencha o passo Configurar e toque em Continuar; o app calcula o calendário a partir do início da monta." />
  );

  const telas = [
    // 0 · Configurar
    <Stack gap={4} key="0">
      <Titulo sub="Feito uma vez por fazenda. O app lembra no navegador.">Configurar</Titulo>
      <TextInput label="Nome da fazenda" value={cfg.nome} onChange={(v) => setCfg({...cfg, nome: v})} />
      <HStack gap={3} wrap="wrap">
        <NumberInput label="Latitude" value={cfg.lat} onChange={(v) => setCfg({...cfg, lat: v})} min={-90} max={90} step={0.01} width={160} />
        <NumberInput label="Longitude" value={cfg.lon} onChange={(v) => setCfg({...cfg, lon: v})} min={-180} max={180} step={0.01} width={160} />
        <Button label="Exemplo: Goiás" variant="ghost" onClick={() => setCfg({...cfg, lat: -16.5, lon: -49.5})} />
      </HStack>
      <Text type="supporting">Os limiares do app foram pensados para o Cerrado (Goiás). Em outras regiões, trate o resultado com mais cautela.</Text>
      <SegmentedControl label="Raça" value={cfg.raca} onChange={(v) => setCfg({...cfg, raca: v})}>
        <SegmentedControlItem value="nelore" label="Nelore (gestação 292 dias)" />
        <SegmentedControlItem value="taurino" label="Taurino (gestação 280 dias)" />
      </SegmentedControl>
      <HStack gap={3} wrap="wrap">
        <NumberInput label="Vacas adultas" value={cfg.rebanho.vacas} onChange={mudarRebanho('vacas')} min={0} isIntegerOnly width={170} />
        <NumberInput label="Primíparas" value={cfg.rebanho.primiparas} onChange={mudarRebanho('primiparas')} min={0} isIntegerOnly width={170} />
        <NumberInput label="Novilhas" value={cfg.rebanho.novilhas} onChange={mudarRebanho('novilhas')} min={0} isIntegerOnly width={170} />
      </HStack>
      {total === 0 && <Banner status="warning" title="Informe ao menos um animal" />}
    </Stack>,

    // 1 · Preparar
    <Stack gap={4} key="1">
      <Titulo sub="Exames, lotes e touros antes de a monta começar.">Preparar</Titulo>
      {semPlano}
      {plano && (
        <>
          <Banner status="info" title={`Prazos calculados para a monta começar em ${fmt(plano.inicio, true)}`}
                  description={`Origem da data: ${origem || 'escolhida por você'}. O que já passou aparece como "já passou"; mude a data no passo Ver o plano.`} />
          <Table density="compact" idKey="item" data={[
            {item: 'Exames', quando: fmtIntervalo(plano.exames.inicio, plano.exames.fim, true), sit: [plano.exames.inicio, plano.exames.fim],
             nota: 'Ginecológico das vacas e andrológico dos touros, feitos por veterinário (laudo com até 60 dias antes).'},
            {item: 'Lotes', quando: plano.lotes.map((l) => `${l.nome}: ${l.animais}`).join(' · '), nota: 'Um lote por categoria, formado com base no exame ginecológico.'},
            {item: 'Touros', quando: `${plano.touros.minimo} a ${plano.touros.maximo} touros`, nota: `Para ${plano.touros.femeas_na_monta} fêmeas na monta (25 a 30 vacas por touro).`},
            ...plano.lotes.filter((l) => l.id === 'novilhas').map((l) => ({
              item: 'Novilhas entram antes', quando: fmtIntervalo(l.monta.inicio, l.monta.fim, true), sit: [l.monta.inicio, l.monta.fim],
              nota: 'Regra da Embrapa (um mês antes e por até 45 dias); não depende da chuva.'})),
          ]} columns={[
            {key: 'item', header: 'O que'},
            {key: 'quando', header: 'Quando / quanto'},
            {key: 'sit', header: 'Situação', renderCell: (r) => (r.sit ? <Situacao inicio={r.sit[0]} fim={r.sit[1]} /> : <Text type="supporting">—</Text>)},
            {key: 'nota', header: 'Observação'},
          ]} />
        </>
      )}
    </Stack>,

    // 2 · Ver a chuva
    <Stack gap={4} key="2">
      <Titulo sub="A Embrapa manda começar a monta logo depois de 80 a 100 mm de chuva acumulada no início das águas.">Ver a chuva</Titulo>
      {!estacao ? (
        <Banner status="info" title="Falta buscar a chuva" description="Volte ao passo Configurar e toque em Continuar." />
      ) : (
        <>
          {estacao.atual.encerrada && (
            <Banner status="warning" title="Esta é a estação passada" description="A estação nova começa a ser contada em 1º de setembro." />
          )}
          <ProgressBar label={`Chuva acumulada desde ${fmt(estacao.atual.desde, true)}`} value={Math.min(estacao.atual.acumulado_mm, estacao.atual.limite_mm)}
                       max={estacao.atual.limite_mm} hasValueLabel formatValueLabel={() => `${num(estacao.atual.acumulado_mm)} de ${num(estacao.atual.limite_mm)} mm`}
                       variant={estacao.atual.cruzou_em ? 'success' : 'accent'} />
          {estacao.atual.cruzou_em ? (
            <Banner status="success" title={`As águas chegaram: ${num(estacao.atual.limite_mm)} mm cruzados em ${fmt(estacao.atual.cruzou_em, true)}`}
                    description={`A monta das vacas começa em ${fmt(estacao.atual.inicio_monta, true)}.`} />
          ) : (
            <Banner status="info" title={`Faltam ${num(estacao.atual.faltam_mm)} mm`}
                    description={estacao.atual.inicio_esperado ? `Sem a chuva, o histórico aponta o início por volta de ${fmt(estacao.atual.inicio_esperado, true)}.` : undefined} />
          )}
          {estacao.historico.p50 && (
            <Text>No histórico ({estacao.historico.anos_avaliados} anos de 1991 a 2019), a monta começaria entre {estacao.historico.p10.data} e {estacao.historico.p90.data} em 80% dos anos; a mediana é {estacao.historico.p50.data}.</Text>
          )}
          <Text type="supporting">
            Chuva observada até {fmt(estacao.atual.observado_ate, true)} · fonte: {estacao.fonte.nome}. Os dias mais recentes podem faltar.
            {estacao.fonte.avisos.length ? ` Avisos: ${estacao.fonte.avisos.join('; ')}` : ''}
          </Text>
          <HStack gap={2} wrap="wrap">
            {estacao.atual.inicio_monta && (
              <Button label={`Usar ${fmt(estacao.atual.inicio_monta)} no plano`} variant="primary" onClick={() => { usarInicio(estacao.atual.inicio_monta, 'chuva observada'); setPasso(3); }} />
            )}
            {estacao.atual.inicio_esperado && (
              <Button label={`Usar o início esperado (${fmt(estacao.atual.inicio_esperado)})`} onClick={() => { usarInicio(estacao.atual.inicio_esperado, 'início esperado (mediana histórica)'); setPasso(3); }} />
            )}
          </HStack>
        </>
      )}
    </Stack>,

    // 3 · Ver o plano
    <Stack gap={4} key="3">
      <Titulo sub="Tudo parte da data em que a monta das vacas começa.">Ver o plano</Titulo>
      <DateInput label="Início da monta das vacas" value={inicio || undefined} description={origem ? `Origem: ${origem}` : undefined}
                 onChange={(v) => v && usarInicio(v, 'escolhida por você')} />
      {erroPlano && <Banner status="error" title="Não foi possível calcular" description={erroPlano} />}
      {semPlano}
      {plano && (() => {
        const v = plano.lotes.find((l) => l.id !== 'novilhas') || plano.lotes[0];
        return (
          <>
            <HStack gap={3} wrap="wrap">
              <Numero rotulo="Monta" valor={fmtIntervalo(v.monta.inicio, v.monta.fim)} sub={`${plano.monta_dias} dias`} />
              <Numero rotulo="Partos" valor={fmtIntervalo(v.partos.primeiro, v.partos.ultimo)} sub={`gestação ${plano.gestacao_dias} dias`} />
              <Numero rotulo="Desmama" valor={fmt(v.desmama, true)} sub={`parto mediano + ${plano.desmama_dias} dias`} />
              <Numero rotulo="Touros" valor={`${plano.touros.minimo} a ${plano.touros.maximo}`} sub={`${plano.touros.femeas_na_monta} fêmeas`} />
            </HStack>
            <Cronograma plano={plano} />
            <Table density="compact" idKey="id" data={plano.lotes} columns={[
              {key: 'nome', header: 'Lote'},
              {key: 'animais', header: 'Animais'},
              {key: 'monta', header: 'Monta', renderCell: (l) => fmtIntervalo(l.monta.inicio, l.monta.fim)},
              {key: 'partos', header: 'Partos', renderCell: (l) => fmtIntervalo(l.partos.primeiro, l.partos.ultimo)},
              {key: 'desmama', header: 'Desmama', renderCell: (l) => fmt(l.desmama, true)},
            ]} />
          </>
        );
      })()}
    </Stack>,

    // 4 · Levar à agenda
    <Stack gap={4} key="4">
      <Titulo sub="Baixe as datas e importe no calendário do celular ou do computador.">Levar à agenda</Titulo>
      {semPlano}
      {plano && (
        <>
          <HStack gap={2} wrap="wrap">
            <Button label="Baixar calendário (.ics)" variant="primary"
                    onClick={() => baixar(`monta-${plano.inicio}.ics`, resultado.ics, 'text/calendar;charset=utf-8')} />
          </HStack>
          <Banner status="info" title="Importação não testada aqui" description="O arquivo segue o padrão iCalendar (dias inteiros, UTF-8), mas a importação no Google Agenda ou no Outlook ainda não foi conferida." />
          <Table density="compact" idKey="n" data={plano.eventos.map((e, n) => ({n, titulo: e.titulo, quando: fmtIntervalo(e.inicio, e.fim, true), sit: [e.inicio, e.fim]}))}
                 columns={[
                   {key: 'quando', header: 'Quando'},
                   {key: 'titulo', header: 'Evento'},
                   {key: 'sit', header: 'Situação', renderCell: (r) => <Situacao inicio={r.sit[0]} fim={r.sit[1]} />},
                 ]} />
        </>
      )}
    </Stack>,

    // 5 · Diagnóstico
    <Stack gap={4} key="5">
      <Titulo sub="Informe quantas fêmeas saíram vazias quando o diagnóstico sair. Sem esse número, o app não prevê quantos bezerros nascerão.">Diagnóstico</Titulo>
      {semPlano}
      {plano && (
        <>
          <Table density="compact" idKey="id" data={plano.lotes} columns={[
            {key: 'nome', header: 'Lote'},
            {key: 'animais', header: 'Animais'},
            {key: 'dg', header: 'Ultrassom ou palpação, a partir de', renderCell: (l) => `${fmt(l.diagnostico.ultrassom)} ou ${fmt(l.diagnostico.palpacao, true)}`},
            {key: 'seca', header: 'Descartar antes de', renderCell: (l) => fmt(l.diagnostico.descartar_antes_de, true)},
          ]} />
          <HStack gap={3} wrap="wrap">
            {plano.lotes.map((l) => (
              <NumberInput key={l.id} label={`Vazias: ${l.nome}`} value={vazias[l.id]} min={0} max={l.animais} isIntegerOnly width={190}
                           description={`de ${l.animais} animais`}
                           onChange={(v) => { setVazias((x) => ({...x, [l.id]: v ?? 0})); setDiagOn(true); }} />
            ))}
            {diagOn && <Button label="Limpar" variant="ghost" onClick={() => { setDiagOn(false); setVazias({vacas: 0, primiparas: 0, novilhas: 0}); }} />}
          </HStack>
          {erroPlano && <Banner status="error" title="Número inválido" description={erroPlano} />}
          {diag && (
            <>
              <HStack gap={3} wrap="wrap">
                <Numero rotulo="Prenhes" valor={diag.prenhes} sub={`taxa de prenhez ${(diag.taxa_prenhez * 100).toFixed(1).replace('.', ',')}% (a sua)`} />
                <Numero rotulo="Descarte sugerido" valor={diag.descarte_sugerido} sub="vacas e primíparas vazias" />
                <Numero rotulo="Teto de reposição" valor={diag.teto_reposicao} sub="30% das matrizes (Embrapa)" />
              </HStack>
              {diag.reposicao_acima_do_teto && (
                <Banner status="warning" title="Descarte acima do teto de reposição"
                        description={`Repor mais de ${diag.teto_reposicao} matrizes no mesmo ano compromete a produtividade seguinte (as primíparas reconcebem pior). Considere descartar menos ou repor em dois anos.`} />
              )}
            </>
          )}
        </>
      )}
    </Stack>,

    // 6 · Partos
    <Stack gap={4} key="6">
      <Titulo sub="Quando nascem os bezerros e o que cuidar antes e depois.">Partos</Titulo>
      {semPlano}
      {plano && (
        <>
          <Cronograma plano={plano} fases={['pre_parto', 'partos', 'desmama']} />
          <Table density="compact" idKey="id" data={plano.lotes} columns={[
            {key: 'nome', header: 'Lote'},
            {key: 'pre', header: 'Pré-parto crítico', renderCell: (l) => fmtIntervalo(l.pre_parto.inicio, l.pre_parto.fim)},
            {key: 'partos', header: 'Partos (primeiro · mediano · último)', renderCell: (l) => `${fmt(l.partos.primeiro)} · ${fmt(l.partos.mediano)} · ${fmt(l.partos.ultimo)}`},
            {key: 'desmama', header: 'Desmama', renderCell: (l) => fmt(l.desmama, true)},
          ]} />
          {diag ? (
            <Banner status="success" title={`Bezerros esperados: ${diag.bezerros_esperados}`} description="Número de fêmeas prenhes que você informou no diagnóstico; o app não estima taxa de prenhez." />
          ) : (
            <Banner status="info" title="Número de bezerros" description="Aparece quando você informar o diagnóstico no passo anterior." />
          )}
          <Text type="supporting">Os dois últimos meses de gestação são críticos; vacas em má condição corporal e primíparas pedem pasto e suplementação melhores (Embrapa).</Text>
        </>
      )}
    </Stack>,

    // 7 · Próximo ciclo
    <Stack gap={4} key="7">
      <Titulo sub="O ciclo fecha em 12 meses? Cada vaca precisa estar recuperada do parto quando a próxima monta ainda está aberta.">Próximo ciclo</Titulo>
      {semPlano}
      {plano && (
        <>
          <Text type="supporting">Premissa: a próxima estação começa no mesmo dia do ano seguinte, e a vaca precisa de {plano.descanso_pos_parto_dias} dias depois do parto para voltar a ciclar. Exposição abaixo de {plano.ciclo_estral_dias} dias (um ciclo estral) é pouca para emprenhar.</Text>
          <Table density="compact" idKey="id" data={plano.lotes} columns={[
            {key: 'nome', header: 'Lote'},
            ...[['primeiros', 'Primeiros partos'], ['medianos', 'Partos medianos'], ['ultimos', 'Últimos partos']].map(([k, h]) => ({
              key: k, header: h,
              renderCell: (l) => <HStack gap={1} align="center"><Text>{l.exposicao[k]} dias</Text><Badge variant={l.exposicao[k] < plano.ciclo_estral_dias ? 'warning' : 'success'} label={l.exposicao[k] < plano.ciclo_estral_dias ? 'curta' : 'ok'} /></HStack>,
            })),
            {key: 'prox', header: 'Próxima monta (premissa)', renderCell: (l) => fmtIntervalo(l.proxima_monta.inicio, l.proxima_monta.fim, true)},
          ]} />
          {plano.lotes.some((l) => l.exposicao_curta.length) && (
            <Banner status="warning" title="Parte do rebanho não fecha o ciclo em 12 meses"
                    description="Com gestação de zebuíno (292 dias) e monta de 90 dias, quem emprenha no fim da estação sobra com poucos dias na estação seguinte; a Embrapa estima 73 dias para emprenhar de novo. Isso não é falha do app: é a conta do ciclo." />
          )}
          <Button label="Recomeçar o ciclo no passo Preparar" onClick={() => setPasso(1)} />
        </>
      )}
    </Stack>,
  ];

  return (
    <div style={{maxWidth: 1000, margin: '0 auto', padding: 24}}>
    <Stack gap={5}>
      <Stack gap={1}>
        <Heading level={1}>Vacas V2 · planejar o nascimento dos bezerros</Heading>
        <Text color="secondary">{cfg.nome} · {total} animais · {cfg.raca} · hoje é {fmt(hoje(), true)}</Text>
      </Stack>
      <Stepper activeStep={passo} onStepClick={(i) => setPasso(i)} label="Etapas do ciclo reprodutivo">
        {PASSOS.map((nome, i) => <Step key={nome} step={i} label={nome} />)}
      </Stepper>
      {erro && <Banner status="error" title="Não foi possível buscar a chuva" description={erro} isDismissable onDismiss={() => setErro(null)} />}
      <Card padding={5}>{telas[passo]}</Card>
      <HStack gap={2} justify="between">
        <Button label="Voltar" variant="ghost" isDisabled={passo === 0} onClick={() => setPasso(passo - 1)} />
        {passo === 0 ? (
          <Button label="Continuar" variant="primary" isLoading={carregando} isDisabled={total === 0} onClick={continuar} />
        ) : (
          <Button label={passo === PASSOS.length - 1 ? 'Fim do ciclo' : 'Avançar'} variant="primary" isDisabled={passo === PASSOS.length - 1} onClick={() => setPasso(passo + 1)} />
        )}
      </HStack>
    </Stack>
    </div>
  );
}
