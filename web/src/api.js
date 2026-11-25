async function resposta(r) {
  let corpo = null;
  try {
    corpo = await r.json();
  } catch {
    /* corpo vazio ou não-JSON */
  }
  if (!r.ok) throw new Error((corpo && corpo.erro) || `Erro ${r.status}`);
  return corpo;
}

export const getEstacao = (lat, lon, signal) =>
  fetch(`/api/estacao?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`, {signal}).then(resposta);

export const postPlano = (corpo, signal) =>
  fetch('/api/plano', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(corpo), signal}).then(resposta);

const dataLocal = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};
export const hoje = dataLocal;
export const num = (n, casas = 1) => Number(n).toLocaleString('pt-BR', {maximumFractionDigits: casas});

const aData = (iso) => new Date(`${iso}T12:00:00`);
export const fmt = (iso, comAno = false) =>
  iso ? aData(iso).toLocaleDateString('pt-BR', {day: '2-digit', month: 'short', ...(comAno ? {year: 'numeric'} : {})}).replace(/\./g, '') : '—';
export const fmtIntervalo = (a, b, comAno = false) =>
  a === b ? fmt(a, comAno) : `${fmt(a, comAno && a.slice(0, 4) !== b.slice(0, 4))} a ${fmt(b, comAno)}`;
export const situacao = (inicio, fim, agora = dataLocal()) => (fim < agora ? 'passou' : inicio <= agora ? 'andamento' : 'futuro');

export function baixar(nome, texto, tipo) {
  const url = URL.createObjectURL(new Blob([texto], {type: tipo}));
  const a = Object.assign(document.createElement('a'), {href: url, download: nome});
  document.body.append(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
