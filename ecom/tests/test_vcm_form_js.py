"""Tests utilidades JS del formulario VCM (payload de asignación)."""

import json
import subprocess
import unittest
from pathlib import Path

_JS_PATH = Path(__file__).resolve().parents[1] / "static" / "ecom" / "js" / "vcm_form.js"
_TPL_PATH = Path(__file__).resolve().parents[1] / "templates" / "ecom" / "config_vendedor_cliente_marca.html"


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


class TestVcmFormJs(unittest.TestCase):
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

    def test_payload_con_mas_de_60_sucursales(self):
        out = _run_vcm_js(
            """
const selSucs = Array.from({length: 65}, (_, i) => ({ id_cliente_domicilio: i + 1 }));
const selMars = [{ CodMarca: 10, nombre: 'PUM' }, { CodMarca: 11, nombre: 'PUS' }];
const body = vcmFormUtils.vcmBuildCrearPayload(
  { CodViajante: 7 },
  { id_cliente: 42 },
  selSucs,
  selMars
);
console.log(JSON.stringify({
  nSuc: body.ids_cliente_domicilio.length,
  nMar: body.CodMarcas.length,
  first: body.ids_cliente_domicilio[0],
  last: body.ids_cliente_domicilio[64],
}));
"""
        )
        self.assertEqual(out["nSuc"], 65)
        self.assertEqual(out["nMar"], 2)
        self.assertEqual(out["first"], 1)
        self.assertEqual(out["last"], 65)

    def test_resumen_asignacion(self):
        out = _run_vcm_js(
            """
const line = vcmFormUtils.vcmResumenAsignacion(
  { nombre: 'Vend A' },
  { nombre: 'Cli B' },
  Array(60).fill({ id_cliente_domicilio: 1 }),
  [{ CodMarca: 1 }, { CodMarca: 2 }, { CodMarca: 3 }]
);
console.log(JSON.stringify({ line, rel: vcmFormUtils.vcmCountRelaciones(Array(60).fill({}), [{},{},{}]) }));
"""
        )
        self.assertIn("Vend A › Cli B › 60 sucursales × 3 marcas = 180 relaciones", out["line"])
        self.assertEqual(out["rel"], 180)

    def test_chips_preview_y_ocultas(self):
        out = _run_vcm_js(
            """
const items = Array.from({length: 12}, (_, i) => ({ id: i }));
const vis = vcmFormUtils.vcmChipsPreview(items, 8, false);
const hidden = vcmFormUtils.vcmChipsHiddenCount(items, 8, false);
const all = vcmFormUtils.vcmChipsPreview(items, 8, true);
console.log(JSON.stringify({ vis: vis.length, hidden, all: all.length }));
"""
        )
        self.assertEqual(out["vis"], 8)
        self.assertEqual(out["hidden"], 4)
        self.assertEqual(out["all"], 12)

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


class TestVcmTemplateLayout(unittest.TestCase):
    def setUp(self):
        self.html = _TPL_PATH.read_text(encoding="utf-8")

    def test_combobox_tiene_color_texto_modo_claro(self):
        self.assertIn('id="vcm-vend"', self.html)
        self.assertIn("text-slate-900", self.html)
        self.assertIn("placeholder:text-slate-400", self.html)
        self.assertIn("vcm_form.js", self.html)
        self.assertIn("onFocusVend()", self.html)
        self.assertIn("Seleccionado:", self.html)

    def test_modal_asignar_scroll_y_detalle_colapsado(self):
        self.assertIn("max-h-[70vh]", self.html)
        self.assertIn("Ver detalle", self.html)
        self.assertIn("modalAsignarDetalle", self.html)
        self.assertIn("resumenAsignacionLinea()", self.html)
        self.assertIn("flex-shrink-0", self.html)
        self.assertIn("<footer", self.html)

    def test_chips_sucursal_preview_y_toggle(self):
        self.assertIn("sucChipsVisibles()", self.html)
        self.assertIn("sucChipsOcultas()", self.html)
        self.assertIn("chipsSucExpandidas", self.html)
        self.assertIn("contadorSucursales()", self.html)
        self.assertIn("seleccionarTodasSucDesdeForm()", self.html)
        self.assertIn("+", self.html)
        self.assertIn("más", self.html)

    def test_modal_anular_lote_detalle_scroll(self):
        self.assertIn("modalAnularDetalle", self.html)
        self.assertIn("max-h-48", self.html)


try:
    from django.test import SimpleTestCase

    class TestVcmFormJsDjango(TestVcmFormJs, SimpleTestCase):
        pass

    class TestVcmTemplateLayoutDjango(TestVcmTemplateLayout, SimpleTestCase):
        pass
except ImportError:  # pragma: no cover — entorno sin Django
    pass
