/**
 * Informe Pedidos pendientes (Producción): tabla, KPIs y ordenamiento.
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "pedidos-pendientes-produccion") {
    return;
  }

  const UNIT_FORMAT = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

  const MONEY_FORMAT = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const FOOTER_NOTA =
    "Stock actual global: depósitos activos con Suma stock=Si. Disponible = terminado − pendiente. " +
    "Backorder = pendiente sin cobertura de terminado. Producción se muestra aparte. " +
    "Importe neto sin IVA ni descuento de cabecera.";

  const COLUMNS = [
    { key: "codigo", label: "Código", align: "left", sortable: true, type: "text" },
    { key: "cod_manual", label: "Cod. manual", align: "left", sortable: true, type: "text" },
    { key: "articulo", label: "Artículo", align: "left", sortable: true, type: "text" },
    { key: "marca", label: "Marca", align: "left", sortable: true, type: "text" },
    { key: "unidad_base", label: "Unidad base", align: "left", sortable: true, type: "text" },
    { key: "pendiente_qty", label: "Pedido pendiente", align: "right", sortable: true, type: "unit" },
    { key: "stock_terminado", label: "Stock terminado", align: "right", sortable: true, type: "unit" },
    { key: "stock_produccion", label: "Stock producción", align: "right", sortable: true, type: "unit" },
    { key: "disponible", label: "Disponible", align: "right", sortable: true, type: "unit", cellClass: "ppp-disponible" },
    { key: "backorder", label: "Backorder", align: "right", sortable: true, type: "unit", cellClass: "ppp-backorder" },
    { key: "importe_pendiente", label: "Importe pendiente", align: "right", sortable: true, type: "money" },
    { key: "mpr_demanda_pedido", label: "MPR demanda", align: "right", sortable: true, type: "unit" },
    { key: "mpr_cantidad_a_fabricar", label: "MPR a fabricar", align: "right", sortable: true, type: "unit" },
    { key: "mpr_brecha_vs_pendiente", label: "Brecha", align: "right", sortable: true, type: "unit", cellClass: "ppp-brecha" },
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
  };

  let lastResponse = null;
  let sortKey = "pendiente_qty";
  let sortDir = "desc";

  function formatUnit(value) {
    if (value === null || value === undefined || value === "") return "0";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return UNIT_FORMAT.format(n);
  }

  function formatMoney(value) {
    if (value === null || value === undefined || value === "") return MONEY_FORMAT.format(0);
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return MONEY_FORMAT.format(n);
  }

  function escHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function compareRows(a, b, key, type) {
    const va = a[key];
    const vb = b[key];
    if (type === "text") {
      return String(va || "").localeCompare(String(vb || ""), "es", { sensitivity: "base" });
    }
    const na = Number(va) || 0;
    const nb = Number(vb) || 0;
    return na - nb;
  }

  function sortedArticulos(articulos) {
    const col = COLUMNS.find((c) => c.key === sortKey) || COLUMNS[5];
    const dir = sortDir === "asc" ? 1 : -1;
    return articulos.slice().sort((a, b) => compareRows(a, b, col.key, col.type) * dir);
  }

  function cellValue(col, row) {
    const raw = row[col.key];
    if (col.type === "money") return formatMoney(raw);
    if (col.type === "unit") return formatUnit(raw);
    return escHtml(raw);
  }

  function cellExtraClass(col, row) {
    if (col.key === "disponible" && Number(row.disponible) < 0) {
      return " text-red-600 dark:text-red-400 font-semibold";
    }
    if (col.key === "backorder" && Number(row.backorder) > 0) {
      return " bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 font-semibold";
    }
    if (col.key === "mpr_brecha_vs_pendiente") {
      const n = Number(row.mpr_brecha_vs_pendiente);
      if (n < 0) return " text-red-600 dark:text-red-400";
      if (n > 0) return " text-emerald-700 dark:text-emerald-400";
    }
    return "";
  }

  function updateKpis(totals) {
    const set = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };
    set("ppp-kpi-pendiente", formatUnit(totals.total_pendiente_qty));
    set("ppp-kpi-importe", formatMoney(totals.total_importe_pendiente));
    set("ppp-kpi-backorder", formatUnit(totals.total_backorder));
    const nBo = totals.articulos_con_backorder ?? 0;
    const nAll = totals.row_count ?? totals.total_articulos ?? 0;
    set("ppp-kpi-backorder-art", nBo + " de " + nAll);
    set("ppp-kpi-stock-term", formatUnit(totals.total_stock_terminado));
    set("ppp-kpi-mpr-fabricar", formatUnit(totals.total_mpr_cantidad_a_fabricar));
  }

  function bindSortHandlers(wrap) {
    wrap.querySelectorAll("th[data-sort-key]").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.getAttribute("data-sort-key");
        if (sortKey === key) {
          sortDir = sortDir === "asc" ? "desc" : "asc";
        } else {
          sortKey = key;
          sortDir = key === "pendiente_qty" ? "desc" : "asc";
        }
        if (lastResponse) renderTable(lastResponse);
      });
    });
  }

  function renderTable(response) {
    const wrap = document.getElementById("ppp-table-wrap");
    const summary = document.getElementById("ppp-filters-summary");
    if (!wrap) return;

    lastResponse = response;
    const articulos = sortedArticulos(response.data || []);
    const totals = response.totals || {};
    const footerNota =
      (response.meta && response.meta.extra && response.meta.extra.footer_nota) || FOOTER_NOTA;

    if (summary) {
      const fa = (response.meta && response.meta.filters_applied) || {};
      const parts = [];
      if (fa.busqueda) parts.push("Búsqueda: " + fa.busqueda);
      if (fa.clientes_incluir && fa.clientes_incluir.length)
        parts.push(fa.clientes_incluir.length + " cliente(s)");
      summary.textContent = parts.length ? parts.join(" · ") : "";
    }

    updateKpis(totals);

    const n = totals.row_count || articulos.length;
    let head = "<tr>";
    COLUMNS.forEach(function (col) {
      const arrow = sortKey === col.key ? (sortDir === "asc" ? " ▲" : " ▼") : "";
      head +=
        '<th class="ppp-sort-th cursor-pointer select-none ' +
        (col.align === "right" ? "text-right" : "") +
        '" data-sort-key="' +
        escHtml(col.key) +
        '">' +
        escHtml(col.label) +
        arrow +
        "</th>";
    });
    head += "</tr>";

    let body = "";
    articulos.forEach(function (row) {
      body += "<tr>";
      COLUMNS.forEach(function (col) {
        body +=
          '<td class="' +
          (col.align === "right" ? "text-right " : "") +
          (col.cellClass || "") +
          cellExtraClass(col, row) +
          '">' +
          cellValue(col, row) +
          "</td>";
      });
      body += "</tr>";
    });

    if (articulos.length) {
      body += '<tr class="bg-slate-100 dark:bg-slate-800 font-semibold">';
      COLUMNS.forEach(function (col, idx) {
        if (idx === 0) {
          body += '<td colspan="5">TOTALES</td>';
          return;
        }
        if (idx < 5) return;
        if (col.key === "mpr_brecha_vs_pendiente") {
          body += '<td class="text-right"></td>';
          return;
        }
        if (TOTAL_KEYS[col.key]) {
          const tkey = TOTAL_KEYS[col.key];
          const val = totals[tkey];
          const formatted = col.type === "money" ? formatMoney(val) : formatUnit(val);
          body += '<td class="text-right">' + formatted + "</td>";
        } else {
          body += "<td></td>";
        }
      });
      body += "</tr>";
    }

    wrap.innerHTML =
      '<p class="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-3 uppercase tracking-wide">' +
      "FILAS: " +
      formatUnit(n) +
      " | Orden y totales sobre todo el resultado" +
      "</p>" +
      '<div class="overflow-x-auto"><table class="w-full text-xs text-left border-collapse ppp-data-table">' +
      '<thead class="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase tracking-wide">' +
      head +
      "</thead><tbody>" +
      (body || '<tr><td colspan="20" class="py-6 text-center text-slate-500">Sin datos</td></tr>') +
      "</tbody></table></div>" +
      '<p class="text-[10px] text-slate-500 dark:text-slate-400 mt-4 leading-relaxed">' +
      escHtml(footerNota) +
      "</p>";

    bindSortHandlers(wrap);
  }

  document.addEventListener("reportDataLoaded", function (event) {
    if (!event.detail || event.detail.slug !== "pedidos-pendientes-produccion") return;
    sortKey = "pendiente_qty";
    sortDir = "desc";
    renderTable(event.detail.response || {});
  });

  window.pedidosPendientesProduccionHandler = { renderTable };
})();
