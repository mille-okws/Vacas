import React from 'react';
import {fmt, hoje} from './api.js';

const ROTULO = {exames: 'Exames', monta: 'Monta', diagnostico: 'Diagnóstico', pre_parto: 'Pré-parto', partos: 'Partos', desmama: 'Desmama'};
const COR = {exames: '#898781', monta: '#1baf7a', diagnostico: '#eb6834', pre_parto: '#7a6ad8', partos: '#3987e5', desmama: '#c98500'};
const MS = 864e5;
const t = (iso) => new Date(`${iso}T12:00:00`).getTime();

// Uma linha por fase e por lote, sobre um eixo de meses. Só desenha o que o servidor calculou.
export default function Cronograma({plano, fases}) {
  const nomes = Object.fromEntries(plano.lotes.map((l) => [l.id, l.nome]));
  const eventos = plano.eventos.filter((e) => !fases || fases.includes(e.chave));
  if (!eventos.length) return null;
  const agora = t(hoje());
  const ini = Math.min(...eventos.map((e) => t(e.inicio))) - 7 * MS;
  const fim = Math.max(...eventos.map((e) => t(e.fim))) + 14 * MS;
  const L = 190, W = 900, R = 12, LINHA = 26, TOPO = 38;
  const alto = TOPO + eventos.length * LINHA + 8;
  const x = (ms) => L + ((ms - ini) / (fim - ini)) * (W - L - R);
  const meses = [];
  for (let d = new Date(new Date(ini).getFullYear(), new Date(ini).getMonth(), 1); d.getTime() <= fim && meses.length < 48;
       d = new Date(d.getFullYear(), d.getMonth() + 1, 1)) {
    if (d.getTime() >= ini) meses.push(new Date(d));
  }
  return (
    <div style={{overflowX: 'auto'}}>
    <svg viewBox={`0 0 ${W} ${alto}`} width="100%" role="img" style={{display: 'block', minWidth: 720}}
         aria-label="Cronograma do ano reprodutivo: exames, monta, diagnóstico, pré-parto, partos e desmama por lote">
      {meses.map((m) => (
        <g key={m.getTime()}>
          <line x1={x(m.getTime())} x2={x(m.getTime())} y1={TOPO - 4} y2={alto - 4} stroke="currentColor" opacity="0.1" />
          <text x={x(m.getTime()) + 3} y={TOPO - 8} fontSize="11" fill="currentColor" opacity="0.65">
            {m.toLocaleDateString('pt-BR', {month: 'short'}).replace('.', '')}
          </text>
          {(m.getMonth() === 0 || m === meses[0]) && (
            <text x={x(m.getTime()) + 3} y={TOPO - 22} fontSize="11" fontWeight="600" fill="currentColor" opacity="0.85">{m.getFullYear()}</text>
          )}
        </g>
      ))}
      {agora >= ini && agora <= fim && (
        <g>
          <line x1={x(agora)} x2={x(agora)} y1={TOPO - 4} y2={alto - 4} stroke="currentColor" strokeWidth="1.5" opacity="0.55" />
          <text x={x(agora) + 4} y={alto - 8} fontSize="11" fill="currentColor" opacity="0.8">hoje</text>
        </g>
      )}
      {eventos.map((e, i) => {
        const y = TOPO + i * LINHA;
        const a = x(t(e.inicio)), b = Math.max(x(t(e.fim) + MS), a + 6);
        const rotulo = `${ROTULO[e.chave]}${e.lote ? ` · ${nomes[e.lote]}` : ''}`;
        return (
          <g key={`${e.chave}-${e.lote}-${e.inicio}`}>
            <title>{`${rotulo}: ${fmt(e.inicio, true)}${e.inicio === e.fim ? '' : ` a ${fmt(e.fim, true)}`}`}</title>
            <text x={L - 8} y={y + 15} fontSize="12" textAnchor="end" fill="currentColor">{rotulo}</text>
            <rect x={a} y={y + 4} width={b - a} height={14} rx="3" fill={COR[e.chave]} />
          </g>
        );
      })}
    </svg>
    </div>
  );
}
