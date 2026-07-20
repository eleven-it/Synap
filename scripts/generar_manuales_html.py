#!/usr/bin/env python3
"""
Genera HTML navegable desde los manuales Markdown de MPR y Stock.
Sin dependencias externas. Fuente: docs/mpr|stock/MANUAL_USUARIO_*.md
"""
from __future__ import annotations

import html
import re
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MPR_ALIASES: dict[str, str] = {
    "acceso": "1. Acceso al módulo",
    "tablero": "2. Tablero de control",
    "tablero-produccion": "2.1 Tablero de producción (operación diaria)",
    "demanda": "3. Demanda",
    "ventana-unidades": "3.1 Pedido producción trabajo (OPT) / Ventana Unidades",
    "confirmar-opt": "3.1.1 Confirmar OPT (agrupar)",
    "pedidos-fabrica": "3.2 Pedidos a fábrica",
    "wizard": "5.0 Asistente de producción (wizard)",
    "lista-opt": "5.1 Lista de OPT",
    "nueva-opt": "5.2 Nueva OPT",
    "detalle-opt": "5.3 Detalle de una OP",
    "liberar-opt": "5.4 Liberar a producción (OPT)",
    "registrar-opp": "5.5 Registrar parte de producción (OPP)",
    "cerrar-opt": "5.6 Cerrar OPT",
    "operarios": "5.8 Operarios (ABM)",
    "lista-materiales": "6. Lista de materiales (recetas)",
    "armado": "7. Armado unificado (1ra y 2da)",
    "armado-2da": "7.1 Armado 2da (composición libre)",
    "armado-1ra": "7.2 Armado 1ra (BOM fija)",
    "imputacion-pedido": "7.3 Imputación de pedido (supervisor)",
    "reclasificacion": "8. Reclasificación",
    "depositos": "9. Configuración: Depósitos",
    "reportes-mpr": "10. Reportes MPR",
    "flujo-resumido": "11. Flujo resumido",
    "trazabilidad": "12. Trazabilidad por máquina, línea y operario",
    "config-planta": "12.1 Configuración de planta (supervisor)",
    "asignar-articulo-maquina": "Asignar artículo a máquina e imprimir planilla",
    "carga-movil-operario": "12.2 Carga móvil del operario",
    "partes-pendientes": "12.3 Aprobación de partes (supervisor)",
    "mensajes-mpr": "13. Mensajes y errores frecuentes",
}

STOCK_ALIASES: dict[str, str] = {
    "acceso-stock": "1. Acceso",
    "inventario-por-etapa": "2. Inventario por etapa",
    "alta-movimiento": "3. Alta de movimiento (orientación)",
    "mensajes-stock": "4. Mensajes frecuentes",
}

# alias -> título exacto (invertido para búsqueda)
_ALIAS_BY_TITLE: dict[frozenset, dict[str, str]] = {
    frozenset({"mpr"}): {v: k for k, v in MPR_ALIASES.items()},
    frozenset({"stock"}): {v: k for k, v in STOCK_ALIASES.items()},
}


