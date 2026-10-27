# -*- coding: utf-8 -*-
"""Layout responsive PPP: CSS, template y contención de scroll horizontal."""
import unittest
from pathlib import Path

REPORTS_ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = REPORTS_ROOT / "static" / "reports" / "css" / "pedidos_pendientes_produccion_layout.css"
TEMPLATE_PATH = REPORTS_ROOT / "templates" / "reports" / "dashboard_detail.html"
FILTERS_PATH = REPORTS_ROOT / "templates" / "reports" / "includes" / "filters_pedidos_pendientes_produccion.html"
JS_PATH = REPORTS_ROOT / "static" / "reports" / "js" / "pedidos_pendientes_produccion.js"


class TestPppLayoutCss(unittest.TestCase):
    def test_css_scoped_y_scroll_solo_tabla(self):
        css = CSS_PATH.read_text(encoding="utf-8")
        self.assertIn("#ppp-report-dashboard", css)
        self.assertIn(".ppp-table-scroll", css)
        self.assertIn("overflow-x: auto", css)
        self.assertIn("overflow-x: clip", css)
        self.assertIn("width: max-content", css)
        self.assertIn("white-space: nowrap", css)
        self.assertIn("th.ppp-sort-th", css)

    def test_css_dashboard_root_solo_bajo_ppp(self):
        css = CSS_PATH.read_text(encoding="utf-8")
        self.assertIn("#ppp-report-dashboard #dashboard-root", css)
        stripped = css.replace("#ppp-report-dashboard #dashboard-root", "")
        self.assertNotIn("\n#dashboard-root", stripped)


class TestPppLayoutTemplate(unittest.TestCase):
    def test_template_ppp_report_dashboard_id(self):
        html = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("id=\"ppp-report-dashboard\"", html)
        self.assertIn("pedidos_pendientes_produccion_layout.css", html)
        self.assertIn("reports-ppp-card", html)
        self.assertIn("reports-ppp-outer", html)

    def test_filters_min_width(self):
        filt = FILTERS_PATH.read_text(encoding="utf-8")
        self.assertIn("min-w-0", filt)

    def test_script_version_bumped(self):
        html = TEMPLATE_PATH.read_text(encoding="utf-8")
        self.assertIn("pedidos_pendientes_produccion.js' %}?v=20261028a", html)


class TestPppLayoutJs(unittest.TestCase):
    def test_js_usa_ppp_table_scroll(self):
        js = JS_PATH.read_text(encoding="utf-8")
        self.assertIn("ppp-table-scroll", js)
        self.assertIn("ppp-sort-th", js)


class TestPppLayoutPlaywright(unittest.TestCase):
    """Verificación headless de scrollWidth vs viewport (fixture local)."""

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            cls._playwright_skip = True
            return
        cls._playwright_skip = False
        cls.css_uri = CSS_PATH.resolve().as_uri()

    def _build_fixture_html(self) -> str:
        cols = "".join(f"<th class='ppp-sort-th'>Columna {i}</th>" for i in range(24))
        cells = "".join("<td>9.999.999,99</td>" for _ in range(24))
        rows = "".join(f"<tr>{cells}</tr>" for _ in range(8))
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="{self.css_uri}">
<style>
  html, body {{ margin: 0; max-width: 100%; overflow-x: hidden; font-family: system-ui, sans-serif; }}
  .mock-hero {{ padding: 1rem; background: #1e293b; color: #fff; display: flex; flex-wrap: wrap; gap: 0.5rem; }}
  .mock-btn {{ padding: 0.35rem 0.75rem; border: 1px solid #38bdf8; border-radius: 999px; }}
</style>
</head>
<body>
<section id="ppp-report-dashboard">
  <div class="mock-hero reports-ppp-hero-actions">
    <span style="flex:1;min-width:0">Pedidos pendientes (Producción)</span>
    <button type="button" class="mock-btn">Actualizar</button>
    <button type="button" class="mock-btn">Exportar Excel</button>
    <button type="button" class="mock-btn">Filtros</button>
  </div>
  <div class="reports-ppp-outer" style="padding:1rem;box-sizing:border-box;width:100%;">
    <div class="reports-ppp-card" style="border:1px solid #e2e8f0;border-radius:1rem;width:100%;">
      <div id="dashboard-root">
        <section id="ppp-section">
          <div class="grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:0.5rem;padding:1rem;">
            <div>KPI 1</div><div>KPI 2</div><div>KPI 3</div>
          </div>
          <div id="ppp-table-wrap">
            <div class="ppp-table-scroll">
              <table class="ppp-data-table">
                <thead><tr>{cols}</tr></thead>
                <tbody>{rows}</tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</section>
</body>
</html>"""

    def _run_viewport(self, width: int):
        if self._playwright_skip:
            self.skipTest("playwright no instalado")
        from playwright.sync_api import sync_playwright

        html = self._build_fixture_html()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.set_content(html, wait_until="load")
            doc_sw = page.evaluate("() => document.documentElement.scrollWidth")
            inner_w = page.evaluate("() => window.innerWidth")
            scroll_el = page.evaluate(
                """() => {
                  const el = document.querySelector('.ppp-table-scroll');
                  return el ? el.scrollWidth > el.clientWidth : false;
                }"""
            )
            browser.close()
        return doc_sw, inner_w, scroll_el

    def test_viewport_1280_sin_scroll_pagina(self):
        doc_sw, inner_w, table_scrolls = self._run_viewport(1280)
        self.assertLessEqual(doc_sw, inner_w + 1, f"scrollWidth={doc_sw} innerWidth={inner_w}")
        self.assertTrue(table_scrolls)

    def test_viewport_1024_sin_scroll_pagina(self):
        doc_sw, inner_w, table_scrolls = self._run_viewport(1024)
        self.assertLessEqual(doc_sw, inner_w + 1)
        self.assertTrue(table_scrolls)

    def test_viewport_768_sin_scroll_pagina(self):
        doc_sw, inner_w, table_scrolls = self._run_viewport(768)
        self.assertLessEqual(doc_sw, inner_w + 1)
        self.assertTrue(table_scrolls)


if __name__ == "__main__":
    unittest.main()
