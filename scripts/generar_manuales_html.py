#!/usr/bin/env python3
"""
Genera HTML navegable desde los manuales Markdown de MPR, Stock y Ventas (ecom).
Sin dependencias externas. Fuente: docs/mpr|stock|ecom/MANUAL_USUARIO_*.md

El HTML de usuario final usa branding administraNET (colores website, Plus Jakarta Sans)
y el logo del login (`Logo_Signo_administraNET.png` → logo-administranet.png por módulo),
embebido en base64 para funcionar vía /mpr/manual/, /stock/manual/, /ecom/manual/ o docs/.
"""
from __future__ import annotations

import base64
import html
import re
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

MPR_ALIASES: dict[str, str] = {
    "acceso": "1. Acceso al módulo",
    "flujo-diario": "2. Flujo del día a día",
    "tablero-produccion": "3. Tablero de producción",
    "tablero": "3. Tablero de producción",
    "parte-produccion": "4. Parte de producción",
    "parte-supervisor": "4.1 Parte de producción (supervisor)",
    "carga-movil-operario": "4.2 Carga de producción (operario)",
    "partes-pendientes": "4.3 Partes pendientes (aprobación)",
    "control-calidad": "5. Control de calidad",
    "armado": "6. Armado",
    "imputacion-pedido": "7. Imputación de pedido",
    "configuracion": "8. Configuración (orden recomendado)",
    "config-planta": "8. Configuración (orden recomendado)",
    "config-lineas": "8.1 Líneas",
    "config-maquinas": "8.2 Máquinas",
    "asignar-articulo-maquina": "Asignar artículo a máquina",
    "depositos": "8.3 Config. Depósitos",
    "operarios": "8.4 Operarios",
    "operarios-usuarios": "8.5 Operarios y usuarios",
    "linea-habitual": "8.6 Línea habitual (operarios)",
    "turnos": "8.7 Turnos de producción",
    "planificacion-turnos": "8.8 Planificación de turnos",
    "resumen": "9. Resumen rápido",
    "mensajes-mpr": "10. Problemas frecuentes",
    "problemas-frecuentes": "10. Problemas frecuentes",
    "migracion-best": "11. Migración BEST (cutover)",
    "articulos-fabricados": "Artículos fabricados (PP BEST → Admin)",
    "packs-sin-receta": "Modo Pack y packs sin receta",
}

STOCK_ALIASES: dict[str, str] = {
    "acceso-stock": "1. Acceso",
    "inventario-por-etapa": "2. Inventario por etapa",
    "alta-movimiento": "3. Alta de movimiento",
    "mensajes-stock": "4. Mensajes frecuentes",
}

ECOM_ALIASES: dict[str, str] = {
    "acceso": "1. Acceso al módulo",
    "presupuestos": "2. Presupuestos",
    "pedidos": "3. Pedidos (hub)",
    "pedidos-hub": "3. Pedidos (hub)",
    "pedido-masivo": "4. Pedido masivo por sucursales",
    "vendedor-cliente-marca": "5. Vendedor · Cliente · Marca",
    "actualizacion-precios": "6. Actualización de precios",
    "precios-terminados": "6. Actualización de precios",
    "evolucion-precios": "7. Evolución de precios",
    "ajustes-ventas": "8. Ajustes de ventas",
    "asignacion-vendedor": "9. Asignación vendedor",
    "objetivos-venta": "10. Objetivos de venta",
}

ALIASES_BY_MODULE: dict[str, dict[str, str]] = {
    "mpr": MPR_ALIASES,
    "stock": STOCK_ALIASES,
    "ecom": ECOM_ALIASES,
}

# alias -> título exacto del encabezado en el MD
# Varios alias pueden apuntar al mismo título (anclas alternativas).