def slug_es(text: str) -> str:
    """Slug en español: minúsculas, sin acentos, guiones."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _alias_for_title(title: str, module: str) -> str | None:
    key = frozenset({"mpr"} if module == "mpr" else {"stock"})
    return _ALIAS_BY_TITLE[key].get(title.strip())


def _heading_id(level: int, title: str, module: str) -> str:
    alias = _alias_for_title(title, module)
    if alias:
        return alias
    return slug_es(title)


CSS = """
:root {
  --bg: #f4f6f9;
  --surface: #ffffff;
  --border: #e2e8f0;
  --text: #1e293b;
  --muted: #64748b;
  --accent: #0f766e;
  --accent-light: #ccfbf1;
  --accent-dark: #115e59;
  --warn: #b45309;
  --sidebar-w: 280px;
  --radius: 10px;
  --shadow: 0 1px 3px rgba(15, 23, 42, 0.08), 0 4px 16px rgba(15, 23, 42, 0.04);
  --font: "Segoe UI", system-ui, -apple-system, sans-serif;
  --mono: ui-monospace, "Cascadia Code", "Source Code Pro", monospace;
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 1.25rem; }
body {
  margin: 0;
  font-family: var(--font);
  font-size: 16px;
  line-height: 1.6;
  color: var(--text);
  background: var(--bg);
}
.layout { display: flex; min-height: 100vh; }
.sidebar {
  position: fixed; top: 0; left: 0;
  width: var(--sidebar-w); height: 100vh;
  overflow-y: auto;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 1.5rem 1rem 2rem;
  z-index: 100;
}
.sidebar-brand { font-weight: 700; font-size: 0.95rem; color: var(--accent-dark); margin-bottom: 0.25rem; }
.sidebar-sub { font-size: 0.78rem; color: var(--muted); margin-bottom: 1.25rem; line-height: 1.4; }
.sidebar nav ul { list-style: none; padding: 0; margin: 0; }
.sidebar nav li { margin-bottom: 2px; }
.sidebar nav a {
  display: block; padding: 0.45rem 0.65rem; border-radius: 6px;
  color: var(--text); text-decoration: none; font-size: 0.875rem;
  transition: background 0.15s;
}
.sidebar nav a:hover, .sidebar nav a:focus { background: var(--accent-light); color: var(--accent-dark); }
.sidebar nav .nav-h3 a { padding-left: 1.15rem; font-size: 0.82rem; color: var(--muted); }
.sidebar nav .nav-h4 a { padding-left: 1.65rem; font-size: 0.78rem; color: var(--muted); }
.main { margin-left: var(--sidebar-w); flex: 1; padding: 2rem 2.5rem 4rem; max-width: 960px; }
.hero {
  background: linear-gradient(135deg, var(--accent-dark) 0%, var(--accent) 100%);
  color: #fff; border-radius: var(--radius);
  padding: 2rem 2.25rem; margin-bottom: 2rem; box-shadow: var(--shadow);
}
.hero h1 { margin: 0 0 0.5rem; font-size: 1.75rem; font-weight: 700; line-height: 1.25; }
.hero p { margin: 0; opacity: 0.92; font-size: 1rem; max-width: 58ch; }
.meta-bar { display: flex; flex-wrap: wrap; gap: 0.75rem 1.5rem; margin-top: 1.25rem; font-size: 0.82rem; opacity: 0.88; }
.content-section { margin-bottom: 2rem; }
.content-section h2, .content-section h3, .content-section h4 {
  scroll-margin-top: 1.25rem;
}
.content-section h2 {
  margin: 2rem 0 0.75rem; font-size: 1.35rem; color: var(--accent-dark);
  padding-bottom: 0.35rem; border-bottom: 2px solid var(--accent-light);
}
.content-section h3 { margin: 1.5rem 0 0.6rem; font-size: 1.1rem; color: var(--accent-dark); }
.content-section h4 { margin: 1.25rem 0 0.5rem; font-size: 1rem; color: var(--text); }
.content-section p { margin: 0 0 0.85rem; }
.content-section ul, .content-section ol { margin: 0 0 1rem; padding-left: 1.5rem; }
.content-section li { margin-bottom: 0.35rem; }
.content-section hr {
  border: none; border-top: 1px solid var(--border); margin: 2rem 0;
}
.content-section table {
  width: 100%; border-collapse: collapse; font-size: 0.875rem;
  margin: 0.75rem 0 1.25rem; background: var(--surface);
  border: 1px solid var(--border); border-radius: 8px; overflow: hidden;
}
.content-section th, .content-section td {
  padding: 0.6rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border);
}
.content-section th { background: #f8fafc; font-weight: 600; color: var(--muted); font-size: 0.78rem; }
.content-section tr:last-child td { border-bottom: none; }
.content-section code {
  font-family: var(--mono); font-size: 0.88em;
  background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px;
}
.content-section a { color: var(--accent); }
.content-section strong { font-weight: 600; }
:target {
  animation: hash-highlight 2.2s ease-out;
}
@keyframes hash-highlight {
  0% { background-color: var(--accent-light); box-shadow: 0 0 0 4px var(--accent-light); }
  100% { background-color: transparent; box-shadow: none; }
}
h2:target, h3:target, h4:target {
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
  margin-left: -0.5rem;
}
@media print {
  .sidebar { display: none !important; }
  .main { margin-left: 0; max-width: none; padding: 0; }
}
@media (max-width: 860px) {
  .sidebar { position: static; width: 100%; height: auto; border-right: none; border-bottom: 1px solid var(--border); }
  .layout { flex-direction: column; }
  .main { margin-left: 0; padding: 1.25rem; }
}
"""

HASH_JS = """
(function () {
  function highlightHash() {
    var hash = window.location.hash;
    if (!hash || hash.length < 2) return;
    var el = document.getElementById(hash.slice(1));
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.classList.add('hash-flash');
    window.setTimeout(function () { el.classList.remove('hash-flash'); }, 2200);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', highlightHash);
  } else {
    highlightHash();
  }
  window.addEventListener('hashchange', highlightHash);
})();
"""


def _inline_md(text: str) -> str:
    """Negrita, código inline, links.

    Primero desescapa entidades HTML del Markdown (&gt;, &amp;, …)
    para no generar doble escape (&amp;gt;) en el HTML final.
    """
    text = html.unescape(text)
    parts: list[str] = []
    pos = 0
    pattern = re.compile(
        r"\*\*(.+?)\*\*|"
        r"`([^`]+)`|"
        r"\[([^\]]+)\]\(([^)]+)\)"
    )
    for m in pattern.finditer(text):
        parts.append(html.escape(text[pos : m.start()]))
        if m.group(1) is not None:
            parts.append(f"<strong>{html.escape(m.group(1))}</strong>")
        elif m.group(2) is not None:
            parts.append(f"<code>{html.escape(m.group(2))}</code>")
        else:
            label, url = m.group(3), m.group(4)
            if url.endswith(".md"):
                url = url[:-3]
            if url.startswith("../"):
                url = url[3:]
            parts.append(f'<a href="{html.escape(url, quote=True)}">{html.escape(label)}</a>')
        pos = m.end()
    parts.append(html.escape(text[pos:]))
    return "".join(parts)


def _parse_table_lines(lines: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.match(r"^[-:\s]+$", c) for c in cells):
            continue
        rows.append(cells)
    return rows


def _render_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    out = ["<table><thead><tr>"]
    for cell in rows[0]:
        out.append(f"<th>{_inline_md(cell)}</th>")
    out.append("</tr></thead><tbody>")
    for row in rows[1:]:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_inline_md(cell)}</td>")
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def _render_list(items: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    parts = [f"<{tag}>"]
    for item in items:
        parts.append(f"<li>{_inline_md(item)}</li>")
    parts.append(f"</{tag}>")
    return "".join(parts)


def parse_markdown(md: str, module: str) -> tuple[str, str, list[tuple[int, str, str]]]:
    """
    Devuelve (título documento, cuerpo HTML, entradas TOC).
    TOC: (level, id, label)
    """
    lines = md.splitlines()
    doc_title = "Manual de usuario"
    body_parts: list[str] = []
    toc: list[tuple[int, str, str]] = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        hm = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            hid = _heading_id(level, title, module)
            tag = f"h{min(level, 4)}"
            if level == 1:
                doc_title = title
            else:
                if level <= 2:
                    toc.append((level, hid, title))
                body_parts.append(
                    f'<{tag} id="{html.escape(hid, quote=True)}">{_inline_md(title)}</{tag}>'
                )
            i += 1
            continue

        if stripped == "---":
            body_parts.append("<hr>")
            i += 1
            continue

        if stripped.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            body_parts.append(_render_table(_parse_table_lines(table_lines)))
            continue

        if re.match(r"^[-*]\s+", stripped):
            items = []
            while i < len(lines):
                m = re.match(r"^[-*]\s+(.+)$", lines[i].strip())
                if not m:
                    break
                items.append(m.group(1))
                i += 1
            body_parts.append(_render_list(items, ordered=False))
            continue

        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines):
                m = re.match(r"^\d+\.\s+(.+)$", lines[i].strip())
                if not m:
                    break
                items.append(m.group(1))
                i += 1
            body_parts.append(_render_list(items, ordered=True))
            continue

        para_lines = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (
                not nxt
                or nxt == "---"
                or re.match(r"^#{1,4}\s+", nxt)
                or nxt.startswith("|")
                or re.match(r"^[-*]\s+", nxt)
                or re.match(r"^\d+\.\s+", nxt)
            ):
                break
            para_lines.append(nxt)
            i += 1
        body_parts.append(f"<p>{_inline_md(' '.join(para_lines))}</p>")

    # TOC extendido con h3/h4 de secciones con alias
    toc_extended: list[tuple[int, str, str]] = []
    for level, hid, label in toc:
        toc_extended.append((level, hid, label))
    # h3/h4 con alias
    alias_titles = MPR_ALIASES if module == "mpr" else STOCK_ALIASES
    for alias, title in alias_titles.items():
        if not any(t[1] == alias for t in toc_extended):
            # buscar en body si existe el id
            if f'id="{alias}"' in "".join(body_parts):
                lvl = 3 if alias not in {v for v in MPR_ALIASES.values()} else 2
                toc_extended.append((lvl, alias, title))

    # Re-parse headings h3/h4 para TOC sidebar
    toc_all: list[tuple[int, str, str]] = []
    for line in lines:
        hm = re.match(r"^(#{2,4})\s+(.+)$", line.strip())
        if hm:
            level = len(hm.group(1))
            title = hm.group(2).strip()
            hid = _heading_id(level, title, module)
            toc_all.append((level, hid, title))

    sidebar = _build_sidebar(toc_all)
    body = f'<div class="content-section">{"".join(body_parts)}</div>'
    return doc_title, sidebar, body


def _build_sidebar(toc: list[tuple[int, str, str]]) -> str:
    if not toc:
        return "<ul></ul>"
    parts = ["<ul>"]
    for level, hid, label in toc:
        cls = ""
        if level == 3:
            cls = ' class="nav-h3"'
        elif level >= 4:
            cls = ' class="nav-h4"'
        short = re.sub(r"^\d+(\.\d+)*\.\s*", "", label)
        parts.append(f'<li{cls}><a href="#{html.escape(hid, quote=True)}">{html.escape(short)}</a></li>')
    parts.append("</ul>")
    return "".join(parts)


def build_html(
    doc_title: str,
    sidebar_nav: str,
    body: str,
    brand: str,
    subtitle: str,
    module: str,
) -> str:
    today = date.today().strftime("%d/%m/%Y")
    url_hint = "/mpr/manual/" if module == "mpr" else "/stock/manual/"
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(doc_title)} — Synap</title>
  <meta name="description" content="{html.escape(subtitle)}">
  <style>{CSS}</style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-brand">{html.escape(brand)}</div>
      <div class="sidebar-sub">{html.escape(subtitle)}</div>
      <nav aria-label="Índice del manual">
        {sidebar_nav}
      </nav>
    </aside>
    <main class="main">
      <header class="hero">
        <h1>{html.escape(doc_title)}</h1>
        <p>Manual de usuario en Synap. Navegue por el índice o use enlaces directos con ancla (<code>#seccion</code>).</p>
        <div class="meta-bar">
          <span>Generado: {today}</span>
          <span>URL app: {html.escape(url_hint)}</span>
          <span>Fuente: Markdown en docs/</span>
        </div>
      </header>
      {body}
    </main>
  </div>
  <script>{HASH_JS}</script>
</body>
</html>
"""


def generate_one(
    md_path: Path,
    out_runtime: Path,
    out_docs: Path,
    module: str,
    brand: str,
    subtitle: str,
) -> None:
    md = md_path.read_text(encoding="utf-8")
    doc_title, sidebar, body = parse_markdown(md, module)
    html_out = build_html(doc_title, sidebar, body, brand, subtitle, module)
    out_runtime.parent.mkdir(parents=True, exist_ok=True)
    out_docs.parent.mkdir(parents=True, exist_ok=True)
    out_runtime.write_text(html_out, encoding="utf-8")
    out_docs.write_text(html_out, encoding="utf-8")
    print(f"OK {out_runtime}")
    print(f"OK {out_docs}")


def main() -> None:
    generate_one(
        ROOT / "docs/mpr/MANUAL_USUARIO_MPR.md",
        ROOT / "mpr/static/mpr/manuales/manual_usuario_mpr.html",
        ROOT / "docs/mpr/manual_usuario_mpr.html",
        "mpr",
        "Synap · MPR",
        "Manual de usuario — Producción",
    )
    generate_one(
        ROOT / "docs/stock/MANUAL_USUARIO_STOCK.md",
        ROOT / "stock/static/stock/manuales/manual_usuario_stock.html",
        ROOT / "docs/stock/manual_usuario_stock.html",
        "stock",
        "Synap · Stock",
        "Manual de usuario — Inventario y movimientos",
    )


if __name__ == "__main__":
    main()
