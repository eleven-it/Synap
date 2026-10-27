/**
 * Informe Pedidos pendientes (Producción): tabla con stock, disponible/backorder y MPR.
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

  const MONEY_FORMAT = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function formatNumber(value) {
    if (value === null || value === undefined || isNaN(value)) return "0";
    return NUMBER_FORMAT.format(value);
  }

  function formatMoney(value) {
    if (value === null || value === undefined || isNaN(value)) return "0,00";
    return MONEY_FORMAT.format(value);
  }

  function escHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  const COLUMNS = [
    { key: "codigo", label: "Código", align: "left" },
    { key: "cod_manual", label: "Cod. manual", align: "left" },
    { key: "articulo", label: "Artículo", align: "left" },
    { key: "marca", label: "Marca", align: "left" },
    { key: "unidad_base", label: "Unidad base", align: "left" },
    { key: "pendiente_qty", label: "Pedido pendiente", align: "right", fmt: formatNumber },
    { key: "stock_terminado", label: "Stock terminado", align: "right", fmt: formatNumber },
    { key: "stock_produccion", label: "Stock producción", align: "right", fmt: formatNumber },
    { key: "disponible", label: "Disponible", align: "right", fmt: formatNumber },
    { key: "backorder", label: "Backorder", align: "right", fmt: formatNumber },
    { key: "importe_pendiente", label: "Importe pendiente", align: "right", fmt: formatMoney },
    { key: "mpr_demanda_pedido", label: "MPR demanda", align: "right", fmt: formatNumber },
    { key: "mpr_cantidad_a_fabricar", label: "MPR a fabricar", align: "right", fmt: formatNumber },
    { key: "mpr_brecha_vs_pendiente", label: "Brecha", align: "right", fmt: formatNumber },
  ];

  const TOTAL_KEYS = {
    pendiente_qty: "total_pendiente_qty",
    stock_terminado: "total_stock_terminado",
    stock_produccion: "total_stock_produccion",
    disponible: "total_disponible",
    backorder: "total_backorder",
    importe_pendiente: "total_importe_pendiente",
    mpr_demanda_pedido: "total_mpr_demanda_pedido",
    mpr_cantidad_a_fabricar: "total_mpr_cantidad_a_fabricar",
    mpr_brecha_vs_pendiente: "total_mpr_brecha_vs_pendiente",
  };

  function renderTable(response) {
    const wrap = document.getElementById("ppp-table-wrap");
    const summary = document.getElementById("ppp-filters-summary");
    if (!wrap) return;

    const articulos = response.data || [];
    const totals = response.totals || {};

    if (summary) {
      const fa = (response.meta && response.meta.filters_applied) || {};
      const parts = [];
      if (fa.busqueda) parts.push("Búsqueda: " + fa.busqueda);
      if (fa.clientes_incluir && fa.clientes_incluir.length)
        parts.push(fa.clientes_incluir.length + " cliente(s)");
      if (fa.vendedores_incluir && fa.vendedores_incluir.length)
        parts.push(fa.vendedores_incluir.length + " vendedor(es)");
      summary.textContent = parts.length ? parts.join(" · ") : "";
    }

    const kpiArt = document.getElementById("ppp-kpi-articulos");
    const kpiPend = document.getElementById("ppp-kpi-pendiente");
    if (kpiArt) kpiArt.textContent = formatNumber(totals.row_count || articulos.length);
    if (kpiPend) kpiPend.textContent = formatNumber(totals.total_pendiente_qty || 0);

    let head = "<tr>";
    COLUMNS.forEach(function (col) {
      head += '<th class="' + (col.align === "right" ? "text-right" : "") + '">' + escHtml(col.label) + "</th>";
    });
    head += "</tr>";

    let body = "";
    articulos.forEach(function (row) {
      body += "<tr>";
      COLUMNS.forEach(function (col) {
        const raw = row[col.key];
        const val = col.fmt ? col.fmt(raw) : escHtml(raw);
        body += '<td class="' + (col.align === "right" ? "text-right" : "") + '">' + val + "</td>";
      });
      body += "</tr>";
    });

    if (articulos.length) {
      body += '<tr class="bg-slate-100 dark:bg-slate-800 font-semibold">';
      COLUMNS.forEach(function (col, idx) {
        if (idx === 0) {
          body += '<td colspan="5">Totales (' + formatNumber(totals.row_count || articulos.length) + " filas)</td>";
        } else if (TOTAL_KEYS[col.key]) {
          const tkey = TOTAL_KEYS[col.key];
          const fmt = col.fmt || formatNumber;
          body += '<td class="text-right">' + fmt(totals[tkey]) + "</td>";
        } else {
          body += "<td></td>";
        }
      });
      body += "</tr>";
    }

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