def slug_es(text: str) -> str:
    """Slug en español: minúsculas, sin acentos, guiones."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def _aliases_for_title(title: str, module: str) -> list[str]:
    aliases = ALIASES_BY_MODULE.get(module, {})
    t = title.strip()
    return [a for a, tit in aliases.items() if tit.strip() == t]


def _heading_id(level: int, title: str, module: str) -> str:
    als = _aliases_for_title(title, module)
    if als:
        return als[0]
    return slug_es(title)


def _extra_anchor_spans(title: str, module: str, primary_id: str) -> str:
    extras = [a for a in _aliases_for_title(title, module) if a != primary_id]
    if not extras:
        return ""
    return "".join(
        f'<span id="{html.escape(a, quote=True)}" class="anchor-alias" aria-hidden="true"></span>'
        for a in extras
    )


MODULE_CONFIG: dict[str, dict[str, str | Path]] = {
    "mpr": {
        "module_label": "Producción",
        "static_logo": "/static/mpr/manuales/logo-administranet.png",
        "logo_path": ROOT / "mpr/static/mpr/manuales/logo-administranet.png",
    },
    "stock": {
        "module_label": "Stock",
        "static_logo": "/static/stock/manuales/logo-administranet.png",
        "logo_path": ROOT / "stock/static/stock/manuales/logo-administranet.png",
    },
    "ecom": {
        "module_label": "Ventas",
        "static_logo": "/static/ecom/manuales/logo-administranet.png",
        "logo_path": ROOT / "ecom/static/ecom/manuales/logo-administranet.png",
    },
}

CSS = """
:root {
  --bg: #F5F6F8;
  --surface: #FFFFFF;
  --border: #E2E8F0;
  --text: #202030;
  --muted: #64748B;
  --accent: #3D9B9B;
  --accent-light: rgba(61, 155, 155, 0.12);
  --accent-dark: #1E3A4C;
  --hero-mid: #2A4A5C;
  --terracotta: #C06050;
  --warn: #b45309;
  --sidebar-w: 280px;
  --radius: 10px;
  --shadow: 0 1px 3px rgba(32, 32, 48, 0.08), 0 4px 16px rgba(32, 32, 48, 0.04);
  --font: "Plus Jakarta Sans", system-ui, -apple-system, sans-serif;
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
.sidebar-logo {
  display: block;
  height: 88px;
  width: 88px;
  max-width: 100%;
  object-fit: contain;
  margin: 0 0 1rem;
  border-radius: 14px;
}
.sidebar-brand-block {
  margin-bottom: 1.35rem;
  padding-bottom: 1.15rem;
  border-bottom: 1px solid var(--border);
}
.sidebar-brand {
  font-weight: 700; font-size: 1.2rem; letter-spacing: -0.02em;
  color: var(--text); margin: 0 0 0.2rem; line-height: 1.2;
}
.sidebar-sub {
  font-size: 0.88rem; font-weight: 600; color: var(--accent);
  margin: 0 0 0.45rem; line-height: 1.35;
}
.sidebar-meta { font-size: 0.72rem; color: var(--muted); margin: 0; }
.sidebar nav ul { list-style: none; padding: 0; margin: 0; }
.sidebar nav li { margin-bottom: 2px; }
.sidebar nav a {
  display: block; padding: 0.45rem 0.65rem; border-radius: 6px;
  color: var(--text); text-decoration: none; font-size: 0.875rem;
  transition: background 0.15s;
}
.sidebar nav a:hover, .sidebar nav a:focus { background: var(--accent-light); color: var(--accent); }
.sidebar nav .nav-h3 a { padding-left: 1.15rem; font-size: 0.82rem; color: var(--muted); }
.sidebar nav .nav-h4 a { padding-left: 1.65rem; font-size: 0.78rem; color: var(--muted); }
.main { margin-left: var(--sidebar-w); flex: 1; padding: 2rem 2.5rem 4rem; max-width: 960px; }
.hero {
  background: linear-gradient(135deg, var(--accent-dark) 0%, var(--hero-mid) 52%, var(--accent) 100%);
  color: #fff; border-radius: var(--radius);
  padding: 2rem 2.25rem; margin-bottom: 2rem; box-shadow: var(--shadow);
}
.hero h1 { margin: 0; font-size: 1.75rem; font-weight: 700; line-height: 1.25; }
.meta-bar {
  display: flex; flex-wrap: wrap; gap: 0.75rem 1.5rem;
  margin-top: 1.25rem; font-size: 0.82rem; opacity: 0.9;
}
.meta-bar span + span::before { content: "·"; margin-right: 0.75rem; opacity: 0.65; }
.content-section { margin-bottom: 2rem; }
.content-section h2, .content-section h3, .content-section h4 {
  scroll-margin-top: 1.25rem;
}
.content-section h2 {
  margin: 2rem 0 0.75rem; font-size: 1.35rem; color: var(--text);
  padding-bottom: 0.35rem; border-bottom: 2px solid var(--accent);
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
.content-section a { color: var(--accent); text-decoration-color: rgba(61, 155, 155, 0.45); }
.content-section a:hover { color: var(--accent-dark); text-decoration-color: var(--accent); }
.content-section strong { font-weight: 600; }
.anchor-alias {
  position: relative; top: -0.5rem; display: block;
  height: 0; width: 0; overflow: hidden;
}
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
                extras = _extra_anchor_spans(title, module, hid)
                body_parts.append(
                    f'{extras}<{tag} id="{html.escape(hid, quote=True)}">{_inline_md(title)}</{tag}>'
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
    alias_titles = ALIASES_BY_MODULE.get(module, {})
    for alias, title in alias_titles.items():
        if not any(t[1] == alias for t in toc_extended):
            # buscar en body si existe el id
            if f'id="{alias}"' in "".join(body_parts):
                lvl = 3 if alias not in set(alias_titles.values()) else 2
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


def _logo_data_uri(logo_path: Path) -> str:
    if not logo_path.is_file():
        raise FileNotFoundError(f"No se encontró el logo del manual: {logo_path}")
    encoded = base64.standard_b64encode(logo_path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_html(
    doc_title: str,
    sidebar_nav: str,
    body: str,
    module: str,
) -> str:
    cfg = MODULE_CONFIG[module]
    module_label = str(cfg["module_label"])
    static_logo = str(cfg["static_logo"])
    logo_path = Path(cfg["logo_path"])
    logo_src = _logo_data_uri(logo_path)
    today = date.today().strftime("%d/%m/%Y")
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(doc_title)} — administraNET</title>
  <meta name="description" content="Manual de usuario {html.escape(module_label)} — administraNET">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>{CSS}</style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <img
        class="sidebar-logo"
        src="{logo_src}"
        data-static-src="{html.escape(static_logo, quote=True)}"
        alt="administraNET"
        width="88"
        height="88"
      >
      <div class="sidebar-brand-block">
        <div class="sidebar-brand">administraNET</div>
        <div class="sidebar-sub">{html.escape(module_label)}</div>
        <div class="sidebar-meta">Manual de usuario · Synap</div>
      </div>
      <nav aria-label="Índice del manual">
        {sidebar_nav}
      </nav>
    </aside>
    <main class="main">
      <header class="hero">
        <h1>{html.escape(doc_title)}</h1>
        <div class="meta-bar">
          <span>Actualizado: {today}</span>
          <span>Synap</span>
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
) -> None:
    md = md_path.read_text(encoding="utf-8")
    doc_title, sidebar, body = parse_markdown(md, module)
    html_out = build_html(doc_title, sidebar, body, module)
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
    )
    generate_one(
        ROOT / "docs/stock/MANUAL_USUARIO_STOCK.md",
        ROOT / "stock/static/stock/manuales/manual_usuario_stock.html",
        ROOT / "docs/stock/manual_usuario_stock.html",
        "stock",
    )
    generate_one(
        ROOT / "docs/ecom/MANUAL_USUARIO_VENTAS.md",
        ROOT / "ecom/static/ecom/manuales/manual_usuario_ventas.html",
        ROOT / "docs/ecom/manual_usuario_ventas.html",
        "ecom",
    )


if __name__ == "__main__":
    main()
