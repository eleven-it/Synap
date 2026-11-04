/**
 * Informes BestSox Marca/SuperArt (producción, compras) — jerarquía + columnas mensuales.
 */
(function () {
  "use strict";

  const SLUGS = new Set([
    "produccion-marca-superart",
    "compras-marca-superart",
  ]);

  const root = document.getElementById("dashboard-root");
  const reportSlug = root?.dataset?.reportSlug || "";
  if (!SLUGS.has(reportSlug)) return;

  const wrap = document.getElementById("bmx-table-wrap");
  const summary = document.getElementById("bmx-filters-summary");
  const kpiPrimary = document.getElementById("bmx-kpi-primary");
  const kpiSecondary = document.getElementById("bmx-kpi-secondary");

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function metricPrefixes() {
    if (reportSlug === "compras-marca-superart") {
      return ["Packs", "Prendas", "Docenas"];
    }
    return ["Pares", "Docenas"];
  }

  function flattenTree(nodes, depth) {
    const rows = [];
    (nodes || []).forEach((n) => {
      rows.push({ node: n, depth: depth || 0 });
      if (n.children && n.children.length) {
        rows.push(...flattenTree(n.children, (depth || 0) + 1));
      }
    });
    return rows;
  }

  function labelForNode(n) {
    if (n.tipo === "marca") return n.nombre_marca || "Marca";
    if (n.tipo === "superart") return n.nombre_superart || "SuperArt";
    return n.nombre_articulo || n.codigo_articulo || "Artículo";
  }

  function renderTable(jerarquia, totals) {
    if (!wrap) return;
    if (!jerarquia || !jerarquia.length) {
      wrap.innerHTML = '<p class="text-xs text-slate-500">Sin datos para el período.</p>';
      return;
    }
    const sample = jerarquia[0].metrics || {};
    const monthKeys = Object.keys(sample).filter((k) => k.includes("_") && !k.endsWith("_Total"));
    const prefixes = metricPrefixes();
    let html = '<div class="overflow-x-auto"><table class="min-w-full text-xs">';
    html += "<thead><tr>";
    html += '<th class="text-left p-2">Nivel</th><th class="text-left p-2">Descripción</th>';
    prefixes.forEach((pref) => {
      monthKeys
        .filter((k) => k.startsWith(pref + "_"))
        .forEach((k) => {
          html += `<th class="text-right p-2">${esc(k.replace(pref + "_", pref + " "))}</th>`;
        });
    });
    html += "</tr></thead><tbody>";
    flattenTree(jerarquia, 0).forEach(({ node, depth }) => {
      html += "<tr>";
      html += `<td class="p-2">${esc(node.tipo || "")}</td>`;
      html += `<td class="p-2" style="padding-left:${8 + depth * 14}px">${esc(labelForNode(node))}</td>`;
      prefixes.forEach((pref) => {
        monthKeys
          .filter((k) => k.startsWith(pref + "_"))
          .forEach((k) => {
            const v = (node.metrics || {})[k];
            html += `<td class="p-2 text-right">${v != null ? esc(Number(v).toLocaleString("es-AR")) : "—"}</td>`;
          });
      });
      html += "</tr>";
    });
    html += "</tbody></table></div>";
    wrap.innerHTML = html;

    if (kpiPrimary && totals) {
      if (reportSlug === "compras-marca-superart") {
        kpiPrimary.textContent = Number(totals.packs_total || 0).toLocaleString("es-AR");
        if (kpiSecondary) {
          kpiSecondary.textContent = Number(totals.docenas_total || 0).toLocaleString("es-AR");
        }
      } else {
        kpiPrimary.textContent = Number(totals.pares_total || 0).toLocaleString("es-AR");
        if (kpiSecondary) {
          kpiSecondary.textContent = Number(totals.docenas_total || 0).toLocaleString("es-AR");
        }
      }
    }
  }

  function processData(payload) {
    const meta = payload.meta || {};
    const extra = meta.extra || {};
    const tabs = extra.tabs || {};
    const jerarquia = tabs.marca_superart_jerarquia || [];
    renderTable(jerarquia, payload.totals || {});
    const fa = meta.filters_applied || extra.filtros || {};
    if (summary && fa.desde_iso && fa.hasta_iso) {
      summary.textContent = `Período: ${fa.desde_iso} — ${fa.hasta_iso}`;
    }
  }

  window.bestsoxMarcaInformeHandler = { processData };
})();
