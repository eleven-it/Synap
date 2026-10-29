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
    "Stock terminado: depósitos Terminado/Consignación (suma_stock=Si). " +
    "Stock producción: unidades armables según semi de componentes Fabricado (receta); no suma al disponible. " +
    "Disponible = max(0, terminado − pendiente). Backorder = pendiente sin cobertura de terminado. " +
    "Importe neto sin IVA ni descuento de cabecera.";

  const COLUMNS = [
    { key: "codigo", label: "Código", align: "left", sortable: true, type: "text" },
    { key: "cod_manual", label: "Cod. manual", align: "left", sortable: true, type: "text" },
    { key: "articulo", label: "Artículo", align: "left", sortable: true, type: "text" },
    { key: "marca", label: "Marca", align: "left", sortable: true, type: "text" },
    { key: "unidad_base", label: "Unidad base", align: "left", sortable: true, type: "text" },
    { key: "pendiente_qty", label: "Pedido pendiente", align: "right", sortable: true, type: "unit" },
    { key: "stock_terminado", label: "Stock terminado", align: "right", sortable: true, type: "unit" },
    {
      key: "stock_produccion",
      label: "Stock producción",
      title:
        "Cantidad armable: mínimo según saldo en Semi elaborado de componentes Fabricado de la receta (solo informativo).",
      align: "right",
      sortable: true,
      type: "unit",
    },
    { key: "disponible", label: "Disponible", align: "right", sortable: true, type: "unit" },
    { key: "backorder", label: "Backorder", align: "right", sortable: true, type: "unit", cellClass: "ppp-backorder" },
    { key: "importe_pendiente", label: "Importe pendiente", align: "right", sortable: true, type: "money" },
    { key: "mpr_demanda_pedido", label: "MPR demanda", align: "right", sortable: true, type: "unit" },
    { key: "reserva_objetivo", label: "Reserva objetivo", align: "right", sortable: true, type: "unit" },
    { key: "reserva_disponible", label: "Reserva disponible", align: "right", sortable: true, type: "unit" },
    { key: "reposicion_reserva", label: "Reposición reserva", align: "right", sortable: true, type: "unit" },
    { key: "mpr_cantidad_a_fabricar", label: "MPR a fabricar", align: "right", sortable: true, type: "unit" },
  ];

  const TOTAL_KEYS = {
    pendiente_qty: "total_pendiente_qty",
    stock_terminado: "total_stock_terminado",
    stock_produccion: "total_stock_produccion",
    disponible: "total_disponible",
    backorder: "total_backorder",
    importe_pendiente: "total_importe_pendiente",
    mpr_demanda_pedido: "total_mpr_demanda_pedido",
    reserva_objetivo: "total_reserva_objetivo",
    reserva_disponible: "total_reserva_disponible",
    reposicion_reserva: "total_reposicion_reserva",
    mpr_cantidad_a_fabricar: "total_mpr_cantidad_a_fabricar",
  };

  let lastResponse = null;
  let sortKey = "pendiente_qty";
  let sortDir = "desc";

  function ensurePppTableStyles() {
    if (document.getElementById("ppp-table-header-styles")) return;
    const style = document.createElement("style");
    style.id = "ppp-table-header-styles";
    style.textContent =
      "main.app-content:has(#ppp-section) { min-width: 0; }" +
      "#ppp-section { width: 100%; max-width: 100%; min-width: 0; overflow-x: hidden; contain: inline-size; }" +
      "#ppp-section #ppp-table-wrap { max-width: 100%; min-width: 0; overflow: hidden; }" +
      "#ppp-section .ppp-table-scroll { overflow: auto; max-width: 100%; max-height: calc(100vh - 220px); -webkit-overflow-scrolling: touch; }" +
      "#ppp-section .ppp-data-table { width: max-content; min-width: 100%; }" +
      "#ppp-section .ppp-data-table th.ppp-sort-th { position: sticky; top: 0; z-index: 2; white-space: nowrap; padding: 0.5rem 0.75rem; vertical-align: middle; background: rgb(241 245 249); box-shadow: inset 0 -1px 0 rgb(226 232 240); }" +
      ".dark #ppp-section .ppp-data-table th.ppp-sort-th { background: rgb(30 41 59); box-shadow: inset 0 -1px 0 rgb(51 65 85); }" +
      "#ppp-section .ppp-data-table td { color: rgb(30 41 59); padding: 0.375rem 0.75rem; border-bottom: 1px solid rgb(241 245 249); white-space: nowrap; }" +
      "#ppp-section .ppp-data-table th.ppp-sort-th { color: rgb(71 85 105); }" +
      ".dark #ppp-section .ppp-data-table td { color: rgb(226 232 240); border-bottom-color: rgb(30 41 59); }" +
      ".dark #ppp-section .ppp-data-table th.ppp-sort-th { color: rgb(203 213 225); }" +
      ".dark #ppp-section .ppp-data-table tr.ppp-totals-row td { color: rgb(248 250 252); background: rgb(30 41 59); }" +
      "#ppp-section .ppp-data-table td.ppp-backorder-hit { color: rgb(146 64 14); }" +
      ".dark #ppp-section .ppp-data-table td.ppp-backorder-hit { color: rgb(254 243 199); background-color: rgb(69 26 3 / 0.85) !important; }";
    document.head.appendChild(style);
  }

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
    if (col.key === "backorder" && Number(row.backorder) > 0) {
      return " ppp-backorder-hit bg-amber-50 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 font-semibold";
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


  // ---------------------------------------------------------------
  // Agrupación anidada (mismo componente que bo-stock-facturacion)
  // ---------------------------------------------------------------
  const RNG = window.ReportsNestedGrouping || null;
  const GROUP_SELECT_ID = "ppp-group-by";
  const SEARCH_INPUT_ID = "ppp-search";
  const SEARCH_KEYS = ["codigo", "cod_manual", "articulo", "marca", "cliente", "unidad_base"];
  const GROUP_DIMENSIONS = [
    { key: "cliente", label: "Cliente" },
    { key: "marca", label: "Marca" },
    { key: "articulo", label: "Artículo" },
  ];
  /** Métricas que se reparten por cliente (las demás son por artículo y no se subtotalizan al agrupar por cliente). */
  const CLIENTE_METRIC_KEYS = ["pendiente_qty", "importe_pendiente"];
  let groupByInitialized = false;

  function buildGroupConfig(metricKeys) {
    const metrics = COLUMNS.filter((c) => c.type === "unit" || c.type === "money").map((c) => ({
      key: c.key,
      label: c.label,
      format: c.type === "money" ? "currency" : "number",
    }));
    const dims = GROUP_DIMENSIONS.concat(
      COLUMNS.filter((c) => c.type === "text" && !GROUP_DIMENSIONS.some((d) => d.key === c.key)).map((c) => ({
        key: c.key,
        label: c.label,
      }))
    );
    return {
      // Solo Cliente/Marca/Artículo se ofrecen en "Agrupar por".
      groupDimensions: GROUP_DIMENSIONS,
      dimensions: dims,
      metrics: metrics,
      metricKeys: metricKeys,
      columns: COLUMNS.map((c) => c.key),
      formatCell: function (value, colKey) {
        const col = COLUMNS.find((c) => c.key === colKey);
        if (!col) return value == null ? "" : escHtml(value);
        return cellValue(col, Object.fromEntries([[colKey, value]]));
      },
      decorateCell: function (colKey, row) {
        const col = COLUMNS.find((c) => c.key === colKey);
        if (!col) return {};
        return { cellClass: ((col.cellClass || "") + cellExtraClass(col, row)).trim() };
      },
    };
  }

  /**
   * Si se agrupa por Cliente, cada artículo se abre en una fila por cliente con su pendiente/importe.
   * Stock y MPR son por artículo: se muestran en el detalle pero no se subtotalizan.
   */
  function explodeByCliente(rows) {
    const out = [];
    rows.forEach(function (row) {
      const det = Array.isArray(row.clientes_detalle) ? row.clientes_detalle : [];
      if (!det.length) {
        out.push(Object.assign({}, row, { cliente: "" }));
        return;
      }
      det.forEach(function (d) {
        out.push(
          Object.assign({}, row, {
            cliente: d.cliente,
            id_cliente: d.id_cliente,
            pendiente_qty: d.pendiente_qty,
            importe_pendiente: d.importe_pendiente,
          })
        );
      });
    });
    return out;
  }

  function currentSearchQuery() {
    const el = document.getElementById(SEARCH_INPUT_ID);
    return (el && el.value) || "";
  }

  function ensureSearchInput() {
    if (!RNG) return;
    const slot = document.getElementById("ppp-search-slot");
    if (!slot || document.getElementById(SEARCH_INPUT_ID)) return;
    slot.innerHTML = RNG.searchInputHtml(SEARCH_INPUT_ID, "Buscar por código, artículo, marca, cliente...", "");
    RNG.attachSearchListener(SEARCH_INPUT_ID, function () {
      if (lastResponse) renderTable(lastResponse);
    });
  }

  function ensureGroupByUI() {
    if (!RNG || groupByInitialized) return;
    if (!document.getElementById(GROUP_SELECT_ID)) return;
    groupByInitialized = true;
    RNG.initializeGroupByUI(
      GROUP_SELECT_ID,
      { dimensions: GROUP_DIMENSIONS },
      function () { return lastResponse; },
      function (resp) { if (resp) renderTable(resp); }
    );
  }

  function currentGroupByFields() {
    if (!RNG) return [];
    return RNG.getGroupByFieldsInSelectionOrder(GROUP_SELECT_ID);
  }

  function renderGroupedBody(rows, groupByFields) {
    const byCliente = groupByFields.indexOf("cliente") !== -1;
    const data = byCliente ? explodeByCliente(rows) : rows;
    const metricKeys = byCliente ? CLIENTE_METRIC_KEYS.slice() : Object.keys(TOTAL_KEYS);
    const config = buildGroupConfig(metricKeys);
    const grouped = RNG.groupTableDataGeneric(data, groupByFields, metricKeys, sortedArticulos);
    return {
      html: RNG.renderGroupedTableRows(grouped, config, 0, true),
      groups: grouped.length,
      byCliente: byCliente,
    };
  }

  function renderTable(response) {
    const wrap = document.getElementById("ppp-table-wrap");
    const summary = document.getElementById("ppp-filters-summary");
    if (!wrap) return;

    ensurePppTableStyles();
    lastResponse = response;
    ensureSearchInput();
    ensureGroupByUI();
    const searchQuery = currentSearchQuery();
    const allRows = response.data || [];
    const filteredRows = RNG ? RNG.filterBySearch(allRows, searchQuery, SEARCH_KEYS) : allRows;
    const articulos = sortedArticulos(filteredRows);
    const groupByFields = currentGroupByFields();
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
      const titleAttr = col.title ? ' title="' + escHtml(col.title) + '"' : "";
      head +=
        '<th class="ppp-sort-th whitespace-nowrap px-3 py-2 cursor-pointer select-none ' +
        (col.align === "right" ? "text-right" : "text-left") +
        '"' +
        titleAttr +
        ' data-sort-key="' +
        escHtml(col.key) +
        '">' +
        escHtml(col.label) +
        arrow +
        "</th>";
    });
    head += "</tr>";

    let body = "";
    let groupedInfo = null;
    if (RNG && groupByFields.length && articulos.length) {
      groupedInfo = renderGroupedBody(articulos, groupByFields);
      body = groupedInfo.html;
    } else articulos.forEach(function (row) {
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

    if (articulos.length && !groupedInfo && searchQuery.trim().length < 2) {
      body += '<tr class="ppp-totals-row bg-slate-100 dark:bg-slate-800 font-semibold">';
      COLUMNS.forEach(function (col, idx) {
        if (idx === 0) {
          body += '<td colspan="5">TOTALES</td>';
          return;
        }
        if (idx < 5) return;
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
      (searchQuery.trim().length >= 2 ? " | Mostrando " + formatUnit(articulos.length) + " por búsqueda" : "") +
      (groupedInfo
        ? " | Agrupado por: " +
          escHtml(groupByFields.map((f) => (GROUP_DIMENSIONS.find((d) => d.key === f) || { label: f }).label).join(" → ")) +
          " · " + groupedInfo.groups + " agrupación" + (groupedInfo.groups !== 1 ? "es" : "") +
          (groupedInfo.byCliente ? " · Subtotales por cliente: pendiente e importe" : "")
        : " | Orden y totales sobre todo el resultado") +
      "</p>" +
      '<div class="ppp-table-scroll"><table class="ppp-data-table text-xs text-left border-collapse text-slate-800 dark:text-slate-200">' +
      '<thead class="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 uppercase tracking-wide">' +
      head +
      "</thead><tbody>" +
      (body || '<tr><td colspan="20" class="py-6 text-center text-slate-500">Sin datos</td></tr>') +
      "</tbody></table></div>" +
      '<p class="text-[10px] text-slate-500 dark:text-slate-400 mt-4 leading-relaxed">' +
      escHtml(footerNota) +
      "</p>";

    bindSortHandlers(wrap);
    if (groupedInfo) RNG.attachGroupToggleListeners(wrap);
  }

  document.addEventListener("reportDataLoaded", function (event) {
    if (!event.detail || event.detail.slug !== "pedidos-pendientes-produccion") return;
    sortKey = "pendiente_qty";
    sortDir = "desc";
    renderTable(event.detail.response || {});
  });

  window.pedidosPendientesProduccionHandler = { renderTable, explodeByCliente };
})();
