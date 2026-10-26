/**
 * Informe Pedidos pendientes (Producción): tabla con stock por depósito y MPR.
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "pedidos-pendientes-produccion") {
    return;
  }

  const NUMBER_FORMAT = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

  function formatNumber(value) {
    if (value === null || value === undefined || isNaN(value)) return "0";
    return NUMBER_FORMAT.format(value);
  }

  function escHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderTable(response) {
    const wrap = document.getElementById("ppp-table-wrap");
    const summary = document.getElementById("ppp-filters-summary");
    if (!wrap) return;

    const articulos = response.data || [];
    const extra = (response.meta && response.meta.extra) || {};
    const columnas = extra.columnas_stock || {};
    const otros = columnas.otros || [];
    const totals = response.totals || {};

    if (summary) {
      const fa = (response.meta && response.meta.filters_applied) || {};
      const parts = [];
      if (fa.criterio_pendiente) parts.push("Criterio: " + fa.criterio_pendiente);
      if (fa.clientes_incluir && fa.clientes_incluir.length)
        parts.push(fa.clientes_incluir.length + " cliente(s)");
      summary.textContent = parts.length ? parts.join(" · ") : "";
    }

    const kpiArt = document.getElementById("ppp-kpi-articulos");
    const kpiPend = document.getElementById("ppp-kpi-pendiente");
    if (kpiArt) kpiArt.textContent = formatNumber(totals.total_articulos || articulos.length);
    if (kpiPend) kpiPend.textContent = formatNumber(totals.total_pendiente_qty || 0);

    let head =
      "<tr>" +
      "<th>Código</th><th>Artículo</th><th>Marca</th><th>Cant. pendiente</th>" +
      "<th>Stock terminado</th><th>Stock producción</th>";
    otros.forEach(function (c) {
      head += "<th>" + escHtml(c.nombre || c.key) + "</th>";
    });
    head +=
      "<th>Stock total</th>" +
      "<th>MPR demanda</th><th>MPR a fabricar</th><th>Brecha</th>" +
      "</tr>";

    let body = "";
    articulos.forEach(function (row) {
      body += "<tr>";
      body += "<td>" + escHtml(row.codigo) + "</td>";
      body += "<td>" + escHtml(row.articulo) + "</td>";
      body += "<td>" + escHtml(row.marca) + "</td>";
      body += '<td class="text-right">' + formatNumber(row.pendiente_qty) + "</td>";
      body += '<td class="text-right">' + formatNumber(row.stock_terminado) + "</td>";
      body += '<td class="text-right">' + formatNumber(row.stock_produccion) + "</td>";
      otros.forEach(function (c) {
        body += '<td class="text-right">' + formatNumber(row[c.key]) + "</td>";
      });
      body += '<td class="text-right font-semibold">' + formatNumber(row.stock_total) + "</td>";
      body +=
        '<td class="text-right">' +
        formatNumber(row.mpr_demanda_pedido) +
        "</td>";
      body +=
        '<td class="text-right">' +
        formatNumber(row.mpr_cantidad_a_fabricar) +
        "</td>";
      body +=
        '<td class="text-right">' +
        formatNumber(row.mpr_brecha_vs_pendiente) +
        "</td>";
      body += "</tr>";
    });

    wrap.innerHTML =
      '<div class="overflow-x-auto"><table class="w-full text-xs text-left border-collapse">' +
      '<thead class="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase tracking-wide">' +
      head +
      "</thead><tbody>" +
      (body || '<tr><td colspan="20" class="py-6 text-center text-slate-500">Sin datos</td></tr>') +
      "</tbody></table></div>";
  }

  document.addEventListener("reportDataLoaded", function (event) {
    if (!event.detail || event.detail.slug !== "pedidos-pendientes-produccion") return;
    renderTable(event.detail.response || {});
  });

  window.pedidosPendientesProduccionHandler = { renderTable };
})();
