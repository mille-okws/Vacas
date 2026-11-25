import json
import shutil
import subprocess
from pathlib import Path

import pytest

HTML = Path(__file__).parents[1] / 'src' / 'vacas' / 'resources' / 'dashboard.html'
SCRIPT = r"""
const t = require('fs').readFileSync(process.argv[1], 'utf8');
const code = t.match(/const map=[\s\S]*?function heat\(pct\)\{[\s\S]*?\}\n/)[0];
const heat = new Function(code + '; return heat;')();
console.log(JSON.stringify(JSON.parse(process.argv[2]).map(p => heat(p))));
"""


@pytest.mark.skipif(shutil.which('node') is None, reason='node não instalado')
def test_cor_do_quadrado_segue_os_pontos_do_gradiente():
    # preto = 0, vermelho 25, laranja 50, amarelo 75, verde 100; entre eles, interpolação linear (map)
    esperado = {0: 'rgb(26,26,26)', 25: 'rgb(255,0,0)', 50: 'rgb(255,140,0)', 75: 'rgb(255,229,0)',
                100: 'rgb(0,255,21)', 12.5: 'rgb(141,13,13)', 62.5: 'rgb(255,185,0)',
                87.5: 'rgb(128,242,11)', -5: 'rgb(26,26,26)', 130: 'rgb(0,255,21)'}
    saida = subprocess.run(['node', '-e', SCRIPT, str(HTML), json.dumps(list(esperado))],
                           capture_output=True, text=True, check=True).stdout
    assert json.loads(saida) == list(esperado.values())


def test_legenda_usa_o_mesmo_gradiente_do_calendario():
    html = HTML.read_text(encoding='utf-8')
    assert ('linear-gradient(90deg,rgba(26,26,26,1) 0%,rgba(255,0,0,1) 25%,rgba(255,140,0,1) 50%,'
            'rgba(255,229,0,1) 75%,rgba(0,255,21,1) 100%)') in html
