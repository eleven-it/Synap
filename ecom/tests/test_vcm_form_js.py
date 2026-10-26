"""Tests utilidades JS del formulario VCM (payload de asignación)."""

import json
import subprocess
from pathlib import Path

from django.test import SimpleTestCase

_JS_PATH = Path(__file__).resolve().parents[1] / "static" / "ecom" / "js" / "vcm_form.js"


def _run_vcm_js(snippet: str) -> dict:
    script = f"""
const fs = require('fs');
const path = require('path');
const code = fs.readFileSync(path.join({json.dumps(str(_JS_PATH.parent))}, 'vcm_form.js'), 'utf8');
eval(code);
{snippet}
"""
    proc = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    line = (proc.stdout or "").strip().splitlines()[-1]
    return json.loads(line)


class TestVcmFormJs(TestCase):
    def test_formulario_incompleto_sin_vendedor(self):
        out = _run_vcm_js(
            """
const ok = vcmFormUtils.vcmFormularioListo(null, {id_cliente: 1}, [{id_cliente_domicilio: 2}], [{CodMarca: 3}]);
console.log(JSON.stringify({ok}));
"""
        )
        self.assertFalse(out["ok"])

    def test_payload_asignacion_completo(self):
        out = _run_vcm_js(
            """
const selVend = { CodViajante: 12, nombre: 'Esteban Carrizo' };
const selCli = { id_cliente: 99, nombre: 'ANTONIO LUQUIN S.A.C.I.F.I' };
const selSucs = [{ id_cliente_domicilio: 240106, etiqueta: 'CAP06' }, { id_cliente_domicilio: 240107 }];
const selMars = [{ CodMarca: 1, nombre: 'PUM' }, { CodMarca: 2, nombre: 'PUS' }, { CodMarca: 3, nombre: 'PUW' }];
const body = vcmFormUtils.vcmBuildCrearPayload(selVend, selCli, selSucs, selMars);
console.log(JSON.stringify(body));
"""
        )
        self.assertEqual(
            out,
            {
                "CodViajante": 12,
                "id_cliente": 99,
                "CodMarcas": [1, 2, 3],
                "ids_cliente_domicilio": [240106, 240107],
            },
        )

    def test_payload_null_si_falta_marca(self):
        out = _run_vcm_js(
            """
const body = vcmFormUtils.vcmBuildCrearPayload(
  { CodViajante: 1 },
  { id_cliente: 2 },
  [{ id_cliente_domicilio: 3 }],
  []
);
console.log(JSON.stringify({ body }));
"""
        )
        self.assertIsNone(out["body"])


class TestVcmTemplateInputTheme(TestCase):
    def test_combobox_tiene_color_texto_modo_claro(self):
        tpl = Path(__file__).resolve().parents[1] / "templates" / "ecom" / "config_vendedor_cliente_marca.html"
        html = tpl.read_text(encoding="utf-8")
        self.assertIn('id="vcm-vend"', html)
        self.assertIn("text-slate-900", html)
        self.assertIn("placeholder:text-slate-400", html)
        self.assertIn("vcm_form.js", html)
        self.assertIn("onFocusVend()", html)
        self.assertIn("Seleccionado:", html)
