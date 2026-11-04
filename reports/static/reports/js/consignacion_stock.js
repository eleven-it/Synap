/**
 * Informe Stock en consignación (cliente → marca → superart → artículo + remitos).
 */
(function () {
  "use strict";

  const root = document.getElementById("dashboard-root");
  const reportSlug = root?.dataset?.reportSlug || "";
  if (reportSlug !== "consignacion-stock") return;

  const wrap = document.getElementById("csg-table-wrap");
  const remWrap = document.getElementById("csg-remitos-wrap");
  const summary = document.getElementById("csg-filters-summary");

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderJerarquia(tree) {
    if (!wrap) return;
    if (!tree || !tree.length) {
      wrap.innerHTML = '<p class="text-xs text-slate-500">Sin saldo en consignación.</p>';
      return;
    }
    let html = '<table class="min-w-full text-xs"><thead><tr>';
    html +=
      '<th>Cliente</th><th>Marca</th><th>SuperArt</th><th>Artículo</th><th>Packs</th><th>Prendas</th><th>Docenas</th></tr></thead><tbody>';
    tree.forEach((cli) => {
      (cli.children || []).forEach((marca) => {
        (marca.children || []).forEach((sa) => {
          (sa.children || []).forEach((art) => {
            html += "<tr>";
            html += `<td>${esc(cli.nombre_cliente)}</td>`;
            html += `<td>${esc(marca.nombre_marca)}</td>`;
            html += `<td>${esc(sa.nombre_superart)}</td>`;
            html += `<td>${esc(art.nombre_articulo)}</td>`;
            html += `<td class="text-right">${esc(art.packs_saldo)}</td>`;
            html += `<td class="text-right">${esc(art.prendas_saldo)}</td>`;
            html += `<td class="text-right">${esc(art.docenas_saldo)}</td>`;
            html += "</tr>";
          });
        });
      });
    });
    html += "</tbody></table>";
    wrap.innerHTML = html;
  }

  function renderRemitos(remitos) {
    if (!remWrap) return;
    if (!remitos || !remitos.length) {
      remWrap.innerHTML = '<p class="text-xs text-slate-500">Sin remitos en el período.</p>';
      return;
    }
    let html = '<table class="min-w-full text-xs"><thead><tr>';
    html +=
      '<th>Número</th><th>Fecha</th><th>Cliente</th><th>Criterio</th><th>Remitido</th><th>Facturado</th><th>Devuelto</th><th>Saldo</th></tr></thead><tbody>';
    remitos.forEach((r) => {
      html += "<tr>";
      html += `<td>${esc(r.NroComprobante || r.nro_comprobante)}</td>`;
      html += `<td>${esc(r.Fecha || r.fecha)}</td>`;
      html += `<td>${esc(r.nombre_cliente)}</td>`;
      html += `<td>${esc(r.criterio_origen)}</td>`;
      html += `<td class="text-right">${esc(r.packs_remitidos)}</td>`;
      html += `<td class="text-right">${esc(r.packs_facturados)}</td>`;
      html += `<td class="text-right">${esc(r.packs_devueltos)}</td>`;
      html += `<td class="text-right">${esc(r.packs_saldo)}</td>`;
      html += "</tr>";
    });
    html += "</tbody></table>";
    remWrap.innerHTML = html;
  }

  function processData(payload) {
    const meta = payload.meta || {};
    const extra = meta.extra || {};
    const tabs = extra.tabs || {};
    renderJerarquia(tabs.consignacion_jerarquia || []);
    renderRemitos(tabs.remitos || []);
    const fa = meta.filters_applied || extra.filtros || {};
    if (summary) {
      summary.textContent = `Remitos ${fa.desde_iso || ""} — ${fa.hasta_iso || ""} · corte ${fa.corte_facturas || ""}`;
    }
    const kpi = document.getElementById("csg-kpi-packs");
    if (kpi && payload.totals) {
      kpi.textContent = Number(payload.totals.packs_saldo || 0).toLocaleString("es-AR");
    }
  }

  window.consignacionStockHandler = { processData };
})();
