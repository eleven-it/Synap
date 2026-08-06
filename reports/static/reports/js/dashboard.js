// Comentario: Controlador básico para dashboards interactivos con gráficos D3.

import { initializeTagsFilter } from "./tags_filter.mjs";

// ============================================
// SISTEMA COMÚN: Detección de Tipo de Reporte
// ============================================

/**
 * Detecta si el reporte actual es declarativo o legacy
 * @returns {Object} { isDeclarative: boolean, reportSlug: string, reportConfig: object, isLegacy: boolean }
 */
function detectReportType() {
  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  
  // Verificar si hay un atributo data-is-declarative en el DOM
  const isDeclarativeAttr = dashboardRoot?.dataset?.isDeclarative === "true";
  
  // Verificar en el contexto de la página (template variable)
  const isDeclarativeTemplate = window.REPORT_CONFIG?.is_declarative === true;
  
  // Verificar en la configuración del reporte
  const reportConfig = window.REPORT_CONFIG?.config || {};
  const isDeclarativeConfig = reportConfig.version === "declarative-v1";
  
  // Verificar si existe WidgetEngine (solo para declarativos)
  const hasWidgetEngine = typeof window.WidgetEngine !== "undefined";
  
  // Lista de reportes legacy conocidos (hardcodeados)
  const legacyReports = [
    "ventas_netas",
    "ventas-netas",
    "cash_flow_waterfall",
    "cash_flow_by_account",
    "cash_flow_detailed_movements",
    "uninvoiced_remitos",
    "pedidos-pendientes",
    "sales_summary",
    "total-consolidado-operativo",
    "bo-stock-facturacion",
    "ventas-objetivos-vs-bo",
    "ventas-por-vendedor",
    "ventas-por-articulo",
    "ventas-marcas-mensual",
    "comprobantes-rutas",
  ];
  
  const isLegacyBySlug = legacyReports.includes(reportSlug);
  
  // Lógica de decisión (prioridad: atributo > template > config > slug)
  const isDeclarative = isDeclarativeAttr || 
                       isDeclarativeTemplate || 
                       (isDeclarativeConfig && !isLegacyBySlug) ||
                       (hasWidgetEngine && !isLegacyBySlug);
  
  return {
    isDeclarative: Boolean(isDeclarative),
    reportSlug: reportSlug || "",
    reportConfig: reportConfig,
    isLegacy: !isDeclarative
  };
}

/**
 * Indica si el slug corresponde al reporte Ventas Netas (DB puede usar "ventas-netas" o "ventas_netas").
 * @param {string} slug - report.slug del DOM o API
 * @returns {boolean}
 */
function isVentasNetasSlug(slug) {
  return slug === "ventas_netas" || slug === "ventas-netas";
}

/** Informes con doble período (facturación/remitos + backorder), mismos filtros que BO. */
function isInformeBoDualPeriodo(slug) {
  return (
    slug === "bo-stock-facturacion" ||
    slug === "ventas-objetivos-vs-bo" ||
    slug === "ventas-por-vendedor" ||
    slug === "ventas-por-articulo" ||
    slug === "ventas-marcas-mensual"
  );
}

/** Informe matriz ventas marcas mensual (PuW/PuM). */
function isVentasMarcasMensualSlug(slug) {
  return slug === "ventas-marcas-mensual";
}

/** Familia filtros período facturación + sucursal/clientes (sin backorder obligatorio). */
function isInformeVentasMarcasFamiliaSlug(slug) {
  return (
    isJerarquiaVentasBoFamiliaSlug(slug) || isVentasMarcasMensualSlug(slug)
  );
}

/**
 * BO vs stock vs facturación y Objetivos vs BO: no recargar datos al cambiar filtros en pantalla.
 * Solo «Actualizar», carga inicial o intervalo de tiempo real (`fetchDashboardData(true)`).
 */
function isInformeQuerySoloManualORealtime(slug) {
  return (
    slug === "bo-stock-facturacion" ||
    slug === "ventas-objetivos-vs-bo" ||
    slug === "ventas-por-vendedor" ||
    slug === "ventas-por-articulo" ||
    slug === "ventas-marcas-mensual"
  );
}

/** VO, ventas por vendedor y ventas por artículo: filtros BO y período facturación. */
function isJerarquiaVentasBoFamiliaSlug(slug) {
  return (
    slug === "ventas-objetivos-vs-bo" ||
    slug === "ventas-por-vendedor" ||
    slug === "ventas-por-articulo"
  );
}

const VMM_FILTER_SPECS = [
  ["vmm_marcas_incluidos", "marcas_incluidos"],
  ["vmm_superarts_incluidos", "superarts_incluidos"],
];

/** Ventas por artículo / vendedor: filtros rubro/subrubro/marca incluir/excluir. */
function isVentasCatalogoFiltersSlug(slug) {
  return slug === "ventas-por-articulo" || slug === "ventas-por-vendedor";
}

const VPA_CATALOG_FILTER_SPECS = [
  ["vpa_rubros_incluidos", "rubros_incluidos"],
  ["vpa_rubros_excluidos", "rubros_excluidos"],
  ["vpa_subrubros_incluidos", "subrubros_incluidos"],
  ["vpa_subrubros_excluidos", "subrubros_excluidos"],
  ["vpa_marcas_incluidos", "marcas_incluidos"],
  ["vpa_marcas_excluidos", "marcas_excluidos"],
];

function appendTagMultiFilter(selectId, filters, filterKey) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const vals = Array.from(sel.selectedOptions)
    .map((opt) => String(opt.value))
    .filter((v) => v);
  if (vals.length > 0) filters[filterKey] = vals;
}

/** Objetivos vs BO y Ventas por vendedor: tabla jerárquica (`objetivos_ventas_bo.js`). */
function isJerarquiaVentasVendedorSlug(slug) {
  return slug === "ventas-objetivos-vs-bo" || slug === "ventas-por-vendedor";
}

function normalizeJerarquiaSortFilters(slug, ordenarPorRaw, ordenFormaRaw) {
  const allowedOrdenarPor =
    slug === "ventas-por-vendedor" || slug === "ventas-por-articulo"
      ? ["facturacion_periodo", "unidades_periodo"]
      : ["objetivo_meta", "objetivo_falta", "total_ventas_periodo"];
  const ordenarPor = String(ordenarPorRaw || "").trim();
  const ordenForma = String(ordenFormaRaw || "").trim().toLowerCase();
  const normalizedOrdenarPor = allowedOrdenarPor.includes(ordenarPor) ? ordenarPor : allowedOrdenarPor[0];
  const normalizedOrdenForma = ordenForma === "asc" || ordenForma === "desc" ? ordenForma : "desc";
  return {
    ordenarPor: normalizedOrdenarPor,
    ordenForma: normalizedOrdenForma,
  };
}

/** Slug canónico del informe Pedidos pendientes (único en backend y catálogo). */
function isPedidosPendientesSlug(slug) {
  return slug === "pedidos-pendientes";
}

/** Lista comprobantes en rutas (logística mayoristapp, legacy Reports). */
function isLogisticaListaComprobantesRutasSlug(slug) {
  return slug === "comprobantes-rutas" || slug === "mayoristapp-lista-comprobantes-rutas";
}

/** Campos que no se muestran en la tabla pero sí entran en «Buscar en tabla» (≥2 caracteres). */
const LOGISTICA_LISTA_CR_SEARCH_KEYS_EXTRA = [
  "nro_pedido",
  "orden_ruta",
  "ventana_horaria_ruta",
  "motivo_no_entrega",
];

/** Etiquetas de dimensión para leyenda «Agrupado por» (clave técnica → texto UI). */
const LOGISTICA_LISTA_CR_GROUP_KEY_LABELS = {
  mes_factura_ym: "Mes de factura",
  estado_entrega: "Estado de entrega",
  cliente: "Cliente",
  nombre_chofer: "Chofer",
  desc_ruta: "Hoja de ruta",
  fecha_remito: "Fecha remito",
};

const _LOGISTICA_MESES_FACTURA_ES = [
  "Enero",
  "Febrero",
  "Marzo",
  "Abril",
  "Mayo",
  "Junio",
  "Julio",
  "Agosto",
  "Septiembre",
  "Octubre",
  "Noviembre",
  "Diciembre",
];

/** Convierte ``YYYY-MM`` a «Mayo 2026» (español, título capitalizado). */
function formatMesFacturaYmEs(ym) {
  if (ym == null || ym === "" || String(ym) === "Sin especificar") return String(ym ?? "");
  const m = /^(\d{4})-(\d{2})$/.exec(String(ym).trim());
  if (!m) return String(ym);
  const y = parseInt(m[1], 10);
  const mo = parseInt(m[2], 10);
  if (mo < 1 || mo > 12) return String(ym);
  return `${_LOGISTICA_MESES_FACTURA_ES[mo - 1]} ${y}`;
}

/** Filas devueltas por la API para agrupación / búsqueda local en la tabla del mismo informe. */
const logisticaListaDataByWidget = new WeakMap();

/**
 * Orden de chips en el contenedor de agrupación (mismo criterio que BO).
 * @returns {string[]}
 */
function getLogisticaListaGroupKeysFromChips() {
  const wrap = document.getElementById("logistica-lista-group-by_tags_container");
  const chips = wrap?.querySelector(".tags-chips");
  if (!chips) return [];
  return Array.from(chips.querySelectorAll("[data-value]"))
    .map((el) => el.getAttribute("data-value"))
    .filter(Boolean);
}

function filterLogisticaListaRowsBySearch(rows, query, keys) {
  const q = (query && String(query).trim()) || "";
  if (q.length < 2) return rows;
  const ql = q.toLowerCase();
  return rows.filter((row) =>
    keys.some((k) => {
      const v = row[k];
      if (v == null) return false;
      return String(v).toLowerCase().includes(ql);
    }),
  );
}

function sortLogisticaListaByGroupKeys(rows, groupKeys) {
  if (!groupKeys || !groupKeys.length) return rows;
  return [...rows].sort((a, b) => {
    for (const k of groupKeys) {
      const sa = String(a[k] ?? "").toLowerCase();
      const sb = String(b[k] ?? "").toLowerCase();
      const c = sa.localeCompare(sb, "es", { sensitivity: "base" });
      if (c !== 0) return c;
    }
    return 0;
  });
}

function escHtmlLogistica(s) {
  if (s == null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Orden de filas hoja (misma idea que sortByArticulo en BO). */
function sortLogisticaLeafRows(items) {
  if (!items || !items.length) return [];
  return [...items].sort((a, b) => {
    const fa = String(a.fecha_factura ?? a.fecha_remito ?? "");
    const fb = String(b.fecha_factura ?? b.fecha_remito ?? "");
    const c = fa.localeCompare(fb, "es");
    if (c !== 0) return c;
    return String(a.nro_remito ?? "").localeCompare(String(b.nro_remito ?? ""), "es", {
      numeric: true,
      sensitivity: "base",
    });
  });
}

/**
 * Árbol de grupos anidados (misma lógica que groupTableDataGeneric en BO).
 * metricKeys: columnas numéricas/moneda para subtotales en cabeceras de grupo.
 */
function groupLogisticaListaData(data, groupByFields, metricKeys) {
  if (!groupByFields || !groupByFields.length || !data || !data.length) return [];
  function groupByLevels(items, fields, lev) {
    if (lev >= fields.length) {
      return sortLogisticaLeafRows(items).map((item) => ({
        type: "item",
        data: item,
        children: [],
      }));
    }
    const currentField = fields[lev];
    const grouped = {};
    items.forEach((row) => {
      const groupKey =
        row[currentField] !== undefined && row[currentField] !== null && row[currentField] !== ""
          ? String(row[currentField])
          : "Sin especificar";
      if (!grouped[groupKey]) {
        grouped[groupKey] = {
          groupKey,
          groupValue: groupKey,
          groupField: currentField,
          items: [],
          totals: {},
        };
        metricKeys.forEach((k) => {
          grouped[groupKey].totals[k] = 0;
        });
      }
      grouped[groupKey].items.push(row);
      metricKeys.forEach((k) => {
        const v = parseFloat(row[k]);
        if (!Number.isNaN(v)) grouped[groupKey].totals[k] += v;
      });
    });
    const result = [];
    Object.keys(grouped)
      .sort((a, b) => a.localeCompare(b, "es", { sensitivity: "base" }))
      .forEach((key) => {
        const g = grouped[key];
        const nested = groupByLevels(g.items, fields, lev + 1);
        result.push({ type: "group", data: g, children: nested });
      });
    return result;
  }
  return groupByLevels(data, groupByFields, 0);
}

function countLogisticaGroupNodes(nodes) {
  let n = 0;
  (nodes || []).forEach((item) => {
    if (item.type === "group") {
      n += 1;
      n += countLogisticaGroupNodes(item.children);
    }
  });
  return n;
}

/**
 * Estilos de apoyo para la tabla «lista comprobantes en rutas»: el layout base carga además Tailwind CDN
 * (`base_app.html`), que puede no generar utilidades para clases solo presentes en JS; además un `td`
 * con hijo `inline-flex` shrink-to-fit puede quedar centrado en la celda y **simular** importes centrados
 * en la columna vecina (TOTAL REMITO). Estas reglas son acotadas a `.synap-logistica-lista-cr-table`.
 */
function ensureSynapLogisticaListaCrTableStylesOnce() {
  const styleId = "synap-lg-cr-table-style-v4";
  document.getElementById("synap-lg-cr-table-style")?.remove();
  document.getElementById("synap-lg-cr-table-style-v3")?.remove();
  if (document.getElementById(styleId)) return;
  const st = document.createElement("style");
  st.id = styleId;
  st.textContent = `
.synap-logistica-lista-cr-table > thead > tr > th {
  position: -webkit-sticky;
  position: sticky;
  top: 0;
}
.synap-logistica-lista-cr-table th.synap-lc-col-money,
.synap-logistica-lista-cr-table td.synap-lc-col-money {
  text-align: right !important;
  vertical-align: middle;
}
.synap-logistica-lista-cr-table th.synap-lc-col-money .synap-lc-money-inner,
.synap-logistica-lista-cr-table td.synap-lc-col-money .synap-lc-money-inner {
  display: block;
  width: 100%;
  box-sizing: border-box;
  text-align: right !important;
  white-space: nowrap;
  unicode-bidi: isolate;
  font-variant-numeric: tabular-nums;
}
.synap-logistica-lista-cr-table th.synap-lc-col-actions,
.synap-logistica-lista-cr-table td.synap-lc-col-actions {
  text-align: right !important;
  vertical-align: middle;
}
.synap-logistica-lista-cr-table td.synap-lc-col-actions .synap-lc-actions-inner {
  display: flex;
  flex-direction: column;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 0.125rem;
  row-gap: 0.25rem;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
/* Agrupación: cuerpo solo tenía filas con colspan; fila ancla + tabla anidada al 100% alinean rejilla con thead. */
.synap-logistica-lista-cr-table tr.logistica-col-anchor {
  height: 0;
  max-height: 0;
  font-size: 0;
  line-height: 0;
  border: none;
}
.synap-logistica-lista-cr-table tr.logistica-col-anchor td {
  height: 0;
  max-height: 0;
  padding: 0 !important;
  border: none !important;
  line-height: 0;
  font-size: 0;
  overflow: hidden;
  vertical-align: top;
}
.synap-logistica-lista-cr-table.logistica-group-nested {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
  margin: 0;
  border-width: 0 !important;
}
.synap-logistica-lista-cr-table.logistica-group-nested td:not(.synap-lc-col-money):not(.synap-lc-col-actions) {
  min-width: 0;
  overflow-wrap: break-word;
  word-break: break-word;
}
`.trim();
  document.head.appendChild(st);
}

function logisticaSetThMoneyContent(th, headerText) {
  th.textContent = "";
  const inner = document.createElement("span");
  inner.className = "synap-lc-money-inner";
  inner.textContent = headerText;
  th.appendChild(inner);
}

function logisticaSetTdMoneyContent(td, displayText) {
  td.textContent = "";
  const inner = document.createElement("span");
  inner.className = "synap-lc-money-inner";
  inner.textContent = displayText;
  td.appendChild(inner);
}

/** Celdas de texto — rejilla explícita; `min-w-0` + `break-words` para `table-layout:fixed` sin desborde. */
const LOGISTICA_LISTA_CR_TD_BASE =
  "min-w-0 max-w-full break-words px-2.5 py-2 text-xs text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600";
/** Celdas monetarias — importe en `.synap-lc-money-inner` con `nowrap`; la celda puede encoger sin desbordar texto. */
const LOGISTICA_LISTA_CR_TD_MONEY =
  "min-w-0 max-w-full px-2.5 py-2 text-right text-xs tabular-nums synap-lc-col-money font-mono text-slate-900 dark:text-white border border-slate-200 dark:border-slate-600";

/**
 * Estilo por columna (lista comprobantes en rutas): cabecera y cuerpo alineados, franjas pastel tipo VO.
 * No altera las reglas de alineación de `synap-lc-col-money` ni `synap-lc-col-actions` (solo fondos/bordes extra).
 */
function logisticaListaCrColumnStyle(fieldKey) {
  const k = String(fieldKey || "").toLowerCase();
  const doc = new Set(["fecha_factura", "nro_remito", "nro_factura"]);
  const rutaFechas = new Set(["fecha_salida_ruta_fmt", "fecha_hora_entrega_fmt"]);
  const personas = new Set(["cliente", "nombre_chofer", "nombre_usuario_entrega"]);
  if (k === "total_remito") {
    return {
      headerBg:
        "border-violet-300 bg-violet-200/90 text-violet-950 dark:border-violet-700 dark:bg-violet-900/55 dark:text-violet-50",
      bodyBg:
        "border-l-violet-300 bg-violet-50/85 dark:border-violet-700 dark:bg-violet-950/35",
      thAlign: "",
      tdAlign: "",
    };
  }
  if (doc.has(k)) {
    const nowrapNros = new Set(["nro_remito", "nro_factura"]);
    return {
      headerBg:
        "bg-emerald-50 text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100",
      bodyBg:
        "border-l-emerald-200/90 bg-emerald-50/40 dark:border-emerald-800/60 dark:bg-emerald-950/18",
      thAlign: "text-right tabular-nums whitespace-normal break-words leading-tight min-w-0",
      tdAlign: nowrapNros.has(k)
        ? "text-right tabular-nums whitespace-nowrap"
        : "text-right tabular-nums whitespace-normal break-words",
    };
  }
  if (k === "estado_entrega") {
    return {
      headerBg:
        "bg-amber-50 text-amber-950 dark:bg-amber-950/30 dark:text-amber-100",
      bodyBg:
        "border-l-amber-200/80 bg-amber-50/35 dark:border-amber-800/50 dark:bg-amber-950/15",
      thAlign: "text-center whitespace-normal break-words leading-tight min-w-0",
      tdAlign: "text-center whitespace-normal break-words",
    };
  }
  if (personas.has(k)) {
    return {
      headerBg:
        "bg-slate-100 text-slate-800 dark:bg-slate-800/90 dark:text-slate-100",
      bodyBg:
        "border-l-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/30",
      thAlign: "text-left whitespace-normal break-words leading-tight min-w-0",
      tdAlign: "text-left whitespace-normal break-words",
    };
  }
  if (k === "estado_ruta") {
    return {
      headerBg:
        "bg-violet-50 text-violet-950 dark:bg-violet-950/35 dark:text-violet-100",
      bodyBg:
        "border-l-violet-200/80 bg-violet-50/35 dark:border-violet-800/50 dark:bg-violet-950/18",
      thAlign: "text-center whitespace-normal break-words leading-tight min-w-0",
      tdAlign: "text-center whitespace-normal break-words",
    };
  }
  if (k === "desc_ruta") {
    return {
      headerBg:
        "bg-violet-50 text-violet-950 dark:bg-violet-950/35 dark:text-violet-100",
      bodyBg:
        "border-l-violet-200/80 bg-violet-50/35 dark:border-violet-800/50 dark:bg-violet-950/18",
      thAlign: "text-left whitespace-normal break-words leading-tight min-w-0",
      tdAlign: "text-left whitespace-normal break-words",
    };
  }
  if (rutaFechas.has(k)) {
    return {
      headerBg:
        "bg-violet-50 text-violet-950 dark:bg-violet-950/35 dark:text-violet-100",
      bodyBg:
        "border-l-violet-200/80 bg-violet-50/35 dark:border-violet-800/50 dark:bg-violet-950/18",
      thAlign: "text-right tabular-nums whitespace-normal break-words leading-tight min-w-0",
      tdAlign: "text-right tabular-nums whitespace-normal break-words",
    };
  }
  return {
    headerBg: "bg-slate-50 text-slate-700 dark:bg-slate-900/55 dark:text-slate-200",
    bodyBg: "border-l-slate-200/90 bg-white dark:border-slate-700 dark:bg-slate-950/40",
    thAlign: "text-left whitespace-normal break-words leading-tight min-w-0",
    tdAlign: "text-left whitespace-normal break-words",
  };
}

/** Cabeceras visibles al hacer scroll dentro de `#logistica-lista-cr-scroll` (cada `th` sticky; sin `overflow-hidden` en la tabla). */
const LOGISTICA_LISTA_CR_TH_STICKY =
  "sticky top-0 z-10 shadow-[0_1px_0_0_rgb(226_232_240)] dark:shadow-[0_1px_0_0_rgb(51_65_85)]";

/** Cabecera «ACCIONES»: franja sky como columna BO TOTAL en VO (alineación existente sin cambios). */
function logisticaListaCrThClassAcciones() {
  return (
    `${LOGISTICA_LISTA_CR_TH_STICKY} border border-slate-200 dark:border-slate-600 border-sky-300 bg-sky-200/90 min-w-0 max-w-full px-2.5 py-2 text-[10px] font-bold uppercase tracking-wide align-middle text-sky-950 whitespace-normal break-words leading-tight synap-lc-col-actions dark:border-sky-700 dark:bg-sky-900/50 dark:text-sky-50`
  );
}

function logisticaListaCrTdClassAcciones() {
  return `${LOGISTICA_LISTA_CR_TD_BASE} align-middle synap-lc-col-actions border-sky-200 bg-sky-50/80 dark:border-sky-800 dark:bg-sky-950/35`;
}

/**
 * Fila invisible con una celda por columna: cuando el cuerpo solo usa ``colspan`` completo, algunos motores
 * no reparten igual el ancho que el ``thead``; esta fila fija la rejilla al ``colgroup``.
 */
function logisticaListaCrColAnchorRowHtml(fieldKeys) {
  const n = fieldKeys.length + 1;
  let tds = "";
  for (let i = 0; i < n; i += 1) {
    tds += '<td class="logistica-col-anchor-cell"></td>';
  }
  return `<tr class="logistica-col-anchor" aria-hidden="true">${tds}</tr>`;
}

/** ``colgroup`` con anchos iguales para alinear thead y cuerpo (evita desajuste con tablas anidadas). */
function logisticaListaColgroupHtml(nCols) {
  const n = Math.max(1, nCols);
  const w = (100 / n).toFixed(4);
  let s = "<colgroup>";
  for (let i = 0; i < n; i += 1) {
    s += `<col style="width:${w}%" />`;
  }
  s += "</colgroup>";
  return s;
}

function logisticaListaDetailRowHtml(row, fieldKeys) {
  let html = `<tr class="hover:bg-slate-50/90 dark:hover:bg-slate-900/35 transition-colors bg-white dark:bg-slate-950 logistica-detail-row">`;
  fieldKeys.forEach((key) => {
    const value = row[key];
    const isCur = isCurrencyField(key);
    const lcSty = logisticaListaCrColumnStyle(key);
    const tdCls = isCur
      ? `${LOGISTICA_LISTA_CR_TD_MONEY} ${lcSty.bodyBg}`
      : `${LOGISTICA_LISTA_CR_TD_BASE} ${lcSty.tdAlign} ${lcSty.bodyBg}`;
    let inner = "";
    if (value !== null && value !== undefined && value !== "") {
      inner = isCur
        ? `<span class="synap-lc-money-inner font-mono">${escHtmlLogistica(formatCurrency(value))}</span>`
        : escHtmlLogistica(String(formatNumber(value)));
    } else if (isCur) {
      inner = '<span class="synap-lc-money-inner font-mono"></span>';
    }
    html += `<td class="${tdCls}">${inner}</td>`;
  });
  const codR = row.cod_mov_remito;
  const codP = row.cod_mov_pedido;
  html += `<td class="${logisticaListaCrTdClassAcciones()}"><div class="synap-lc-actions-inner">`;
  html += `<button type="button" class="text-[10px] font-semibold text-sky-600 hover:text-sky-500 dark:text-sky-400 underline-offset-2 hover:underline leading-tight" data-logistica-detalle="${escHtmlLogistica(String(codR ?? ""))}">Detalle</button>`;
  html += `<button type="button" class="text-[10px] font-semibold text-emerald-600 hover:text-emerald-500 dark:text-emerald-400 underline-offset-2 hover:underline leading-tight" data-logistica-entrega="${escHtmlLogistica(String(codR ?? ""))}" data-logistica-pedido="${escHtmlLogistica(String(codP ?? ""))}">Entrega</button>`;
  html += "</div></td></tr>";
  return html;
}

function renderLogisticaGroupedTreeHtml(
  grouped,
  fieldKeys,
  headerTranslations,
  metricKeys,
  groupIdPrefix,
  level,
  collapsedDefault,
) {
  let rowsHTML = "";
  (grouped || []).forEach((item, idx) => {
    if (item.type === "group") {
      const g = item.data;
      const groupId = `${groupIdPrefix}${level}-${idx}`;
      const dimLabel =
        headerTranslations[g.groupField?.toLowerCase?.()] ||
        (g.groupField ? g.groupField.replace(/_/g, " ") : "");
      const groupValRaw = (g.groupValue || "").toString().substring(0, 120);
      const groupValFormatted =
        g.groupField === "mes_factura_ym" ? formatMesFacturaYmEs(groupValRaw) : groupValRaw;
      const groupHeaderText =
        g.groupField === "mes_factura_ym"
          ? String(groupValFormatted).toUpperCase()
          : `${dimLabel}: ${groupValFormatted}`;
      const bgClass =
        level === 0
          ? "bg-sky-50/80 dark:bg-sky-950/30"
          : level === 1
            ? "bg-slate-100 dark:bg-slate-800/90"
            : "bg-slate-50/80 dark:bg-slate-900/50";
      const padLeft = level * 20 + 8;
      const iconSvgClass =
        g.groupField === "mes_factura_ym"
          ? "w-4 h-4 shrink-0 inline-block align-middle logistica-group-toggle-icon cursor-pointer"
          : "w-4 h-4 inline-block mr-2 align-middle logistica-group-toggle-icon cursor-pointer";
      const expandIcon = `<svg class="${iconSvgClass}" data-logistica-group-toggle="${groupId}" style="transform: ${collapsedDefault ? "rotate(0deg)" : "rotate(90deg)"};" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 18l6-6-6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
      /** Una sola celda ancha: sin rejilla vertical interna (paridad pedida con barra de grupo continua). */
      const colspan = fieldKeys.length + 1;
      const metricKeysShow = fieldKeys.filter(
        (colKey) => metricKeys.includes(colKey) && g.totals && g.totals[colKey] !== undefined,
      );
      let metricHtml = "";
      if (metricKeysShow.length) {
        metricHtml =
          '<div class="flex shrink-0 flex-col items-end gap-0.5 text-right text-xs font-semibold tabular-nums text-sky-600 dark:text-sky-400 font-mono">';
        metricKeysShow.forEach((colKey) => {
          metricHtml += `<span class="synap-lc-money-inner font-mono">${escHtmlLogistica(
            formatCurrency(g.totals[colKey]),
          )}</span>`;
        });
        metricHtml += "</div>";
      }
      const leftInner =
        g.groupField === "mes_factura_ym"
          ? `<div class="flex min-w-0 flex-1 items-center gap-2" style="padding-left:${padLeft}px">${expandIcon}<span class="truncate font-medium uppercase leading-tight text-slate-800 dark:text-slate-200">${escHtmlLogistica(groupHeaderText)}</span></div>`
          : `<div class="flex min-w-0 flex-1 items-center gap-2" style="padding-left:${padLeft}px">${expandIcon}<span class="font-medium text-slate-700 dark:text-slate-300">${escHtmlLogistica(groupHeaderText)}</span></div>`;
      rowsHTML += `<tr class="logistica-group-row" data-logistica-group-id="${groupId}">`;
      rowsHTML += `<td colspan="${colspan}" class="${bgClass} border border-slate-200 px-2 py-2 align-middle text-xs dark:border-slate-600"><div class="flex w-full min-w-0 items-center justify-between gap-3">${leftInner}${metricHtml}</div></td></tr>`;
      rowsHTML += `<tr class="logistica-group-children" data-logistica-group-parent="${groupId}" style="${collapsedDefault ? "display:none" : ""}"><td colspan="${fieldKeys.length + 1}" class="p-0 border-0 align-top"><table dir="ltr" class="synap-logistica-lista-cr-table logistica-group-nested vo-jerarquia-table w-full max-w-full table-fixed border-collapse border-0 text-xs text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-950">${logisticaListaColgroupHtml(fieldKeys.length + 1)}<tbody>`;
      rowsHTML += renderLogisticaGroupedTreeHtml(
        item.children,
        fieldKeys,
        headerTranslations,
        metricKeys,
        groupIdPrefix,
        level + 1,
        collapsedDefault,
      );
      rowsHTML += "</tbody></table></td></tr>";
    } else if (item.type === "item") {
      rowsHTML += logisticaListaDetailRowHtml(item.data, fieldKeys);
    }
  });
  return rowsHTML;
}

function attachLogisticaGroupToggleListeners(container) {
  if (!container) return;
  container.querySelectorAll("[data-logistica-group-toggle]").forEach((el) => {
    if (el._logisticaToggleAttached) return;
    el._logisticaToggleAttached = true;
    el.addEventListener("click", function () {
      const groupId = this.getAttribute("data-logistica-group-toggle");
      const childrenRow = container.querySelector(`tr[data-logistica-group-parent="${groupId}"]`);
      if (!childrenRow) return;
      const isHidden = childrenRow.style.display === "none";
      childrenRow.style.display = isHidden ? "table-row" : "none";
      this.style.transform = isHidden ? "rotate(90deg)" : "rotate(0deg)";
    });
  });
}

/**
 * Construye objeto filters de período igual que setPeriodDatesFromForm (bloque dashboardRoot),
 * para workspace y POST sin depender del scope interno de dashboard.js.
 */
function workspaceBuildPeriodFiltersPayload(periodoTipo, fechaInicio, fechaFin) {
  const filters = {};
  const today = new Date();
  const fallbackMes = () => {
    const first = new Date(today.getFullYear(), today.getMonth(), 1);
    const last = new Date(today.getFullYear(), today.getMonth() + 1, 0);
    return [first.toISOString().split("T")[0], last.toISOString().split("T")[0]];
  };
  const pt = periodoTipo || "personalizado";
  if (fechaInicio && fechaFin) {
    filters.fecha_inicio = fechaInicio;
    filters.fecha_fin = fechaFin;
    if (pt === "dia_actual") filters.dia_actual = true;
    else if (pt === "mes_actual") filters.mes_actual = true;
    else if (pt === "año_actual") filters.año_actual = true;
    return filters;
  }
  if (pt === "dia_actual") {
    const s = today.toISOString().split("T")[0];
    filters.fecha_inicio = s;
    filters.fecha_fin = s;
    filters.dia_actual = true;
  } else if (pt === "mes_actual") {
    const [a, b] = fallbackMes();
    filters.fecha_inicio = a;
    filters.fecha_fin = b;
    filters.mes_actual = true;
  } else if (pt === "año_actual") {
    const first = new Date(today.getFullYear(), 0, 1);
    const last = new Date(today.getFullYear(), 11, 31);
    filters.fecha_inicio = first.toISOString().split("T")[0];
    filters.fecha_fin = last.toISOString().split("T")[0];
    filters.año_actual = true;
  } else {
    const [a, b] = fallbackMes();
    filters.fecha_inicio = a;
    filters.fecha_fin = b;
  }
  return filters;
}

// ============================================
// SISTEMA COMÚN: Valores de Intervalo Unificados
// ============================================

/**
 * Valores de intervalo unificados (solo declarativos)
 */
const INTERVAL_VALUES = {
  INTERVAL_30S: "interval_30s",
  INTERVAL_5M: "interval_5m",
  INTERVAL_10M: "interval_10m",
  INTERVAL_1H: "interval_1h",
  INTERVAL_2H: "interval_2h"
};

/**
 * Mapeo para migrar valores legacy de intervalo a los nuevos valores declarativos.
 * Solo se usa para cargar valores antiguos de localStorage.
 */
const LEGACY_TO_DECLARATIVE_MIGRATION = {
  "realtime": INTERVAL_VALUES.INTERVAL_30S,
  "hourly": INTERVAL_VALUES.INTERVAL_5M,
  "daily": INTERVAL_VALUES.INTERVAL_10M,
  "weekly": INTERVAL_VALUES.INTERVAL_1H,
  "monthly": INTERVAL_VALUES.INTERVAL_2H
};

/**
 * Migra un valor de intervalo legacy a su equivalente declarativo.
 * Si ya es declarativo o no se encuentra mapeo, retorna el valor original.
 * @param {string} interval - Valor de intervalo a migrar
 * @returns {string} Valor de intervalo en formato declarativo
 */
function migrateLegacyInterval(interval) {
  if (!interval) return INTERVAL_VALUES.INTERVAL_10M; // Default
  return LEGACY_TO_DECLARATIVE_MIGRATION[interval] || interval;
}

/**
 * Obtiene el intervalo actual (siempre en formato declarativo)
 * @returns {string} Valor de intervalo en formato declarativo
 */
function getCurrentRefreshIntervalValue() {
  const refreshIntervalSelect = document.getElementById("refresh_interval");
  let value = refreshIntervalSelect?.value;
  
  // Si el valor es legacy, migrarlo
  if (value && LEGACY_TO_DECLARATIVE_MIGRATION[value]) {
    value = migrateLegacyInterval(value);
    // Actualizar el select con el valor migrado
    if (refreshIntervalSelect) {
      refreshIntervalSelect.value = value;
    }
  }
  
  return value || INTERVAL_VALUES.INTERVAL_10M;
}

/**
 * Convierte intervalo a milisegundos (solo valores declarativos)
 * @param {string} interval - Valor de intervalo en formato declarativo
 * @returns {number} Intervalo en milisegundos
 */
function getRefreshIntervalMs(interval) {
  // Asegurar que el intervalo esté en formato declarativo
  const normalizedInterval = migrateLegacyInterval(interval);
  
  const intervalMap = {
    "interval_30s": 30000,      // 30 segundos
    "interval_5m": 300000,       // 5 minutos
    "interval_10m": 600000,     // 10 minutos
    "interval_1h": 3600000,     // 1 hora
    "interval_2h": 7200000      // 2 horas
  };
  
  return intervalMap[normalizedInterval] || 600000; // Default: 10 minutos
}

const dashboardRoot = document.querySelector("#dashboard-root");

const widgetDataCache = new Map();
let resizeObserver = null;
let realtimeInterval = null;
let realtimeActive = false;

const workspaceState = {
  groups: [],
  current: 0,
  total: 0,
  initialized: false,
};

const workspaceControls = {
  prev: null,
  next: null,
  indicator: null,
  prevDate: null,
  nextDate: null,
};

const isWorkspaceMode = Boolean(dashboardRoot?.dataset.workspaceMode === "true");
const isWorkspaceTemplate = dashboardRoot?.dataset.workspaceMode === "true";
const isWorkspaceTv = dashboardRoot?.dataset.workspaceTv === "true";
const isWorkspaceMobile = dashboardRoot?.dataset.workspaceMobile === "true";
const workspaceApiUrl = dashboardRoot?.dataset.workspaceUrl || null;

const resetWorkspaceState = () => {
  workspaceState.groups = [];
  workspaceState.current = 0;
  workspaceState.total = 0;
  workspaceState.initialized = false;
};

const setWorkspaceCount = (value) => {
  const node = document.querySelector("[data-workspace-count]");
  if (node) {
    node.textContent = value;
  }
};

const getCsrfToken = () => {
  const name = "csrftoken";
  const cookies = document.cookie ? document.cookie.split(";") : [];
  for (let i = 0; i < cookies.length; i += 1) {
    const cookie = cookies[i].trim();
    if (cookie.startsWith(`${name}=`)) {
      return decodeURIComponent(cookie.substring(name.length + 1));
    }
  }
  return "";
};

const toast = (message, type = "success") => {
  const container = document.createElement("div");
  container.className = `fixed top-5 right-5 z-50 px-4 py-3 rounded-xl shadow-2xl text-xs font-semibold tracking-wide ${
    type === "success"
      ? "bg-emerald-500 text-white"
      : "bg-rose-500 text-white"
  } animate-[fade-in_0.4s_ease-out]`;
  container.innerText = message;
  document.body.appendChild(container);
  
  // Asegurar que el mensaje desaparezca después de 3 segundos
  const removeToast = () => {
    container.style.opacity = "0";
    container.style.transition = "opacity 0.3s ease-out";
    setTimeout(() => {
      if (container.parentNode) {
        container.remove();
      }
    }, 300);
  };
  
  // Configurar timeout para desaparecer automáticamente
  setTimeout(removeToast, 3000);
  
  // También manejar el evento animationend por si acaso
  container.addEventListener("animationend", (e) => {
    if (e.animationName && e.animationName.includes("fade-out")) {
      if (container.parentNode) {
        container.remove();
      }
    }
  });
};

const initializeFiltersToggle = () => {
  // Buscar los elementos cada vez que se llama la función para asegurar que estén disponibles
  const filtersToggleButton = document.querySelector("[data-filters-toggle]");
  const filtersContainer = document.querySelector("[data-filters-container]");
  const filtersWrapper = document.querySelector("[data-filters-wrapper]");
  
  if (!filtersToggleButton || !filtersContainer) {
    return;
  }

  const labelElement = filtersToggleButton.querySelector("[data-toggle-label]");
  const showLabel = filtersToggleButton.dataset.labelShow || "Mostrar filtros";
  const hideLabel = filtersToggleButton.dataset.labelHide || "Ocultar filtros";

  const setState = (visible) => {
    if (labelElement) {
      labelElement.textContent = visible ? hideLabel : showLabel;
    }
    filtersToggleButton.setAttribute("aria-expanded", String(visible));
    // Mostrar/ocultar el wrapper junto con el formulario
    if (filtersWrapper) {
      if (visible) {
        filtersWrapper.classList.remove("hidden");
        window.dispatchEvent(new CustomEvent("reportPeriodFiltersReady"));
      } else {
        filtersWrapper.classList.add("hidden");
      }
    }
  };

  // Remover listeners anteriores si existen para evitar duplicados
  const newToggleButton = filtersToggleButton.cloneNode(true);
  filtersToggleButton.parentNode.replaceChild(newToggleButton, filtersToggleButton);
  
  newToggleButton.addEventListener("click", () => {
    const isHidden = filtersContainer.classList.toggle("hidden");
    setState(!isHidden);
  });

  // Inicializar como oculto (colapsado)
  filtersContainer.classList.add("hidden");
  if (filtersWrapper) {
    filtersWrapper.classList.add("hidden");
  }
  setState(false);
};

const COLORS = [
  "#38bdf8",
  "#818cf8",
  "#f97316",
  "#10b981",
  "#f472b6",
  "#facc15",
];

const formatNumber = (value) => {
  if (typeof value === "number") {
    try {
      return new Intl.NumberFormat(
        document.documentElement.lang || "es-AR",
        { maximumFractionDigits: 2 }
      ).format(value);
    } catch (e) {
      return value.toFixed(2);
    }
  }
  return value;
};

const formatCurrency = (value) => {
  let n = value;
  if (typeof n === "string") {
    const t = n.replace(/\s/g, "").trim();
    if (!t) return value;
    let parsed = Number(t);
    if (Number.isNaN(parsed)) {
      const arLike = /^-?\d{1,3}(\.\d{3})*,\d+$/;
      if (arLike.test(t)) {
        parsed = Number.parseFloat(t.replace(/\./g, "").replace(",", "."));
      }
    }
    if (!Number.isNaN(parsed)) n = parsed;
  }
  if (typeof n === "number" && !Number.isNaN(n)) {
    try {
      return new Intl.NumberFormat(
        "es-AR",
        {
          style: "currency",
          currency: "ARS",
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }
      ).format(n);
    } catch (e) {
      return `$${n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ".").replace(".", ",")}`;
    }
  }
  return value;
};

/**
 * Formato compacto para KPIs: valores grandes en millones (8.878M), miles (500K), o completo si es pequeño
 */
const formatCurrencyCompact = (value) => {
  if (typeof value !== "number" || isNaN(value)) return formatCurrency(value ?? 0);
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (abs >= 1e6) {
    const millions = abs / 1e6;
    const formatted = millions.toLocaleString("es-AR", {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    });
    return `${sign}${formatted}M`;
  }
  if (abs >= 1e3) {
    const thousands = abs / 1e3;
    const formatted = thousands.toLocaleString("es-AR", {
      maximumFractionDigits: 1,
      minimumFractionDigits: 0,
    });
    return `${sign}${formatted}K`;
  }
  return formatCurrency(value);
};

const isCurrencyField = (fieldName) => {
  // Contadores MPR: mostrar como número entero, no moneda
  const normalized = String(fieldName).toLowerCase().trim();
  if (normalized === "total_pedidos" || normalized === "total_opt_atrasadas" || normalized === "total_movimientos") return false;
  if (normalized === "total_remito") return true;

  const currencyFields = [
    "ventas_brutas",
    "notas_credito",
    "ventas_netas",
    "ventas brutas",
    "notas credito",
    "ventas netas",
    "remitos_no_facturados",
    "pedidos_pendientes",
    "total_consolidado",
    "total_subtotal_desc",
    "subtotal_desc",
    "total",
    "importe",
    "monto",
    "precio",
    "saldo_inicial",
    "operating_flow",
    "operating_ingresos",
    "operating_egresos",
    "investing_flow",
    "financing_flow",
    "cash_variation",
    "saldo_final",
    "cumulative",
    "ingreso",
    "egreso",
    "importe_neto",
    "saldo",
    "ingreso",
    "egreso",
  ];
  const normalizedField = String(fieldName).toLowerCase().replace(/_/g, " ");
  return currencyFields.some((field) => normalizedField.includes(field));
};

// Mapeo de traducciones para términos específicos
const translateFieldName = (fieldName) => {
  const translations = {
    "saldo_inicial": "Saldo Inicial",
    "operating_flow": "Flujo Operativo",
    "investing_flow": "Flujo de Inversión",
    "financing_flow": "Flujo de Financiamiento",
    "cash_variation": "Variación de Caja",
    "saldo_final": "Saldo Final",
    "operating flow": "Flujo Operativo",
    "investing flow": "Flujo de Inversión",
    "financing flow": "Flujo de Financiamiento",
    "cash variation": "Variación de Caja",
    "ventas_netas": "Ventas Netas",
    "ventas netas": "Ventas Netas",
    "ventas_brutas": "Ventas Brutas",
    "ventas brutas": "Ventas Brutas",
    "notas_credito": "Notas de Crédito",
    "notas credito": "Notas de Crédito",
  };
  
  const normalized = String(fieldName).toLowerCase().trim();
  return translations[normalized] || null;
};

const toTitle = (value) => {
  // Primero verificar si hay traducción específica
  const translation = translateFieldName(value);
  if (translation) {
    return translation.toUpperCase();
  }
  
  // Si no hay traducción específica, usar el formato estándar
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
};

const getBounding = (element) => {
  const rect = element.getBoundingClientRect();
  const width = rect.width || element.clientWidth || 640;
  const height = rect.height || width * 0.55 || 360;
  return { width, height };
};

const parseDateIfPossible = (value) => {
  const parsed = Date.parse(value);
  if (!Number.isNaN(parsed)) {
    return new Date(parsed);
  }
  if (typeof value === "string" && value.includes("W")) {
    const [year, weekLabel] = value.split("-W");
    if (year && weekLabel) {
      const week = Number.parseInt(weekLabel, 10) || 1;
      const simple = new Date(Number(year), 0, 1 + (week - 1) * 7);
      return simple;
    }
  }
  return value;
};

const discoverNumericFields = (rows) => {
  if (!rows || !rows.length) return [];
  const sample = rows[0];
  return Object.keys(sample).filter((key) => typeof sample[key] === "number");
};

const getWidgetConfig = (widget) => {
  const configId = widget.dataset.widgetConfigId;
  if (!configId) return {};
  const script = document.getElementById(configId);
  if (!script) return {};
  try {
    return JSON.parse(script.textContent);
  } catch (error) {
    console.warn("No se pudo parsear configuración del widget", error);
    return {};
  }
};

const updateWorkspaceIndicator = () => {
  if (!workspaceControls.indicator) {
    return;
  }
  const total = workspaceState.total || workspaceState.groups.length;
  const current = total ? workspaceState.current + 1 : 0;
  workspaceControls.indicator.textContent = `Espacio de trabajo ${current}/${total}`;
  if (workspaceControls.prevDate) {
    if (isWorkspaceTv || isWorkspaceMobile) {
      workspaceControls.prevDate.textContent = "—";
    } else {
      const prevValue = total > 1 ? ((workspaceState.current - 1 + total) % total) + 1 : null;
      workspaceControls.prevDate.textContent = prevValue && prevValue !== current ? `${prevValue}` : "—";
    }
  }
  if (workspaceControls.nextDate) {
    if (isWorkspaceTv || isWorkspaceMobile) {
      workspaceControls.nextDate.textContent = "—";
    } else {
      const nextValue = total > 1 ? ((workspaceState.current + 1) % total) + 1 : null;
      workspaceControls.nextDate.textContent = nextValue && nextValue !== current ? `${nextValue}` : "—";
    }
  }
  const disableNav = total <= 1;
  if (workspaceControls.prev) {
    workspaceControls.prev.disabled = disableNav;
  }
  if (workspaceControls.next) {
    workspaceControls.next.disabled = disableNav;
  }
};

const showWorkspace = (index, options = { rerender: true }) => {
  const total = workspaceState.total || workspaceState.groups.length;
  if (!total || !workspaceState.groups.length) {
    workspaceState.current = 0;
    updateWorkspaceIndicator();
    return;
  }
  const normalizedIndex = ((index % total) + total) % total;
  workspaceState.groups.forEach((group, idx) => {
    const isActive = idx === normalizedIndex;
    group.classList.toggle("hidden", !isActive);
    if (isActive && options.rerender) {
      const widgets = group.querySelectorAll("[data-widget-id]");
      widgets.forEach((widget) => {
        const cacheKey = widget.dataset.widgetId;
        const cached = widgetDataCache.get(cacheKey);
        if (cached && cached.data) {
          const config = cached.config || getWidgetConfig(widget);
          renderWidgetChart(widget, cached.data, config, cached.meta || {});
        }
      });
    }
  });
  workspaceState.current = normalizedIndex;
  workspaceState.total = total;
  updateWorkspaceIndicator();
};

const setupWorkspaces = (force = false) => {
  if (!dashboardRoot) {
    return;
  }
  if (force) {
    resetWorkspaceState();
  } else if (workspaceState.initialized) {
    return;
  }

  const wrappers = Array.from(dashboardRoot.querySelectorAll("[data-widget-wrapper]"));
  if (!wrappers.length) {
    resetWorkspaceState();
    updateWorkspaceIndicator();
    return;
  }

  if (!isWorkspaceTemplate && wrappers.length <= 1) {
    workspaceState.initialized = true;
    workspaceState.groups = [];
    workspaceState.current = 0;
    workspaceState.total = 1;
    updateWorkspaceIndicator();
    return;
  }

  const chunkSize = isWorkspaceTemplate ? 4 : isWorkspaceMobile ? wrappers.length : 2;
  const fragment = document.createDocumentFragment();
  const groups = [];

  for (let i = 0; i < wrappers.length; i += chunkSize) {
    const slice = wrappers.slice(i, i + chunkSize);
    const group = document.createElement("div");
    group.dataset.workspaceIndex = String(groups.length);
    const tvClassName =
      "reports-workspace-grid workspace-tv-grid grid gap-3 md:grid-cols-2 hidden";
    const mobileClassName =
      "reports-workspace-grid workspace-mobile-grid grid gap-3 sm:grid-cols-1 hidden";
    const defaultClassName =
      "reports-workspace-grid grid gap-3 sm:grid-cols-1 xl:grid-cols-2 hidden";
    group.className = isWorkspaceTv ? tvClassName : isWorkspaceMobile ? mobileClassName : defaultClassName;
    // Asegurar que el gap se mantenga fijo y no cambie durante actualizaciones
    // En modo TV, usar gap más compacto (0.5rem = 8px), en workspace normal usar 0.75rem (12px)
    if (isWorkspaceTv) {
      group.style.gap = "0.5rem"; // gap-2 = 8px, más compacto para TV
      group.style.rowGap = "0.5rem";
      group.style.columnGap = "0.5rem";
    } else {
      group.style.gap = "0.75rem"; // gap-3 = 12px = 3 líneas
      group.style.rowGap = "0.75rem";
      group.style.columnGap = "0.75rem";
    }
    if (slice.length === 1) {
      if (isWorkspaceTv) {
        group.classList.add("md:grid-cols-1");
      } else if (!isWorkspaceMobile) {
        group.classList.add("xl:grid-cols-1");
      }
    }
    slice.forEach((wrapper) => group.appendChild(wrapper));
    fragment.appendChild(group);
    groups.push(group);
  }

  if (!dashboardRoot.querySelector(".reports-workspace-grid") || isWorkspaceTemplate || isWorkspaceMobile) {
    dashboardRoot.innerHTML = "";
    dashboardRoot.classList.remove("space-y-8");
    if (!isWorkspaceMobile) {
      // Reducir gap a 3 líneas (gap-3 = 0.75rem = 12px)
      dashboardRoot.classList.add("flex", "flex-col", "gap-3");
      // Asegurar que el gap se mantenga fijo y no cambie durante actualizaciones
      dashboardRoot.style.gap = "0.75rem"; // gap-3 = 12px = 3 líneas
      dashboardRoot.style.rowGap = "0.75rem";
    }
    dashboardRoot.appendChild(fragment);
  }

  workspaceState.groups = groups;
  workspaceState.total = groups.length;
  workspaceState.current = 0;
  workspaceState.initialized = true;
  showWorkspace(0, { rerender: false });
};

const toggleFullScreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement
      .requestFullscreen()
      .catch((error) => console.warn("No se pudo activar pantalla completa", error));
  } else {
    document.exitFullscreen().catch((error) => console.warn("No se pudo salir de pantalla completa", error));
  }
};

const setFullscreenButtonState = (isActive) => {
  const html = isActive
    ? `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 9H5V5M5 19l4-4m6 0h4v4m0-14l-4 4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> Salir de pantalla completa`
    : `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 8V4h4M4 4l5 5M20 16v4h-4m4 0l-5-5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> Pantalla completa`;
  document.querySelectorAll("[data-fullscreen-toggle]").forEach((btn) => {
    btn.innerHTML = html;
  });
};

const syncFullscreenState = () => {
  const isActive = Boolean(document.fullscreenElement);
  document.body.classList.toggle("reports-fullscreen", isActive);
  setFullscreenButtonState(isActive);
};

const ensureVisible = (element) => {
  element.classList.remove("hidden");
  element.classList.remove("opacity-0");
};

const renderLineChart = (container, data, config, fillArea = false) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const configuredY = config.y_fields || (config.y_field ? [config.y_field] : []);
  const yFields = configuredY.length ? configuredY : discoverNumericFields(data);
  if (!yFields.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 56 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xValues = data.map((row) => parseDateIfPossible(row[xField] ?? row[xField.toLowerCase()]));
  const isTimeScale = xValues.every((value) => value instanceof Date);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const xScale = isTimeScale
    ? d3.scaleTime().domain(d3.extent(xValues)).range([margin.left, margin.left + innerWidth])
    : d3.scalePoint().domain(xValues).range([margin.left, margin.left + innerWidth]).padding(0.4);

  const yMax = d3.max(yFields, (field) => d3.max(data, (row) => Number(row[field]) || 0)) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const axisBottom = svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium");

  if (isTimeScale) {
    axisBottom.call(d3.axisBottom(xScale).ticks(5).tickFormat(d3.timeFormat("%d/%m")));
  } else {
    axisBottom.call(d3.axisBottom(xScale));
  }

  const isCurrency = yFields.some((field) => isCurrencyField(field));
  const yAxis = d3.axisLeft(yScale).ticks(5);
  if (isCurrency) {
    yAxis.tickFormat((d) => formatCurrency(d));
  }
  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(yAxis);

  yFields.forEach((field, index) => {
    const line = d3
      .line()
      .defined((row) => row[field] !== null && row[field] !== undefined)
      .x((row, idx) => xScale(xValues[idx]))
      .y((row) => yScale(Number(row[field]) || 0));

    if (fillArea && index === 0) {
      const area = d3
        .area()
        .defined((row) => row[field] !== null && row[field] !== undefined)
        .x((row, idx) => xScale(xValues[idx]))
        .y0(() => yScale(0))
        .y1((row) => yScale(Number(row[field]) || 0));

      svg
        .append("path")
        .datum(data)
        .attr("fill", d3.color(COLORS[index % COLORS.length]).copy({ opacity: 0.2 }))
        .attr("d", area);
    }

    svg
      .append("path")
      .datum(data)
      .attr("fill", "none")
      .attr("stroke", COLORS[index % COLORS.length])
      .attr("stroke-width", 2.5)
      .attr("d", line);
  });
};

const renderBarChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }
  const xField = config.x_field || Object.keys(data[0])[0];
  const yFieldCandidate = config.y_field || (config.y_fields ? config.y_fields[0] : null);
  const yField = yFieldCandidate || discoverNumericFields(data)[0];
  if (!yField) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 56 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const aggregated = Object.values(
    data.reduce((acc, row) => {
      const key = row[xField] ?? row[xField.toLowerCase()] ?? "Sin categoría";
      if (!acc[key]) {
        acc[key] = { label: key, value: 0 };
      }
      acc[key].value += Number(row[yField]) || 0;
      return acc;
    }, {})
  );

  const xScale = d3
    .scaleBand()
    .domain(aggregated.map((item) => item.label))
    .range([margin.left, margin.left + innerWidth])
    .padding(0.3);

  const yMax = d3.max(aggregated, (item) => item.value) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  const isCurrency = isCurrencyField(yField);
  const yAxis = d3.axisLeft(yScale).ticks(5);
  if (isCurrency) {
    yAxis.tickFormat((d) => formatCurrency(d));
  }
  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(yAxis);

  svg
    .selectAll("rect")
    .data(aggregated)
    .join("rect")
    .attr("x", (item) => xScale(item.label))
    .attr("y", (item) => yScale(item.value))
    .attr("width", xScale.bandwidth())
    .attr("height", (item) => margin.top + innerHeight - yScale(item.value))
    .attr("rx", 6)
    .attr("fill", (_, i) => COLORS[i % COLORS.length]);
};

const renderGroupedBarChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  // Para ventas_netas, usar mes_formato en lugar de mes si existe
  const xField = config.x_field === "mes" && data[0].mes_formato ? "mes_formato" : (config.x_field || Object.keys(data[0])[0]);
  const valueField = config.y_field || config.value_field || discoverNumericFields(data)[0];
  const groupField = config.group_field === "sucursal" && data[0].nombre_sucursal ? "nombre_sucursal" : (config.group_field || Object.keys(data[0]).find((key) => key !== xField && key !== valueField && typeof data[0][key] === "string"));
  
  if (!valueField) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  // Agrupar datos por mes y sucursal
  const grouped = d3.group(data, (row) => row[xField] ?? "Sin categoría");
  const groupKeys = Array.from(new Set(data.map((row) => row[groupField] ?? "Sin grupo"))).sort();
  
  // Crear estructura de datos agrupada
  const groupedData = Array.from(grouped, ([xKey, rows]) => {
    const base = { x: xKey, xKey: xKey }; // Guardar xKey para ordenar
    groupKeys.forEach((groupKey) => {
      const groupRows = rows.filter((row) => (row[groupField] ?? "Sin grupo") === groupKey);
      base[groupKey] = groupRows.reduce((sum, row) => sum + (Number(row[valueField]) || 0), 0);
    });
    return base;
  });
  
  // Ordenar los datos cronológicamente (de más antiguo a más reciente)
  // Si xField es mes_formato (formato MM/YYYY), ordenar por fecha
  if (xField === "mes_formato" || (data[0] && data[0].mes_formato)) {
    groupedData.sort((a, b) => {
      // Parsear formato MM/YYYY a fecha para comparar
      const parseDate = (str) => {
        const [month, year] = str.split('/');
        return new Date(parseInt(year), parseInt(month) - 1);
      };
      const dateA = parseDate(a.x);
      const dateB = parseDate(b.x);
      return dateA - dateB; // Orden ascendente (más antiguo primero)
    });
  } else {
    // Ordenar alfabéticamente si no es fecha
    groupedData.sort((a, b) => a.x.localeCompare(b.x));
  }

  const { width, height } = getBounding(container);
  // Aumentar el margen izquierdo para dar más espacio a los valores del eje Y cuando son moneda
  const isCurrency = isCurrencyField(valueField);
  const margin = { top: 24, right: 24, bottom: 40, left: isCurrency ? 90 : 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleBand()
    .domain(groupedData.map((item) => item.x))
    .range([margin.left, margin.left + innerWidth])
    .padding(0.2);

  const groupScale = d3
    .scaleBand()
    .domain(groupKeys)
    .range([0, xScale.bandwidth()])
    .padding(0.1);

  const yMax = d3.max(groupedData, (item) => d3.max(groupKeys, (key) => item[key] || 0)) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  const yAxis = d3.axisLeft(yScale).ticks(5);
  if (isCurrency) {
    yAxis.tickFormat((d) => {
      // Asegurar que el valor sea numérico antes de formatear
      if (typeof d === "number" && !isNaN(d) && isFinite(d)) {
        return formatCurrency(d);
      }
      return String(d);
    });
  }
  const yAxisGroup = svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(yAxis);
  
  // Asegurar que los textos del eje Y se muestren correctamente y tengan suficiente espacio
  yAxisGroup.selectAll("text")
    .style("fill", "rgb(203 213 225)") // text-slate-300
    .style("font-size", "10px")
    .style("font-weight", "500")
    .style("text-anchor", "end")
    .attr("dx", "-0.5em");

  // Crear grupos de barras para cada mes con animaciones
  const barGroups = svg
    .append("g")
    .selectAll("g")
    .data(groupedData)
    .join(
      (enter) => {
        const g = enter
          .append("g")
          .attr("transform", (d) => `translate(${xScale(d.x)}, 0)`);
        
        // Dibujar barras para cada grupo (sucursal) con animación de entrada
        groupKeys.forEach((groupKey, groupIndex) => {
          const rect = g.append("rect")
            .attr("x", groupScale(groupKey))
            .attr("y", margin.top + innerHeight) // Comenzar desde abajo
            .attr("width", groupScale.bandwidth())
            .attr("height", 0) // Comenzar con altura 0
            .attr("rx", 4)
            .attr("fill", COLORS[groupIndex % COLORS.length])
            .attr("data-group", groupKey)
            .transition()
            .duration(600)
            .attr("y", (d) => yScale(d[groupKey] || 0))
            .attr("height", (d) => margin.top + innerHeight - yScale(d[groupKey] || 0));
          
          // Agregar etiqueta de texto con el valor
          const text = g.append("text")
            .attr("x", groupScale(groupKey) + groupScale.bandwidth() / 2)
            .attr("y", margin.top + innerHeight)
            .attr("text-anchor", "middle")
            .attr("class", "font-semibold")
            .style("font-size", "14px")
            .style("font-weight", "600")
            .style("opacity", 0)
            .text((d) => {
              const value = d[groupKey] || 0;
              return isCurrency ? formatCurrency(value) : formatNumber(value);
            });
          
          // Animar el texto junto con la barra
          text.transition()
            .duration(600)
            .delay(300)
            .attr("y", (d) => {
              const barHeight = margin.top + innerHeight - yScale(d[groupKey] || 0);
              const barTop = yScale(d[groupKey] || 0);
              
              // Si la barra es lo suficientemente alta (> 20px), mostrar el texto dentro (centrado)
              // Si no, mostrar el texto por fuera, en la parte superior
              if (barHeight > 20) {
                // Dentro de la barra, centrado verticalmente
                return barTop + Math.max(barHeight / 2, 12);
              } else {
                // Por fuera, en la parte superior de la barra (5px arriba)
                return barTop - 5;
              }
            })
            .style("fill", (d) => {
              const barHeight = margin.top + innerHeight - yScale(d[groupKey] || 0);
              // Si está dentro de la barra, usar color blanco; si está fuera, usar color del texto del gráfico
              return barHeight > 20 ? "white" : "rgb(203 213 225)"; // text-slate-300
            })
            .style("opacity", (d) => {
              // Siempre mostrar el texto, ya sea dentro o fuera
              return 1;
            });
        });
        
        return g;
      },
      (update) => {
        // Actualizar posición de grupos existentes con animación
        update
          .transition()
          .duration(300)
          .attr("transform", (d) => `translate(${xScale(d.x)}, 0)`);
        
        // Actualizar barras existentes con animación suave
        groupKeys.forEach((groupKey, groupIndex) => {
          const bars = update
            .selectAll(`rect[data-group="${groupKey}"]`)
            .data((d) => [d], () => groupKey);
          
          bars.enter()
            .append("rect")
            .attr("x", groupScale(groupKey))
            .attr("y", margin.top + innerHeight)
            .attr("width", groupScale.bandwidth())
            .attr("height", 0)
            .attr("rx", 4)
            .attr("fill", COLORS[groupIndex % COLORS.length])
            .attr("data-group", groupKey)
            .merge(bars)
            .transition()
            .duration(600)
            .attr("x", groupScale(groupKey))
            .attr("width", groupScale.bandwidth())
            .attr("y", (d) => yScale(d[groupKey] || 0))
            .attr("height", (d) => margin.top + innerHeight - yScale(d[groupKey] || 0));
          
          bars.exit()
            .transition()
            .duration(300)
            .attr("height", 0)
            .attr("y", margin.top + innerHeight)
            .remove();
          
          // Actualizar etiquetas de texto
          const texts = update
            .selectAll(`text[data-group-text="${groupKey}"]`)
            .data((d) => [d], () => groupKey);
          
          texts.enter()
            .append("text")
            .attr("x", groupScale(groupKey) + groupScale.bandwidth() / 2)
            .attr("y", margin.top + innerHeight)
            .attr("text-anchor", "middle")
            .attr("class", "font-semibold")
            .attr("data-group-text", groupKey)
            .style("font-size", "14px")
            .style("font-weight", "600")
            .style("opacity", 0)
            .text((d) => {
              const value = d[groupKey] || 0;
              return isCurrency ? formatCurrency(value) : formatNumber(value);
            })
            .merge(texts)
            .transition()
            .duration(600)
            .delay(300)
            .attr("x", groupScale(groupKey) + groupScale.bandwidth() / 2)
            .attr("y", (d) => {
              const barHeight = margin.top + innerHeight - yScale(d[groupKey] || 0);
              const barTop = yScale(d[groupKey] || 0);
              
              // Si la barra es lo suficientemente alta (> 20px), mostrar el texto dentro (centrado)
              // Si no, mostrar el texto por fuera, en la parte superior
              if (barHeight > 20) {
                // Dentro de la barra, centrado verticalmente
                return barTop + Math.max(barHeight / 2, 12);
              } else {
                // Por fuera, en la parte superior de la barra (5px arriba)
                return barTop - 5;
              }
            })
            .style("fill", (d) => {
              const barHeight = margin.top + innerHeight - yScale(d[groupKey] || 0);
              // Si está dentro de la barra, usar color blanco; si está fuera, usar color del texto del gráfico
              return barHeight > 20 ? "white" : "rgb(203 213 225)"; // text-slate-300
            })
            .style("opacity", (d) => {
              // Siempre mostrar el texto, ya sea dentro o fuera
              return 1;
            })
            .text((d) => {
              const value = d[groupKey] || 0;
              return isCurrency ? formatCurrency(value) : formatNumber(value);
            });
          
          texts.exit()
            .transition()
            .duration(300)
            .style("opacity", 0)
            .remove();
        });
        
        return update;
      },
      (exit) => {
        // Animar salida de grupos eliminados
        exit
          .selectAll("rect")
          .transition()
          .duration(300)
          .attr("height", 0)
          .attr("y", margin.top + innerHeight);
        
        // Eliminar etiquetas de texto también
        exit
          .selectAll("text[data-group-text]")
          .transition()
          .duration(300)
          .style("opacity", 0)
          .remove();
        
        return exit
          .transition()
          .duration(300)
          .attr("opacity", 0)
          .remove();
      }
    );

  // Leyenda
  const legend = svg
    .append("g")
    .attr("transform", `translate(${width - margin.right - 150}, ${margin.top})`);

  groupKeys.forEach((groupKey, index) => {
    const legendItem = legend
      .append("g")
      .attr("transform", `translate(0, ${index * 20})`);

    legendItem
      .append("rect")
      .attr("width", 12)
      .attr("height", 12)
      .attr("rx", 2)
      .attr("fill", COLORS[index % COLORS.length]);

    legendItem
      .append("text")
      .attr("x", 16)
      .attr("y", 9)
      .attr("class", "text-[10px] fill-slate-300 font-medium")
      .text(groupKey);
  });
};

const renderStackedBarChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const first = data[0];
  const xField = config.x_field || (first.mes_formato ? "mes_formato" : "mes") || Object.keys(first)[0];
  const valueField = config.y_field || config.value_field || discoverNumericFields(data)[0];
  if (!valueField) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  const isCurrency = isCurrencyField(valueField) || config.unit === "ARS";
  let stackField =
    config.stack_field || (config.group_field === "sucursal" && first.nombre_sucursal ? "nombre_sucursal" : config.group_field) ||
    Object.keys(first).find((key) => key !== xField && key !== valueField && typeof first[key] === "string");
  // Forzar nombre_sucursal cuando los datos lo tienen y hay varias sucursales (evita "Total" si config trae "Sucursal" y no existe en filas)
  if (first.nombre_sucursal !== undefined && first.nombre_sucursal !== null) {
    const sucursalValues = Array.from(new Set(data.map((r) => r.nombre_sucursal ?? ""))).filter(Boolean);
    if (sucursalValues.length > 1) {
      stackField = "nombre_sucursal";
    }
  }
  const grouped = d3.group(data, (row) => row[xField] ?? "Sin categoría");
  const keys = Array.from(new Set(Array.from(grouped.values()).flat().map((row) => row[stackField] ?? "Total"))).filter(Boolean);

  const stackedData = Array.from(grouped, ([key, rows]) => {
    const base = { x: key };
    keys.forEach((stackKey) => {
      base[stackKey] = rows
        .filter((row) => (row[stackField] ?? "Total") === stackKey)
        .reduce((sum, row) => sum + (Number(row[valueField]) || 0), 0);
    });
    return base;
  });

  // Ordenar cronológicamente si es mes (mes_formato MM/YYYY o mes YYYY-MM)
  if (first.mes_formato || first.mes) {
    stackedData.sort((a, b) => {
      const parse = (str) => {
        if (!str) return new Date(0);
        if (str.indexOf("/") !== -1) {
          const [m, y] = str.split("/");
          return new Date(parseInt(y, 10), parseInt(m, 10) - 1);
        }
        const [y, m] = String(str).split("-");
        return new Date(parseInt(y, 10), parseInt(m || 1, 10) - 1);
      };
      return parse(a.x) - parse(b.x);
    });
  }

  const { width, height } = getBounding(container);
  const margin = { top: 28, right: 160, bottom: 40, left: isCurrency ? 90 : 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleBand()
    .domain(stackedData.map((item) => item.x))
    .range([margin.left, margin.left + innerWidth])
    .padding(0.3);

  const stackGenerator = d3.stack().keys(keys);
  const series = stackGenerator(stackedData);

  const yMax = d3.max(series, (serie) => d3.max(serie, (d) => d[1])) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([0, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  const yAxis = d3.axisLeft(yScale).ticks(5);
  if (isCurrency) {
    yAxis.tickFormat((d) => {
      if (typeof d === "number" && !isNaN(d) && isFinite(d)) {
        return formatCurrency(d);
      }
      return String(d);
    });
  }
  const yAxisGroup = svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(yAxis);
  yAxisGroup.selectAll("text")
    .style("fill", "rgb(203 213 225)")
    .style("font-size", "10px")
    .style("font-weight", "500")
    .style("text-anchor", "end")
    .attr("dx", "-0.5em");

  svg
    .append("g")
    .selectAll("g")
    .data(series)
    .join("g")
    .attr("fill", (_, index) => COLORS[index % COLORS.length])
    .selectAll("rect")
    .data((serie) => serie)
    .join("rect")
    .attr("x", (d) => xScale(d.data.x))
    .attr("y", (d) => yScale(d[1]))
    .attr("height", (d) => yScale(d[0]) - yScale(d[1]))
    .attr("width", xScale.bandwidth())
    .attr("rx", 4);

  // Total sobre cada barra (como en el informe anterior)
  stackedData.forEach((d) => {
    const total = keys.reduce((sum, k) => sum + (d[k] || 0), 0);
    if (total <= 0) return;
    const x = xScale(d.x) + xScale.bandwidth() / 2;
    const y = yScale(total) - 8;
    svg
      .append("text")
      .attr("x", x)
      .attr("y", y)
      .attr("text-anchor", "middle")
      .attr("class", "text-[11px] font-semibold fill-white")
      .style("font-size", "11px")
      .style("font-weight", "600")
      .text(isCurrency ? formatCurrency(total) : formatNumber(total));
  });

  // Leyenda (esquina superior derecha)
  const legend = svg
    .append("g")
    .attr("transform", `translate(${width - margin.right - 140}, ${margin.top})`);
  keys.forEach((key, i) => {
    const g = legend.append("g").attr("transform", `translate(0, ${i * 20})`);
    g.append("rect")
      .attr("width", 12)
      .attr("height", 12)
      .attr("rx", 2)
      .attr("fill", COLORS[i % COLORS.length]);
    g.append("text")
      .attr("x", 16)
      .attr("y", 9)
      .attr("class", "text-[10px] fill-slate-300 font-medium")
      .style("fill", "rgb(203 213 225)")
      .text(key);
  });
};

const renderHeatmap = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const yField = config.y_field || Object.keys(data[0])[1];
  const valueField = config.value_field || discoverNumericFields(data)[0];

  const xKeys = Array.from(new Set(data.map((row) => row[xField] ?? "-")));
  const yKeys = Array.from(new Set(data.map((row) => row[yField] ?? "-")));

  const { width, height } = getBounding(container);
  const margin = { top: 40, right: 24, bottom: 40, left: 80 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3.scaleBand().domain(xKeys).range([margin.left, margin.left + innerWidth]).padding(0.1);
  const yScale = d3.scaleBand().domain(yKeys).range([margin.top, margin.top + innerHeight]).padding(0.1);

  const values = data.map((row) => Number(row[valueField]) || 0);
  const color = d3
    .scaleSequential(d3.interpolateBlues)
    .domain([d3.min(values) || 0, d3.max(values) || 1]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale));

  svg
    .append("g")
    .selectAll("rect")
    .data(data)
    .join("rect")
    .attr("x", (row) => xScale(row[xField] ?? "-"))
    .attr("y", (row) => yScale(row[yField] ?? "-"))
    .attr("width", xScale.bandwidth())
    .attr("height", yScale.bandwidth())
    .attr("rx", 8)
    .attr("fill", (row) => color(Number(row[valueField]) || 0));
};

const renderGauge = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const valueField = config.value_field || discoverNumericFields(data)[0];
  const value = d3.mean(data, (row) => Number(row[valueField]) || 0) || 0;
  const min = config.min ?? 0;
  const max = config.max ?? 100;
  const qualifier = config.target ?? config.threshold ?? 95;

  const { width, height } = getBounding(container);
  const radius = Math.min(width, height) / 2 - 20;
  const centerX = width / 2;
  const centerY = height - 20;

  const scale = d3.scaleLinear().domain([min, max]).range([-Math.PI / 2, Math.PI / 2]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const arcBackground = d3.arc().innerRadius(radius - 20).outerRadius(radius).startAngle(-Math.PI / 2).endAngle(Math.PI / 2);

  svg
    .append("path")
    .attr("d", arcBackground())
    .attr("fill", "#1e293b")
    .attr("transform", `translate(${centerX}, ${centerY})`);

  const arcValue = d3.arc().innerRadius(radius - 20).outerRadius(radius).startAngle(-Math.PI / 2).endAngle(scale(value));

  svg
    .append("path")
    .attr("d", arcValue())
    .attr("fill", value >= qualifier ? "#22c55e" : "#f97316")
    .attr("transform", `translate(${centerX}, ${centerY})`);

  const needleAngle = scale(value);

  const needleLine = d3
    .line()
    .x((d) => d.x)
    .y((d) => d.y);

  const needle = [
    { x: centerX, y: centerY },
    { x: centerX + Math.cos(needleAngle) * (radius - 10), y: centerY + Math.sin(needleAngle) * (radius - 10) },
  ];

  svg
    .append("path")
    .attr("d", needleLine(needle))
    .attr("stroke", "#f8fafc")
    .attr("stroke-width", 4)
    .attr("stroke-linecap", "round");

  svg
    .append("text")
    .attr("x", centerX)
    .attr("y", centerY + 28)
    .attr("class", "text-base font-semibold fill-white")
    .attr("text-anchor", "middle")
    .text(`${formatNumber(value)}${config.unit ? ` ${config.unit}` : ""}`);
};

const renderWaterfall = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  // Detectar si los datos tienen múltiples períodos (cash flow waterfall con períodos mensuales)
  const hasPeriods = data.some(row => row.period || row.mes_formato || row.type);
  const isCashFlowWaterfall = hasPeriods && data.some(row => 
    row.operating_flow !== undefined || 
    row.investing_flow !== undefined || 
    row.financing_flow !== undefined
  );

  if (isCashFlowWaterfall) {
    // Formato para cash flow waterfall con múltiples períodos
    // Los datos vienen con: period, operating_flow, investing_flow, financing_flow, cash_variation, cumulative, type
    const startingRow = data.find(row => row.type === "starting");
    const endingRow = data.find(row => row.type === "ending");
    const periodRows = data.filter(row => row.type === "period");

    // Crear secuencia acumulada: Saldo Inicial -> Períodos -> Saldo Final
    const nodes = [];
    
    // Saldo inicial - mostrar como barra desde 0 hasta el valor del saldo inicial
    if (startingRow) {
      const saldoInicial = Number(startingRow.cumulative) || 0;
      nodes.push({
        key: startingRow.period || "Saldo Inicial",
        value: saldoInicial,
        type: "initial",
        start: 0,
        end: saldoInicial,
      });
    }

    let cumulative = Number(startingRow?.cumulative) || 0;
    
    // Períodos intermedios - mostrar variación neta por período
    periodRows.forEach((row, index) => {
      const periodLabel = row.mes_formato || row.period || `Período ${index + 1}`;
      const cashVariation = Number(row.cash_variation) || 0;
      
      // Solo agregar si hay variación significativa
      if (Math.abs(cashVariation) > 0.01 || index === 0) {
        nodes.push({
          key: periodLabel,
          value: cashVariation,
          type: "delta",
          start: cumulative,
          end: cumulative + cashVariation,
          period: periodLabel,
          operatingFlow: Number(row.operating_flow) || 0,
          investingFlow: Number(row.investing_flow) || 0,
          financingFlow: Number(row.financing_flow) || 0,
        });
        cumulative += cashVariation;
      }
    });

    // Si no hay períodos intermedios, agregar una barra de variación total
    if (periodRows.length === 0 && startingRow && endingRow) {
      const totalVariation = Number(endingRow.cumulative) - Number(startingRow.cumulative);
      nodes.push({
        key: "Variación Total",
        value: totalVariation,
        type: "delta",
        start: cumulative,
        end: Number(endingRow.cumulative) || cumulative,
      });
      cumulative = Number(endingRow.cumulative) || cumulative;
    }

    // Saldo final - mostrar como barra desde 0 hasta el valor del saldo final
    if (endingRow) {
      const saldoFinal = Number(endingRow.cumulative) || cumulative;
      nodes.push({
        key: endingRow.period || "Saldo Final",
        value: saldoFinal,
        type: "total",
        start: 0,
        end: saldoFinal,
      });
    }

    const { width, height } = getBounding(container);
    const margin = { top: 24, right: 24, bottom: 60, left: 80 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const xScale = d3
      .scaleBand()
      .domain(nodes.map((node) => node.key))
      .range([margin.left, margin.left + innerWidth])
      .padding(0.3);

    const yMin = Math.min(0, d3.min(nodes, (node) => Math.min(node.start, node.end)) || 0);
    const yMax = d3.max(nodes, (node) => Math.max(node.start, node.end)) || 1;
    const yScale = d3
      .scaleLinear()
      .domain([yMin, yMax])
      .nice()
      .range([margin.top + innerHeight, margin.top]);

    const svg = d3
      .select(container)
      .html("")
      .append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet");

    // Eje X con rotación para etiquetas largas
    svg
      .append("g")
      .attr("transform", `translate(0, ${margin.top + innerHeight})`)
      .attr("class", "text-[9px] text-slate-300 font-medium")
      .call(d3.axisBottom(xScale))
      .selectAll("text")
      .style("text-anchor", "end")
      .attr("dx", "-.8em")
      .attr("dy", ".15em")
      .attr("transform", "rotate(-45)");

    // Eje Y con formato de moneda
    const yAxis = d3.axisLeft(yScale).ticks(8);
    yAxis.tickFormat((d) => formatCurrency(d));
    svg
      .append("g")
      .attr("transform", `translate(${margin.left}, 0)`)
      .attr("class", "text-[10px] text-slate-300 font-medium")
      .call(yAxis);

    // Línea de referencia en cero
    const zeroY = yScale(0);
    if (zeroY >= margin.top && zeroY <= margin.top + innerHeight) {
      svg
        .append("line")
        .attr("x1", margin.left)
        .attr("y1", zeroY)
        .attr("x2", margin.left + innerWidth)
        .attr("y2", zeroY)
        .attr("stroke", "rgba(148, 163, 184, 0.3)")
        .attr("stroke-width", 1)
        .attr("stroke-dasharray", "4,4");
    }

    // Línea de tendencia del saldo acumulado (conecta los puntos de saldo)
    const cumulativePoints = [];
    nodes.forEach((node, index) => {
      const x = xScale(node.key) + xScale.bandwidth() / 2;
      const y = yScale(node.end);
      cumulativePoints.push({ x, y, node });
    });

    if (cumulativePoints.length > 1) {
      const lineGenerator = d3.line()
        .x(d => d.x)
        .y(d => d.y)
        .curve(d3.curveMonotoneX);

      svg
        .append("path")
        .datum(cumulativePoints)
        .attr("d", lineGenerator)
        .attr("fill", "none")
        .attr("stroke", "#0ea5e9")
        .attr("stroke-width", 2.5)
        .attr("opacity", 0.7)
        .attr("stroke-dasharray", "0")
        .attr("opacity", 0)
        .transition()
        .duration(800)
        .delay(300)
        .attr("opacity", 0.7);

      // Puntos en la línea de tendencia
      svg
        .selectAll("circle.trend-point")
        .data(cumulativePoints)
        .join("circle")
        .attr("class", "trend-point")
        .attr("cx", d => d.x)
        .attr("cy", d => d.y)
        .attr("r", 4)
        .attr("fill", "#0ea5e9")
        .attr("stroke", "#ffffff")
        .attr("stroke-width", 2)
        .attr("opacity", 0)
        .transition()
        .duration(400)
        .delay((_, i) => 300 + i * 50)
        .attr("opacity", 1);
    }

    // Líneas de conexión entre barras (más sutiles ahora que tenemos la línea de tendencia)
    nodes.slice(0, -1).forEach((node, index) => {
      const nextNode = nodes[index + 1];
      if (nextNode) {
        svg
          .append("line")
          .attr("x1", xScale(node.key) + xScale.bandwidth())
          .attr("y1", yScale(node.end))
          .attr("x2", xScale(nextNode.key))
          .attr("y2", yScale(nextNode.start))
          .attr("stroke", "rgba(148, 163, 184, 0.2)")
          .attr("stroke-width", 1)
          .attr("stroke-dasharray", "2,2");
      }
    });

    // Barras
    svg
      .selectAll("rect")
      .data(nodes)
      .join("rect")
      .attr("x", (node) => xScale(node.key))
      .attr("y", (node) => {
        // Para saldo inicial y final, mostrar desde 0 hasta el valor
        if (node.type === "initial" || node.type === "total") {
          return yScale(Math.max(0, node.value));
        }
        return yScale(Math.max(node.start, node.end));
      })
      .attr("height", (node) => {
        // Para saldo inicial y final, altura desde 0 hasta el valor
        if (node.type === "initial" || node.type === "total") {
          return Math.abs(yScale(0) - yScale(node.value));
        }
        return Math.abs(yScale(node.start) - yScale(node.end));
      })
      .attr("width", xScale.bandwidth())
      .attr("fill", (node) => {
        if (node.type === "total" || node.type === "initial") return "#0ea5e9";
        return node.end >= node.start ? "#10b981" : "#f97316";
      })
      .attr("rx", 4)
      .attr("opacity", 0)
      .transition()
      .duration(600)
      .delay((_, i) => i * 50)
      .attr("opacity", 1);

    // Etiquetas de valor en las barras
    svg
      .selectAll("text.value-label")
      .data(nodes.filter(node => {
        // Para saldo inicial y final, siempre mostrar si hay valor
        if (node.type === "initial" || node.type === "total") {
          return Math.abs(node.value) > 0.01;
        }
        // Para variaciones, solo mostrar si la barra es lo suficientemente alta
        const barHeight = Math.abs(yScale(node.start) - yScale(node.end));
        return barHeight > 20 && Math.abs(node.value) > 0.01;
      }))
      .join("text")
      .attr("class", "value-label text-[9px] font-semibold fill-white")
      .attr("x", (node) => xScale(node.key) + xScale.bandwidth() / 2)
      .attr("y", (node) => {
        if (node.type === "initial" || node.type === "total") {
          // Para saldo inicial y final, centrar en la barra desde 0
          const barTop = yScale(Math.max(0, node.value));
          const barBottom = yScale(Math.min(0, node.value));
          return (barTop + barBottom) / 2;
        }
        const barTop = yScale(Math.max(node.start, node.end));
        const barBottom = yScale(Math.min(node.start, node.end));
        return (barTop + barBottom) / 2;
      })
      .attr("text-anchor", "middle")
      .attr("dy", "0.35em")
      .text((node) => {
        if (node.type === "initial" || node.type === "total") {
          return formatCurrency(node.value);
        }
        // Mostrar variación con signo
        const sign = node.value >= 0 ? "+" : "";
        return `${sign}${formatCurrency(node.value)}`;
      })
      .attr("opacity", 0)
      .transition()
      .duration(600)
      .delay((_, i) => i * 50 + 300)
      .attr("opacity", 1);

    // Tooltips mejorados para mostrar desglose de flujos
    const tooltip = d3.select("body")
      .append("div")
      .attr("class", "absolute bg-slate-900 text-white text-xs rounded-lg px-4 py-3 shadow-2xl pointer-events-none opacity-0 z-50 border border-slate-700")
      .style("font-family", "system-ui, sans-serif")
      .style("min-width", "200px")
      .style("max-width", "280px");

    // Función para calcular porcentaje de cambio
    const calculatePercentageChange = (current, previous) => {
      if (!previous || previous === 0) return null;
      const change = ((current - previous) / Math.abs(previous)) * 100;
      return change;
    };

    svg
      .selectAll("rect")
      .data(nodes)
      .on("mouseover", function(event, node) {
        let tooltipContent = '';
        
        if (node.type === "initial") {
          // Calcular información del período completo
          const endingNode = nodes.find(n => n.type === "total");
          const totalVariation = endingNode ? endingNode.value - node.value : 0;
          const totalVariationSign = totalVariation >= 0 ? "+" : "";
          const totalVariationColor = totalVariation >= 0 ? "text-green-400" : "text-orange-400";
          
          tooltipContent = `
            <div class="font-bold text-sm mb-2 text-cyan-400">${node.key}</div>
            <div class="text-slate-200 font-semibold text-base mb-2">${formatCurrency(node.value)}</div>
            <div class="pt-2 border-t border-slate-700">
              <div class="text-slate-300 text-[10px] mb-1">Saldo al inicio del período</div>
              ${endingNode ? `
                <div class="mt-2 space-y-1">
                  <div class="text-slate-300 text-[10px]">Variación total del período:</div>
                  <div class="${totalVariationColor} font-semibold text-sm">
                    ${totalVariationSign}${formatCurrency(totalVariation)}
                  </div>
                  <div class="text-slate-400 text-[10px] mt-1">
                    Saldo final: ${formatCurrency(endingNode.value)}
                  </div>
                </div>
              ` : ''}
            </div>
          `;
        } else if (node.type === "total") {
          const startingValue = nodes.find(n => n.type === "initial")?.value || 0;
          const percentageChange = calculatePercentageChange(node.value, startingValue);
          const changeValue = node.value - startingValue;
          const changeSign = changeValue >= 0 ? "+" : "";
          const changeColor = changeValue >= 0 ? "text-green-400" : "text-orange-400";
          
          // Calcular desglose de flujos del período completo
          const periodNodes = nodes.filter(n => n.type === "delta" && n.operatingFlow !== undefined);
          const totalOperating = periodNodes.reduce((sum, n) => sum + (n.operatingFlow || 0), 0);
          const totalInvesting = periodNodes.reduce((sum, n) => sum + (n.investingFlow || 0), 0);
          const totalFinancing = periodNodes.reduce((sum, n) => sum + (n.financingFlow || 0), 0);
          const hasFlows = Math.abs(totalOperating) > 0.01 || Math.abs(totalInvesting) > 0.01 || Math.abs(totalFinancing) > 0.01;
          
          tooltipContent = `
            <div class="font-bold text-sm mb-2 text-cyan-400">${node.key}</div>
            <div class="text-slate-200 font-semibold text-base mb-2">${formatCurrency(node.value)}</div>
            ${hasFlows ? `
              <div class="space-y-1.5 mb-2">
                <div class="flex justify-between items-center">
                  <span class="text-slate-300 text-[10px]">Flujo Operativo:</span>
                  <span class="font-semibold text-[10px] ${totalOperating >= 0 ? 'text-green-400' : 'text-orange-400'}">
                    ${formatCurrency(totalOperating)}
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-300 text-[10px]">Flujo de Inversión:</span>
                  <span class="font-semibold text-[10px] ${totalInvesting >= 0 ? 'text-green-400' : 'text-orange-400'}">
                    ${formatCurrency(totalInvesting)}
                  </span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-300 text-[10px]">Flujo de Financiamiento:</span>
                  <span class="font-semibold text-[10px] ${totalFinancing >= 0 ? 'text-green-400' : 'text-orange-400'}">
                    ${formatCurrency(totalFinancing)}
                  </span>
                </div>
              </div>
            ` : ''}
              <div class="pt-2 border-t border-slate-700">
                <div class="text-slate-300 text-[10px] mb-1">Variación del período:</div>
              <div class="${changeColor} font-semibold text-sm">
                  ${changeSign}${formatCurrency(changeValue)} 
                  ${percentageChange !== null ? `(${changeSign}${percentageChange.toFixed(1)}%)` : ''}
                </div>
              <div class="text-slate-400 text-[10px] mt-2">
                Saldo al final del período
              </div>
              ${startingValue !== 0 ? `
                <div class="text-slate-400 text-[10px] mt-1">
                  Saldo inicial: ${formatCurrency(startingValue)}
              </div>
            ` : ''}
            </div>
          `;
        } else if (node.operatingFlow !== undefined) {
          // Período con desglose de flujos
          const totalFlow = node.operatingFlow + node.investingFlow + node.financingFlow;
          const operatingPercent = totalFlow !== 0 ? ((node.operatingFlow / Math.abs(totalFlow)) * 100).toFixed(1) : 0;
          const investingPercent = totalFlow !== 0 ? ((node.investingFlow / Math.abs(totalFlow)) * 100).toFixed(1) : 0;
          const financingPercent = totalFlow !== 0 ? ((node.financingFlow / Math.abs(totalFlow)) * 100).toFixed(1) : 0;
          
          tooltipContent = `
            <div class="font-bold text-sm mb-2 text-cyan-400">${node.period || node.key}</div>
            <div class="space-y-1.5">
              <div class="flex justify-between items-center">
                <span class="text-slate-300">Flujo Operativo:</span>
                <span class="font-semibold ${node.operatingFlow >= 0 ? 'text-green-400' : 'text-orange-400'}">
                  ${formatCurrency(node.operatingFlow)}
                  ${operatingPercent !== '0.0' ? ` <span class="text-slate-400 text-[10px]">(${operatingPercent}%)</span>` : ''}
                </span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-slate-300">Flujo de Inversión:</span>
                <span class="font-semibold ${node.investingFlow >= 0 ? 'text-green-400' : 'text-orange-400'}">
                  ${formatCurrency(node.investingFlow)}
                  ${investingPercent !== '0.0' ? ` <span class="text-slate-400 text-[10px]">(${investingPercent}%)</span>` : ''}
                </span>
              </div>
              <div class="flex justify-between items-center">
                <span class="text-slate-300">Flujo de Financiamiento:</span>
                <span class="font-semibold ${node.financingFlow >= 0 ? 'text-green-400' : 'text-orange-400'}">
                  ${formatCurrency(node.financingFlow)}
                  ${financingPercent !== '0.0' ? ` <span class="text-slate-400 text-[10px]">(${financingPercent}%)</span>` : ''}
                </span>
              </div>
            </div>
            <div class="pt-2 mt-2 border-t border-slate-700">
              <div class="flex justify-between items-center">
                <span class="text-slate-200 font-semibold">Variación Total:</span>
                <span class="font-bold text-base ${node.value >= 0 ? 'text-green-400' : 'text-orange-400'}">
                  ${node.value >= 0 ? '+' : ''}${formatCurrency(node.value)}
                </span>
              </div>
              <div class="text-slate-400 text-[10px] mt-1">
                Saldo acumulado: ${formatCurrency(node.end)}
              </div>
            </div>
          `;
        } else {
          // Variación simple sin desglose
          tooltipContent = `
            <div class="font-semibold mb-1">${node.key}</div>
            <div class="text-slate-200 font-semibold">${formatCurrency(node.value)}</div>
            <div class="text-slate-400 text-[10px] mt-1">Saldo acumulado: ${formatCurrency(node.end)}</div>
          `;
        }
        
        tooltip.html(tooltipContent);
        tooltip.style("opacity", 1);
      })
      .on("mousemove", function(event) {
        const tooltipWidth = 280;
        const tooltipHeight = 150;
        const padding = 10;
        
        let left = event.pageX + padding;
        let top = event.pageY - padding;
        
        // Ajustar si se sale por la derecha
        if (left + tooltipWidth > window.innerWidth) {
          left = event.pageX - tooltipWidth - padding;
        }
        
        // Ajustar si se sale por abajo
        if (top + tooltipHeight > window.innerHeight) {
          top = event.pageY - tooltipHeight - padding;
        }
        
        tooltip
          .style("left", left + "px")
          .style("top", top + "px");
      })
      .on("mouseout", function() {
        tooltip.style("opacity", 0);
      });

    // Tooltips para la línea de tendencia
    if (cumulativePoints.length > 1) {
      svg
        .selectAll("circle.trend-point")
        .data(cumulativePoints)
        .on("mouseover", function(event, d) {
          const node = d.node;
          const startingValue = nodes.find(n => n.type === "initial")?.value || 0;
          const percentageChange = calculatePercentageChange(node.end, startingValue);
          
          let tooltipContent = '';
          
          if (node.type === "initial") {
            const endingNode = nodes.find(n => n.type === "total");
            const totalVariation = endingNode ? endingNode.value - node.end : 0;
            const totalVariationSign = totalVariation >= 0 ? "+" : "";
            const totalVariationColor = totalVariation >= 0 ? "text-green-400" : "text-orange-400";
            
            tooltipContent = `
              <div class="font-bold text-sm mb-2 text-cyan-400">${node.key}</div>
              <div class="text-slate-200 font-semibold text-base mb-2">${formatCurrency(node.end)}</div>
              <div class="pt-2 border-t border-slate-700">
                <div class="text-slate-300 text-[10px] mb-1">Saldo al inicio del período</div>
                ${endingNode ? `
                  <div class="mt-2">
                    <div class="text-slate-300 text-[10px]">Variación total del período:</div>
                    <div class="${totalVariationColor} font-semibold text-sm">
                      ${totalVariationSign}${formatCurrency(totalVariation)}
                    </div>
                    <div class="text-slate-400 text-[10px] mt-1">
                      Saldo final: ${formatCurrency(endingNode.value)}
                    </div>
                  </div>
                ` : ''}
              </div>
            `;
          } else if (node.type === "total") {
            const changeValue = node.end - startingValue;
            const changeSign = changeValue >= 0 ? "+" : "";
            const changeColor = changeValue >= 0 ? "text-green-400" : "text-orange-400";
            
            // Calcular desglose de flujos del período completo
            const periodNodes = nodes.filter(n => n.type === "delta" && n.operatingFlow !== undefined);
            const totalOperating = periodNodes.reduce((sum, n) => sum + (n.operatingFlow || 0), 0);
            const totalInvesting = periodNodes.reduce((sum, n) => sum + (n.investingFlow || 0), 0);
            const totalFinancing = periodNodes.reduce((sum, n) => sum + (n.financingFlow || 0), 0);
            const hasFlows = Math.abs(totalOperating) > 0.01 || Math.abs(totalInvesting) > 0.01 || Math.abs(totalFinancing) > 0.01;
            
            tooltipContent = `
              <div class="font-bold text-sm mb-2 text-cyan-400">${node.key}</div>
              <div class="text-slate-200 font-semibold text-base mb-2">${formatCurrency(node.end)}</div>
              ${hasFlows ? `
                <div class="space-y-1.5 mb-2">
                  <div class="flex justify-between items-center">
                    <span class="text-slate-300 text-[10px]">Flujo Operativo:</span>
                    <span class="font-semibold text-[10px] ${totalOperating >= 0 ? 'text-green-400' : 'text-orange-400'}">
                      ${formatCurrency(totalOperating)}
                    </span>
                  </div>
                  <div class="flex justify-between items-center">
                    <span class="text-slate-300 text-[10px]">Flujo de Inversión:</span>
                    <span class="font-semibold text-[10px] ${totalInvesting >= 0 ? 'text-green-400' : 'text-orange-400'}">
                      ${formatCurrency(totalInvesting)}
                    </span>
                  </div>
                  <div class="flex justify-between items-center">
                    <span class="text-slate-300 text-[10px]">Flujo de Financiamiento:</span>
                    <span class="font-semibold text-[10px] ${totalFinancing >= 0 ? 'text-green-400' : 'text-orange-400'}">
                      ${formatCurrency(totalFinancing)}
                    </span>
                  </div>
                </div>
              ` : ''}
              <div class="pt-2 border-t border-slate-700">
                <div class="text-slate-300 text-[10px] mb-1">Variación del período:</div>
                <div class="${changeColor} font-semibold text-sm">
                  ${changeSign}${formatCurrency(changeValue)} 
                  ${percentageChange !== null ? `(${changeSign}${percentageChange.toFixed(1)}%)` : ''}
                </div>
                <div class="text-slate-400 text-[10px] mt-2">
                  Saldo al final del período
                </div>
                ${startingValue !== 0 ? `
                  <div class="text-slate-400 text-[10px] mt-1">
                    Saldo inicial: ${formatCurrency(startingValue)}
                  </div>
                ` : ''}
              </div>
            `;
          } else {
            // Períodos intermedios
            tooltipContent = `
            <div class="font-bold text-sm mb-1 text-cyan-400">${node.key}</div>
            <div class="text-slate-200 font-semibold text-base">${formatCurrency(node.end)}</div>
          `;
          
            if (percentageChange !== null) {
            const changeValue = node.end - startingValue;
            const changeSign = changeValue >= 0 ? "+" : "";
            const changeColor = changeValue >= 0 ? "text-green-400" : "text-orange-400";
            
            tooltipContent += `
              <div class="pt-2 mt-2 border-t border-slate-700">
                <div class="text-slate-300 text-[10px] mb-1">Cambio desde inicio:</div>
                <div class="${changeColor} font-semibold">
                  ${changeSign}${formatCurrency(changeValue)} (${changeSign}${percentageChange.toFixed(1)}%)
                </div>
              </div>
            `;
            }
          }
          
          tooltip.html(tooltipContent);
          tooltip.style("opacity", 1);
        })
        .on("mousemove", function(event) {
          const tooltipWidth = 200;
          const tooltipHeight = 100;
          const padding = 10;
          
          let left = event.pageX + padding;
          let top = event.pageY - padding;
          
          if (left + tooltipWidth > window.innerWidth) {
            left = event.pageX - tooltipWidth - padding;
          }
          
          if (top + tooltipHeight > window.innerHeight) {
            top = event.pageY - tooltipHeight - padding;
          }
          
          tooltip
            .style("left", left + "px")
            .style("top", top + "px");
        })
        .on("mouseout", function() {
          tooltip.style("opacity", 0);
        });
    }

    return;
  }

  // Formato original para waterfall simple (una sola fila)
  const sequence = config.sequence || Object.keys(data[0]);
  const baseRow = data[0];
  const steps = sequence
    .map((key, index) => ({
      key,
      value: Number(baseRow[key]) || 0,
      type: index === 0 ? "initial" : index === sequence.length - 1 ? "total" : "delta",
    }))
    .filter((step) => !Number.isNaN(step.value));

  let cumulative = 0;
  const nodes = steps.map((step) => {
    const start = step.type === "initial" ? 0 : cumulative;
    cumulative = step.type === "delta" ? cumulative + step.value : step.value;
    return {
      ...step,
      start,
      end: step.type === "delta" ? cumulative : step.value,
    };
  });

  const { width, height } = getBounding(container);
  const narrowChart = width < 640;
  const margin = {
    top: 24,
    right: narrowChart ? 8 : 24,
    bottom: narrowChart ? 52 : 40,
    left: narrowChart ? 44 : 72,
  };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleBand()
    .domain(nodes.map((node) => node.key))
    .range([margin.left, margin.left + innerWidth])
    .padding(narrowChart ? 0.25 : 0.4);

  const yMin = Math.min(0, d3.min(nodes, (node) => Math.min(node.start, node.end)) || 0);
  const yMax = d3.max(nodes, (node) => Math.max(node.start, node.end)) || 1;
  const yScale = d3
    .scaleLinear()
    .domain([yMin, yMax])
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const xAxisG = svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));
  if (narrowChart) {
    xAxisG
      .selectAll("text")
      .attr("transform", "rotate(-42)")
      .style("text-anchor", "end")
      .attr("dx", "-0.35em")
      .attr("dy", "0.15em");
  }

  const yAxis = d3.axisLeft(yScale).ticks(8);
  if (isCurrencyField("value")) {
    yAxis.tickFormat((d) => formatCurrency(d));
  }
  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(yAxis);

  svg
    .selectAll("rect")
    .data(nodes)
    .join("rect")
    .attr("x", (node) => xScale(node.key))
    .attr("y", (node) => yScale(Math.max(node.start, node.end)))
    .attr("height", (node) => Math.abs(yScale(node.start) - yScale(node.end)))
    .attr("width", xScale.bandwidth())
    .attr("fill", (node, index) => {
      if (node.type === "total") return "#0ea5e9";
      return node.end >= node.start ? COLORS[index % COLORS.length] : "#f97316";
    })
    .attr("rx", 6);
};

const renderCards = (container, data, config) => {
  ensureVisible(container);
  console.log("[renderCards] Renderizando:", { dataLength: data?.length, config, data });
  let reportSlug = dashboardRoot?.dataset?.reportSlug;
  if (!reportSlug && container) {
    const widgetElement = container.closest("section[data-report-slug]") || container.closest("[data-report-slug]");
    if (widgetElement?.dataset?.reportSlug) reportSlug = widgetElement.dataset.reportSlug;
  }
  // total-consolidado-operativo: data es lista de {label, value} — renderizar 4 cards verticales
  const isTotalConsolidadoOperativo = reportSlug === "total-consolidado-operativo";
  const isKpiList = isTotalConsolidadoOperativo && Array.isArray(data) && data.length > 0 && data[0].label != null && data[0].value != null;
  if (isKpiList) {
    console.log(`[renderCards] Total Consolidado: renderizando ${data.length} KPIs:`, data.map(d => d.label));
    const wrapper = d3.select(container).html("");
    // Detectar si estamos en workspace (contenedor más pequeño)
    const isInWorkspace = container.closest("[data-workspace-mode]") || container.closest("[data-widget-wrapper]");
    const gridClass = isInWorkspace
      ? "grid grid-cols-1 gap-2"
      : "grid grid-cols-1 gap-3 sm:gap-4 h-full";
    const grid = wrapper.append("div").attr("class", gridClass);
    const borderColors = ["#ea580c", "#2563eb", "#16a34a", "#7c3aed"];
    data.forEach((item, index) => {
      const isTotal = (item.label || "").toUpperCase().includes("TOTAL CONSOLIDADO");
      const cardClasses = isInWorkspace
        ? "flex flex-col justify-center rounded-lg px-2.5 py-2.5 bg-white dark:bg-slate-800 shadow-md border border-slate-200 dark:border-slate-700"
        : "flex flex-col justify-center rounded-xl sm:rounded-2xl px-3 sm:px-4 py-4 sm:py-6 bg-white dark:bg-slate-800 shadow-lg border border-slate-200 dark:border-slate-700";
      const labelClass = isInWorkspace
        ? "text-[10px] uppercase tracking-wide text-slate-600 dark:text-slate-300 mb-1 leading-tight"
        : "text-xs sm:text-sm uppercase tracking-wide text-slate-600 dark:text-slate-300 mb-1.5";
      const valueClass = isInWorkspace
        ? "text-base font-semibold text-slate-900 dark:text-slate-100"
        : "text-xl sm:text-2xl font-semibold text-slate-900 dark:text-slate-100";
      const subtitleClass = isInWorkspace
        ? "text-[9px] text-slate-500 dark:text-slate-400 mt-1 text-center font-medium"
        : "text-[10px] text-slate-500 dark:text-slate-400 mt-2 text-center font-medium";
      
      grid.append("div").attr("class", cardClasses).style("border-left", `3px solid ${borderColors[index] || "#64748b"}`).html(`
        <span class="${labelClass}">${(item.label || "").replace(/_/g, " ")}</span>
        <span class="${valueClass}">${formatCurrency(Number(item.value) || 0)}</span>
        ${isTotal ? `<p class="${subtitleClass}">VENTAS NETAS + REMITOS NO FACTURADOS + PEDIDOS EN ARMADO</p>` : ""}
      `);
    });
    return;
  }

  const numericFields = config.fields || discoverNumericFields(data);
  if (!numericFields.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas</p>";
    return;
  }
  const row = data[0] || {};
  const wrapper = d3.select(container).html("");
  const isSalesSummary = reportSlug === "sales_summary";
  const gridClass = isSalesSummary
    ? "grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 h-full"
    : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4 h-full";
  const grid = wrapper.append("div").attr("class", gridClass);

  let orderedFields = [];
  if (isSalesSummary) {
    const order = ["ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"];
    orderedFields = order.filter(field => numericFields.includes(field));
    // Agregar cualquier campo que no esté en el orden
    numericFields.forEach(field => {
      if (!orderedFields.includes(field)) {
        orderedFields.push(field);
      }
    });
  } else {
    orderedFields = numericFields;
  }

  // Renderizar todas las tarjetas en el orden especificado
  orderedFields.forEach((field, index) => {
    const value = Number(row[field]) || 0;
    const isCurrency = isCurrencyField(field);
    
    // Formatear labels específicos
    let displayLabel = toTitle(field);
    const fieldLower = field.toLowerCase();
    const isTotalConsolidado = fieldLower === "total_consolidado";
    
    if (fieldLower === "ventas_netas") {
      displayLabel = "VENTAS NETAS";
    } else if (fieldLower === "remitos_no_facturados") {
      displayLabel = "REMITOS NO FACTURADOS";
    } else if (fieldLower === "pedidos_pendientes") {
      displayLabel = "PEDIDOS PENDIENTES";
    } else if (isTotalConsolidado) {
      displayLabel = "TOTAL CONSOLIDADO";
    }
    
    // Agregar subtítulo con la fórmula para TOTAL CONSOLIDADO (más visible)
    let subtitle = "";
    if (isTotalConsolidado) {
      subtitle = `<p class="text-[10px] sm:text-[11px] text-purple-100 dark:text-purple-200 opacity-90 mt-2.5 sm:mt-3 text-center font-medium">VENTAS NETAS + REMITOS NO FACTURADOS + PEDIDOS PENDIENTES</p>`;
    }
    
    // Estilos diferenciados para TOTAL CONSOLIDADO
    // Ajustar colores para dark mode: usar colores más claros en dark mode
    const baseClasses = "flex flex-col justify-center rounded-xl sm:rounded-2xl px-3 sm:px-4 py-4 sm:py-6";
    const cardClasses = isTotalConsolidado
      ? `${baseClasses} bg-gradient-to-br from-purple-700 via-purple-800 to-purple-900 dark:from-purple-600 dark:via-purple-700 dark:to-purple-800 shadow-2xl shadow-purple-500/40 dark:shadow-purple-600/30 ring-2 ring-purple-400/30 dark:ring-purple-300/30 text-white`
      : `${baseClasses} bg-white dark:bg-slate-800 shadow-lg border border-slate-200 dark:border-slate-700`;
    
    const labelClasses = isTotalConsolidado
      ? "text-xs sm:text-sm uppercase tracking-[0.2em] sm:tracking-[0.3em] text-purple-100 dark:text-purple-50 mb-1.5 sm:mb-2 leading-tight font-semibold"
      : "text-xs sm:text-sm uppercase tracking-[0.2em] sm:tracking-[0.3em] text-slate-600 dark:text-slate-300 mb-1.5 sm:mb-2 leading-tight";
    
    const valueClasses = isTotalConsolidado
      ? "text-xl sm:text-2xl font-bold break-words text-white dark:text-purple-50"
      : "text-xl sm:text-2xl font-semibold break-words text-slate-900 dark:text-slate-100";
    
    const borderWidth = isTotalConsolidado ? "6px" : "4px";
    const borderColor = isTotalConsolidado ? "#a855f7" : COLORS[index % COLORS.length];
    
    grid
      .append("div")
      .attr("class", cardClasses)
      .html(`
        <span class="${labelClasses}">${displayLabel}</span>
        <span class="${valueClasses}">${isCurrency ? formatCurrency(value) : formatNumber(value)}</span>
        ${subtitle}
      `)
      .style("border-left", `${borderWidth} solid ${borderColor}`);
  });
};

const renderAreaChart = (container, data, config) => {
  renderLineChart(container, data, config, true);
};

const renderLollipopChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const valueField = config.y_field || discoverNumericFields(data)[0];
  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const sorted = [...data].sort((a, b) => (Number(a[valueField]) || 0) - (Number(b[valueField]) || 0));

  const yScale = d3
    .scaleBand()
    .domain(sorted.map((row) => row[xField]))
    .range([margin.top, margin.top + innerHeight])
    .padding(0.5);

  const xScale = d3
    .scaleLinear()
    .domain([0, d3.max(sorted, (row) => Number(row[valueField]) || 0) || 1])
    .nice()
    .range([margin.left, margin.left + innerWidth]);

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

  svg
    .append("g")
    .attr("transform", `translate(${margin.left}, 0)`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisLeft(yScale));

  svg
    .selectAll("line.lollipop")
    .data(sorted)
    .join("line")
    .attr("class", "lollipop")
    .attr("x1", xScale(0))
    .attr("x2", (row) => xScale(Number(row[valueField]) || 0))
    .attr("y1", (row) => yScale(row[xField]) + yScale.bandwidth() / 2)
    .attr("y2", (row) => yScale(row[xField]) + yScale.bandwidth() / 2)
    .attr("stroke", "#334155")
    .attr("stroke-width", 2);

  svg
    .selectAll("circle.lollipop")
    .data(sorted)
    .join("circle")
    .attr("class", "lollipop")
    .attr("cx", (row) => xScale(Number(row[valueField]) || 0))
    .attr("cy", (row) => yScale(row[xField]) + yScale.bandwidth() / 2)
    .attr("r", 8)
    .attr("fill", (_, index) => COLORS[index % COLORS.length]);
};

const renderBulletChart = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const valueField = config.value_field || discoverNumericFields(data)[0];
  const targetField = config.target_field || config.target || "target";
  const row = data[0];
  const value = Number(row[valueField]) || 0;
  const target = Number(row[targetField]) || value * 1.1;
  const max = Math.max(value, target) * 1.15;

  const { width, height } = getBounding(container);
  const margin = { top: 32, right: 24, bottom: 32, left: 72 };

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  const scale = d3.scaleLinear().domain([0, max]).range([margin.left, width - margin.right]);

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", height / 2 - 18)
    .attr("width", scale(max) - margin.left)
    .attr("height", 36)
    .attr("rx", 12)
    .attr("fill", "#1e293b");

  svg
    .append("rect")
    .attr("x", margin.left)
    .attr("y", height / 2 - 12)
    .attr("width", Math.max(scale(value) - margin.left, 0))
    .attr("height", 24)
    .attr("rx", 10)
    .attr("fill", "#38bdf8");

  svg
    .append("line")
    .attr("x1", scale(target))
    .attr("x2", scale(target))
    .attr("y1", height / 2 - 22)
    .attr("y2", height / 2 + 22)
    .attr("stroke", "#f97316")
    .attr("stroke-width", 4)
    .attr("stroke-linecap", "round");

  svg
    .append("text")
    .attr("x", scale(value))
    .attr("y", height / 2 - 24)
    .attr("class", "text-xs font-semibold fill-white")
    .attr("text-anchor", "end")
    .text(formatNumber(value));

  svg
    .append("text")
    .attr("x", scale(target))
    .attr("y", height / 2 + 36)
    .attr("class", "text-xs font-semibold fill-white")
    .attr("text-anchor", "middle")
    .text(`Objetivo ${formatNumber(target)}`);
};

const renderConnectedScatter = (container, data, config) => {
  ensureVisible(container);
  if (!window.d3 || !data?.length) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Visualización no disponible.</p>";
    return;
  }

  const xField = config.x_field || Object.keys(data[0])[0];
  const yField = config.y_field || discoverNumericFields(data)[0];
  const radiusField = config.radius_field || null;
  const labelField = config.label_field || xField;
  const showGrid = config.grid ?? true;
  const xLabel = config.x_label || toTitle(xField);
  const yLabel = config.y_label || toTitle(yField);

  const parsedData = data
    .map((row) => ({
      ...row,
      xValue: Number(row[xField]) || 0,
      yValue: Number(row[yField]) || 0,
      radiusValue: radiusField ? Number(row[radiusField]) || 0 : 0,
      labelValue: row[labelField],
    }))
    .sort((a, b) => a.xValue - b.xValue);

  const { width, height } = getBounding(container);
  const margin = { top: 40, right: 56, bottom: 64, left: 88 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleLinear()
    .domain(d3.extent(parsedData, (row) => row.xValue))
    .nice()
    .range([margin.left, margin.left + innerWidth]);

  const yScale = d3
    .scaleLinear()
    .domain(d3.extent(parsedData, (row) => row.yValue))
    .nice()
    .range([margin.top + innerHeight, margin.top]);

  const radiusScale = radiusField
    ? d3
        .scaleSqrt()
        .domain(d3.extent(parsedData, (row) => row.radiusValue))
        .range([6, 16])
    : () => 8;

  const line = d3
    .line()
    .curve(d3.curveCatmullRom.alpha(0.85))
    .x((row) => xScale(row.xValue))
    .y((row) => yScale(row.yValue));

  const svg = d3
    .select(container)
    .html("")
    .append("svg")
    .attr("viewBox", `0 0 ${width} ${height}`)
    .attr("preserveAspectRatio", "xMidYMid meet");

  if (showGrid) {
    svg
      .append("g")
      .attr("transform", `translate(0, ${margin.top + innerHeight})`)
      .attr("class", "pointer-events-none")
      .call(
        d3
          .axisBottom(xScale)
          .ticks(6)
          .tickSize(-innerHeight)
          .tickFormat("")
      )
      .call((axis) => axis.selectAll("line").attr("stroke", "rgba(148, 163, 184, 0.2)"))
      .call((axis) => axis.selectAll("path").remove());

    svg
      .append("g")
      .attr("transform", `translate(${margin.left}, 0)`)
      .attr("class", "pointer-events-none")
      .call(
        d3
          .axisLeft(yScale)
          .ticks(6)
          .tickSize(-innerWidth)
          .tickFormat("")
      )
      .call((axis) => axis.selectAll("line").attr("stroke", "rgba(148, 163, 184, 0.15)").attr("stroke-dasharray", "3 3"))
      .call((axis) => axis.selectAll("path").remove());
  }

  const xAxis = (g) =>
    g
      .attr("transform", `translate(0, ${margin.top + innerHeight})`)
      .call(d3.axisBottom(xScale).ticks(6, "%"))
      .call((axis) => axis.selectAll("text").attr("class", "fill-slate-400 text-[10px]"))
      .call((axis) => axis.selectAll("path,line").attr("stroke", "rgba(148, 163, 184, 0.35)"));

  const yAxis = (g) =>
    g
      .attr("transform", `translate(${margin.left}, 0)`)
      .call(d3.axisLeft(yScale).ticks(6, "%"))
      .call((axis) => axis.selectAll("text").attr("class", "fill-slate-400 text-[10px]"))
      .call((axis) => axis.selectAll("path,line").attr("stroke", "rgba(148, 163, 184, 0.35)"));

  svg.append("g").call(xAxis);
  svg.append("g").call(yAxis);

  svg
    .append("text")
    .attr("x", margin.left + innerWidth / 2)
    .attr("y", margin.top + innerHeight + 48)
    .attr("text-anchor", "middle")
    .attr("class", "text-xs font-semibold fill-slate-300")
    .text(xLabel);

  svg
    .append("text")
    .attr("transform", `translate(${margin.left - 56}, ${margin.top + innerHeight / 2}) rotate(-90)`)
    .attr("text-anchor", "middle")
    .attr("class", "text-xs font-semibold fill-slate-300")
    .text(yLabel);

  const path = svg
    .append("path")
    .datum(parsedData)
    .attr("fill", "none")
    .attr("stroke", "#38bdf8")
    .attr("stroke-width", 2.5)
    .attr("stroke-linejoin", "round")
    .attr("stroke-linecap", "round")
    .attr("d", line);

  const totalLength = path.node().getTotalLength();
  path
    .attr("stroke-dasharray", `${totalLength} ${totalLength}`)
    .attr("stroke-dashoffset", totalLength)
    .transition()
    .duration(1200)
    .ease(d3.easeCubicOut)
    .attr("stroke-dashoffset", 0);

  const nodes = svg
    .append("g")
    .selectAll("g")
    .data(parsedData)
    .join("g")
    .attr("transform", (row) => `translate(${xScale(row.xValue)}, ${yScale(row.yValue)})`);

  nodes
    .append("circle")
    .attr("r", 0)
    .attr("fill", "#0f172a")
    .attr("stroke", "#ffffff")
    .attr("stroke-width", 2)
    .transition()
    .delay((_, index) => 200 + index * 60)
    .duration(600)
    .ease(d3.easeBackOut.overshoot(1.2))
    .attr("r", (row) => radiusScale(row.radiusValue));

  nodes
    .append("text")
    .attr("text-anchor", "middle")
    .attr("dy", -6)
    .attr("opacity", 0)
    .attr("class", "text-[10px] font-semibold fill-white drop-shadow")
    .text((row) => row.labelValue)
    .transition()
    .delay((_, index) => 350 + index * 60)
    .duration(400)
    .attr("dy", (row) => -radiusScale(row.radiusValue) - 4)
    .attr("opacity", 1);
};

const renderUnsupportedChart = (container, type) => {
  container.innerHTML = `
    <div class="h-full w-full grid place-content-center text-xs text-slate-200 tracking-[0.2em] uppercase">
      ${type ? `Gráfico ${type} en desarrollo` : "Visualización no disponible"}
    </div>
  `;
};

// Normaliza config declarativo (x_dimension, y_metrics, series_dimension) a formato legacy (x_field, y_field, stack_field)
const normalizeBarConfig = (config, data) => {
  if (!config || !data?.length) return config || {};
  const first = data[0];
  const hasSucursal = first && first.nombre_sucursal !== undefined && first.nombre_sucursal !== null;
  const distinctSucursales = hasSucursal ? Array.from(new Set(data.map((r) => r.nombre_sucursal ?? ""))).filter(Boolean) : [];
  const shouldStackBySucursal = hasSucursal && distinctSucursales.length > 1;
  const stackField =
    config.stack_field ||
    config.series_dimension ||
    (config.group_field === "sucursal" && hasSucursal ? "nombre_sucursal" : config.group_field) ||
    (shouldStackBySucursal ? "nombre_sucursal" : undefined);
  return {
    ...config,
    x_field: config.x_field || config.x_dimension || (first.mes_formato ? "mes_formato" : "mes") || Object.keys(first)[0],
    y_field: config.y_field || config.value_field || (Array.isArray(config.y_metrics) ? config.y_metrics[0] : config.y_metrics) || "ventas_netas",
    stack_field: stackField,
    stacked: shouldStackBySucursal ? true : config.stacked,
  };
};

const widgetRenderers = {
  "d3-line": (container, data, config) => renderLineChart(container, data, config),
  "d3-line-area": (container, data, config) => renderLineChart(container, data, config, true),
  "d3-bar": (container, data, config) => {
    const first = data?.[0];
    const hasSucursal = first && first.nombre_sucursal !== undefined;
    const distinctSucursales = hasSucursal ? Array.from(new Set((data || []).map((r) => r.nombre_sucursal ?? ""))).filter(Boolean) : [];
    const useStackedBySucursal = hasSucursal && distinctSucursales.length > 1;
    if (useStackedBySucursal) {
      const normalized = {
        ...config,
        x_field: config.x_field || (first.mes_formato ? "mes_formato" : "mes"),
        y_field: config.y_field || config.value_field || "ventas_netas",
        stack_field: "nombre_sucursal",
      };
      renderStackedBarChart(container, data, normalized);
    } else {
      renderBarChart(container, data, config);
    }
  },
  "d3-bar-grouped": (container, data, config) => {
    const first = data?.[0];
    const stackBySucursal =
      (config.group_field === "sucursal" || config.group_field === "nombre_sucursal") &&
      first &&
      first.nombre_sucursal !== undefined &&
      Array.from(new Set((data || []).map((r) => r.nombre_sucursal))).filter(Boolean).length > 1;
    if (stackBySucursal) {
      const normalized = {
        ...config,
        x_field: config.x_field || (first.mes_formato ? "mes_formato" : "mes"),
        y_field: config.y_field || config.value_field || "ventas_netas",
        stack_field: "nombre_sucursal",
      };
      renderStackedBarChart(container, data, normalized);
    } else {
      renderGroupedBarChart(container, data, config);
    }
  },
  "d3-bar-stacked": (container, data, config) => renderStackedBarChart(container, data, config),
  "bar": (container, data, config) => {
    const normalized = normalizeBarConfig(config, data);
    const useStacked =
      normalized.stack_field ||
      config?.stacked === true ||
      config?.series_dimension ||
      (data?.length && data[0].nombre_sucursal !== undefined && Array.from(new Set(data.map((r) => r.nombre_sucursal))).length > 1);
    if (useStacked) {
      renderStackedBarChart(container, data, normalized);
    } else {
      renderBarChart(container, data, normalized);
    }
  },
  "d3-heatmap": (container, data, config) => renderHeatmap(container, data, config),
  "d3-gauge": (container, data, config) => renderGauge(container, data, config),
  "d3-waterfall": (container, data, config) => renderWaterfall(container, data, config),
  "d3-cards": (container, data, config) => renderCards(container, data, config),
  "d3-area": (container, data, config) => renderAreaChart(container, data, config),
  "d3-lollipop": (container, data, config) => renderLollipopChart(container, data, config),
  "d3-bullet": (container, data, config) => renderBulletChart(container, data, config),
  "d3-connected-scatter": (container, data, config) => renderConnectedScatter(container, data, config),
};

const renderChart = (widget, data, configParam) => {
  const container = widget.querySelector("[data-widget-content]");
  if (!container) return;
  const config = configParam || getWidgetConfig(widget);
  const type = widget.dataset.widgetType;
  const renderer = widgetRenderers[type];

  // Para d3-cards, permitir renderizar incluso si no hay datos (usa config.fields)
  const isCards = type === "d3-cards";
  
  if (!data?.length && !isCards) {
    container.innerHTML = `
      <div class="h-full w-full grid place-content-center text-xs text-slate-200 tracking-[0.2em] uppercase">
        Sin datos disponibles
      </div>
    `;
    return;
  }

  // Para d3-cards sin datos, crear datos vacíos pero permitir que renderCards use config.fields
  const dataToRender = isCards && (!data || !data.length) ? [{}] : (data || []);

  if (!window.d3) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Cargando librería D3...</p>";
    return;
  }

  if (renderer) {
    renderer(container, dataToRender, config);
  } else {
    renderUnsupportedChart(container, type);
  }
};

/**
 * Renderiza el gráfico de un widget, usando WidgetEngine para Ventas Netas bar
 * o renderChart para el resto. Usar esto en lugar de renderChart directo para
 * evitar que ResizeObserver/reRenderAllCharts sobrescriban el gráfico de WidgetEngine.
 */
const renderWidgetChart = (widget, data, config, meta = {}) => {
  // En workspace el reportSlug está en el widget; en dashboard detail en dashboardRoot
  const reportSlug = widget.dataset?.reportSlug || dashboardRoot?.dataset?.reportSlug;
  const widgetType = widget.dataset?.widgetType;
  const useWidgetEngine =
    isVentasNetasSlug(reportSlug) &&
    (widgetType === "d3-bar-grouped" || widgetType === "d3-bar" || widgetType === "d3-bar-stacked" || widgetType === "bar") &&
    window.WidgetEngine &&
    data?.length > 0;

  if (useWidgetEngine) {
    const chartContainer = widget.querySelector("[data-widget-content]");
    if (chartContainer) {
      const widgetEngine = Object.create(window.WidgetEngine);
      widgetEngine.queryResult = { data, meta };
      widgetEngine.reportSlug = reportSlug;
      widgetEngine.rootElement = dashboardRoot;
      widgetEngine.schema = {
        metrics: [{ name: "ventas_netas", label: "Ventas Netas", data_type: "currency" }],
        dimensions: [
          { name: "mes", label: "Mes", data_type: "date" },
          { name: "nombre_sucursal", label: "Sucursal", data_type: "string" }
        ]
      };
      const widgetSchema = {
        x_dimension: "mes",
        y_metrics: ["ventas_netas"],
        series_dimension: "nombre_sucursal",
        options: { stacked: true, unit: "ARS" },
        kind: "bar"
      };
      widgetEngine.renderBarChart(chartContainer, widgetSchema);
      chartContainer.setAttribute("data-rendered-by", "widget-engine");
      chartContainer.style.position = "relative";
      if (!chartContainer.querySelector("[data-widget-engine-badge]")) {
        const badge = document.createElement("div");
        badge.className = "absolute bottom-1 right-2 text-[9px] text-slate-500 dark:text-slate-400 opacity-50 pointer-events-none";
        badge.textContent = "WidgetEngine";
        badge.setAttribute("data-widget-engine-badge", "true");
        chartContainer.appendChild(badge);
      }
      // Botón Colores + panel de personalización (igual que reportes declarativos)
      const actionsDiv = widget.querySelector("[data-toggle-table]")?.parentElement ||
        widget.querySelector("header > div:last-child");
      if (actionsDiv && !widget.querySelector("[data-customize-colors]")) {
        const colorBtn = document.createElement("button");
        colorBtn.type = "button";
        colorBtn.dataset.customizeColors = "";
        colorBtn.className = "inline-flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold text-purple-500 hover:text-purple-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-purple-400 rounded-full px-2.5 sm:px-3 py-1 transition";
        colorBtn.innerHTML = `
          <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M7 21a4 4 0 0 1-4-4V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v12a4 4 0 0 1-4 4Zm0 0h12a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 0 1 2.828 0l2.829 2.829a2 2 0 0 1 0 2.828l-8.486 8.485M7 17h.01" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">Colores</span>
        `;
        colorBtn.title = "Personalizar colores de las series";
        actionsDiv.insertBefore(colorBtn, actionsDiv.firstChild);
        widgetEngine.attachColorCustomizer(widget, widgetSchema);
      }
    }
  } else {
    const chartContainer = widget.querySelector("[data-widget-content]");
    if (chartContainer) chartContainer.removeAttribute("data-rendered-by");
    renderChart(widget, data, config);
  }
};

const renderTable = (widgetElement, data, options = {}) => {
  const show = options.show ?? false;
  const tableReportSlugEarly =
    widgetElement?.dataset?.reportSlug || dashboardRoot?.dataset?.reportSlug || "";

  if (isLogisticaListaComprobantesRutasSlug(tableReportSlugEarly) && options.logisticaToolbarRefresh) {
    const cached = logisticaListaDataByWidget.get(widgetElement);
    if (cached) {
      data = cached;
    }
  } else if (isLogisticaListaComprobantesRutasSlug(tableReportSlugEarly) && Array.isArray(data)) {
    logisticaListaDataByWidget.set(widgetElement, data);
  }

  const target = widgetElement.querySelector("[data-widget-table-wrapper]") || widgetElement;

  if (!show) {
    target.classList.add("hidden");
    return;
  }

  target.classList.remove("hidden");

  // Ventas Netas: usar WidgetEngine para tabla con agrupación (Agrupar por, filas expandibles)
  const reportSlug = widgetElement.dataset?.reportSlug || dashboardRoot?.dataset?.reportSlug;
  const isVentasNetas = isVentasNetasSlug(reportSlug) ||
    (data?.[0] && data[0].mes_formato !== undefined && data[0].nombre_sucursal !== undefined && data[0].ventas_netas !== undefined);

  if (isVentasNetas && window.WidgetEngine && data?.length > 0) {
    target.innerHTML = "";
    const cached = widgetElement.dataset?.widgetId ? widgetDataCache.get(widgetElement.dataset.widgetId) : null;
    const meta = options.meta || cached?.meta || {};
    const widgetEngine = Object.create(window.WidgetEngine);
    widgetEngine.queryResult = { data, meta };
    widgetEngine.rootElement = dashboardRoot;
    widgetEngine.schema = {
      dimensions: [
        { name: "mes_formato", label: "MES", data_type: "string" },
        { name: "nombre_sucursal", label: "SUCURSAL", data_type: "string" },
        { name: "nro_punto_venta", label: "PUNTO DE VENTA", data_type: "string" }
      ],
      metrics: [
        { name: "ventas_netas", label: "Ventas Netas", data_type: "currency" },
        { name: "notas_credito", label: "Notas Crédito", data_type: "currency" },
        { name: "ventas_brutas", label: "Ventas Brutas", data_type: "currency" }
      ]
    };
    const widgetSchema = {
      id: `ventas_netas_table_${widgetElement.dataset?.widgetId || "main"}`,
      kind: "table",
      options: {
        table_dimensions: ["mes_formato", "nombre_sucursal", "nro_punto_venta"],
        table_metrics: ["ventas_netas", "notas_credito", "ventas_brutas"]
      }
    };
    widgetEngine.reportSlug = reportSlug;
    widgetEngine.renderTable(target, widgetSchema);
    return;
  }

  target.innerHTML = "";

  if (!data || !data.length) {
    const emptyMessage = widgetElement.dataset.emptyLabel || "Sin datos disponibles.";
    target.innerHTML = `<p class="text-sm text-slate-500 dark:text-slate-400">${emptyMessage}</p>`;
    if (show) {
      target.classList.remove("hidden");
    }
    if (show && isLogisticaListaComprobantesRutasSlug(tableReportSlugEarly)) {
      document.getElementById("logistica-lista-tabla-toolbar")?.classList.remove("hidden");
    }
    return;
  }
  
  // Debug: verificar que los datos sean un array de objetos, no solo totales
  if (data.length > 0 && typeof data[0] !== 'object') {
    console.warn("renderTable: Los datos no son un array de objetos", data);
    return;
  }

  const table = document.createElement("table");
  table.className =
    "min-w-full text-[11px] text-left bg-white dark:bg-slate-950 border border-slate-100 dark:border-slate-800 rounded-xl overflow-hidden";

  const thead = document.createElement("thead");
  thead.className =
    "bg-slate-50 dark:bg-slate-900/40 text-slate-500 dark:text-slate-300 uppercase tracking-wide";
  const headerRow = document.createElement("tr");

  // Columnas a excluir
  let excludedColumns = ["id_sucursal", "id_punto_venta", "mes"];
  const tableReportSlug = widgetElement.dataset?.reportSlug || dashboardRoot?.dataset?.reportSlug;
  if (isPedidosPendientesSlug(tableReportSlug)) {
    excludedColumns = excludedColumns.concat(["tipo_comprobante", "estado"]);
  }
  if (isLogisticaListaComprobantesRutasSlug(tableReportSlug)) {
    excludedColumns = excludedColumns.concat([
      "cod_mov_remito",
      "cod_mov_pedido",
      "entregado",
      "id_usuario_no_entrega",
    ]);
  }
  /** Lista comprobantes en rutas: unir claves de todas las filas (evita que ``data[0]`` omita columnas y desalinee thead vs cuerpo). */
  let allKeys;
  if (isLogisticaListaComprobantesRutasSlug(tableReportSlug) && data?.length) {
    const uni = new Set();
    data.forEach((row) => {
      if (row && typeof row === "object") {
        Object.keys(row).forEach((k) => {
          if (!excludedColumns.includes(k)) uni.add(k);
        });
      }
    });
    allKeys = Array.from(uni);
  } else {
    allKeys = Object.keys(data[0]).filter((key) => !excludedColumns.includes(key));
  }

  // Ventas Netas: orden de columnas y agrupación visual (MES, SUCURSAL, PUNTO DE VENTA, métricas)
  const isVentasNetasTable = data[0].mes_formato !== undefined && data[0].nombre_sucursal !== undefined && data[0].ventas_netas !== undefined;
  const ventasNetasColumnOrder = ["mes_formato", "nombre_sucursal", "nro_punto_venta", "ventas_netas", "notas_credito", "ventas_brutas"];
  const logisticaListaCrOrder = [
    "fecha_factura",
    "nro_remito",
    "nro_factura",
    "estado_entrega",
    "cliente",
    "nombre_chofer",
    "nombre_usuario_entrega",
    "desc_ruta",
    "estado_ruta",
    "fecha_salida_ruta_fmt",
    "fecha_hora_entrega_fmt",
    "total_remito",
  ];
  const isLogisticaListaCrTable =
    isLogisticaListaComprobantesRutasSlug(tableReportSlug) &&
    data[0].fecha_factura !== undefined &&
    data[0].nro_remito !== undefined;
  const fieldKeys = isVentasNetasTable
    ? ventasNetasColumnOrder.filter((k) => allKeys.includes(k))
    : isLogisticaListaCrTable
      ? logisticaListaCrOrder.filter((k) => allKeys.includes(k))
      : allKeys;

  // Ordenar datos para Ventas Netas: mes DESC, sucursal ASC, punto de venta ASC
  let dataToRender = isVentasNetasTable
    ? [...data].sort((a, b) => {
        const mesCmp = (b.mes || "").localeCompare(a.mes || "");
        if (mesCmp !== 0) return mesCmp;
        const sucCmp = (a.nombre_sucursal || "").localeCompare(b.nombre_sucursal || "");
        if (sucCmp !== 0) return sucCmp;
        return String(a.nro_punto_venta || "").localeCompare(String(b.nro_punto_venta || ""));
      })
    : isLogisticaListaCrTable
      ? [...data]
      : data;

  /** Campos de agrupación (orden de chips) para lista comprobantes / rutas */
  let logisticaGroupKeys = [];
  if (isLogisticaListaCrTable) {
    const searchInput = document.getElementById("logistica-lista-tabla-search");
    const q = (searchInput && searchInput.value) || "";
    logisticaGroupKeys = getLogisticaListaGroupKeysFromChips();
    let rows = Array.isArray(dataToRender) ? [...dataToRender] : [];
    const searchKeys = [...fieldKeys, ...LOGISTICA_LISTA_CR_SEARCH_KEYS_EXTRA];
    rows = filterLogisticaListaRowsBySearch(rows, q, searchKeys);
    if (!logisticaGroupKeys.length) {
      rows = sortLogisticaListaByGroupKeys(rows, logisticaGroupKeys);
    }
    dataToRender = rows;
  }

  if (isLogisticaListaCrTable) {
    ensureSynapLogisticaListaCrTableStylesOnce();
    table.className =
      "synap-logistica-lista-cr-table vo-jerarquia-table min-w-full table-fixed border-collapse text-xs text-slate-900 antialiased dark:bg-slate-950 dark:text-slate-100 bg-white rounded-t-md border border-slate-200 dark:border-slate-600";
    table.setAttribute("dir", "ltr");
    thead.className = "";
  }

  // Mapeo de términos en inglés a español
  const headerTranslations = {
    "period": "PERÍODO",
    "mes_formato": "MES",
    "mes": "MES",
    "nombre_sucursal": "SUCURSAL",
    "nro_punto_venta": "PUNTO DE VENTA",
    "notas_credito": "NOTAS CRÉDITO",
    "ventas_netas": "VENTAS NETAS",
    "ventas_brutas": "VENTAS BRUTAS",
    "operating_flow": "FLUJO OPERATIVO",
    "investing_flow": "FLUJO DE INVERSIÓN",
    "financing_flow": "FLUJO DE FINANCIAMIENTO",
    "cash_variation": "VARIACIÓN DE CAJA",
    "cumulative": "ACUMULADO",
    "type": "TIPO",
    "operating_ingresos": "INGRESOS OPERATIVOS",
    "operating_egresos": "EGRESOS OPERATIVOS",
    fecha_remito: "FECHA REMITO",
    fecha_factura: "FECHA FACTURA",
    mes_factura_ym: "MES DE FACTURA",
    nro_remito: "Nº REMITO",
    nro_pedido: "Nº PEDIDO",
    nro_factura: "Nº FACTURA",
    estado_entrega: "ESTADO ENTREGA",
    cliente: "CLIENTE",
    nombre_chofer: "CHOFER",
    nombre_usuario_entrega: "USUARIO ENTREGA",
    desc_ruta: "HOJA DE RUTA",
    estado_ruta: "ESTADO RUTA",
    orden_ruta: "ORDEN EN RUTA",
    fecha_salida_ruta_fmt: "SALIDA PROGRAMADA (RUTA)",
    ventana_horaria_ruta: "FRANJA HORARIA (RUTA)",
    fecha_hora_entrega_fmt: "FECHA/HORA ENTREGA",
    motivo_no_entrega: "MOTIVO NO ENTREGA",
    total_remito: "TOTAL REMITO",
  };
  
  fieldKeys.forEach((key) => {
    const th = document.createElement("th");
    const isCurrency = isCurrencyField(key);
    if (isLogisticaListaCrTable) {
      const lcSty = logisticaListaCrColumnStyle(key);
      if (isCurrency) {
        th.className = `${LOGISTICA_LISTA_CR_TH_STICKY} border border-slate-200 dark:border-slate-600 min-w-0 max-w-full px-2.5 py-2 text-[10px] font-bold uppercase tracking-wide align-middle whitespace-nowrap synap-lc-col-money ${lcSty.headerBg}`;
        th.style.setProperty("text-align", "right", "important");
      } else {
        th.className = `${LOGISTICA_LISTA_CR_TH_STICKY} border border-slate-200 dark:border-slate-600 min-w-0 max-w-full px-2.5 py-2 text-[10px] font-bold uppercase tracking-wide align-middle ${lcSty.headerBg} ${lcSty.thAlign}`;
      }
    } else {
      th.className = `px-4 py-3 ${isCurrency ? "text-right" : ""}`;
    }

    // Usar traducción si existe, sino convertir a formato legible
    let headerText = headerTranslations[key.toLowerCase()];
    if (!headerText) {
      headerText = key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
    }

    if (isLogisticaListaCrTable && isCurrency) {
      logisticaSetThMoneyContent(th, headerText);
    } else {
      th.textContent = headerText;
    }
    headerRow.appendChild(th);
  });
  if (isLogisticaListaCrTable) {
    const thAct = document.createElement("th");
    thAct.className = logisticaListaCrThClassAcciones();
    thAct.style.setProperty("text-align", "right", "important");
    thAct.textContent = "ACCIONES";
    headerRow.appendChild(thAct);
  }
  thead.appendChild(headerRow);
  if (isLogisticaListaCrTable) {
    const colgroup = document.createElement("colgroup");
    const nCols = fieldKeys.length + 1;
    const wPct = `${(100 / nCols).toFixed(4)}%`;
    for (let i = 0; i < nCols; i += 1) {
      const col = document.createElement("col");
      col.style.width = wPct;
      colgroup.appendChild(col);
    }
    table.appendChild(colgroup);
  }
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  if (!isLogisticaListaCrTable) {
    tbody.className = "divide-y divide-slate-100 dark:divide-slate-800";
  } else {
    tbody.className = "";
  }

  // Detectar si es cash_flow_waterfall (tiene filas con type: "starting" o "ending")
  const isCashFlowWaterfall = data.some(row => row.type === "starting" || row.type === "ending");
  
  // Calcular totales para columnas monetarias (solo variaciones, no acumulados)
  const totals = {};
  const columnsToTotal = ["operating_flow", "investing_flow", "financing_flow", "cash_variation"];
  
  if (!isCashFlowWaterfall) {
    // Para otros reportes, sumar todas las columnas monetarias
  fieldKeys.forEach((key) => {
    if (isCurrencyField(key)) {
      totals[key] = 0;
    }
  });
  } else {
    // Para cash_flow_waterfall, solo sumar variaciones (no acumulados ni saldos)
    columnsToTotal.forEach((key) => {
      if (fieldKeys.includes(key)) {
        totals[key] = 0;
      }
    });
  }

  // Mostrar más registros para reportes de tabla (pivot-table)
  const maxRows = 1000;
  const rowsToRender = dataToRender.slice(0, maxRows);
  const useLogisticaNestedGroups =
    isLogisticaListaCrTable && logisticaGroupKeys.length > 0;
  let logisticaGroupedTree = null;

  let prevMes = null;
  let prevSucursal = null;

  if (useLogisticaNestedGroups) {
    const metricKeysLg = fieldKeys.filter((k) => isCurrencyField(k));
    logisticaGroupedTree = groupLogisticaListaData(rowsToRender, logisticaGroupKeys, metricKeysLg);
    const groupIdPrefix = `lg-${Math.random().toString(36).slice(2, 10)}-`;
    tbody.innerHTML =
      logisticaListaCrColAnchorRowHtml(fieldKeys) +
      renderLogisticaGroupedTreeHtml(
        logisticaGroupedTree,
        fieldKeys,
        headerTranslations,
        metricKeysLg,
        groupIdPrefix,
        0,
        true,
      );
  } else {
  rowsToRender.forEach((row) => {
    const tr = document.createElement("tr");
    if (isLogisticaListaCrTable) {
      tr.className =
        "hover:bg-slate-50/90 dark:hover:bg-slate-900/35 transition-colors bg-white dark:bg-slate-950";
    } else {
      tr.className =
        "hover:bg-slate-50/70 dark:hover:bg-slate-900/60 transition-colors";
    }

    // Agrupación visual para Ventas Netas: borde superior al cambiar mes o sucursal
    if (isVentasNetasTable) {
      const currMes = row.mes || row.mes_formato;
      const currSucursal = row.nombre_sucursal;
      const isNewMes = prevMes !== null && currMes !== prevMes;
      const isNewSucursal = prevMes === currMes && prevSucursal !== null && currSucursal !== prevSucursal;
      if (isNewMes || isNewSucursal) {
        tr.classList.add("border-t", "border-slate-300", "dark:border-slate-600");
        if (isNewMes) tr.classList.add("border-t-2");
      }
      prevMes = currMes;
      prevSucursal = currSucursal;
    }

    // Resaltar filas de saldo inicial y final
    if (isCashFlowWaterfall && (row.type === "starting" || row.type === "ending")) {
      tr.className += " bg-blue-50 dark:bg-blue-900/20";
    }

    fieldKeys.forEach((key, index) => {
      const value = row[key];
      const td = document.createElement("td");
      const isCurrency = isCurrencyField(key);
      if (isLogisticaListaCrTable) {
        const lcSty = logisticaListaCrColumnStyle(key);
        if (isCurrency) {
          td.className = `${LOGISTICA_LISTA_CR_TD_MONEY} ${lcSty.bodyBg}`;
          td.style.setProperty("text-align", "right", "important");
        } else {
          td.className = `${LOGISTICA_LISTA_CR_TD_BASE} ${lcSty.tdAlign} ${lcSty.bodyBg}`;
        }
      } else {
        td.className = `px-4 py-3 text-slate-700 dark:text-slate-200 ${isCurrency ? "text-right font-medium" : ""}`;
      }

      // Formatear valores
      if (value === null || value === undefined || value === "") {
        if (isLogisticaListaCrTable && isCurrency) {
          logisticaSetTdMoneyContent(td, "");
        } else {
          td.textContent = "";
        }
      } else if (key.toLowerCase() === "type" || key.toLowerCase() === "tipo") {
        // Traducir valores de tipo al español
        const typeTranslations = {
          "starting": "Inicial",
          "period": "Período",
          "ending": "Final"
        };
        td.textContent = typeTranslations[value.toLowerCase()] || value;
      } else if (isCurrency) {
        if (isLogisticaListaCrTable) {
          logisticaSetTdMoneyContent(td, String(formatCurrency(value)));
        } else {
          td.textContent = formatCurrency(value);
        }
      } else {
        td.textContent = formatNumber(value);
      }
      
      tr.appendChild(td);
      
      // Acumular totales solo para columnas de variación (no acumulados ni saldos)
      if (isCashFlowWaterfall) {
        if (columnsToTotal.includes(key) && typeof value === "number" && row.type === "period") {
          totals[key] += value;
        }
      } else {
        // Para otros reportes, acumular todas las columnas monetarias
      if (isCurrency && typeof value === "number") {
        totals[key] += value;
        }
      }
    });
    if (isLogisticaListaCrTable) {
      const tdAct = document.createElement("td");
      tdAct.className = logisticaListaCrTdClassAcciones();
      tdAct.style.setProperty("text-align", "right", "important");
      const wrap = document.createElement("div");
      wrap.className = "synap-lc-actions-inner";
      const codR = row.cod_mov_remito;
      const codP = row.cod_mov_pedido;
      const btnDet = document.createElement("button");
      btnDet.type = "button";
      btnDet.className =
        "text-[10px] font-semibold text-sky-600 hover:text-sky-500 dark:text-sky-400 underline-offset-2 hover:underline";
      btnDet.textContent = "Detalle";
      btnDet.setAttribute("data-logistica-detalle", String(codR ?? ""));
      const btnEnt = document.createElement("button");
      btnEnt.type = "button";
      btnEnt.className =
        "text-[10px] font-semibold text-emerald-600 hover:text-emerald-500 dark:text-emerald-400 underline-offset-2 hover:underline";
      btnEnt.textContent = "Entrega";
      btnEnt.setAttribute("data-logistica-entrega", String(codR ?? ""));
      btnEnt.setAttribute("data-logistica-pedido", String(codP ?? ""));
      wrap.appendChild(btnDet);
      wrap.appendChild(btnEnt);
      tdAct.appendChild(wrap);
      tr.appendChild(tdAct);
    }
    tbody.appendChild(tr);
  });
  }

  // Agregar fila de totales solo si hay columnas monetarias y no es cash_flow_waterfall ni sales_summary
  const currentReportSlug = dashboardRoot?.dataset?.reportSlug || widgetElement?.dataset?.reportSlug;
  const shouldShowTotals =
    Object.keys(totals).length > 0 &&
    !isCashFlowWaterfall &&
    currentReportSlug !== "sales_summary" &&
    currentReportSlug !== "total-consolidado-operativo" &&
    !isLogisticaListaComprobantesRutasSlug(currentReportSlug);
  
  if (shouldShowTotals) {
    const totalsRow = document.createElement("tr");
    totalsRow.className = "bg-slate-100 dark:bg-slate-800 border-t-2 border-slate-300 dark:border-slate-600 font-semibold";
    fieldKeys.forEach((key, index) => {
      const td = document.createElement("td");
      const isCurrency = isCurrencyField(key);
      if (isCurrency && totals[key] !== undefined) {
        td.className = "px-4 py-3 text-slate-900 dark:text-white text-right font-bold";
        td.textContent = formatCurrency(totals[key]);
      } else if (index === 0) {
        // Solo la primera columna muestra "TOTAL"
        td.className = "px-4 py-3 text-slate-900 dark:text-white font-semibold";
        td.textContent = "TOTAL";
      } else {
        // Las demás columnas de texto quedan vacías
        td.className = "px-4 py-3 text-slate-900 dark:text-white";
        td.textContent = "";
      }
      totalsRow.appendChild(td);
    });
    tbody.appendChild(totalsRow);
  }

  table.appendChild(tbody);
  target.innerHTML = "";

  const sr = window.SynapReportsResponsive;
  const mobileLabelMap = {};
  fieldKeys.forEach((k) => {
    mobileLabelMap[k] =
      headerTranslations[k.toLowerCase()] ||
      headerTranslations[k] ||
      undefined;
  });
  const mobileColumns = sr ? sr.buildColumnsFromKeys(fieldKeys, mobileLabelMap) : [];
  const formatCellForMobile = (key, value) => {
    if (!sr) return String(value ?? "");
    if (value == null || value === "") return "—";
    if (key.toLowerCase() === "type" || key.toLowerCase() === "tipo") {
      const typeTranslations = {
        starting: "Inicial",
        period: "Período",
        ending: "Final",
      };
      return sr.escHtml(typeTranslations[String(value).toLowerCase()] || String(value));
    }
    if (isCurrencyField(key)) return sr.escHtml(formatCurrency(value));
    return sr.escHtml(formatNumber(value));
  };
  const mountResponsiveTable = () => {
    if (sr) {
      sr.mountDualTableView(target, table, {
        columns: mobileColumns,
        rows: rowsToRender,
        formatCell: formatCellForMobile,
        reportSlug:
          tableReportSlug ||
          widgetElement?.dataset?.reportSlug ||
          dashboardRoot?.dataset?.reportSlug ||
          "",
      });
    } else {
      target.appendChild(table);
    }
  };

  if (isLogisticaListaCrTable) {
    mountResponsiveTable();
    const logisticaScrollHost = document.getElementById("logistica-lista-cr-scroll");
    if (useLogisticaNestedGroups) {
      attachLogisticaGroupToggleListeners(logisticaScrollHost || target);
    }
    const foot = document.createElement("p");
    foot.className = "mt-2 px-2 text-xs text-slate-400 dark:text-slate-500 sm:px-2";
    const qTabla = (document.getElementById("logistica-lista-tabla-search")?.value || "").trim();
    const totalOriginal =
      logisticaListaDataByWidget.get(widgetElement)?.length ?? data.length;
    let legendText;
    if (useLogisticaNestedGroups && logisticaGroupedTree) {
      const nGr = countLogisticaGroupNodes(logisticaGroupedTree);
      const agrTxt = nGr === 1 ? "agrupación" : "agrupaciones";
      const agrDims = logisticaGroupKeys.map(
        (k) => LOGISTICA_LISTA_CR_GROUP_KEY_LABELS[k] || k.replace(/_/g, " "),
      );
      legendText = `Lista comprobantes en rutas. Agrupado por: ${agrDims.join(" → ")}. ${nGr} ${agrTxt}. `;
      if (qTabla.length >= 2) {
        legendText += `Mostrando ${dataToRender.length} de ${totalOriginal} renglones.`;
      } else if (dataToRender.length > maxRows) {
        legendText += `Mostrando las primeras ${maxRows} de ${dataToRender.length} renglones.`;
      } else {
        legendText += `Mostrando ${dataToRender.length} renglones.`;
      }
    } else if (qTabla.length >= 2) {
      legendText = `Mostrando ${dataToRender.length} de ${totalOriginal} renglones`;
    } else if (dataToRender.length > maxRows) {
      legendText = `Mostrando las primeras ${maxRows} de ${dataToRender.length} renglones`;
    } else {
      legendText = `Mostrando ${dataToRender.length} renglones`;
    }
    foot.textContent = legendText;
    target.appendChild(foot);
  } else {
    mountResponsiveTable();
  }

  if (show) {
    target.classList.remove("hidden");
  }

  if (show && isLogisticaListaComprobantesRutasSlug(tableReportSlugEarly)) {
    document.getElementById("logistica-lista-tabla-toolbar")?.classList.remove("hidden");
  }

  if (show && isLogisticaListaCrTable && !widgetElement.dataset.logisticaActionDelegate) {
    widgetElement.dataset.logisticaActionDelegate = "1";
    widgetElement.addEventListener("click", (e) => {
      const det = e.target.closest("[data-logistica-detalle]");
      if (det && window.SynapLogisticaListaCR?.openDetalle) {
        const v = det.getAttribute("data-logistica-detalle");
        if (v !== null && v !== "") window.SynapLogisticaListaCR.openDetalle(v);
        return;
      }
      const ent = e.target.closest("[data-logistica-entrega]");
      if (ent && window.SynapLogisticaListaCR?.openEntrega) {
        window.SynapLogisticaListaCR.openEntrega({
          cod_mov_remito: ent.getAttribute("data-logistica-entrega"),
          cod_mov_pedido: ent.getAttribute("data-logistica-pedido") || "",
        });
      }
    });
  }
};

/**
 * Re-renderiza la tabla del informe lista comprobantes / rutas usando la caché de filas
 * (agrupación y búsqueda sobre datos ya cargados; no vuelve a llamar a la API).
 */
window.refreshLogisticaListaComprobantesTabla = function refreshLogisticaListaComprobantesTabla() {
  const widget = document.querySelector("[data-widget-id]");
  if (!widget || !dashboardRoot) return;
  renderTable(widget, null, { show: true, logisticaToolbarRefresh: true });
};

// Movimientos detallados de caja: reports/static/reports/js/cash_flow_detailed_movements.js
window.fetchDetailedMovements = function fetchDetailedMovementsDelegated() {
  if (window.cashFlowDetailedMovementsHandler?.fetchForWaterfall) {
    return window.cashFlowDetailedMovementsHandler.fetchForWaterfall();
  }
};

/** Debe estar en ámbito de módulo: renderSummary (también de módulo) la invoca al cargar datos BO. */
function syncBoDualSummaryPeriod() {
  const slug = document.querySelector("#dashboard-root")?.dataset?.reportSlug;
  if (!isInformeBoDualPeriodo(slug) || !document.getElementById("bo-period-filters-root")) {
    return;
  }
  const boPeriodEl = document.getElementById("bo-summary-period");
  const voPeriodEl = document.getElementById("vo-summary-period");
  if (!boPeriodEl && !voPeriodEl) return;
  const fmt = (s) => {
    if (!s) return "—";
    const p = String(s).split("-");
    return p.length === 3 ? `${p[2]}-${p[1]}-${p[0]}` : s;
  };
  const fif = document.getElementById("fecha_inicio_facturacion")?.value;
  const fff = document.getElementById("fecha_fin_facturacion")?.value;
  const bi = document.getElementById("fecha_inicio")?.value;
  const bf = document.getElementById("fecha_fin")?.value;
  const line =
    slug === "ventas-por-vendedor" || slug === "ventas-por-articulo" || slug === "ventas-marcas-mensual"
      ? `Periodo facturación: ${fmt(fif)} al ${fmt(fff)}`
      : `Facturación y remitos: ${fmt(fif)} al ${fmt(fff)} · Backorder: ${fmt(bi)} al ${fmt(bf)}`;
  if (boPeriodEl) boPeriodEl.textContent = line;
  if (voPeriodEl) voPeriodEl.textContent = line;
}

const renderSummary = (meta, totals) => {
  const summaryContainer = document.querySelector("[data-summary-container]");
  const summaryGrid = document.querySelector("[data-summary-grid]");
  if (!summaryContainer || !summaryGrid) {
    return;
  }

  const reportSlug = dashboardRoot?.dataset?.reportSlug;
  const isSalesSummary = reportSlug === "sales_summary";
  const isTotalConsolidadoOperativo = reportSlug === "total-consolidado-operativo";
  const isBoStockFacturacion = isInformeBoDualPeriodo(reportSlug);
  const isMprReportSummary = reportSlug && reportSlug.startsWith("mpr-");
  const isCashFlowReport = reportSlug === "cash_flow_waterfall" || reportSlug === "cash_flow_by_account" || reportSlug === "cash_flow_detailed_movements";

  if (isMprReportSummary && totals && Object.keys(totals).length > 0) {
    summaryContainer.classList.remove("hidden");
  }

  // Helper: formatear fecha YYYY-MM-DD -> DD-MM-YYYY
  const formatDateForPeriod = (dateStr) => {
    if (!dateStr) return "";
    const parts = dateStr.split("-");
    if (parts.length !== 3) return dateStr;
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  };
  const fechaInicio = document.getElementById("fecha_inicio")?.value;
  const fechaFin = document.getElementById("fecha_fin")?.value;
  const periodText = fechaInicio && fechaFin ? `Periodo ${formatDateForPeriod(fechaInicio)} al ${formatDateForPeriod(fechaFin)}` : "";

  // bo-stock-facturacion y ventas-objetivos-vs-bo: doble rango (facturación/remitos vs backorder)
  if (isBoStockFacturacion) {
    syncBoDualSummaryPeriod();
    if (summaryContainer) summaryContainer.classList.add("hidden");
    updateLastUpdateTime();
    return;
  }

  // stock-existencias: sin KPI en el resumen (búsqueda y orden en la tabla)
  if (reportSlug === "stock-existencias") {
    summaryGrid.innerHTML = "";
    if (summaryContainer) summaryContainer.classList.add("hidden");
    updateLastUpdateTime();
    return;
  }

  // cash_flow_detailed_movements: totales en tabla; resumen solo período en el panel
  if (reportSlug === "cash_flow_detailed_movements") {
    summaryGrid.innerHTML = "";
    if (summaryContainer) summaryContainer.classList.add("hidden");
    updateLastUpdateTime();
    return;
  }

  // Actualizar el período en el título (otros reportes)
  const summaryPeriodElement = document.getElementById("summary-period");
  if (summaryPeriodElement) summaryPeriodElement.textContent = periodText;
  if (isVentasNetasSlug(reportSlug)) {
    const vnPeriodEl = document.getElementById("ventas-netas-summary-period");
    if (vnPeriodEl) vnPeriodEl.textContent = periodText;
  }

  summaryGrid.innerHTML = "";

  // Lista comprobantes en rutas: sin KPI en el resumen (solo período + última actualización)
  if (isLogisticaListaComprobantesRutasSlug(reportSlug)) {
    updateLastUpdateTime();
    summaryContainer.classList.remove("hidden");
    return;
  }

  // Para sales_summary y total-consolidado-operativo: solo header (Resumen + período + Última actualización), sin tarjetas en el resumen
  // Los KPIs de total-consolidado-operativo se muestran solo en el widget (renderCards), para no duplicar
  if (isSalesSummary || isTotalConsolidadoOperativo) {
    updateLastUpdateTime();
    summaryContainer.classList.remove("hidden");
    return;
  }

  // Ordenar las claves para mostrar en un orden específico
  // Excluir campos que ya se muestran en otras tarjetas (operating_ingresos, operating_egresos, cash_variation_sum_movements)
  const excludedKeys = ["operating_ingresos", "operating_egresos", "cash_variation_sum_movements"];
  
  // Orden específico: total-consolidado-operativo (4 KPIs verticales), ventas_netas, otros
  const isVentasNetasReport = isVentasNetasSlug(reportSlug);
  const isMprReport = reportSlug && reportSlug.startsWith("mpr-");
  const order = isTotalConsolidadoOperativo
    ? ["ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"]
    : isMprReport
    ? ["total_pedidos", "total_opt_atrasadas", "total_movimientos", "ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"]
    : isVentasNetasReport
    ? ["ventas_brutas", "notas_credito", "ventas_netas", "saldo_inicial", "operating_flow", "investing_flow", "financing_flow", "cash_variation", "saldo_final", "total_subtotal_desc", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"]
    : ["saldo_inicial", "operating_flow", "investing_flow", "financing_flow", "cash_variation", "saldo_final", "total_subtotal_desc", "ventas_brutas", "notas_credito", "ventas_netas", "remitos_no_facturados", "pedidos_pendientes", "total_consolidado"];
  const totalKeys = Object.keys(totals || {})
    .filter((key) => typeof totals[key] === "number" && !excludedKeys.includes(key.toLowerCase()))
    .sort((a, b) => {
      const indexA = order.indexOf(a.toLowerCase());
      const indexB = order.indexOf(b.toLowerCase());
      if (indexA === -1 && indexB === -1) return 0;
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;
      return indexA - indexB;
    });

  if (!totalKeys.length) {
    summaryContainer.classList.add("hidden");
    return;
  }

  // total-consolidado-operativo: una sola columna (KPIs verticales)
  if (isTotalConsolidadoOperativo) {
    summaryGrid.className = "grid grid-cols-1 gap-4";
  }

  let ventasNetasCard = null;
  let financingFlowCard = null;
  let cashVariationCard = null;
  let saldoFinalCard = null;
  
  totalKeys.forEach((key) => {
    const card = document.createElement("div");
    const keyLower = key.toLowerCase();
    const isTotalPedidos = keyLower === "total_pedidos";
    const isTotalOptAtrasadas = keyLower === "total_opt_atrasadas";
    const isTotalMovimientos = keyLower === "total_movimientos";
    const isCurrency = isCurrencyField(key);
    
    // Destacar la tarjeta de "ventas_netas" con un color más llamativo
    const isVentasNetas = keyLower.includes("ventas_netas") || keyLower.includes("ventas netas");
    
    // Identificar ventas brutas y notas de crédito
    const isVentasBrutas = keyLower.includes("ventas_brutas") || keyLower.includes("ventas brutas");
    const isNotasCredito = keyLower.includes("notas_credito") || keyLower.includes("notas credito") || keyLower.includes("notas de crédito");
    
    // Destacar saldo inicial y saldo final con colores diferentes
    const isSaldoInicial = keyLower === "saldo_inicial";
    const isSaldoFinal = keyLower === "saldo_final";
    const isVariacion = keyLower === "cash_variation" || keyLower === "variación de caja";
    
    // Destacar total de remitos no facturados
    const isTotalRemitos = keyLower === "total_subtotal_desc" || keyLower.includes("total_subtotal") || keyLower.includes("remitos");
    
    // Destacar métricas del resumen de ventas
    const isRemitosNoFacturados = keyLower === "remitos_no_facturados" || (keyLower.includes("remitos") && keyLower.includes("no") && keyLower.includes("facturados"));
    const isPedidosPendientes = keyLower === "pedidos_pendientes" || (keyLower.includes("pedidos") && keyLower.includes("pendientes"));
    const isTotalConsolidado = keyLower === "total_consolidado" || (keyLower.includes("total") && keyLower.includes("consolidado"));
    
    let cardBgClass, cardShadowClass, textColorClass;
    
    if (isTotalConsolidado) {
      cardBgClass = "bg-gradient-to-br from-purple-600 via-purple-700 to-purple-800";
      cardShadowClass = "shadow-lg shadow-purple-500/30";
      textColorClass = "text-purple-100";
    } else if (isTotalPedidos) {
      cardBgClass = "bg-gradient-to-br from-indigo-600 via-indigo-700 to-indigo-800";
      cardShadowClass = "shadow-lg shadow-indigo-500/30";
      textColorClass = "text-indigo-100";
    } else if (isTotalMovimientos) {
      cardBgClass = "bg-gradient-to-br from-cyan-600 via-cyan-700 to-cyan-800";
      cardShadowClass = "shadow-lg shadow-cyan-500/30";
      textColorClass = "text-cyan-100";
    } else if (isVentasNetas || keyLower.includes("ventas_netas")) {
      // Tarjeta de Ventas Netas - naranja/rojo (destacada)
      cardBgClass = "bg-gradient-to-br from-orange-500 via-orange-600 to-orange-700";
      cardShadowClass = "shadow-lg shadow-orange-500/30";
      textColorClass = "text-orange-100";
    } else if (isRemitosNoFacturados) {
      cardBgClass = "bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800";
      cardShadowClass = "shadow-lg shadow-blue-500/30";
      textColorClass = "text-blue-100";
    } else if (isPedidosPendientes) {
      cardBgClass = "bg-gradient-to-br from-green-600 via-green-700 to-green-800";
      cardShadowClass = "shadow-lg shadow-green-500/30";
      textColorClass = "text-green-100";
    } else if (isTotalRemitos) {
      cardBgClass = "bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800";
      cardShadowClass = "shadow-lg shadow-blue-500/30";
      textColorClass = "text-blue-100";
    } else if (isSaldoInicial) {
      cardBgClass = "bg-gradient-to-br from-blue-600 via-blue-700 to-blue-800";
      cardShadowClass = "shadow-lg shadow-blue-500/30";
      textColorClass = "text-blue-100";
    } else if (isSaldoFinal) {
      cardBgClass = "bg-gradient-to-br from-green-600 via-green-700 to-green-800";
      cardShadowClass = "shadow-lg shadow-green-500/30";
      textColorClass = "text-green-100";
    } else if (isVariacion) {
      cardBgClass = "bg-gradient-to-br from-purple-600 via-purple-700 to-purple-800";
      cardShadowClass = "shadow-lg shadow-purple-500/30";
      textColorClass = "text-purple-100";
    } else {
      cardBgClass = "bg-slate-900 dark:bg-slate-800";
      cardShadowClass = "shadow-lg shadow-slate-900/20";
      textColorClass = "text-slate-300";
    }
    
    card.className =
      `rounded-2xl ${cardBgClass} text-white px-4 py-4 ${cardShadowClass}`;
    // Mostrar subtítulo para Variación de Caja explicando que es la suma de los flujos
    let subtitle = "";
    const isOperatingFlow = keyLower === "operating_flow" || keyLower === "flujo operativo";
    
    if (isVariacion) {
      const operating = totals["operating_flow"] || 0;
      const investing = totals["investing_flow"] || 0;
      const financing = totals["financing_flow"] || 0;
      subtitle = `<p class="text-[9px] ${textColorClass} opacity-75 mt-1 text-right">Op + Inv + Fin</p>`;
    } else if (isOperatingFlow) {
      // Mostrar ingresos y egresos para Flujo Operativo
      const ingresos = totals["operating_ingresos"] || 0;
      const egresos = totals["operating_egresos"] || 0;
      const fmtMon = isCashFlowReport ? formatCurrency : formatCurrencyCompact;
      subtitle = `<p class="text-[9px] ${textColorClass} opacity-75 mt-1 text-right">Ing: ${fmtMon(ingresos)} | Egr: ${fmtMon(egresos)}</p>`;
    }
    
    // Formatear el label según la key
    let displayLabel = toTitle(key);
    if (isTotalPedidos) {
      displayLabel = "TOTAL PEDIDOS";
    } else if (isTotalMovimientos) {
      displayLabel = "TOTAL MOVIMIENTOS";
    } else if (isTotalRemitos) {
      displayLabel = "TOTAL DE REMITOS NO FACTURADOS";
    } else if (isVentasBrutas) {
      displayLabel = "VENTAS BRUTAS";
    } else if (isNotasCredito) {
      displayLabel = "NOTAS DE CRÉDITO";
    } else if (isVentasNetas) {
      displayLabel = "VENTAS NETAS";
    } else if (isRemitosNoFacturados) {
      displayLabel = "REMITOS NO FACTURADOS";
    } else if (isPedidosPendientes) {
      displayLabel = isTotalConsolidadoOperativo ? "PEDIDOS EN ARMADO" : "PEDIDOS PENDIENTES";
    } else if (isTotalConsolidado) {
      displayLabel = "TOTAL CONSOLIDADO";
    }
    
    // Total pedidos / OPT atrasadas / movimientos: siempre número entero sin decimales (nunca moneda)
    const isCountCard = isTotalPedidos || isTotalOptAtrasadas || isTotalMovimientos;
    const formatCardValue = (v) => {
      if (isCountCard && typeof v === "number") return Math.round(v).toLocaleString("es-AR", { maximumFractionDigits: 0 });
      if (isCurrency) return (isCashFlowReport ? formatCurrency : formatCurrencyCompact)(v);
      return formatNumber(v);
    };
    card.innerHTML = `
        <p class="text-[10px] uppercase tracking-[0.25em] ${textColorClass} mb-2">${displayLabel}</p>
        <p class="text-xl font-semibold text-right">${formatCardValue(totals[key])}</p>
        ${subtitle}
      `;
    summaryGrid.appendChild(card);
    
    if (isVentasNetas) {
      ventasNetasCard = card;
    }
    
    // Identificar la tarjeta de financing_flow para cash_flow_waterfall
    const isFinancingFlow = keyLower === "financing_flow" || keyLower === "flujo de financiamiento";
    if (isFinancingFlow) {
      financingFlowCard = card;
    }
    
    // Identificar la tarjeta de cash_variation
    if (isVariacion) {
      cashVariationCard = card;
    }
    
    // Identificar la tarjeta de saldo_final para ubicar la última actualización después de ella
    if (isSaldoFinal) {
      saldoFinalCard = card;
    }
  });

  // "Última actualización" en la misma línea que Resumen (header #last-update-time), igual que pedidos-pendientes
  updateLastUpdateTime();

  summaryContainer.classList.remove("hidden");
};

const updateLastUpdateTime = () => {
  const lastUpdateElement = document.getElementById("last-update-time");
  if (!lastUpdateElement) {
    return;
  }

  const now = new Date();
  const days = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
  const months = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const dayName = days[now.getDay()];
  const day = now.getDate();
  const month = months[now.getMonth()];
  const year = now.getFullYear();
  const time = now.toLocaleTimeString("es-AR");

  // Mismo criterio que pedidos-pendientes: una sola línea en el header (Resumen | Última actualización)
  const updateDateText = lastUpdateElement.querySelector("[data-update-date-text]");
  const updateTimeText = lastUpdateElement.querySelector("[data-update-time-text]");
  if (updateDateText && updateTimeText) {
    const dateOptions = { weekday: "long", year: "numeric", month: "long", day: "numeric" };
    const dateString = now.toLocaleDateString("es-AR", dateOptions);
    const formattedDate = dateString.charAt(0).toUpperCase() + dateString.slice(1);
    const timeString = now.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
    updateDateText.textContent = formattedDate;
    updateTimeText.textContent = timeString;
  } else {
    const oneLineHtml = `
      <span class="font-medium text-slate-600 dark:text-slate-400">Última actualización:</span>
      <span class="font-semibold text-slate-700 dark:text-slate-200"> ${dayName}, ${day} de ${month} de ${year} ${time}</span>
    `;
    lastUpdateElement.innerHTML = oneLineHtml;
    // BO tiene su propio contenedor en la misma línea (periodo | última actualización)
    const boLastUpdate = document.getElementById("bo-last-update-time");
    if (boLastUpdate) boLastUpdate.innerHTML = oneLineHtml;
    const voLastUpdate = document.getElementById("vo-last-update-time");
    if (voLastUpdate) voLastUpdate.innerHTML = oneLineHtml;
  }
};

const renderWidgets = (payload) => {
  if (isWorkspaceMode) {
    return;
  }
  if (!workspaceState.initialized) {
    setupWorkspaces();
  }
  const widgets = dashboardRoot.querySelectorAll("[data-widget-id]");
  const currentReportSlug = dashboardRoot?.dataset?.reportSlug;

  widgets.forEach((widget) => {
    const config = getWidgetConfig(widget);
    const cacheKey = widget.dataset.widgetId;
    widgetDataCache.set(cacheKey, { data: payload.data, config, meta: payload.meta || {} });

    const widgetType = widget.dataset.widgetType;

    // Lista comprobantes en rutas: una sola vista (tabla), sin gráfico ni alternancia «Ver tabla»
    if (isLogisticaListaComprobantesRutasSlug(currentReportSlug)) {
      const chartContainer = widget.querySelector("[data-widget-content]");
      if (chartContainer) {
        chartContainer.style.display = "none";
      }
      const toggleBtn = widget.querySelector("[data-toggle-table]");
      if (toggleBtn?.parentElement) {
        toggleBtn.parentElement.style.display = "none";
      }
      renderTable(widget, payload.data, { show: true, meta: payload.meta || {} });
      widget.querySelectorAll("[data-widget-note]").forEach((note) => note.remove());
      if (payload.notes && payload.notes.length) {
        const info = document.createElement("div");
        info.className =
          "px-6 py-4 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400";
        info.dataset.widgetNote = "true";
        const noteLabel = widget.dataset.noteLabel || "Notas";
        info.innerHTML = `<strong>${noteLabel}:</strong> ${payload.notes.join(" · ")}`;
        widget.appendChild(info);
      }
      return;
    }

    // HÍBRIDO: Para Ventas Netas, usar WidgetEngine para el gráfico de barras (tooltips, valores por serie, etc.)
    const isVentasNetasBarChart = isVentasNetasSlug(currentReportSlug) &&
      (widgetType === "d3-bar-grouped" || widgetType === "d3-bar" || widgetType === "d3-bar-stacked" || widgetType === "bar") &&
      window.WidgetEngine &&
      payload.data?.length > 0;
    
    if (isVentasNetasBarChart) {
      renderWidgetChart(widget, payload.data, config, payload.meta || {});
      console.log("[Ventas Netas] Gráfico de barras renderizado con WidgetEngine (dashboard)");
      renderTable(widget, payload.data, { show: false });
      attachTableToggle(widget, payload.data);
    } else if (widgetType === "pivot-table") {
      // Si es pivot-table, solo mostrar tabla (sin gráfico)
      // Ocultar el contenedor del gráfico
      const chartContainer = widget.querySelector("[data-widget-content]");
      if (chartContainer) {
        chartContainer.style.display = "none";
      }
      // Mostrar la tabla
      renderTable(widget, payload.data, { show: true });
      // Asegurar que el wrapper de la tabla esté visible
      const tableWrapper = widget.querySelector("[data-widget-table-wrapper]");
      if (tableWrapper) {
        tableWrapper.classList.remove("hidden");
      }
    } else if (widgetType === "d3-cards") {
      // Para d3-cards, mostrar solo las tarjetas (sin tabla)
      const chartContainer = widget.querySelector("[data-widget-content]");
      if (chartContainer) {
        chartContainer.style.display = ""; // Asegurar que esté visible
      }
      renderChart(widget, payload.data, config); // renderChart maneja d3-cards correctamente
      renderTable(widget, payload.data, { show: false }); // No mostrar tabla
      attachTableToggle(widget, payload.data);
    } else {
      const chartContainer = widget.querySelector("[data-widget-content]");
      if (chartContainer) chartContainer.removeAttribute("data-rendered-by");
      if (isVentasNetasSlug(currentReportSlug) &&
          (widgetType === "d3-bar-grouped" || widgetType === "d3-bar" || widgetType === "d3-bar-stacked" || widgetType === "bar") &&
          payload.data?.length > 0) {
        console.warn("[Ventas Netas] Gráfico con render legacy (WidgetEngine no disponible o condición no cumplida). reportSlug=%s widgetType=%s WidgetEngine=%s",
          currentReportSlug, widgetType, !!window.WidgetEngine);
      }
      renderChart(widget, payload.data, config);
      renderTable(widget, payload.data, { show: false });
      attachTableToggle(widget, payload.data);
    }

    widget.querySelectorAll("[data-widget-note]").forEach((note) => note.remove());

    if (payload.notes && payload.notes.length) {
      const info = document.createElement("div");
      info.className =
        "px-6 py-4 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400";
      info.dataset.widgetNote = "true";
      const noteLabel = widget.dataset.noteLabel || "Notas";
      info.innerHTML = `<strong>${noteLabel}:</strong> ${payload.notes.join(
        " · "
      )}`;
      widget.appendChild(info);
    }
  });

  // Reportes MPR sin widgets: mostrar tabla por defecto con los datos
  if (widgets.length === 0) {
    const placeholder = document.getElementById("widgets-placeholder");
    if (placeholder && currentReportSlug && currentReportSlug.startsWith("mpr-") && payload.data && payload.data.length > 0) {
      const fakeWidget = document.createElement("div");
      fakeWidget.dataset.reportSlug = currentReportSlug;
      fakeWidget.dataset.emptyLabel = "Sin datos disponibles.";
      const tableWrapper = document.createElement("div");
      tableWrapper.setAttribute("data-widget-table-wrapper", "");
      fakeWidget.appendChild(tableWrapper);
      placeholder.innerHTML = "";
      placeholder.classList.remove("p-12", "text-center");
      placeholder.classList.add("rounded-2xl", "border", "border-slate-200", "dark:border-slate-800", "bg-white", "dark:bg-slate-950", "overflow-hidden");
      const section = document.createElement("section");
      section.className = "rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-lg overflow-hidden";
      const header = document.createElement("header");
      header.className = "px-6 py-4 border-b border-slate-100 dark:border-slate-800";
      header.innerHTML = "<h2 class=\"text-sm font-semibold text-slate-900 dark:text-white\">Datos del reporte</h2>";
      section.appendChild(header);
      section.appendChild(tableWrapper);
      placeholder.appendChild(section);
      renderTable(fakeWidget, payload.data, { show: true });
    }
  }

  if (!resizeObserver && "ResizeObserver" in window) {
    resizeObserver = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        const widget = entry.target;
        const cacheKey = widget.dataset.widgetId;
        if (!cacheKey || !widgetDataCache.has(cacheKey)) {
          return;
        }
        const { data, config, meta } = widgetDataCache.get(cacheKey) || {};
        renderWidgetChart(widget, data || [], config, meta || {});
      });
    });
  }

  if (resizeObserver) {
    widgets.forEach((widget) => resizeObserver.observe(widget));
  }

  showWorkspace(workspaceState.current, { rerender: true });
};

// Estado para drag and drop de widgets
let dragWidgetIndex = null;
let dragOverWidgetIndex = null;

const attachWorkspaceDragAndDrop = (container) => {
  const wrappers = container.querySelectorAll ? 
    container.querySelectorAll("[data-widget-wrapper]") :
    Array.from(container.children || []).filter(el => el.dataset && el.dataset.widgetWrapper === "true");
  
  if (!wrappers || wrappers.length === 0) {
    return;
  }
  
  Array.from(wrappers).forEach((wrapper) => {
    // Remover listeners anteriores si existen
    const newWrapper = wrapper.cloneNode(true);
    wrapper.parentNode.replaceChild(newWrapper, wrapper);
    
    newWrapper.addEventListener("dragstart", (e) => {
      dragWidgetIndex = parseInt(newWrapper.dataset.widgetIndex, 10);
      newWrapper.style.opacity = "0.5";
      e.dataTransfer.effectAllowed = "move";
    });
    
    newWrapper.addEventListener("dragend", () => {
      newWrapper.style.opacity = "1";
      dragWidgetIndex = null;
      dragOverWidgetIndex = null;
      // Remover clases de highlight
      const allWrappers = dashboardRoot.querySelectorAll("[data-widget-wrapper]");
      allWrappers.forEach(w => {
        w.classList.remove("ring-2", "ring-sky-400", "border-sky-300", "dark:border-sky-500");
      });
    });
    
    newWrapper.addEventListener("dragenter", (e) => {
      e.preventDefault();
      const targetIndex = parseInt(newWrapper.dataset.widgetIndex, 10);
      if (targetIndex !== dragWidgetIndex && dragWidgetIndex !== null) {
        dragOverWidgetIndex = targetIndex;
        newWrapper.classList.add("ring-2", "ring-sky-400", "border-sky-300", "dark:border-sky-500");
      }
    });
    
    newWrapper.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
    });
    
    newWrapper.addEventListener("dragleave", () => {
      newWrapper.classList.remove("ring-2", "ring-sky-400", "border-sky-300", "dark:border-sky-500");
    });
    
    newWrapper.addEventListener("drop", async (e) => {
      e.preventDefault();
      const targetIndex = parseInt(newWrapper.dataset.widgetIndex, 10);
      
      if (dragWidgetIndex === null || dragWidgetIndex === targetIndex) {
        dragWidgetIndex = null;
        dragOverWidgetIndex = null;
        return;
      }
      
      // Reordenar widgets en el DOM
      const allWrappers = Array.from(dashboardRoot.querySelectorAll("[data-widget-wrapper]"));
      const fromWrapper = allWrappers[dragWidgetIndex];
      const toWrapper = allWrappers[targetIndex];
      
      if (fromWrapper && toWrapper) {
        // Insertar el widget arrastrado en la nueva posición
        if (dragWidgetIndex < targetIndex) {
          toWrapper.parentNode.insertBefore(fromWrapper, toWrapper.nextSibling);
        } else {
          toWrapper.parentNode.insertBefore(fromWrapper, toWrapper);
        }
        
        // Actualizar índices de todos los wrappers
        const updatedWrappers = Array.from(dashboardRoot.querySelectorAll("[data-widget-wrapper]"));
        updatedWrappers.forEach((w, idx) => {
          w.dataset.widgetIndex = String(idx);
          const widget = w.querySelector("[data-widget-id]");
          if (widget) {
            const newId = `workspace-${idx}`;
            widget.dataset.widgetId = newId;
            // Actualizar el ID del script de configuración si existe
            const configId = widget.dataset.widgetConfigId;
            if (configId) {
              const configScript = document.getElementById(configId);
              if (configScript) {
                configScript.id = `workspace-config-${idx}`;
                widget.dataset.widgetConfigId = `workspace-config-${idx}`;
              }
            }
          }
        });
        
        // Guardar el nuevo orden en el backend
        await saveWorkspaceOrder();
        
        // Recargar los widgets en el nuevo orden
        await fetchWorkspaceData();
      }
      
      dragWidgetIndex = null;
      dragOverWidgetIndex = null;
      newWrapper.classList.remove("ring-2", "ring-sky-400", "border-sky-300", "dark:border-sky-500");
    });
  });
};

const saveWorkspaceOrder = async () => {
  if (!workspaceApiUrl) {
    return;
  }
  
  const wrappers = Array.from(dashboardRoot.querySelectorAll("[data-widget-wrapper]"));
  const itemKeys = wrappers.map(w => w.dataset.widgetItemKey || w.dataset.widgetSlug).filter(Boolean);
  
  if (itemKeys.length === 0) {
    return;
  }
  
  try {
    const response = await fetch(workspaceApiUrl, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({ items: itemKeys }),
    });
    
    if (!response.ok) {
      throw new Error("No se pudo guardar el orden");
    }
    
    toast("Orden de widgets actualizado", "success");
  } catch (error) {
    console.error("Error guardando orden:", error);
    toast("Error al guardar el orden", "error");
  }
};

const buildWorkspaceDOM = (slots) => {
  resetWorkspaceState();
  dashboardRoot.innerHTML = "";
  dashboardRoot.classList.remove("flex", "flex-col", "gap-10", "gap-12", "gap-3", "space-y-8");

  if (!slots.length) {
    dashboardRoot.innerHTML = `
      <div class="flex flex-col items-center justify-center text-center gap-4 py-24 text-slate-400">
        <svg class="w-12 h-12" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M4 4h16v16H4z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M4 9h16M9 4v16" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div>
          <h2 class="text-lg font-semibold text-slate-600 dark:text-slate-200">Aún no hay informes en el workspace</h2>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">Visita el catálogo y utiliza la opción “Guardar en workspace” para construir tu tablero para Smart TV.</p>
        </div>
      </div>
    `;
    updateWorkspaceIndicator();
    return;
  }

  const fragment = document.createDocumentFragment();

  slots.forEach((slot, index) => {
    const itemKey = slot.item_key != null ? slot.item_key : slot.slug;
    const wrapper = document.createElement("div");
    wrapper.dataset.widgetWrapper = "true";
    wrapper.dataset.widgetIndex = String(index);
    wrapper.dataset.widgetSlug = slot.slug;
    wrapper.dataset.widgetItemKey = itemKey;
    wrapper.className = "flex flex-col gap-0";
    // Agregar drag and drop para reordenar widgets
    wrapper.draggable = true;
    wrapper.style.cursor = "move";
    // Asegurar que el wrapper no cause espacios adicionales
    wrapper.style.margin = "0";
    wrapper.style.padding = "0";
    wrapper.style.flexShrink = "0";
    wrapper.style.minHeight = "0";
    wrapper.style.height = "auto";
    // Asegurar que el wrapper no cause cambios en el grid
    wrapper.style.gridRow = "auto";
    wrapper.style.gridColumn = "auto";

    const section = document.createElement("section");
    section.className = "rounded-2xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-950 shadow-lg shadow-slate-900/5 overflow-hidden transition-all duration-500 hover:-translate-y-1";
    // Asegurar altura mínima fija para evitar cambios de tamaño durante actualización
    section.style.minHeight = "420px";
    section.style.height = "auto";
    section.style.flexShrink = "0";
    section.style.margin = "0";
    section.style.gridRow = "span 1";
    section.style.gridColumn = "span 1";
    const widgetId = `workspace-${index}`;
    const configId = `workspace-config-${index}`;

    section.dataset.widgetId = widgetId;
    section.dataset.widgetType = slot.widget.widget_type;
    section.dataset.widgetConfigId = configId;
    section.dataset.noteLabel = "Notas";
    section.dataset.emptyLabel = "No hay datos disponibles.";
    section.dataset.reportSlug = slot.slug;
    section.dataset.itemKey = itemKey;

    const displayTitle = slot.display_name || slot.name;
    const allowDuplicateSlugs = ["total-consolidado-operativo"];
    const showConsolidadoWorkspaceFilters = slot.slug === "total-consolidado-operativo";
    const showPedidosWorkspaceFilters = isPedidosPendientesSlug(slot.slug);
    const showDuplicate = allowDuplicateSlugs.includes(slot.slug);
    const showFiltersButton = showConsolidadoWorkspaceFilters || showPedidosWorkspaceFilters;
    // Crear un ID seguro para los elementos (sin caracteres especiales)
    const safeItemKey = itemKey.replace(/[^a-zA-Z0-9]/g, '_');
    
    section.innerHTML = `
      <header class="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
        <div class="flex items-center gap-2 flex-1 min-w-0">
          <button type="button"
                  class="cursor-move text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 flex-shrink-0"
                  title="Arrastrar para reordenar"
                  style="pointer-events: none;">
            ⠿
          </button>
          <div class="flex flex-col gap-1 flex-1 min-w-0">
            <h2 class="text-sm font-semibold text-slate-900 dark:text-white truncate" data-widget-title>${displayTitle}</h2>
            <span class="text-[10px] text-slate-500 dark:text-slate-400 truncate" data-widget-subtitle>
              Última actualización: <span data-workspace-last-update>—</span>
            </span>
          </div>
        </div>
        <div class="flex items-center gap-2 text-[11px] flex-shrink-0">
          ${showFiltersButton ? `<button type="button" data-toggle-filters data-item-key="${itemKey}"
                  class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition border border-slate-200 dark:border-slate-700" title="Mostrar/ocultar filtros">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Filtros
          </button>` : ""}
          <a href="/reports/dashboard/${slot.slug}/" target="_blank" rel="noopener"
             class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M7 7h10v10M17 7l-8 8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Abrir
          </a>
          ${showDuplicate ? `<button type="button" data-duplicate-workspace data-item-key="${itemKey}" data-report-slug="${slot.slug}"
                  class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sky-500 hover:text-sky-400 transition" title="Duplicar con filtros independientes">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            Duplicar
          </button>` : ""}
          <button type="button" data-remove-from-workspace data-item-key="${itemKey}" data-report-slug="${slot.slug}"
                  class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-rose-500 hover:text-rose-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-rose-400 transition">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M6 6l12 12M6 18L18 6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Quitar
          </button>
        </div>
      </header>
      ${showConsolidadoWorkspaceFilters ? `
      <div class="workspace-filters-panel hidden border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50" data-filters-panel data-workspace-filter-kind="consolidado" data-item-key="${itemKey}">
        <div class="px-6 py-4 space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                Fecha Inicio
              </span>
              <input type="date" id="fecha_inicio_${safeItemKey}" name="fecha_inicio" class="px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-sky-400 focus:border-sky-400" data-item-key="${itemKey}">
            </label>
            <label class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                </svg>
                Fecha Fin
              </span>
              <input type="date" id="fecha_fin_${safeItemKey}" name="fecha_fin" class="px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-sky-400 focus:border-sky-400" data-item-key="${itemKey}">
            </label>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"/>
                </svg>
                Sucursal
              </span>
              <div class="relative">
                <select name="sucursales" id="sucursales_${safeItemKey}" multiple class="hidden" data-tags-field="sucursales" data-item-key="${itemKey}">
                  <option value="">Cargando...</option>
                </select>
                <div id="sucursales_${safeItemKey}_tags_container" class="tags-filter-container flex flex-wrap items-center gap-1.5 py-2 px-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md min-h-[2.5rem] focus-within:ring-2 focus-within:ring-sky-400 focus-within:border-sky-400 transition-all duration-300">
                  <div class="tags-chips flex flex-wrap gap-1.5 flex-1"></div>
                  <input type="text" id="sucursales_${safeItemKey}_search" class="tags-input flex-1 min-w-[120px] bg-transparent border-none outline-none text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500" placeholder="Buscar sucursales..." autocomplete="off">
                  <div id="sucursales_${safeItemKey}_dropdown" class="tags-dropdown absolute top-full left-0 right-0 z-50 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg max-h-60 overflow-y-auto hidden"></div>
                </div>
              </div>
            </label>
            <label class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2">
              <span class="flex items-center gap-2">
                <svg class="w-4 h-4 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"/>
                </svg>
                Punto de venta
              </span>
              <div class="relative">
                <select name="punto_venta" id="punto_venta_${safeItemKey}" multiple class="hidden" data-tags-field="punto_venta" data-item-key="${itemKey}">
                  <option value="">Cargando...</option>
                </select>
                <div id="punto_venta_${safeItemKey}_tags_container" class="tags-filter-container flex flex-wrap items-center gap-1.5 py-2 px-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md min-h-[2.5rem] focus-within:ring-2 focus-within:ring-sky-400 focus-within:border-sky-400 transition-all duration-300">
                  <div class="tags-chips flex flex-wrap gap-1.5 flex-1"></div>
                  <input type="text" id="punto_venta_${safeItemKey}_search" class="tags-input flex-1 min-w-[120px] bg-transparent border-none outline-none text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500" placeholder="Buscar punto de venta..." autocomplete="off">
                  <div id="punto_venta_${safeItemKey}_dropdown" class="tags-dropdown absolute top-full left-0 right-0 z-50 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg max-h-60 overflow-y-auto hidden"></div>
                </div>
              </div>
            </label>
          </div>
          <label class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2">
            <span class="flex items-center gap-2">
              <svg class="w-4 h-4 text-slate-500 dark:text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
              </svg>
              Clientes a excluir
            </span>
            <div class="relative">
              <select name="clientes_excluidos" id="clientes_excluidos_${safeItemKey}" multiple class="hidden" data-tags-field="clientes_excluidos" data-item-key="${itemKey}">
                <option value="">Cargando...</option>
              </select>
              <div id="clientes_excluidos_${safeItemKey}_tags_container" class="tags-filter-container flex flex-wrap items-center gap-1.5 py-2 px-3 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md min-h-[2.5rem] focus-within:ring-2 focus-within:ring-sky-400 focus-within:border-sky-400 transition-all duration-300">
                <div class="tags-chips flex flex-wrap gap-1.5 flex-1"></div>
                <input type="text" id="clientes_excluidos_${safeItemKey}_search" class="tags-input flex-1 min-w-[120px] bg-transparent border-none outline-none text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500" placeholder="Buscar clientes..." autocomplete="off">
                <div id="clientes_excluidos_${safeItemKey}_dropdown" class="tags-dropdown absolute top-full left-0 right-0 z-50 mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-md shadow-lg max-h-60 overflow-y-auto hidden"></div>
              </div>
            </div>
          </label>
          <div class="flex justify-end">
            <button type="button" data-apply-workspace-filters data-workspace-filter-kind="consolidado" data-item-key="${itemKey}" data-report-slug="${slot.slug}"
                    class="inline-flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-600 text-white text-sm font-medium rounded-lg transition">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M5 13l4 4L19 7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Aplicar Filtros
            </button>
          </div>
        </div>
      </div>
      ` : ""}
      ${showPedidosWorkspaceFilters ? `
      <div class="workspace-filters-panel workspace-pedidos-period-panel hidden border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50" data-filters-panel data-workspace-filter-kind="pedidos-period" data-item-key="${itemKey}" data-safe-item-key="${safeItemKey}">
        <div class="px-6 py-4 space-y-4">
          <div class="flex flex-row flex-wrap items-end gap-4">
            <div class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2 flex-shrink-0">
              <span>Período</span>
              <div class="flex flex-wrap items-center gap-2">
                <button type="button" data-periodo="dia_actual" class="ws-pedidos-periodo-btn px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-xs font-medium rounded-full border transition-all duration-200 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-sky-400">Día</button>
                <button type="button" data-periodo="mes_actual" class="ws-pedidos-periodo-btn px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-xs font-medium rounded-full border transition-all duration-200 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-sky-400">Mes</button>
                <button type="button" data-periodo="año_actual" class="ws-pedidos-periodo-btn px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-xs font-medium rounded-full border transition-all duration-200 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-sky-400">Año</button>
                <button type="button" data-periodo="personalizado" class="ws-pedidos-periodo-btn px-2.5 sm:px-3 py-1 sm:py-1.5 text-[10px] sm:text-xs font-medium rounded-full border transition-all duration-200 border-sky-500 bg-sky-50 dark:bg-sky-900/20 text-sky-700 dark:text-sky-300 shadow-md">Personalizado</button>
              </div>
              <select id="periodo_tipo_${safeItemKey}" class="hidden">
                <option value="dia_actual">Día en curso</option>
                <option value="mes_actual">Mes en curso</option>
                <option value="año_actual">Año en curso</option>
                <option value="personalizado" selected>Personalizado</option>
              </select>
            </div>
            <label class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2 flex-shrink-0">
              Fecha desde
              <input type="date" id="fecha_inicio_${safeItemKey}" name="fecha_inicio" class="px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-sky-400 focus:border-sky-400">
            </label>
            <label class="flex flex-col text-xs font-semibold text-slate-500 dark:text-slate-400 gap-2 flex-shrink-0">
              Fecha hasta
              <input type="date" id="fecha_fin_${safeItemKey}" name="fecha_fin" class="px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md text-xs text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-sky-400 focus:border-sky-400">
            </label>
          </div>
          <div class="flex flex-col gap-2">
            <label class="text-xs font-semibold text-slate-500 dark:text-slate-400">Intervalo de actualización</label>
            <div class="flex flex-wrap gap-2" role="group" aria-label="Intervalo de actualización">
              <button type="button" data-interval="interval_30s" class="ws-pedidos-refresh-btn px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-sky-400">30 seg</button>
              <button type="button" data-interval="interval_5m" class="ws-pedidos-refresh-btn px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-sky-400">5 min</button>
              <button type="button" data-interval="interval_10m" class="ws-pedidos-refresh-btn px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 border-sky-500 bg-sky-50 dark:bg-sky-900/20 text-sky-700 dark:text-sky-300 shadow-md">10 min</button>
              <button type="button" data-interval="interval_1h" class="ws-pedidos-refresh-btn px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-sky-400">1 h</button>
              <button type="button" data-interval="interval_2h" class="ws-pedidos-refresh-btn px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:border-sky-400">2 h</button>
            </div>
            <select id="refresh_interval_${safeItemKey}" class="hidden">
              <option value="interval_30s">30 seg</option>
              <option value="interval_5m">5 min</option>
              <option value="interval_10m" selected>10 min</option>
              <option value="interval_1h">1 h</option>
              <option value="interval_2h">2 h</option>
            </select>
            <span class="text-[10px] font-normal text-slate-400 dark:text-slate-500 italic">Frecuencia de actualización automática en tiempo real</span>
          </div>
          <div id="workspace_pedidos_grouping_${safeItemKey}" class="workspace-pedidos-grouping-mount" data-workspace-pedidos-grouping-mount></div>
          <p class="text-[10px] text-slate-500 dark:text-slate-400">No hay filtros marcados para mostrar. Los filtros constantes se aplican automáticamente.</p>
          <div class="flex justify-end">
            <button type="button" data-apply-workspace-filters data-workspace-filter-kind="pedidos-period" data-item-key="${itemKey}" data-report-slug="${slot.slug}"
                    class="inline-flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-600 text-white text-sm font-medium rounded-lg transition">
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M5 13l4 4L19 7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Aplicar filtros
            </button>
          </div>
        </div>
      </div>
      ` : ""}
      <div class="relative" style="min-height: 350px;">
        <div class="aspect-[16/7] w-full bg-white dark:bg-slate-950 p-6" data-widget-content>
          <div class="h-full w-full grid place-content-center text-xs text-slate-500 dark:text-slate-400 tracking-[0.2em] uppercase">
            Cargando datos...
          </div>
        </div>
        <div class="px-6 py-3 hidden" data-widget-table-wrapper style="min-height: 288px;"></div>
      </div>
    `;

    const configScript = document.createElement("script");
    configScript.type = "application/json";
    configScript.id = configId;
    configScript.textContent = JSON.stringify(slot.widget.configuration || {});

    wrapper.appendChild(section);
    wrapper.appendChild(configScript);
    fragment.appendChild(wrapper);
  });

  dashboardRoot.appendChild(fragment);
};

// Variable global para controlar si ya se adjuntó el event delegation
let workspaceRemovalDelegationAttached = false;

const attachWorkspaceRemovalHandlers = () => {
  if (!workspaceApiUrl) {
    return;
  }
  
  // Si ya se adjuntó el event delegation, no hacer nada
  if (workspaceRemovalDelegationAttached) {
    console.log("[Workspace] Event delegation ya está activo");
    return;
  }
  
  console.log("[Workspace] Adjuntando event delegation para botones 'Quitar'");
  
  // Usar event delegation en el dashboardRoot
  dashboardRoot.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-remove-from-workspace]");
    if (!button) {
      return;
    }
    
    e.preventDefault();
    e.stopPropagation();
    
    const itemKey = button.dataset.itemKey || button.dataset.reportSlug;
    console.log(`[Workspace] Click en "Quitar" - itemKey: "${itemKey}", reportSlug: "${button.dataset.reportSlug}"`);
    
    if (!itemKey) {
      console.warn("[Workspace] Botón sin itemKey ni reportSlug, ignorando");
      return;
    }
    
    if (button.dataset.loading === "true") {
      console.log("[Workspace] Botón ya en estado loading, ignorando click");
      return;
    }
    
    button.dataset.loading = "true";
    button.classList.add("opacity-60", "pointer-events-none");
    
    try {
      console.log(`[Workspace] Enviando DELETE a ${workspaceApiUrl} con item_key: "${itemKey}"`);
      const response = await fetch(workspaceApiUrl, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ item_key: itemKey }),
      });
      console.log(`[Workspace] Respuesta DELETE: status=${response.status}`);
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        console.error("[Workspace] Error en DELETE:", detail);
        throw new Error(detail.detail || "No se pudo quitar el informe");
      }
      const payload = await response.json();
      console.log("[Workspace] DELETE exitoso:", payload);
      setWorkspaceCount(payload.count ?? "-");
      toast("Informe eliminado del workspace");
      await fetchWorkspaceData();
    } catch (error) {
      console.error("[Workspace] Error al quitar informe:", error);
      toast(error.message || "No se pudo quitar", "error");
      button.classList.remove("opacity-60", "pointer-events-none");
      button.dataset.loading = "false";
    }
  });
  
  workspaceRemovalDelegationAttached = true;
};

const wsPedidosPeriodBtnActive = ["border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md"];
const wsPedidosPeriodBtnIdle = ["border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300"];

const highlightWorkspacePedidosPeriodButtons = (panel, periodo) => {
  panel.querySelectorAll(".ws-pedidos-periodo-btn").forEach((btn) => {
    const on = btn.getAttribute("data-periodo") === periodo;
    wsPedidosPeriodBtnActive.forEach((c) => btn.classList.toggle(c, on));
    wsPedidosPeriodBtnIdle.forEach((c) => btn.classList.toggle(c, !on));
  });
};

const highlightWorkspacePedidosRefreshButtons = (panel, intervalVal) => {
  const iv = migrateLegacyInterval(intervalVal);
  panel.querySelectorAll(".ws-pedidos-refresh-btn").forEach((btn) => {
    const on = btn.getAttribute("data-interval") === iv;
    wsPedidosPeriodBtnActive.forEach((c) => btn.classList.toggle(c, on));
    wsPedidosPeriodBtnIdle.forEach((c) => btn.classList.toggle(c, !on));
  });
};

/**
 * Filtros de período + intervalo en workspace para pedidos-pendientes (misma semántica que el informe en dashboard_detail).
 */
const initializeWorkspacePedidosPeriodFilters = (itemKey) => {
  const safeItemKey = itemKey.replace(/[^a-zA-Z0-9]/g, "_");
  const panel = dashboardRoot.querySelector(
    `[data-workspace-filter-kind="pedidos-period"][data-item-key="${itemKey}"]`
  );
  if (!panel) {
    return;
  }
  const periodoSel = document.getElementById(`periodo_tipo_${safeItemKey}`);
  const fechaInicioInput = document.getElementById(`fecha_inicio_${safeItemKey}`);
  const fechaFinInput = document.getElementById(`fecha_fin_${safeItemKey}`);
  const refreshSel = document.getElementById(`refresh_interval_${safeItemKey}`);

  let filters = {};
  try {
    const raw = localStorage.getItem(`report_filters_${itemKey}`);
    if (raw) {
      filters = JSON.parse(raw);
    }
  } catch (e) {
    console.warn("No se pudieron leer filtros guardados (pedidos workspace):", e);
  }

  let periodo = filters.periodo_tipo || "personalizado";
  if (filters.dia_actual) {
    periodo = "dia_actual";
  } else if (filters.mes_actual) {
    periodo = "mes_actual";
  } else if (filters.año_actual) {
    periodo = "año_actual";
  }
  if (periodoSel) {
    periodoSel.value = periodo;
  }
  if (filters.fecha_inicio && fechaInicioInput) {
    fechaInicioInput.value = filters.fecha_inicio;
  }
  if (filters.fecha_fin && fechaFinInput) {
    fechaFinInput.value = filters.fecha_fin;
  }
  if ((!fechaInicioInput?.value || !fechaFinInput?.value) && fechaInicioInput && fechaFinInput) {
    const built = workspaceBuildPeriodFiltersPayload(periodoSel?.value || periodo, "", "");
    fechaInicioInput.value = built.fecha_inicio;
    fechaFinInput.value = built.fecha_fin;
  }
  if (refreshSel) {
    refreshSel.value = migrateLegacyInterval(filters.refresh_interval);
  }
  highlightWorkspacePedidosPeriodButtons(panel, periodoSel?.value || periodo);
  highlightWorkspacePedidosRefreshButtons(panel, refreshSel?.value);

  if (panel.dataset.wsPedidosUiBound === "1") {
    updateWorkspaceWidgetTitle(itemKey, filters);
    return;
  }
  panel.dataset.wsPedidosUiBound = "1";

  panel.addEventListener("click", (ev) => {
    const pBtn = ev.target.closest(".ws-pedidos-periodo-btn");
    if (pBtn && periodoSel) {
      const p = pBtn.getAttribute("data-periodo") || "personalizado";
      periodoSel.value = p;
      highlightWorkspacePedidosPeriodButtons(panel, p);
      const today = new Date();
      const fi = document.getElementById(`fecha_inicio_${safeItemKey}`);
      const ff = document.getElementById(`fecha_fin_${safeItemKey}`);
      if (p === "dia_actual") {
        const s = today.toISOString().split("T")[0];
        if (fi) fi.value = s;
        if (ff) ff.value = s;
      } else if (p === "mes_actual") {
        const a = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split("T")[0];
        const b = new Date(today.getFullYear(), today.getMonth() + 1, 0).toISOString().split("T")[0];
        if (fi) fi.value = a;
        if (ff) ff.value = b;
      } else if (p === "año_actual") {
        const a = new Date(today.getFullYear(), 0, 1).toISOString().split("T")[0];
        const b = new Date(today.getFullYear(), 11, 31).toISOString().split("T")[0];
        if (fi) fi.value = a;
        if (ff) ff.value = b;
      } else if (fi && ff && (!fi.value || !ff.value)) {
        const built = workspaceBuildPeriodFiltersPayload("personalizado", "", "");
        fi.value = built.fecha_inicio;
        ff.value = built.fecha_fin;
      }
    }
    const rBtn = ev.target.closest(".ws-pedidos-refresh-btn");
    if (rBtn && refreshSel) {
      const interval = rBtn.getAttribute("data-interval");
      if (interval) {
        refreshSel.value = interval;
        highlightWorkspacePedidosRefreshButtons(panel, interval);
      }
    }
  });

  const onDateChange = () => {
    if (periodoSel) {
      periodoSel.value = "personalizado";
    }
    highlightWorkspacePedidosPeriodButtons(panel, "personalizado");
  };
  fechaInicioInput?.addEventListener("change", onDateChange);
  fechaFinInput?.addEventListener("change", onDateChange);

  updateWorkspaceWidgetTitle(itemKey, filters);
};

// Función para inicializar los filtros tags en el workspace (total consolidado operativo)
const initializeWorkspaceFilters = async (itemKey, slug) => {
  console.log(`[initializeWorkspaceFilters] Inicializando filtros para ${itemKey}`);
  const safeItemKey = itemKey.replace(/[^a-zA-Z0-9]/g, '_');
  console.log(`[initializeWorkspaceFilters] safeItemKey: ${safeItemKey}`);

  if (slug === "pedidos-pendientes") {
    initializeWorkspacePedidosPeriodFilters(itemKey);
    return;
  }
  
  // Establecer fechas por defecto (mes anterior completo hasta hoy)
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const lastDay = new Date(today);
  
  const fechaInicioInput = document.getElementById(`fecha_inicio_${safeItemKey}`);
  const fechaFinInput = document.getElementById(`fecha_fin_${safeItemKey}`);
  
  if (fechaInicioInput && !fechaInicioInput.value) {
    fechaInicioInput.value = firstDay.toISOString().split('T')[0];
  }
  if (fechaFinInput && !fechaFinInput.value) {
    fechaFinInput.value = lastDay.toISOString().split('T')[0];
  }
  
  // Cargar opciones de filtros
  try {
    // Sucursales
    console.log(`[initializeWorkspaceFilters] Cargando sucursales...`);
    const sucursalesResponse = await fetch(`/api/reports/filters/?type=sucursales`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    console.log(`[initializeWorkspaceFilters] Respuesta sucursales:`, sucursalesResponse.status);
    if (sucursalesResponse.ok) {
      const data = await sucursalesResponse.json();
      console.log(`[initializeWorkspaceFilters] Data sucursales:`, data);
      const sucursalesSelect = document.getElementById(`sucursales_${safeItemKey}`);
      console.log(`[initializeWorkspaceFilters] Select sucursales encontrado:`, !!sucursalesSelect);
      if (sucursalesSelect && data.sucursales) {
        console.log(`[initializeWorkspaceFilters] Poblando ${data.sucursales.length} sucursales`);
        sucursalesSelect.innerHTML = data.sucursales.map(s => 
          `<option value="${s.value}">${s.label}</option>`
        ).join("");
        console.log(`[initializeWorkspaceFilters] Inicializando tags filter para sucursales_${safeItemKey}`);
        initializeTagsFilter(`sucursales_${safeItemKey}`, 'sucursales');
      }
    }
    
    // Punto de venta
    const puntoVentaResponse = await fetch(`/api/reports/filters/?type=puntos_venta`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (puntoVentaResponse.ok) {
      const data = await puntoVentaResponse.json();
      const puntoVentaSelect = document.getElementById(`punto_venta_${safeItemKey}`);
      if (puntoVentaSelect && data.puntos_venta) {
        puntoVentaSelect.innerHTML = data.puntos_venta.map(pv => 
          `<option value="${pv.value}">${pv.label}</option>`
        ).join("");
        initializeTagsFilter(`punto_venta_${safeItemKey}`, 'punto_venta');
      }
    }
    
    // Clientes
    const clientesResponse = await fetch(`/api/reports/filters/?type=clientes`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    });
    if (clientesResponse.ok) {
      const data = await clientesResponse.json();
      const clientesSelect = document.getElementById(`clientes_excluidos_${safeItemKey}`);
      if (clientesSelect && data.clientes) {
        clientesSelect.innerHTML = data.clientes.map(c => 
          `<option value="${c.value}">${c.label}</option>`
        ).join("");
        initializeTagsFilter(`clientes_excluidos_${safeItemKey}`, 'clientes_excluidos');
      }
    }
    
    // Restaurar filtros guardados
    try {
      const saved = localStorage.getItem(`report_filters_${itemKey}`);
      if (saved) {
        const filters = JSON.parse(saved);
        
        // Restaurar fechas
        if (filters.fecha_inicio && fechaInicioInput) {
          fechaInicioInput.value = filters.fecha_inicio;
        }
        if (filters.fecha_fin && fechaFinInput) {
          fechaFinInput.value = filters.fecha_fin;
        }
        
        // Restaurar sucursales
        if (filters.sucursales && Array.isArray(filters.sucursales)) {
          const sucursalesSelect = document.getElementById(`sucursales_${safeItemKey}`);
          if (sucursalesSelect) {
            filters.sucursales.forEach(val => {
              const option = sucursalesSelect.querySelector(`option[value="${val}"]`);
              if (option) option.selected = true;
            });
            // Trigger change para actualizar los tags
            sucursalesSelect.dispatchEvent(new Event('change'));
          }
        }
        
        // Restaurar punto de venta
        if (filters.punto_venta && Array.isArray(filters.punto_venta)) {
          const puntoVentaSelect = document.getElementById(`punto_venta_${safeItemKey}`);
          if (puntoVentaSelect) {
            filters.punto_venta.forEach(val => {
              const option = puntoVentaSelect.querySelector(`option[value="${val}"]`);
              if (option) option.selected = true;
            });
            puntoVentaSelect.dispatchEvent(new Event('change'));
          }
        }
        
        // Restaurar clientes excluidos
        if (filters.clientes_excluidos && Array.isArray(filters.clientes_excluidos)) {
          const clientesSelect = document.getElementById(`clientes_excluidos_${safeItemKey}`);
          if (clientesSelect) {
            filters.clientes_excluidos.forEach(val => {
              const option = clientesSelect.querySelector(`option[value="${String(val).trim()}"]`);
              if (option) option.selected = true;
            });
            clientesSelect.dispatchEvent(new Event('change'));
          }
        }
        
        // Actualizar título con filtros
        updateWorkspaceWidgetTitle(itemKey, filters);
      } else {
        // Si no hay filtros guardados, establecer fechas por defecto
        const fechaInicioInput = document.getElementById(`fecha_inicio_${safeItemKey}`);
        const fechaFinInput = document.getElementById(`fecha_fin_${safeItemKey}`);
        
        if (fechaInicioInput && fechaFinInput) {
          const today = new Date();
          const firstDay = new Date(today.getFullYear(), today.getMonth() - 1, 1);
          const lastDay = new Date(today);
          
          fechaInicioInput.value = firstDay.toISOString().split('T')[0];
          fechaFinInput.value = lastDay.toISOString().split('T')[0];
        }
      }
    } catch (e) {
      console.warn("Error restaurando filtros guardados:", e);
    }
  } catch (error) {
    console.error("Error inicializando filtros del workspace:", error);
  }
};

// Función para actualizar el título del widget con los filtros seleccionados
const updateWorkspaceWidgetTitle = (itemKey, filters) => {
  const widget = dashboardRoot.querySelector(`[data-widget-id][data-item-key="${itemKey}"]`);
  if (!widget) return;
  
  const safeItemKey = itemKey.replace(/[^a-zA-Z0-9]/g, '_');
  const titleElement = widget.querySelector("[data-widget-title]");
  const subtitleElement = widget.querySelector("[data-widget-subtitle]");
  if (!titleElement) return;

  const reportSlug = widget.dataset.reportSlug || "";
  
  // Construir el título con sucursales
  let titleText = reportSlug === "pedidos-pendientes" ? "Pedidos pendientes" : "Total Consolidado";
  const sucursalesNames = [];
  
  // Sucursales - agregar al título
  if (filters.sucursales && filters.sucursales.length > 0) {
    // Primero intentar usar los nombres guardados
    if (filters._sucursales_names && filters._sucursales_names.length > 0) {
      sucursalesNames.push(...filters._sucursales_names);
    } else {
      // Fallback: buscar en el select si está disponible
      const sucursalesSelect = document.getElementById(`sucursales_${safeItemKey}`);
      if (sucursalesSelect) {
        filters.sucursales.forEach(val => {
          const option = sucursalesSelect.querySelector(`option[value="${val}"]`);
          if (option) {
            sucursalesNames.push(option.textContent);
          }
        });
      }
    }
  }
  
  // Si hay sucursales, agregarlas al título separadas por |
  if (sucursalesNames.length > 0) {
    titleElement.innerHTML = `${titleText} <span class="font-bold text-sky-600 dark:text-sky-400">${sucursalesNames.join(" | ")}</span>`;
  } else {
    titleElement.textContent = titleText;
  }
  
  // Construir el subtítulo con período y otros filtros
  const subtitleParts = [];
  
  // Período
  if (filters.fecha_inicio && filters.fecha_fin) {
    const formatDate = (dateStr) => {
      if (!dateStr) return '';
      const [year, month, day] = dateStr.split('-');
      return `${day}/${month}/${year}`;
    };
    subtitleParts.push(`${formatDate(filters.fecha_inicio)} - ${formatDate(filters.fecha_fin)}`);
  }
  
  // Punto de venta
  if (filters.punto_venta && filters.punto_venta.length > 0) {
    let nombres = [];
    // Primero intentar usar los nombres guardados
    if (filters._punto_venta_names && filters._punto_venta_names.length > 0) {
      nombres = filters._punto_venta_names;
    } else {
      // Fallback: buscar en el select si está disponible
      const pvSelect = document.getElementById(`punto_venta_${safeItemKey}`);
      if (pvSelect) {
        nombres = filters.punto_venta.map(val => {
          const option = pvSelect.querySelector(`option[value="${val}"]`);
          return option ? option.textContent : val;
        });
      }
    }
    
    if (nombres.length > 0) {
      if (nombres.length <= 2) {
        subtitleParts.push(`PV: ${nombres.join(", ")}`);
      } else {
        subtitleParts.push(`PV: ${nombres[0]} +${nombres.length - 1}`);
      }
    }
  }
  
  // Clientes excluidos
  if (filters.clientes_excluidos && filters.clientes_excluidos.length > 0) {
    subtitleParts.push(`Excl. ${filters.clientes_excluidos.length} cliente(s)`);
  }
  
  // Actualizar subtítulo
  if (subtitleElement) {
    const lastUpdateSpan = subtitleElement.querySelector("[data-workspace-last-update]");
    const lastUpdateText = lastUpdateSpan ? lastUpdateSpan.textContent : "—";
    
    if (subtitleParts.length > 0) {
      subtitleElement.innerHTML = `<span class="font-bold text-sky-600 dark:text-sky-400">${subtitleParts.join(' • ')}</span> • Últ. act.: <span data-workspace-last-update>${lastUpdateText}</span>`;
    } else {
      subtitleElement.innerHTML = `Última actualización: <span data-workspace-last-update>${lastUpdateText}</span>`;
    }
  }
};

// Variable global para controlar si ya se adjuntó el event delegation para toggle filtros
let workspaceFilterToggleDelegationAttached = false;

const attachWorkspaceFilterToggleHandlers = () => {
  if (!workspaceApiUrl) return;
  
  if (workspaceFilterToggleDelegationAttached) {
    return;
  }
  
  // Event delegation para botón "Filtros"
  dashboardRoot.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-toggle-filters]");
    if (!button) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    const itemKey = button.dataset.itemKey;
    if (!itemKey) return;
    
    const panel = dashboardRoot.querySelector(`[data-filters-panel][data-item-key="${itemKey}"]`);
    if (!panel) return;
    
    const isHidden = panel.classList.contains("hidden");
    
    if (isHidden) {
      // Mostrar panel
      panel.classList.remove("hidden");
      button.classList.add("bg-sky-100", "dark:bg-sky-900/30", "text-sky-600", "dark:text-sky-400");
      
      await new Promise((resolve) => setTimeout(resolve, 100));
      const section = button.closest("section[data-report-slug]");
      const slug = section?.dataset.reportSlug || "";
      // Pedidos: mismo patrón de período/intervalo que el informe completo; sincronizar al abrir siempre.
      if (slug === "pedidos-pendientes") {
        initializeWorkspacePedidosPeriodFilters(itemKey);
      } else if (!panel.dataset.initialized) {
        console.log(`[toggleFilters] Primera apertura, inicializando filtros para ${itemKey}`);
        await initializeWorkspaceFilters(itemKey, slug || "total-consolidado-operativo");
        panel.dataset.initialized = "true";
      }
    } else {
      // Ocultar panel
      panel.classList.add("hidden");
      button.classList.remove("bg-sky-100", "dark:bg-sky-900/30", "text-sky-600", "dark:text-sky-400");
    }
  });
  
  workspaceFilterToggleDelegationAttached = true;
};

// Variable global para controlar si ya se adjuntó el event delegation para aplicar filtros
let workspaceApplyFiltersDelegationAttached = false;

const attachWorkspaceApplyFiltersHandlers = () => {
  if (!workspaceApiUrl) return;
  
  if (workspaceApplyFiltersDelegationAttached) {
    return;
  }
  
  // Event delegation para botón "Aplicar Filtros"
  dashboardRoot.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-apply-workspace-filters]");
    if (!button) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    const itemKey = button.dataset.itemKey;
    const slug = button.dataset.reportSlug;
    if (!itemKey || !slug) return;
    
    if (button.dataset.loading === "true") return;
    button.dataset.loading = "true";
    button.classList.add("opacity-60", "pointer-events-none");
    
    try {
      const safeItemKey = itemKey.replace(/[^a-zA-Z0-9]/g, '_');
      const filterKind = button.dataset.workspaceFilterKind || "consolidado";

      if (filterKind === "pedidos-period") {
        const periodoTipo = document.getElementById(`periodo_tipo_${safeItemKey}`)?.value || "personalizado";
        const fechaInicio = document.getElementById(`fecha_inicio_${safeItemKey}`)?.value;
        const fechaFin = document.getElementById(`fecha_fin_${safeItemKey}`)?.value;
        const filters = workspaceBuildPeriodFiltersPayload(periodoTipo, fechaInicio, fechaFin);
        filters.periodo_tipo = periodoTipo;
        const refreshIntervalSelect = document.getElementById(`refresh_interval_${safeItemKey}`);
        if (refreshIntervalSelect?.value) {
          filters.refresh_interval = migrateLegacyInterval(refreshIntervalSelect.value);
        }
        try {
          localStorage.setItem(`report_filters_${itemKey}`, JSON.stringify(filters));
        } catch (err) {
          console.warn("No se pudieron guardar filtros:", err);
        }
        updateWorkspaceWidgetTitle(itemKey, filters);
        const widgetPedidos = dashboardRoot.querySelector(`[data-widget-id][data-item-key="${itemKey}"]`);
        if (widgetPedidos) {
          const widgetId = widgetPedidos.dataset.widgetId;
          const index = parseInt(widgetId.replace("workspace-", ""), 10);
          const response = await fetch(workspaceApiUrl, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });
          if (response.ok) {
            const payload = await response.json();
            const slot = (payload.slots || []).find((s) => (s.item_key || s.slug) === itemKey);
            if (slot) {
              await loadWorkspaceSlot(slot, index, false);
            }
          }
        }
        toast("Filtros aplicados correctamente");
        return;
      }

      // Recolectar filtros del panel total consolidado operativo
      const filters = {};
      
      // Fechas
      const fechaInicioInput = document.getElementById(`fecha_inicio_${safeItemKey}`);
      const fechaFinInput = document.getElementById(`fecha_fin_${safeItemKey}`);
      if (fechaInicioInput && fechaInicioInput.value) {
        filters.fecha_inicio = fechaInicioInput.value;
      }
      if (fechaFinInput && fechaFinInput.value) {
        filters.fecha_fin = fechaFinInput.value;
      }
      
      // Sucursales
      const sucursalesSelect = document.getElementById(`sucursales_${safeItemKey}`);
      if (sucursalesSelect) {
        const selectedSucursales = Array.from(sucursalesSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        filters.sucursales = selectedSucursales;
        // Guardar también los nombres para mostrar en el título
        filters._sucursales_names = Array.from(sucursalesSelect.selectedOptions).map(opt => opt.textContent).filter(v => v);
      }
      
      // Punto de venta
      const puntoVentaSelect = document.getElementById(`punto_venta_${safeItemKey}`);
      if (puntoVentaSelect) {
        const selectedPuntoVenta = Array.from(puntoVentaSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        filters.punto_venta = selectedPuntoVenta;
        // Guardar también los nombres
        filters._punto_venta_names = Array.from(puntoVentaSelect.selectedOptions).map(opt => opt.textContent).filter(v => v);
      }
      
      // Clientes excluidos
      const clientesExcluidosSelect = document.getElementById(`clientes_excluidos_${safeItemKey}`);
      if (clientesExcluidosSelect) {
        const selectedClientes = Array.from(clientesExcluidosSelect.selectedOptions).map(opt => String(opt.value)).filter(v => v);
        filters.clientes_excluidos = selectedClientes;
      }
      
      // Guardar filtros en localStorage con el item_key
      try {
        localStorage.setItem(`report_filters_${itemKey}`, JSON.stringify(filters));
      } catch (e) {
        console.warn("No se pudieron guardar filtros:", e);
      }
      
      // Actualizar el título con los filtros seleccionados
      updateWorkspaceWidgetTitle(itemKey, filters);
      
      // Recargar solo este widget
      const widget = dashboardRoot.querySelector(`[data-widget-id][data-item-key="${itemKey}"]`);
      if (widget) {
        const widgetId = widget.dataset.widgetId;
        const index = parseInt(widgetId.replace("workspace-", ""), 10);
        
        // Buscar el slot correspondiente
        const response = await fetch(workspaceApiUrl, {
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (response.ok) {
          const payload = await response.json();
          const slot = (payload.slots || []).find(s => (s.item_key || s.slug) === itemKey);
          if (slot) {
            await loadWorkspaceSlot(slot, index, false);
          }
        }
      }
      
      toast("Filtros aplicados correctamente");
    } catch (error) {
      console.error("Error al aplicar filtros:", error);
      toast(error.message || "No se pudieron aplicar los filtros", "error");
    } finally {
      button.classList.remove("opacity-60", "pointer-events-none");
      button.dataset.loading = "false";
    }
  });
  
  workspaceApplyFiltersDelegationAttached = true;
};

// Variable global para controlar si ya se adjuntó el event delegation para duplicar
let workspaceDuplicateDelegationAttached = false;

const attachWorkspaceDuplicateHandlers = () => {
  if (!workspaceApiUrl) return;
  
  // Si ya se adjuntó el event delegation, no hacer nada
  if (workspaceDuplicateDelegationAttached) {
    return;
  }
  
  // Usar event delegation en el dashboardRoot
  dashboardRoot.addEventListener("click", async (e) => {
    const button = e.target.closest("[data-duplicate-workspace]");
    if (!button) {
      return;
    }
    
    e.preventDefault();
    e.stopPropagation();
    
    const itemKey = button.dataset.itemKey;
    const slug = button.dataset.reportSlug;
    if (!slug) return;
    
    if (button.dataset.loading === "true") return;
    button.dataset.loading = "true";
    button.classList.add("opacity-60", "pointer-events-none");
    
    try {
      const response = await fetch(workspaceApiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ slug, allow_duplicate: true }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || "No se pudo duplicar");
      }
      const payload = await response.json();
      const newItemKey = payload.item_key;
      if (newItemKey && itemKey && newItemKey !== itemKey) {
        try {
          const saved = localStorage.getItem(`report_filters_${itemKey}`);
          if (saved) {
            localStorage.setItem(`report_filters_${newItemKey}`, saved);
          }
        } catch (e) {
          console.warn("No se pudieron copiar filtros al duplicado:", e);
        }
      }
      setWorkspaceCount(payload.count ?? "-");
      toast("Duplicado agregado al workspace");
      await fetchWorkspaceData();
    } catch (error) {
      console.error(error);
      toast(error.message || "No se pudo duplicar", "error");
    } finally {
      button.classList.remove("opacity-60", "pointer-events-none");
      button.dataset.loading = "false";
    }
  });
  
  workspaceDuplicateDelegationAttached = true;
};

// Función para mostrar animación de carga en un widget específico del workspace
const showWorkspaceWidgetLoading = (widget) => {
  const container = widget.querySelector("[data-widget-content]");
  if (!container) return;
  
  // Usar un ID único basado en el widget para evitar conflictos
  const widgetId = widget.dataset.widgetId || "unknown";
  const overlayId = `workspace-loading-overlay-${widgetId}`;
  
  // Remover overlay anterior si existe
  const existingOverlay = widget.querySelector(`#${overlayId}`);
  if (existingOverlay) {
    existingOverlay.remove();
  }
  
  // Buscar el contenedor relativo (el div con class="relative" que envuelve data-widget-content)
  const relativeContainer = container.parentElement;
  if (!relativeContainer) return;
  
  const loadingOverlay = document.createElement("div");
  loadingOverlay.id = overlayId;
  loadingOverlay.className = "absolute inset-0 bg-slate-900/80 flex items-center justify-center z-10 pointer-events-none";
  loadingOverlay.style.position = "absolute";
  loadingOverlay.style.top = "0";
  loadingOverlay.style.left = "0";
  loadingOverlay.style.right = "0";
  loadingOverlay.style.bottom = "0";
  loadingOverlay.style.margin = "0";
  loadingOverlay.style.padding = "0";
  loadingOverlay.style.boxSizing = "border-box";
  loadingOverlay.style.width = "100%";
  loadingOverlay.style.height = "100%";
  loadingOverlay.style.overflow = "hidden";
  loadingOverlay.innerHTML = `
    <div class="flex flex-col items-center gap-3">
      <div class="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
      <p class="text-xs text-slate-200 tracking-[0.2em] uppercase">Actualizando...</p>
    </div>
  `;
  
  // El relativeContainer ya tiene position: relative en el HTML
  // Agregar el overlay directamente sin modificar estilos del parent
  relativeContainer.appendChild(loadingOverlay);
};

// Función para ocultar animación de carga en un widget específico del workspace
const hideWorkspaceWidgetLoading = (widget) => {
  const widgetId = widget.dataset.widgetId || "unknown";
  const overlayId = `workspace-loading-overlay-${widgetId}`;
  const loadingOverlay = widget.querySelector(`#${overlayId}`);
  if (loadingOverlay) {
    loadingOverlay.style.opacity = "0";
    loadingOverlay.style.transition = "opacity 0.3s ease-out";
    setTimeout(() => {
      if (loadingOverlay.parentNode) {
        loadingOverlay.remove();
      }
    }, 300);
  }
};

const loadWorkspaceSlot = async (slot, index, isAutoRefresh = false) => {
  const widgetId = `workspace-${index}`;
  const widget = dashboardRoot.querySelector(`[data-widget-id="${widgetId}"]`);
  if (!widget) {
    console.warn(`[loadWorkspaceSlot] Widget no encontrado: ${widgetId}`);
    return;
  }
  if (isPedidosPendientesSlug(slot.slug)) {
    const ik = slot.item_key != null ? slot.item_key : slot.slug;
    const sk = ik.replace(/[^a-zA-Z0-9]/g, "_");
    const gMount = document.getElementById(`workspace_pedidos_grouping_${sk}`);
    if (gMount) {
      gMount.innerHTML = "";
    }
  }
  const config = getWidgetConfig(widget);
  console.log(`[loadWorkspaceSlot] Config para ${slot.slug}:`, config);
  
  // Mostrar animación de carga (siempre, incluso en auto-refresh para mejor UX)
  showWorkspaceWidgetLoading(widget);
  
  try {
    // Aumentar el límite para reportes que muestran tablas con detalles
    const isTableReport = slot.slug === "uninvoiced_remitos" || isPedidosPendientesSlug(slot.slug);
    const limit = isTableReport ? 1000 : 200;
    const requestBody = { slug: slot.slug, limit: limit };
    
    // Filtros por instancia: report_filters_<item_key> (item_key = slug o slug::instance_id)
    let savedFilters = null;
    const itemKey = slot.item_key != null ? slot.item_key : slot.slug;
    try {
      const storageKey = `report_filters_${itemKey}`;
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        savedFilters = JSON.parse(saved);
        console.log(`[loadWorkspaceSlot] Filtros guardados encontrados en localStorage para ${slot.slug}:`, savedFilters);
      }
    } catch (e) {
      console.warn(`[loadWorkspaceSlot] Error cargando filtros desde localStorage para ${slot.slug}:`, e);
    }
    
    // Para reportes declarativos, usar los filtros guardados en localStorage (prioridad)
    // o en la configuración del widget (fallback)
    const widgetConfig = slot.widget?.configuration || {};
    const reportConfig = widgetConfig.config || {};
    const isDeclarativeReport = reportConfig.version === "declarative-v1";
    
    // Filtrar metadatos de los filtros guardados (aplicar a todos los reportes)
    let actualFilters = null;
    if (savedFilters && Object.keys(savedFilters).length > 0) {
      actualFilters = {};
      Object.keys(savedFilters).forEach(key => {
        // Incluir todos los campos excepto metadatos de UI y claves auxiliares (_sucursales_names, etc.)
        if (
          key !== "refresh_interval" &&
          key !== "realtime_active" &&
          !key.startsWith("_")
        ) {
          actualFilters[key] = savedFilters[key];
        }
      });
      // Solo usar si hay filtros reales (no solo metadatos)
      if (Object.keys(actualFilters).length === 0) {
        actualFilters = null;
      }
    }

    if (actualFilters && isPedidosPendientesSlug(slot.slug)) {
      ["sucursales", "punto_venta", "clientes_excluidos", "periodo_tipo"].forEach((k) => {
        delete actualFilters[k];
      });
      if (Object.keys(actualFilters).length === 0) {
        actualFilters = null;
      }
    }
    
    if (isDeclarativeReport) {
      // Prioridad 1: Filtros guardados en localStorage (más recientes)
      if (actualFilters) {
        requestBody.filters = actualFilters;
        console.log(`[loadWorkspaceSlot] Usando filtros guardados de localStorage para ${slot.slug}:`, requestBody.filters);
      } 
      // Prioridad 2: Filtros guardados en la configuración del widget
      else if (reportConfig.filters && Object.keys(reportConfig.filters).length > 0) {
        requestBody.filters = { ...reportConfig.filters };
        if (isPedidosPendientesSlug(slot.slug)) {
          ["sucursales", "punto_venta", "clientes_excluidos", "periodo_tipo"].forEach((k) => {
            delete requestBody.filters[k];
          });
        }
        console.log(`[loadWorkspaceSlot] Usando filtros guardados de configuración del widget para ${slot.slug}:`, requestBody.filters);
      }
    } else {
      // Para reportes legacy, usar filtros guardados si existen, sino usar lógica automática
      if (actualFilters) {
        requestBody.filters = actualFilters;
        console.log(`[loadWorkspaceSlot] Usando filtros guardados de localStorage para reporte legacy ${slot.slug}:`, requestBody.filters);
      } else {
        // Lógica de filtros automáticos solo si no hay filtros guardados
        const reportsWithDateFilters = [
          "ventas_netas",
          "cash_flow_waterfall",
          "cash_flow_by_account",
          "uninvoiced_remitos",
          "pedidos-pendientes",
          "sales_summary",
          "total-consolidado-operativo",
          "comprobantes-rutas",
        ];
        
        if (reportsWithDateFilters.includes(slot.slug)) {
          const today = new Date();
          
          // Calcular fecha de inicio: día 1 del mes anterior completo
          const firstDay = new Date(today.getFullYear(), today.getMonth() - 1, 1);
          
          // Fecha fin: hoy (mes en curso hasta la fecha actual)
          const lastDay = new Date(today);
          
          requestBody.filters = {
            fecha_inicio: firstDay.toISOString().split('T')[0],
            fecha_fin: lastDay.toISOString().split('T')[0],
          };
          console.log(`[loadWorkspaceSlot] Usando filtros automáticos para reporte legacy ${slot.slug}:`, requestBody.filters);
        }
      }
    }
    
    console.log(`[loadWorkspaceSlot] Solicitando datos para ${slot.slug}:`, requestBody);
    const response = await fetch(dashboardRoot.dataset.dashboardUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify(requestBody),
    });
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[loadWorkspaceSlot] Error en respuesta para ${slot.slug}:`, response.status, errorText);
      throw new Error(`No se pudieron cargar los datos del informe: ${response.status}`);
    }
    const payload = await response.json();
    console.log(`[loadWorkspaceSlot] Respuesta para ${slot.slug}:`, payload);
    
    // Verificar si es un reporte declarativo (tiene schema y query_result)
    const isDeclarative = payload.schema && payload.query_result;
    
    if (isDeclarative) {
      // Para reportes declarativos, usar WidgetEngine
      console.log(`[loadWorkspaceSlot] Reporte declarativo detectado: ${slot.slug}`, {
        hasSchema: !!payload.schema,
        hasQueryResult: !!payload.query_result,
        schemaWidgets: payload.schema?.default_widgets?.length || 0
      });
      
      // Preservar el header del workspace (título, botones, última actualización)
      const header = widget.querySelector("header");
      
      // Cuerpo del slot: solo el div.relative hijo directo de section. No usar querySelector(".relative")
      // sin :scope porque el panel de filtros (pedidos-pendientes, total-consolidado) incluye varios .relative internos.
      let workspaceSlotBody = widget.querySelector(":scope > .relative");
      if (!workspaceSlotBody) {
        workspaceSlotBody = document.createElement("div");
        workspaceSlotBody.className = "relative";
        workspaceSlotBody.style.minHeight = "350px";
        widget.appendChild(workspaceSlotBody);
      } else {
        workspaceSlotBody.innerHTML = "";
      }

      // Misma estructura que buildWorkspaceDOM (legacy): [data-widget-content] + [data-widget-table-wrapper]
      // para que pedidos-pendientes / total-consolidado y reportes declarativo compartan DOM y estilos fullscreen.
      const contentShell = document.createElement("div");
      // aspect-[16/7] igual que buildWorkspaceDOM en vista normal; en fullscreen workspace.html anula aspect-ratio.
      contentShell.className =
        "aspect-[16/7] w-full min-h-0 flex-1 flex flex-col bg-white dark:bg-slate-950 p-6";
      contentShell.setAttribute("data-widget-content", "");
      const tableWrapper = document.createElement("div");
      tableWrapper.className = "px-6 py-3 hidden";
      tableWrapper.setAttribute("data-widget-table-wrapper", "");
      tableWrapper.style.minHeight = "288px";

      const engineContainer = document.createElement("div");
      engineContainer.className = "w-full flex-1 min-h-0 flex flex-col";
      if (isWorkspaceTv) {
        engineContainer.setAttribute("data-workspace-tv", "true");
      }
      engineContainer.setAttribute("data-workspace-mode", "true");
      contentShell.appendChild(engineContainer);
      workspaceSlotBody.appendChild(contentShell);
      workspaceSlotBody.appendChild(tableWrapper);
      
      if (window.WidgetEngine) {
        // Inicializar y renderizar con WidgetEngine
        try {
          window.WidgetEngine.init(engineContainer, payload.schema, payload.query_result, slot.slug);
          window.WidgetEngine.renderDefaultDashboard();
          
          // Actualizar el título del header del workspace con el título dinámico si es una tabla
          if (header && payload.schema?.default_widgets?.length > 0) {
            const firstWidget = payload.schema.default_widgets[0];
            if (firstWidget.kind === "table" && payload.query_result?.data) {
              const dynamicTitle = window.WidgetEngine.buildTableTitle(firstWidget, payload.query_result.data);
              if (dynamicTitle) {
                const titleElement = header.querySelector("h2");
                if (titleElement) {
                  titleElement.textContent = dynamicTitle;
                }
              }
            }
          }
          
          console.log(`[loadWorkspaceSlot] WidgetEngine renderizado exitosamente para ${slot.slug}`);
        } catch (error) {
          console.error(`[loadWorkspaceSlot] Error renderizando WidgetEngine para ${slot.slug}:`, error);
          engineContainer.innerHTML = `
            <div class="p-4 text-center">
              <p class="text-xs text-rose-400 mb-2">Error al renderizar el informe</p>
              <p class="text-[10px] text-slate-400">${error.message}</p>
            </div>
          `;
        }
      } else {
        console.error(`[loadWorkspaceSlot] No se puede renderizar ${slot.slug}: WidgetEngine no disponible`);
        engineContainer.innerHTML = `
          <div class="p-4 text-center">
            <p class="text-xs text-rose-400 mb-2">Error: WidgetEngine no disponible</p>
            <p class="text-[10px] text-slate-400">Verifique que widget_engine.js esté cargado correctamente</p>
          </div>
        `;
      }
      
      // Ocultar animación de carga después de renderizar
      hideWorkspaceWidgetLoading(widget);
      return;
    }
    
    // Para reportes no declarativos, usar el sistema antiguo
    const data = payload.data || [];
    console.log(`[loadWorkspaceSlot] ${slot.slug}:`, { dataLength: data.length, payload, config });
    widgetDataCache.set(widgetId, { data, config, meta: payload.meta || {} });
    
    // Actualizar el título con el conteo para reportes específicos
    const reportSlug = slot.slug;
    if (isPedidosPendientesSlug(reportSlug) || reportSlug === "uninvoiced_remitos") {
      const titleElement = widget.querySelector("header h2");
      if (titleElement) {
        const baseName = slot.name;
        const count = data.length;
        titleElement.textContent = `${baseName}: ${count}`;
      }
    }
    
    const widgetType = widget.dataset.widgetType;
    
    // HÍBRIDO: Ventas Netas bar → WidgetEngine
    const isVentasNetasBar = isVentasNetasSlug(reportSlug) &&
      (widgetType === "d3-bar-grouped" || widgetType === "d3-bar" || widgetType === "d3-bar-stacked" || widgetType === "bar") &&
      window.WidgetEngine &&
      data?.length > 0;

    if (isVentasNetasBar) {
      renderWidgetChart(widget, data, config, payload.meta || {});
      console.log("[Ventas Netas] Gráfico de barras renderizado con WidgetEngine (workspace)");
      renderTable(widget, data, { show: false });
      const wrapper = widget.closest("[data-widget-wrapper]");
      if (wrapper) {
        wrapper.querySelectorAll("[data-widget-note]").forEach((n) => { n.style.display = "none"; n.remove(); });
        if (payload.notes && payload.notes.length) {
          const info = document.createElement("div");
          info.className = "px-6 py-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400";
          info.dataset.widgetNote = "true";
          info.style.margin = "0";
          info.style.flexShrink = "0";
          info.innerHTML = `<strong>${widget.dataset.noteLabel || "Notas"}:</strong> ${payload.notes.join(" · ")}`;
          wrapper.appendChild(info);
        }
      }
      hideWorkspaceWidgetLoading(widget);
      return;
    }
    
    // Manejar diferentes tipos de widgets en workspace
    if (widgetType === "pivot-table") {
      // Para pivot-table, solo mostrar tabla (sin gráfico)
      const chartContainer = widget.querySelector("[data-widget-content]");
      if (chartContainer) {
        chartContainer.style.display = "none";
      }
      // Mostrar la tabla con todos los datos
      renderTable(widget, data, { show: true });
      // Asegurar que el wrapper de la tabla esté visible y tenga el tamaño correcto
      const tableWrapper = widget.querySelector("[data-widget-table-wrapper]");
      if (tableWrapper) {
        tableWrapper.classList.remove("hidden");
        // Para pedidos pendientes y remitos no facturados: altura para encabezado + 5 filas visibles
        // Encabezado: ~48px, cada fila: ~48px, total: ~288px
        if (isPedidosPendientesSlug(reportSlug) || reportSlug === "uninvoiced_remitos") {
          tableWrapper.style.height = "288px";
          tableWrapper.style.minHeight = "288px";
          tableWrapper.style.maxHeight = "288px";
          tableWrapper.style.overflowY = "auto";
          tableWrapper.style.overflowX = "auto";
        } else {
          // Para otros reportes pivot-table, mantener altura flexible pero consistente
          tableWrapper.style.minHeight = "350px";
          tableWrapper.style.maxHeight = "500px";
          tableWrapper.style.height = "auto";
          tableWrapper.style.overflowY = "auto";
        }
      }
    } else if (widgetType === "d3-cards") {
      // Para d3-cards, mostrar solo las tarjetas
      const chartContainer = widget.querySelector("[data-widget-content]");
      if (chartContainer) {
        chartContainer.style.display = "";
      }
      console.log(`[loadWorkspaceSlot] Renderizando d3-cards para ${reportSlug}:`, { data, config });
      renderChart(widget, data, config);
      renderTable(widget, data, { show: false });
    } else {
      // Para otros tipos de widgets (gráficos)
      console.log(`[loadWorkspaceSlot] Renderizando ${widgetType} para ${reportSlug}:`, { dataLength: data.length, config });
      renderChart(widget, data, config);
      renderTable(widget, data, { show: false });
    }

    const wrapper = widget.closest("[data-widget-wrapper]");
    if (wrapper) {
      // Remover notas anteriores
      wrapper.querySelectorAll("[data-widget-note]").forEach((note) => {
        note.style.display = "none";
        note.remove();
      });
      
      // Agregar notas si existen, pero asegurar que no afecten el layout
      if (payload.notes && payload.notes.length) {
        const info = document.createElement("div");
        info.className = "px-6 py-3 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400";
        info.dataset.widgetNote = "true";
        info.style.margin = "0";
        info.style.flexShrink = "0";
        info.innerHTML = `<strong>${widget.dataset.noteLabel || "Notas"}:</strong> ${payload.notes.join(" · ")}`;
        wrapper.appendChild(info);
      }
    }
    
    // Restaurar el título con los filtros guardados (si existen)
    if (savedFilters && Object.keys(savedFilters).length > 0) {
      const itemKey = slot.item_key != null ? slot.item_key : slot.slug;
      
      // Si hay sucursales pero no tienen nombres guardados, obtenerlos del API
      if (savedFilters.sucursales && savedFilters.sucursales.length > 0 && !savedFilters._sucursales_names) {
        try {
          const sucursalesResponse = await fetch("/api/reports/filters/?type=sucursales");
          if (sucursalesResponse.ok) {
            const sucursalesData = await sucursalesResponse.json();
            const sucursalesList = sucursalesData.sucursales || [];
            savedFilters._sucursales_names = savedFilters.sucursales.map(id => {
              const found = sucursalesList.find(s => String(s.id) === String(id) || s.codigo === id);
              return found ? (found.nombre || found.codigo) : id;
            });
            // Guardar los nombres para la próxima vez
            try {
              localStorage.setItem(`report_filters_${itemKey}`, JSON.stringify(savedFilters));
            } catch (e) { /* ignore */ }
          }
        } catch (e) {
          console.warn("No se pudieron obtener nombres de sucursales:", e);
        }
      }
      
      updateWorkspaceWidgetTitle(itemKey, savedFilters);
    }
    
    // Ocultar animación de carga después de renderizar
    hideWorkspaceWidgetLoading(widget);
  } catch (error) {
    console.error(error);
    // Ocultar animación de carga incluso si hay error
    hideWorkspaceWidgetLoading(widget);
    widget.innerHTML = `<p class="text-xs text-rose-400">${error.message}</p>`;
  }
};

const fetchWorkspaceData = async (isAutoRefresh = false) => {
  if (!workspaceApiUrl) {
    return;
  }
  try {
    const response = await fetch(workspaceApiUrl, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    });
    if (!response.ok) {
      throw new Error("No se pudo cargar el workspace");
    }
    const payload = await response.json();
    const slots = payload.slots || [];
    setWorkspaceCount(payload.count ?? slots.length ?? 0);
    
    if (!isAutoRefresh) {
      // Solo reconstruir el DOM si no es auto-refresh
    widgetDataCache.clear();
    buildWorkspaceDOM(slots);
    attachWorkspaceRemovalHandlers();
    attachWorkspaceDuplicateHandlers();
    attachWorkspaceFilterToggleHandlers();
    attachWorkspaceApplyFiltersHandlers();
    // Re-attach drag and drop después de reconstruir el DOM
    attachWorkspaceDragAndDrop(dashboardRoot);
    setupWorkspaces(true);
    showWorkspace(0, { rerender: false });
    updateWorkspaceIndicator();
    }

    // Actualizar todos los slots del workspace actual
    if (isAutoRefresh) {
      // En auto-refresh, actualizar solo los widgets visibles del workspace actual
      const currentWorkspaceSlots = getCurrentWorkspaceSlots(slots);
      await Promise.all(currentWorkspaceSlots.map((slot, index) => {
        const widgetId = `workspace-${workspaceState.current * 4 + index}`;
        const widget = dashboardRoot.querySelector(`[data-widget-id="${widgetId}"]`);
        if (widget) {
          return loadWorkspaceSlot(slot, workspaceState.current * 4 + index, isAutoRefresh);
        }
        return Promise.resolve();
      }));
    } else {
      // En carga inicial, cargar todos los slots
      await Promise.all(slots.map((slot, index) => loadWorkspaceSlot(slot, index, isAutoRefresh)));
    }
    
    if (!isAutoRefresh) {
    showWorkspace(workspaceState.current, { rerender: true });
    }
    
    // Actualizar última actualización en todos los widgets del workspace actual
    updateWorkspaceLastUpdate();
  } catch (error) {
    console.error(error);
    if (!isAutoRefresh) {
    toast(error.message || "No se pudo cargar el workspace", "error");
    }
  }
};

// Función auxiliar para obtener los slots del workspace actual
const getCurrentWorkspaceSlots = (allSlots) => {
  const startIndex = workspaceState.current * 4;
  return allSlots.slice(startIndex, startIndex + 4);
};

// Función para actualizar la última actualización en todos los widgets del workspace
const updateWorkspaceLastUpdate = () => {
  const widgets = dashboardRoot.querySelectorAll("[data-widget-id]");
  widgets.forEach((widget) => {
    const lastUpdateElement = widget.querySelector("[data-workspace-last-update]");
    if (lastUpdateElement) {
      const now = new Date();
      const formattedDate = now.toLocaleDateString("es-AR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
      const timeString = now.toLocaleTimeString("es-AR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      });
      lastUpdateElement.textContent = `${formattedDate} ${timeString}`;
    }
  });
};

if (dashboardRoot) {
  if (!isWorkspaceMode) {
    setupWorkspaces();
  }

  initializeFiltersToggle();

  const apiUrl = dashboardRoot.dataset.dashboardUrl;
  const reportSlug = dashboardRoot.dataset.reportSlug;

  workspaceControls.prev = document.querySelector("[data-workspace-prev]");
  workspaceControls.next = document.querySelector("[data-workspace-next]");
  workspaceControls.indicator = document.querySelector("[data-workspace-indicator]");
  workspaceControls.prevDate = document.querySelector("[data-workspace-prev-date]");
  workspaceControls.nextDate = document.querySelector("[data-workspace-next-date]");

  updateWorkspaceIndicator();

  if (workspaceControls.prev && !isWorkspaceMobile) {
    workspaceControls.prev.addEventListener("click", () => {
      showWorkspace(workspaceState.current - 1);
    });
  }
  if (workspaceControls.next && !isWorkspaceMobile) {
    workspaceControls.next.addEventListener("click", () => {
      showWorkspace(workspaceState.current + 1);
    });
  }
  const fullscreenToggles = document.querySelectorAll("[data-fullscreen-toggle]");
  fullscreenToggles.forEach((btn) => btn.addEventListener("click", toggleFullScreen));
  if (fullscreenToggles.length) {
    setFullscreenButtonState(false);
  }
  document.addEventListener("fullscreenchange", syncFullscreenState);
};

// initializeTagsFilter: módulo compartido ./tags_filter.mjs (import al inicio del archivo).

// Función para inicializar tiempo real en workspace (debe estar definida antes de usarse)
const initializeWorkspaceRealtime = () => {
  const realtimeButton = document.querySelector("[data-realtime-toggle]");
  if (!realtimeButton) {
    return;
  }

  let workspaceRealtimeInterval = null;
  let workspaceRealtimeActive = false;

  // Obtener intervalo actual (usar función global si está disponible)
  const getCurrentRefreshInterval = () => {
    if (typeof getCurrentRefreshIntervalValue === 'function') {
      return getCurrentRefreshIntervalValue();
    }
    // Fallback
    const refreshIntervalSelect = document.getElementById("refresh_interval");
    if (refreshIntervalSelect && refreshIntervalSelect.value) {
      return refreshIntervalSelect.value;
    }
    return "interval_10m"; // Valor declarativo por defecto
  };

  // Calcular intervalo en milisegundos (usar función global si está disponible)
  const getRefreshIntervalMsLocal = (interval) => {
    if (typeof getRefreshIntervalMs === 'function') {
      return getRefreshIntervalMs(interval);
    }
    // Fallback
    switch (interval) {
      case "interval_30s":
      case "realtime": // Mantener compatibilidad con valores antiguos
        return 30000; // 30 segundos
      case "interval_5m":
      case "hourly": // Mantener compatibilidad con valores antiguos
        return 300000; // 5 minutos
      case "interval_10m":
      case "daily": // Mantener compatibilidad con valores antiguos
        return 600000; // 10 minutos
      case "interval_1h":
      case "weekly": // Mantener compatibilidad con valores antiguos
        return 3600000; // 1 hora
      case "interval_2h":
      case "monthly": // Mantener compatibilidad con valores antiguos
        return 7200000; // 2 horas
      default:
        return 600000; // 10 minutos por defecto
    }
  };

  const startWorkspaceRealtime = (intervalMs) => {
    stopWorkspaceRealtime(); // Asegurar que no hay intervalos duplicados
    workspaceRealtimeInterval = setInterval(() => {
      fetchWorkspaceData(true); // Pasar true para indicar que es auto-refresh
    }, intervalMs);
  };

  const stopWorkspaceRealtime = () => {
    if (workspaceRealtimeInterval) {
      clearInterval(workspaceRealtimeInterval);
      workspaceRealtimeInterval = null;
    }
  };

  // Mismo comportamiento que pedidos-pendientes: emerald cuando activo, rose cuando parado, "Detener tiempo real" / "Tiempo real", icono stop/refresh
  const updateWorkspaceRealtimeUI = (active) => {
    const label = realtimeButton.querySelector("[data-realtime-label]");
    const indicator = realtimeButton.querySelector("[data-realtime-indicator]");
    const icon = realtimeButton.querySelector("[data-realtime-icon]");
    if (active) {
      realtimeButton.classList.remove("text-slate-600", "dark:text-slate-400", "bg-slate-100", "dark:bg-slate-800", "hover:bg-slate-200", "dark:hover:bg-slate-700", "border-slate-300", "dark:border-slate-600", "text-rose-600", "dark:text-rose-400", "bg-rose-50", "dark:bg-rose-900/20", "hover:bg-rose-100", "dark:hover:bg-rose-900/30", "border-rose-300", "dark:border-rose-700");
      realtimeButton.classList.add("text-emerald-700", "dark:text-emerald-400", "bg-emerald-50", "dark:bg-emerald-900/20", "hover:bg-emerald-100", "dark:hover:bg-emerald-900/30", "border-emerald-300", "dark:border-emerald-700", "border");
      if (indicator) {
        indicator.classList.remove("opacity-0");
        indicator.classList.add("bg-emerald-500", "dark:bg-emerald-400");
        indicator.classList.remove("bg-rose-500", "dark:bg-rose-400");
      }
      if (label) label.textContent = "Detener tiempo real";
      if (icon) {
        icon.innerHTML = '<path d="M6 6h12v12H6z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
        icon.classList.remove("text-rose-600", "dark:text-rose-400");
        icon.classList.add("text-emerald-600", "dark:text-emerald-400");
      }
    } else {
      realtimeButton.classList.remove("text-emerald-700", "dark:text-emerald-400", "bg-emerald-50", "dark:bg-emerald-900/20", "hover:bg-emerald-100", "dark:hover:bg-emerald-900/30", "border-emerald-300", "dark:border-emerald-700", "text-slate-600", "dark:text-slate-400", "bg-slate-100", "dark:bg-slate-800", "hover:bg-slate-200", "dark:hover:bg-slate-700", "border-slate-300", "dark:border-slate-600");
      realtimeButton.classList.add("text-rose-600", "dark:text-rose-400", "bg-rose-50", "dark:bg-rose-900/20", "hover:bg-rose-100", "dark:hover:bg-rose-900/30", "border-rose-300", "dark:border-rose-700", "border");
      if (indicator) {
        indicator.classList.add("opacity-0");
        indicator.classList.add("bg-rose-500", "dark:bg-rose-400");
        indicator.classList.remove("bg-emerald-500", "dark:bg-emerald-400");
      }
      if (label) label.textContent = "Tiempo real";
      if (icon) {
        icon.innerHTML = '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
        icon.classList.remove("text-emerald-600", "dark:text-emerald-400");
        icon.classList.add("text-rose-600", "dark:text-rose-400");
      }
    }
    realtimeButton.setAttribute("data-realtime-active", String(active));
  };

  // Cargar estado guardado
  const savedRealtimeState = localStorage.getItem("workspace_realtime");
  if (savedRealtimeState === "true") {
    workspaceRealtimeActive = true;
    updateWorkspaceRealtimeUI(true);
    const currentInterval = getCurrentRefreshInterval();
    startWorkspaceRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
  }

  const toggleWorkspaceRealtime = () => {
    workspaceRealtimeActive = !workspaceRealtimeActive;
    
    if (workspaceRealtimeActive) {
      const currentInterval = getCurrentRefreshInterval();
      startWorkspaceRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
      localStorage.setItem("workspace_realtime", "true");
    } else {
      stopWorkspaceRealtime();
      localStorage.setItem("workspace_realtime", "false");
    }
    
    updateWorkspaceRealtimeUI(workspaceRealtimeActive);
  };

  // Escuchar cambios en el select de refresh_interval para actualizar el intervalo si tiempo real está activo
  const refreshIntervalSelect = document.getElementById("refresh_interval");
  if (refreshIntervalSelect) {
    refreshIntervalSelect.addEventListener("change", () => {
      if (workspaceRealtimeActive) {
        const currentInterval = getCurrentRefreshInterval();
        startWorkspaceRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
      }
    });
  }

  realtimeButton.addEventListener("click", toggleWorkspaceRealtime);
  
  // Limpiar intervalo al salir de la página
  window.addEventListener("beforeunload", () => {
    stopWorkspaceRealtime();
  });
};

// Función para inicializar tiempo real en workspace TV (sin controles visibles)
// Usa la misma configuración guardada en localStorage que la vista normal
const initializeWorkspaceRealtimeForTV = () => {
  let workspaceRealtimeInterval = null;
  let lastInterval = null;

  // Obtener intervalo guardado desde localStorage
  const getCurrentRefreshInterval = () => {
    try {
      const saved = localStorage.getItem("workspace_refresh_interval");
      if (saved) {
        return saved;
      }
    } catch (e) {
      console.warn("No se pudo cargar el intervalo guardado:", e);
    }
    return "interval_10m"; // Valor por defecto
  };

  // Calcular intervalo en milisegundos según refresh_interval
  const getRefreshIntervalMs = (interval) => {
    switch (interval) {
      case "interval_30s":
      case "realtime":
        return 30000; // 30 segundos
      case "interval_5m":
      case "hourly":
        return 300000; // 5 minutos
      case "interval_10m":
      case "daily":
        return 600000; // 10 minutos
      case "interval_1h":
      case "weekly":
        return 3600000; // 1 hora
      case "interval_2h":
      case "monthly":
        return 7200000; // 2 horas
      default:
        return 600000; // 10 minutos por defecto
    }
  };

  const startWorkspaceRealtime = (intervalMs) => {
    stopWorkspaceRealtime(); // Asegurar que no hay intervalos duplicados
    workspaceRealtimeInterval = setInterval(() => {
      fetchWorkspaceData(true); // Pasar true para indicar que es auto-refresh
    }, intervalMs);
  };

  const stopWorkspaceRealtime = () => {
    if (workspaceRealtimeInterval) {
      clearInterval(workspaceRealtimeInterval);
      workspaceRealtimeInterval = null;
    }
  };

  // Cargar estado guardado desde localStorage
  const savedRealtimeState = localStorage.getItem("workspace_realtime");
  const currentInterval = getCurrentRefreshInterval();
  lastInterval = currentInterval;
  
  // Si el tiempo real está activo, iniciarlo automáticamente
  if (savedRealtimeState === "true") {
    startWorkspaceRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
  }
  
  // También escuchar cambios en localStorage para sincronizar con la vista normal
  window.addEventListener("storage", (e) => {
    if (e.key === "workspace_realtime" || e.key === "workspace_refresh_interval") {
      // Recargar configuración cuando cambia en otra pestaña
      const newRealtimeState = localStorage.getItem("workspace_realtime");
      const newInterval = getCurrentRefreshInterval();
      
      if (newRealtimeState === "true") {
        startWorkspaceRealtime(getRefreshIntervalMs(newInterval));
        lastInterval = newInterval;
      } else {
        stopWorkspaceRealtime();
      }
    }
  });
  
  // Verificar cambios periódicamente (por si el storage event no funciona en la misma pestaña)
  setInterval(() => {
    const currentRealtimeState = localStorage.getItem("workspace_realtime");
    const currentIntervalValue = getCurrentRefreshInterval();
    
    if (currentRealtimeState === "true" && !workspaceRealtimeInterval) {
      // Si debería estar activo pero no lo está, iniciarlo
      startWorkspaceRealtime(getRefreshIntervalMs(currentIntervalValue));
      lastInterval = currentIntervalValue;
    } else if (currentRealtimeState !== "true" && workspaceRealtimeInterval) {
      // Si no debería estar activo pero lo está, detenerlo
      stopWorkspaceRealtime();
      lastInterval = null;
    } else if (currentRealtimeState === "true" && workspaceRealtimeInterval) {
      // Si está activo, verificar si el intervalo cambió
      if (currentIntervalValue !== lastInterval) {
        startWorkspaceRealtime(getRefreshIntervalMs(currentIntervalValue));
        lastInterval = currentIntervalValue;
      }
    }
  }, 5000); // Verificar cada 5 segundos
  
  // Limpiar intervalo al salir de la página
  window.addEventListener("beforeunload", () => {
    stopWorkspaceRealtime();
  });
};

if (dashboardRoot) {
  const loadFilterOptions = async () => {
    const apiUrl = dashboardRoot.dataset.dashboardUrl;
    const reportSlug = dashboardRoot.dataset.reportSlug;

    if (isLogisticaListaComprobantesRutasSlug(reportSlug)) {
      const savedFilters = loadFilters();
      if (savedFilters) {
        applyFilters(savedFilters);
      }
      return;
    }
    
    if (!isVentasNetasSlug(reportSlug) && reportSlug !== "cash_flow_waterfall" && reportSlug !== "cash_flow_by_account" && reportSlug !== "cash_flow_detailed_movements" && reportSlug !== "uninvoiced_remitos" && !isInformeBoDualPeriodo(reportSlug) && reportSlug !== "total-consolidado-operativo" && reportSlug !== "stock-existencias") {
      return;
    }
    
    try {
      // Cargar filtros guardados ANTES de cargar las opciones
      const savedFilters = loadFilters();

      // BO / Objetivos vs BO: sin PV en formulario salvo ventas-marcas-mensual (ADR familia BO + A3).
      const isBoReport = isInformeBoDualPeriodo(reportSlug);
      const loadPuntoVentaOptions = !isBoReport || isVentasMarcasMensualSlug(reportSlug);
      if (loadPuntoVentaOptions) {
        const pvResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=puntos_venta`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        });

        if (pvResponse.ok) {
          const pvData = await pvResponse.json();
          const pvSelect = document.getElementById("punto_venta");
          if (pvSelect) {
            pvSelect.innerHTML = "";
            pvData.puntos_venta?.forEach((pv) => {
              const option = document.createElement("option");
              option.value = pv.value;
              option.textContent = pv.label;
              if (savedFilters && savedFilters.punto_venta && Array.isArray(savedFilters.punto_venta)) {
                if (savedFilters.punto_venta.includes(pv.value)) {
                  option.selected = true;
                }
              }
              pvSelect.appendChild(option);
            });
            initializeTagsFilter("punto_venta", "puntos_venta");
          }
        }
      }

      const sucResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=sucursales`, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      if (sucResponse.ok) {
        const sucData = await sucResponse.json();
        const sucSelect = document.getElementById("sucursales");
        if (sucSelect) {
          sucSelect.innerHTML = "";
          sucData.sucursales?.forEach((suc) => {
            const option = document.createElement("option");
            option.value = suc.value;
            option.textContent = suc.label;
            if (savedFilters && savedFilters.sucursales && Array.isArray(savedFilters.sucursales)) {
              if (savedFilters.sucursales.includes(suc.value)) {
                option.selected = true;
              }
            }
            sucSelect.appendChild(option);
          });
          initializeTagsFilter("sucursales", "sucursales");
        }
      }
      
      // Cargar clientes para "Clientes a excluir" (Ventas Netas, Remitos, Total Consolidado, BO Stock Facturación)
      const reportShowsClientesExcluir = isVentasNetasSlug(reportSlug) || reportSlug === "uninvoiced_remitos" || reportSlug === "total-consolidado-operativo" || isInformeBoDualPeriodo(reportSlug);
      if (reportShowsClientesExcluir) {
        const clientesResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=clientes`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        });
        if (clientesResponse.ok) {
          const clientesData = await clientesResponse.json();
          const clientesSelect = document.getElementById("clientes_excluidos");
          if (clientesSelect) {
            clientesSelect.innerHTML = "";
            (clientesData.clientes || []).forEach((cli) => {
              const option = document.createElement("option");
              option.value = cli.value;
              option.textContent = cli.label;
              if (savedFilters && savedFilters.clientes_excluidos && Array.isArray(savedFilters.clientes_excluidos)) {
                if (savedFilters.clientes_excluidos.includes(String(cli.value))) {
                  option.selected = true;
                }
              }
              clientesSelect.appendChild(option);
            });
            initializeTagsFilter(
              "clientes_excluidos",
              "clientes",
              isInformeVentasMarcasFamiliaSlug(reportSlug) ? "clientes_incluir" : undefined
            );
          }
        }
      }
      if (isInformeVentasMarcasFamiliaSlug(reportSlug)) {
        const clientesIncludeSelect = document.getElementById("clientes_incluir");
        if (clientesIncludeSelect) {
          const clientesIncResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=clientes`, {
            headers: {
              "X-Requested-With": "XMLHttpRequest",
            },
          });
          if (clientesIncResponse.ok) {
            const clientesIncData = await clientesIncResponse.json();
            clientesIncludeSelect.innerHTML = "";
            (clientesIncData.clientes || []).forEach((cli) => {
              const option = document.createElement("option");
              option.value = String(cli.value);
              option.textContent = cli.label;
              if (savedFilters && savedFilters.clientes_incluir && Array.isArray(savedFilters.clientes_incluir)) {
                if (savedFilters.clientes_incluir.map(String).includes(String(cli.value))) {
                  option.selected = true;
                }
              }
              clientesIncludeSelect.appendChild(option);
            });
            initializeTagsFilter("clientes_incluir", "clientes", "clientes_excluidos");
          }
        }
      }

      if (isInformeVentasMarcasFamiliaSlug(reportSlug)) {
        const viajResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=viajantes`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        });
        if (viajResponse.ok) {
          const viajData = await viajResponse.json();
          const vendSelect = document.getElementById("vendedores_excluidos");
          const vendIncluirSelect = document.getElementById("vendedores_incluir");
          if (vendSelect || vendIncluirSelect) {
            if (vendSelect) vendSelect.innerHTML = "";
            if (vendIncluirSelect) vendIncluirSelect.innerHTML = "";
            (viajData.viajantes || []).forEach((v) => {
              if (vendSelect) {
                const option = document.createElement("option");
                option.value = String(v.value);
                option.textContent = v.label;
                if (savedFilters && savedFilters.vendedores_excluidos && Array.isArray(savedFilters.vendedores_excluidos)) {
                  if (savedFilters.vendedores_excluidos.map(String).includes(String(v.value))) {
                    option.selected = true;
                  }
                }
                vendSelect.appendChild(option);
              }
              if (vendIncluirSelect) {
                const optionInc = document.createElement("option");
                optionInc.value = String(v.value);
                optionInc.textContent = v.label;
                if (savedFilters && savedFilters.vendedores_incluir && Array.isArray(savedFilters.vendedores_incluir)) {
                  if (savedFilters.vendedores_incluir.map(String).includes(String(v.value))) {
                    optionInc.selected = true;
                  }
                }
                vendIncluirSelect.appendChild(optionInc);
              }
            });
            if (vendSelect) initializeTagsFilter("vendedores_excluidos", "viajantes", "vendedores_incluir");
            if (vendIncluirSelect)
              initializeTagsFilter("vendedores_incluir", "viajantes", "vendedores_excluidos");
          }
        }
      }

      // Cargar depósitos incluidos (BO, Objetivos vs BO, stock existencias)
      if (isInformeBoDualPeriodo(reportSlug) || reportSlug === "stock-existencias") {
        const depositosResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=depositos`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        });
        if (depositosResponse.ok) {
          const depositosData = await depositosResponse.json();
          const depositosSelect = document.getElementById("depositos_incluidos");
          if (depositosSelect) {
            depositosSelect.innerHTML = "";
            (depositosData.depositos || []).forEach((dep) => {
              const option = document.createElement("option");
              option.value = dep.value;
              option.textContent = dep.label;
              if (savedFilters && savedFilters.depositos_incluidos && Array.isArray(savedFilters.depositos_incluidos)) {
                if (savedFilters.depositos_incluidos.includes(String(dep.value))) {
                  option.selected = true;
                }
              }
              depositosSelect.appendChild(option);
            });
            initializeTagsFilter("depositos_incluidos", "depositos");
          }
        }
      }

      if (reportSlug === "stock-existencias") {
        const filterBase = `${apiUrl.replace("/query/", "/filters/")}`;
        const headers = { "X-Requested-With": "XMLHttpRequest" };
        const loadTags = async (type, jsonKey, selectId, initLabel) => {
          const resp = await fetch(`${filterBase}?type=${type}`, { headers });
          if (!resp.ok) return;
          const json = await resp.json();
          const items = json[jsonKey] || [];
          const sel = document.getElementById(selectId);
          if (!sel) return;
          sel.innerHTML = "";
          const sfKey =
            selectId === "marcas_incluidos"
              ? "marcas_incluidos"
              : selectId === "rubros_incluidos"
                ? "rubros_incluidos"
                : "subrubros_incluidos";
          items.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.value);
            option.textContent = item.label;
            if (
              savedFilters &&
              savedFilters[sfKey] &&
              Array.isArray(savedFilters[sfKey]) &&
              savedFilters[sfKey].map(String).includes(String(item.value))
            ) {
              option.selected = true;
            }
            sel.appendChild(option);
          });
          initializeTagsFilter(selectId, initLabel);
        };
        try {
          await loadTags("marcas", "marcas", "marcas_incluidos", "marcas");
          await loadTags("rubros", "rubros", "rubros_incluidos", "rubros");
          await loadTags("subrubros", "subrubros", "subrubros_incluidos", "subrubros");
        } catch (e) {
          console.error("Error cargando marcas/rubros/subrubros:", e);
        }
        const gbCtr = document.getElementById("stock_existencias_group_by_tags_container");
        if (gbCtr && !gbCtr.dataset.tagsFilterReady) {
          initializeTagsFilter("stock_existencias_group_by", "group_by");
          gbCtr.dataset.tagsFilterReady = "1";
        }
      }

      if (reportSlug === "ventas-objetivos-vs-bo") {
        const filterBase = `${apiUrl.replace("/query/", "/filters/")}`;
        const headers = { "X-Requested-With": "XMLHttpRequest" };
        const loadVoRubroTags = async (type, jsonKey, selectId, savedKey) => {
          const resp = await fetch(`${filterBase}?type=${type}`, { headers });
          if (!resp.ok) return;
          const json = await resp.json();
          const items = json[jsonKey] || [];
          const sel = document.getElementById(selectId);
          if (!sel) return;
          sel.innerHTML = "";
          items.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.value);
            option.textContent = item.label;
            if (
              savedFilters &&
              savedFilters[savedKey] &&
              Array.isArray(savedFilters[savedKey]) &&
              savedFilters[savedKey].map(String).includes(String(item.value))
            ) {
              option.selected = true;
            }
            sel.appendChild(option);
          });
          initializeTagsFilter(selectId, jsonKey);
        };
        try {
          await loadVoRubroTags("rubros", "rubros", "vo_rubros_incluidos", "rubros_incluidos");
          await loadVoRubroTags("subrubros", "subrubros", "vo_subrubros_incluidos", "subrubros_incluidos");
        } catch (e) {
          console.error("Error cargando rubros/subrubros (objetivos vs BO):", e);
        }
      }

      if (isVentasCatalogoFiltersSlug(reportSlug)) {
        const filterBase = `${apiUrl.replace("/query/", "/filters/")}`;
        const headers = { "X-Requested-With": "XMLHttpRequest" };
        const loadVpaCatalogTags = async (type, jsonKey, selectId, savedKey) => {
          const resp = await fetch(`${filterBase}?type=${type}`, { headers });
          if (!resp.ok) return;
          const json = await resp.json();
          const items = json[jsonKey] || [];
          const sel = document.getElementById(selectId);
          if (!sel) return;
          sel.innerHTML = "";
          items.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.value);
            option.textContent = item.label;
            if (
              savedFilters &&
              savedFilters[savedKey] &&
              Array.isArray(savedFilters[savedKey]) &&
              savedFilters[savedKey].map(String).includes(String(item.value))
            ) {
              option.selected = true;
            }
            sel.appendChild(option);
          });
          initializeTagsFilter(selectId, jsonKey);
        };
        try {
          await loadVpaCatalogTags("rubros", "rubros", "vpa_rubros_incluidos", "rubros_incluidos");
          await loadVpaCatalogTags("rubros", "rubros", "vpa_rubros_excluidos", "rubros_excluidos");
          await loadVpaCatalogTags("subrubros", "subrubros", "vpa_subrubros_incluidos", "subrubros_incluidos");
          await loadVpaCatalogTags("subrubros", "subrubros", "vpa_subrubros_excluidos", "subrubros_excluidos");
          await loadVpaCatalogTags("marcas", "marcas", "vpa_marcas_incluidos", "marcas_incluidos");
          await loadVpaCatalogTags("marcas", "marcas", "vpa_marcas_excluidos", "marcas_excluidos");
        } catch (e) {
          console.error("Error cargando catálogo ventas por artículo:", e);
        }
        [
          ["vpa_rubros_incluidos", "vpa_rubros_excluidos"],
          ["vpa_subrubros_incluidos", "vpa_subrubros_excluidos"],
          ["vpa_marcas_incluidos", "vpa_marcas_excluidos"],
        ].forEach(([incId, excId]) => {
          const incEl = document.getElementById(incId);
          const excEl = document.getElementById(excId);
          if (incEl && excEl) {
            incEl.addEventListener("change", () => reconcileMutualExclusiveTags(incId, excId));
            excEl.addEventListener("change", () => reconcileMutualExclusiveTags(excId, incId));
          }
        });
      }

      if (isInformeVentasMarcasFamiliaSlug(reportSlug)) {
        const ci = document.getElementById("clientes_incluir");
        const ce = document.getElementById("clientes_excluidos");
        const vi = document.getElementById("vendedores_incluir");
        const ve = document.getElementById("vendedores_excluidos");
        if (ci && ce) {
          ci.addEventListener("change", () => reconcileMutualExclusiveTags("clientes_incluir", "clientes_excluidos"));
          ce.addEventListener("change", () => reconcileMutualExclusiveTags("clientes_excluidos", "clientes_incluir"));
        }
        if (vi && ve) {
          vi.addEventListener("change", () => reconcileMutualExclusiveTags("vendedores_incluir", "vendedores_excluidos"));
          ve.addEventListener("change", () => reconcileMutualExclusiveTags("vendedores_excluidos", "vendedores_incluir"));
        }
      }

      if (isVentasMarcasMensualSlug(reportSlug)) {
        const filterBase = `${apiUrl.replace("/query/", "/filters/")}`;
        const headers = { "X-Requested-With": "XMLHttpRequest" };
        const loadVmmTags = async (type, jsonKey, selectId, savedKey, extraQuery = "") => {
          const resp = await fetch(`${filterBase}?type=${type}${extraQuery}`, { headers });
          if (!resp.ok) return;
          const json = await resp.json();
          const items = json[jsonKey] || [];
          const sel = document.getElementById(selectId);
          if (!sel) return;
          sel.innerHTML = "";
          items.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.value);
            option.textContent = item.label;
            if (
              savedFilters &&
              savedFilters[savedKey] &&
              Array.isArray(savedFilters[savedKey]) &&
              savedFilters[savedKey].map(String).includes(String(item.value))
            ) {
              option.selected = true;
            }
            sel.appendChild(option);
          });
          initializeTagsFilter(selectId, jsonKey);
          if (
            selectId === "vmm_marcas_incluidos" &&
            window.ventasMarcasMensualHandler &&
            typeof window.ventasMarcasMensualHandler.populateMarcaCompareSelects === "function"
          ) {
            window.ventasMarcasMensualHandler.populateMarcaCompareSelects(
              items.map((item) => ({ value: item.value, label: item.label }))
            );
          }
        };
        const reloadSuperArts = async () => {
          const marcasSel = document.getElementById("vmm_marcas_incluidos");
          let q = "";
          if (marcasSel) {
            const vals = Array.from(marcasSel.selectedOptions)
              .map((o) => String(o.value))
              .filter(Boolean);
            if (vals.length) q = `&marcas=${encodeURIComponent(vals.join(","))}`;
          }
          await loadVmmTags("superarts", "superarts", "vmm_superarts_incluidos", "superarts_incluidos", q);
        };
        try {
          await loadVmmTags("marcas", "marcas", "vmm_marcas_incluidos", "marcas_incluidos");
          await reloadSuperArts();
          const marcasSel = document.getElementById("vmm_marcas_incluidos");
          if (marcasSel) {
            marcasSel.addEventListener("change", () => {
              reloadSuperArts().catch((e) => console.error("Error recargando SuperArt:", e));
            });
          }
        } catch (e) {
          console.error("Error cargando filtros ventas marcas mensual:", e);
        }
        const modoHidden = document.getElementById("modo_unidades");
        const modoBtns = document.querySelectorAll("#vmm-modo-unidades-buttons .vmm-modo-btn");
        const applyModoUi = (modo) => {
          const m = modo === "docenas" ? "docenas" : "packs";
          if (modoHidden) modoHidden.value = m;
          modoBtns.forEach((btn) => {
            const active = btn.getAttribute("data-modo-unidades") === m;
            btn.classList.toggle("border-sky-500", active);
            btn.classList.toggle("bg-sky-50", active);
            btn.classList.toggle("dark:bg-sky-900/20", active);
            btn.classList.toggle("text-sky-700", active);
            btn.classList.toggle("dark:text-sky-300", active);
            btn.classList.toggle("shadow-md", active);
            btn.classList.toggle("border-slate-300", !active);
            btn.classList.toggle("dark:border-slate-600", !active);
            btn.classList.toggle("bg-white", !active);
            btn.classList.toggle("dark:bg-slate-800", !active);
            btn.classList.toggle("text-slate-700", !active);
            btn.classList.toggle("dark:text-slate-300", !active);
          });
        };
        applyModoUi(savedFilters?.modo_unidades || "packs");
        modoBtns.forEach((btn) => {
          btn.addEventListener("click", () => {
            applyModoUi(btn.getAttribute("data-modo-unidades"));
          });
        });

        const tasaEl = document.getElementById("vmm_tasa_regalia_pct");
        const tcEl = document.getElementById("vmm_tc");
        const coefEl = document.getElementById("vmm_coef_proyeccion");
        const proyHidden = document.getElementById("vmm_incluir_proyeccion");
        const proyBtns = document.querySelectorAll("#vmm-proyeccion-buttons .vmm-proy-btn");
        const applyProyUi = (val) => {
          const on = String(val) === "1";
          if (proyHidden) proyHidden.value = on ? "1" : "0";
          proyBtns.forEach((btn) => {
            const active = btn.getAttribute("data-incluir-proyeccion") === (on ? "1" : "0");
            btn.classList.toggle("border-sky-500", active);
            btn.classList.toggle("bg-sky-50", active);
            btn.classList.toggle("dark:bg-sky-900/20", active);
            btn.classList.toggle("text-sky-700", active);
            btn.classList.toggle("dark:text-sky-300", active);
            btn.classList.toggle("shadow-md", active);
            btn.classList.toggle("border-slate-300", !active);
            btn.classList.toggle("dark:border-slate-600", !active);
            btn.classList.toggle("bg-white", !active);
            btn.classList.toggle("dark:bg-slate-800", !active);
            btn.classList.toggle("text-slate-700", !active);
            btn.classList.toggle("dark:text-slate-300", !active);
          });
        };
        if (tasaEl && savedFilters?.tasa_regalia_pct != null && savedFilters.tasa_regalia_pct !== "") {
          tasaEl.value = savedFilters.tasa_regalia_pct;
        }
        if (tcEl && savedFilters?.tc != null && savedFilters.tc !== "") {
          tcEl.value = savedFilters.tc;
        }
        if (coefEl && savedFilters?.coef_proyeccion != null && savedFilters.coef_proyeccion !== "") {
          coefEl.value = savedFilters.coef_proyeccion;
        }
        applyProyUi(savedFilters?.incluir_proyeccion === "1" || savedFilters?.incluir_proyeccion === 1 ? "1" : "0");
        proyBtns.forEach((btn) => {
          btn.addEventListener("click", () => {
            applyProyUi(btn.getAttribute("data-incluir-proyeccion"));
          });
        });
      }

      // Aplicar otros filtros guardados (fechas, mes actual)
      if (savedFilters) {
        applyFilters(savedFilters);
      }
    } catch (error) {
      console.error("Error cargando opciones de filtros:", error);
    }
    
    // Cargar cajas para informes de flujo de caja
    if (
      reportSlug === "cash_flow_waterfall" ||
      reportSlug === "cash_flow_by_account" ||
      reportSlug === "cash_flow_detailed_movements"
    ) {
      try {
        const cajasResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=cajas`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        });
        
        const savedFilters = loadFilters();
        
        if (cajasResponse.ok) {
          const cajasData = await cajasResponse.json();
          const cajasSelect = document.getElementById("id_caja");
          if (cajasSelect) {
            cajasSelect.innerHTML = "";
            cajasData.cajas?.forEach((caja) => {
              const option = document.createElement("option");
              option.value = caja.value;
              option.textContent = caja.label;
              // Marcar como seleccionado si está en los filtros guardados
              if (savedFilters && savedFilters.id_caja) {
                if (Array.isArray(savedFilters.id_caja)) {
                  if (savedFilters.id_caja.includes(caja.value)) {
                option.selected = true;
                  }
                } else if (savedFilters.id_caja === caja.value) {
                  option.selected = true;
                }
              }
              cajasSelect.appendChild(option);
            });
            // Inicializar componente de tags (ya con las selecciones aplicadas)
            initializeTagsFilter("id_caja", "cajas");
          }
        }
        
        // Aplicar otros filtros guardados (fechas, mes actual, moneda)
        if (savedFilters) {
          applyFilters(savedFilters);
        }
      } catch (error) {
        console.error("Error cargando opciones de cajas:", error);
      }
    }
  };

  const setupRefreshIntervalButtons = () => {
    const buttons = document.querySelectorAll(".refresh-interval-btn");
    const hiddenSelect = document.getElementById("refresh_interval");
    
    if (!buttons.length || !hiddenSelect) {
      console.warn("setupRefreshIntervalButtons: No se encontraron botones o select");
      return;
    }
    
    // Remover listeners anteriores para evitar duplicados
      buttons.forEach((btn) => {
      // Remover todos los listeners clonando el botón
      const newBtn = btn.cloneNode(true);
      btn.parentNode.replaceChild(newBtn, btn);
    });
    
    // Obtener los botones actualizados después de clonar
    const updatedButtons = document.querySelectorAll(".refresh-interval-btn");
    const updatedSelect = document.getElementById("refresh_interval");
    
    if (!updatedButtons.length || !updatedSelect) {
      console.warn("setupRefreshIntervalButtons: Error al actualizar botones o select");
      return;
    }
    
    // Función para actualizar el estado visual de los botones (usando referencias actualizadas)
    const updateButtonStates = (selectedValue) => {
      // Siempre obtener los botones actuales del DOM
      const currentButtons = document.querySelectorAll(".refresh-interval-btn");
      currentButtons.forEach((btn) => {
        const interval = btn.dataset.interval;
        if (interval === selectedValue) {
          btn.classList.add("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
          btn.classList.remove("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
        } else {
          btn.classList.remove("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
          btn.classList.add("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
        }
      });
    };
    
    // Cargar intervalo guardado desde localStorage
    const loadSavedInterval = () => {
      try {
        // Para workspace, usar clave específica
        const isWorkspace = dashboardRoot?.dataset?.workspaceMode === "true";
        const storageKey = isWorkspace 
          ? "workspace_refresh_interval"
          : `refresh_interval_${dashboardRoot?.dataset?.reportSlug || "default"}`;
        
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          return saved;
        }
      } catch (e) {
        console.warn("No se pudo cargar el intervalo guardado:", e);
      }
      return null;
    };
    
    // Guardar intervalo en localStorage
    const saveInterval = (interval) => {
      try {
        const isWorkspace = dashboardRoot?.dataset?.workspaceMode === "true";
        const storageKey = isWorkspace 
          ? "workspace_refresh_interval"
          : `refresh_interval_${dashboardRoot?.dataset?.reportSlug || "default"}`;
        
        localStorage.setItem(storageKey, interval);
      } catch (e) {
        console.warn("No se pudo guardar el intervalo:", e);
      }
    };
    
    // Cargar intervalo guardado o usar el valor del select o el valor por defecto
    const savedInterval = loadSavedInterval();
    const initialInterval = savedInterval || updatedSelect.value || "interval_10m";
    
    // Actualizar el select con el valor guardado
    if (savedInterval) {
      updatedSelect.value = savedInterval;
    }
    
    // Inicializar estado basado en el intervalo guardado o el select
    updateButtonStates(initialInterval);
    
    // Agregar event listeners a los botones
    updatedButtons.forEach((btn) => {
      btn.addEventListener("click", function(e) {
        e.preventDefault();
        e.stopPropagation();
        const interval = this.dataset.interval;
        console.log("Botón clickeado, intervalo:", interval);
        
        if (!interval) {
          console.warn("No se encontró intervalo en el botón");
          return;
        }
        
        const select = document.getElementById("refresh_interval");
        if (!select) {
          console.warn("No se encontró el select refresh_interval");
          return;
        }
        
        // Actualizar el valor del select
        select.value = interval;
        console.log("Select actualizado a:", select.value);
        
        // Guardar el intervalo seleccionado
        saveInterval(interval);
        
        // Actualizar el estado visual de los botones (usando función que obtiene botones actuales)
        updateButtonStates(interval);
        
        // Disparar evento change en el select para mantener compatibilidad
        const changeEvent = new Event("change", { bubbles: true });
        select.dispatchEvent(changeEvent);
        console.log("Evento change disparado");
      });
    });
    
    // Escuchar cambios en el select oculto (por si se cambia desde otro lugar)
    updatedSelect.addEventListener("change", function() {
      console.log("Select cambió a:", this.value);
      updateButtonStates(this.value);
    });
  };

  const setupBoDualPeriodoTipo = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    const root = document.getElementById("bo-period-filters-root");
    if (!isInformeBoDualPeriodo(reportSlug) || !root) {
      return;
    }
    if (root.getAttribute("data-bo-period-setup") === "true") {
      return;
    }
    root.setAttribute("data-bo-period-setup", "true");

    const activeClasses = ["active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md"];
    const inactiveClasses = ["border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300"];

    const updateBtn = (buttons, selected) => {
      buttons.forEach((btn) => {
        const periodo = btn.dataset.periodo;
        if (periodo === selected) {
          btn.classList.add(...activeClasses);
          inactiveClasses.forEach((c) => btn.classList.remove(c));
        } else {
          activeClasses.forEach((c) => btn.classList.remove(c));
          inactiveClasses.forEach((c) => btn.classList.add(c));
        }
      });
    };

    const applyTipo = (tipo, fiInput, ffInput) => {
      const today = new Date();
      if (tipo === "dia_actual") {
        const s = today.toISOString().split("T")[0];
        fiInput.value = s;
        ffInput.value = s;
        fiInput.disabled = true;
        ffInput.disabled = true;
      } else if (tipo === "mes_actual") {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        fiInput.value = firstDay.toISOString().split("T")[0];
        ffInput.value = lastDay.toISOString().split("T")[0];
        fiInput.disabled = true;
        ffInput.disabled = true;
      } else if (tipo === "año_actual") {
        const firstDay = new Date(today.getFullYear(), 0, 1);
        const lastDay = new Date(today.getFullYear(), 11, 31);
        fiInput.value = firstDay.toISOString().split("T")[0];
        ffInput.value = lastDay.toISOString().split("T")[0];
        fiInput.disabled = true;
        ffInput.disabled = true;
      } else {
        fiInput.disabled = false;
        ffInput.disabled = false;
        if (!fiInput.value || !ffInput.value) {
          const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
          const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
          fiInput.value = firstDay.toISOString().split("T")[0];
          ffInput.value = lastDay.toISOString().split("T")[0];
        }
      }
    };

    const wireRow = (rowAttr, selectId, fiId, ffId) => {
      const row = root.querySelector(`[data-bo-period-row="${rowAttr}"]`);
      if (!row) return;
      const sel = document.getElementById(selectId);
      const fi = document.getElementById(fiId);
      const ff = document.getElementById(ffId);
      const buttons = row.querySelectorAll(".periodo-tipo-btn-bo");
      if (!sel || !fi || !ff || !buttons.length) return;

      const setPeriodo = (tipo) => {
        sel.value = tipo;
        updateBtn(buttons, tipo);
        applyTipo(tipo, fi, ff);
        syncBoDualSummaryPeriod();
        saveFilters();
        if (!isInformeQuerySoloManualORealtime(dashboardRoot?.dataset?.reportSlug)) {
          fetchDashboardData();
        }
      };

      buttons.forEach((btn) => {
        btn.addEventListener("click", () => {
          setPeriodo(btn.dataset.periodo);
          sel.dispatchEvent(new Event("change", { bubbles: true }));
        });
      });
      sel.addEventListener("change", () => {
        updateBtn(buttons, sel.value);
        applyTipo(sel.value, fi, ff);
        syncBoDualSummaryPeriod();
      });

      const onDateChange = () => {
        if (sel.value === "personalizado") {
          syncBoDualSummaryPeriod();
          saveFilters();
          if (!isInformeQuerySoloManualORealtime(dashboardRoot?.dataset?.reportSlug)) {
            fetchDashboardData();
          }
        }
      };
      fi.addEventListener("change", onDateChange);
      ff.addEventListener("change", onDateChange);

      updateBtn(buttons, sel.value);
      if (sel.value !== "personalizado") {
        applyTipo(sel.value, fi, ff);
      } else {
        fi.disabled = false;
        ff.disabled = false;
      }
    };

    wireRow("facturacion", "periodo_tipo_facturacion", "fecha_inicio_facturacion", "fecha_fin_facturacion");
    wireRow("backorder", "periodo_tipo", "fecha_inicio", "fecha_fin");
    syncBoDualSummaryPeriod();
  };

  const setupPeriodoTipo = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (isInformeBoDualPeriodo(reportSlug) && document.getElementById("bo-period-filters-root")) {
      return;
    }
    const buttons = document.querySelectorAll(".periodo-tipo-btn");
    const periodoTipoSelect = document.getElementById("periodo_tipo");
    const fechaInicioInput = document.getElementById("fecha_inicio");
    const fechaFinInput = document.getElementById("fecha_fin");
    
    // Solo aplicar si existen estos elementos (ventas_netas, cash_flow_*, uninvoiced_remitos, pedidos-pendientes, sales_summary, bo-stock-facturacion)
    if (!isVentasNetasSlug(reportSlug) && reportSlug !== "cash_flow_waterfall" && reportSlug !== "cash_flow_by_account" && reportSlug !== "cash_flow_detailed_movements" && reportSlug !== "uninvoiced_remitos" && !isPedidosPendientesSlug(reportSlug) && !isLogisticaListaComprobantesRutasSlug(reportSlug) && reportSlug !== "sales_summary" && reportSlug !== "total-consolidado-operativo" && !isInformeBoDualPeriodo(reportSlug)) {
      return;
    }
    if (!buttons.length || !periodoTipoSelect || !fechaInicioInput || !fechaFinInput) {
      return;
    }

    const periodContainer = document.getElementById("period-filters-container");
    const alreadySetup = periodContainer && periodContainer.getAttribute("data-periodo-setup") === "true";

    // Función para actualizar el estado visual de los botones
    const updateButtonStates = (selectedValue) => {
      buttons.forEach((btn) => {
        const periodo = btn.dataset.periodo;
        if (periodo === selectedValue) {
          btn.classList.add("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
          btn.classList.remove("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
        } else {
          btn.classList.remove("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
          btn.classList.add("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
        }
      });
    };
    
    // Función para establecer las fechas según el tipo de período
    const setPeriodo = (tipo) => {
        const today = new Date();
      
      if (tipo === "dia_actual") {
        // Día en curso: solo el día actual
        const todayStr = today.toISOString().split('T')[0];
        fechaInicioInput.value = todayStr;
        fechaFinInput.value = todayStr;
        fechaInicioInput.disabled = true;
        fechaFinInput.disabled = true;
      } else if (tipo === "mes_actual") {
        // Mes en curso: del 1 al último día del mes actual
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        fechaInicioInput.value = firstDay.toISOString().split('T')[0];
        fechaFinInput.value = lastDay.toISOString().split('T')[0];
        fechaInicioInput.disabled = true;
        fechaFinInput.disabled = true;
      } else if (tipo === "año_actual") {
        // Año en curso: del 1 de enero al 31 de diciembre del año actual
        const firstDay = new Date(today.getFullYear(), 0, 1);
        const lastDay = new Date(today.getFullYear(), 11, 31);
        fechaInicioInput.value = firstDay.toISOString().split('T')[0];
        fechaFinInput.value = lastDay.toISOString().split('T')[0];
        fechaInicioInput.disabled = true;
        fechaFinInput.disabled = true;
      } else if (tipo === "personalizado") {
        // Personalizado: habilitar los campos de fecha para edición manual
        fechaInicioInput.disabled = false;
        fechaFinInput.disabled = false;
        // Si no hay fechas establecidas, establecer mes actual por defecto
        if (!fechaInicioInput.value || !fechaFinInput.value) {
          const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
          const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
          fechaInicioInput.value = firstDay.toISOString().split('T')[0];
          fechaFinInput.value = lastDay.toISOString().split('T')[0];
        }
      }
      
      // Actualizar el período en el título del resumen
      const summaryPeriodElement = document.getElementById("summary-period");
      const periodTextFromInputs = fechaInicioInput.value && fechaFinInput.value
        ? (() => {
            const formatDate = (dateStr) => {
              const [year, month, day] = dateStr.split('-');
              return `${day}-${month}-${year}`;
            };
            return `Periodo ${formatDate(fechaInicioInput.value)} al ${formatDate(fechaFinInput.value)}`;
          })()
        : "";
      if (summaryPeriodElement) summaryPeriodElement.textContent = periodTextFromInputs;
      const boPeriodEl = document.getElementById("bo-summary-period");
      const voPeriodEl = document.getElementById("vo-summary-period");
      const slugDual = dashboardRoot?.dataset?.reportSlug;
      if (isInformeBoDualPeriodo(slugDual)) {
        if (boPeriodEl) boPeriodEl.textContent = periodTextFromInputs;
        if (voPeriodEl) voPeriodEl.textContent = periodTextFromInputs;
      }
      const vnPeriodEl = document.getElementById("ventas-netas-summary-period");
      if (vnPeriodEl && isVentasNetasSlug(dashboardRoot?.dataset?.reportSlug)) vnPeriodEl.textContent = periodTextFromInputs;
      
      // Guardar filtros cuando cambia
      saveFilters();
      
      // Si estamos en vista por caja, recargar datos (solo para cash_flow_waterfall)
      const reportSlug = dashboardRoot?.dataset?.reportSlug;
      if (reportSlug === "cash_flow_waterfall") {
        const savedViewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
        if (savedViewType === "por_caja") {
          fetchByAccountData();
        }
      } else if (
        reportSlug === "cash_flow_by_account" ||
        reportSlug === "sales_summary" ||
        reportSlug === "total-consolidado-operativo" ||
        isVentasNetasSlug(reportSlug) ||
        reportSlug === "uninvoiced_remitos" ||
        isPedidosPendientesSlug(reportSlug) ||
        isLogisticaListaComprobantesRutasSlug(reportSlug)
      ) {
        // Para estos reportes, recargar datos al cambiar período
        fetchDashboardData();
      }
    };
    
    // Inicializar estado basado en el select oculto
    // reportSlug ya está declarado arriba, no redeclarar
    
    // En workspace, cash_flow_waterfall y cash_flow_by_account siempre deben mostrar mes en curso
    if (
      isWorkspaceMode &&
      (reportSlug === "cash_flow_waterfall" ||
        reportSlug === "cash_flow_by_account" ||
        reportSlug === "cash_flow_detailed_movements")
    ) {
      periodoTipoSelect.value = "mes_actual";
    } else {
    const savedFilters = loadFilters();
      if (savedFilters) {
        // Restaurar desde filtros guardados
        if (savedFilters.dia_actual) {
          periodoTipoSelect.value = "dia_actual";
        } else if (savedFilters.mes_actual) {
          periodoTipoSelect.value = "mes_actual";
        } else if (savedFilters.año_actual) {
          periodoTipoSelect.value = "año_actual";
        } else {
          periodoTipoSelect.value = "personalizado";
        }
      } else if (!fechaInicioInput.value || !fechaFinInput.value) {
        // Si no hay fechas, establecer mes actual por defecto
        periodoTipoSelect.value = "mes_actual";
      }
    }
    
    updateButtonStates(periodoTipoSelect.value);
    setPeriodo(periodoTipoSelect.value);

    if (alreadySetup) {
      return;
    }
    if (periodContainer) periodContainer.setAttribute("data-periodo-setup", "true");
    
    // Agregar event listeners a los botones
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const periodo = btn.dataset.periodo;
        periodoTipoSelect.value = periodo;
        updateButtonStates(periodo);
        setPeriodo(periodo);
        
        // Disparar evento change en el select para mantener compatibilidad
        periodoTipoSelect.dispatchEvent(new Event("change", { bubbles: true }));
      });
    });
    
    // Escuchar cambios en el select oculto (por si se cambia desde otro lugar)
    periodoTipoSelect.addEventListener("change", () => {
      updateButtonStates(periodoTipoSelect.value);
      setPeriodo(periodoTipoSelect.value);
    });
    
    // Agregar listeners para guardar filtros cuando cambian las fechas (solo en modo personalizado)
    const syncPeriodLabel = () => {
      if (!fechaInicioInput.value || !fechaFinInput.value) return;
      const formatDate = (dateStr) => {
        const [y, m, d] = dateStr.split('-');
        return `${d}-${m}-${y}`;
      };
      const text = `Periodo ${formatDate(fechaInicioInput.value)} al ${formatDate(fechaFinInput.value)}`;
      const summaryPeriodElement = document.getElementById("summary-period");
      if (summaryPeriodElement) summaryPeriodElement.textContent = text;
      const boPeriodEl = document.getElementById("bo-summary-period");
      const voPeriodElSync = document.getElementById("vo-summary-period");
      const slugDual2 = dashboardRoot?.dataset?.reportSlug;
      if (isInformeBoDualPeriodo(slugDual2)) {
        if (boPeriodEl) boPeriodEl.textContent = text;
        if (voPeriodElSync) voPeriodElSync.textContent = text;
      }
      const vnPeriodEl = document.getElementById("ventas-netas-summary-period");
      if (vnPeriodEl && isVentasNetasSlug(dashboardRoot?.dataset?.reportSlug)) vnPeriodEl.textContent = text;
    };
    fechaInicioInput.addEventListener("change", () => {
      if (periodoTipoSelect.value === "personalizado") {
      saveFilters();
        syncPeriodLabel();
        const reportSlug = dashboardRoot?.dataset?.reportSlug;
        if (reportSlug === "cash_flow_waterfall") {
          const savedViewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
          if (savedViewType === "por_caja") {
            fetchByAccountData();
          }
        } else if (
          reportSlug === "sales_summary" ||
          reportSlug === "total-consolidado-operativo" ||
          isVentasNetasSlug(reportSlug) ||
          reportSlug === "uninvoiced_remitos" ||
          isPedidosPendientesSlug(reportSlug) ||
          isLogisticaListaComprobantesRutasSlug(reportSlug)
        ) {
          fetchDashboardData();
        }
      }
    });
    fechaFinInput.addEventListener("change", () => {
      if (periodoTipoSelect.value === "personalizado") {
      saveFilters();
        syncPeriodLabel();
        const reportSlug = dashboardRoot?.dataset?.reportSlug;
        if (reportSlug === "cash_flow_waterfall") {
          const savedViewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
          if (savedViewType === "por_caja") {
            fetchByAccountData();
          }
        } else if (
          reportSlug === "sales_summary" ||
          reportSlug === "total-consolidado-operativo" ||
          isVentasNetasSlug(reportSlug) ||
          reportSlug === "uninvoiced_remitos" ||
          isPedidosPendientesSlug(reportSlug) ||
          isLogisticaListaComprobantesRutasSlug(reportSlug)
        ) {
          fetchDashboardData();
        }
      }
    });
  };

  // Cuando el template genera los controles de período (ej. ventas_netas con config.filters como objeto), enlazar recarga y guardado
  window.addEventListener("reportPeriodFiltersReady", () => {
    setupPeriodoTipo();
    setupBoDualPeriodoTipo();
  });

  const setupCashFlowFilters = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (
      reportSlug !== "cash_flow_waterfall" &&
      reportSlug !== "cash_flow_by_account" &&
      reportSlug !== "cash_flow_detailed_movements"
    ) {
      return;
    }
    
    // Event listener para caja
    const idCajaSelect = document.getElementById("id_caja");
    if (idCajaSelect) {
      idCajaSelect.addEventListener("change", () => {
        saveFilters();
        // Si estamos en vista por caja, recargar datos
        const viewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
        if (viewType === "por_caja") {
          fetchByAccountData();
        }
      });
    }
    
    // Setup toggle de vista (Consolidada vs Por Caja)
    setupViewTypeToggle();
  };
  
  const setupViewTypeToggle = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (reportSlug !== "cash_flow_waterfall") {
      return;
    }
    
    const buttons = document.querySelectorAll(".view-type-btn");
    const byAccountSection = document.getElementById("by-account-section");
    const widgetsSection = document.querySelector("[data-widgets-container]");
    
    if (!buttons.length || !byAccountSection) {
      return;
    }
    
    // Cargar vista guardada o usar consolidada por defecto
    const savedViewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
    
    // Función para actualizar estado visual de botones
    const updateButtonStates = (selectedViewType) => {
      buttons.forEach((btn) => {
        const viewType = btn.dataset.viewType;
        if (viewType === selectedViewType) {
          btn.classList.add("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
          btn.classList.remove("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
        } else {
          btn.classList.remove("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
          btn.classList.add("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
        }
      });
    };
    
    // Función para cambiar vista
    const switchView = (viewType) => {
      localStorage.setItem(`view_type_${reportSlug}`, viewType);
      updateButtonStates(viewType);
      
      if (viewType === "por_caja") {
        // Mostrar sección por caja, mantener widgets visibles (para mostrar gráfico por caja)
        byAccountSection.classList.remove("hidden");
        if (widgetsSection) {
          widgetsSection.style.display = "";
        }
        // Cargar datos por caja (esto también actualizará el gráfico waterfall)
        fetchByAccountData();
      } else {
        // Ocultar sección por caja, mostrar widgets consolidados
        byAccountSection.classList.add("hidden");
        if (widgetsSection) {
          widgetsSection.style.display = "";
        }
        // Recargar datos consolidados para actualizar el gráfico
        fetchDashboardData();
      }
    };
    
    // Agregar event listeners a los botones
    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const viewType = btn.dataset.viewType;
        switchView(viewType);
      });
    });
    
    // Aplicar vista guardada
    switchView(savedViewType);
  };
  
  const fetchByAccountData = async () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (reportSlug !== "cash_flow_waterfall") {
      return;
    }
    
    const byAccountContent = document.getElementById("by-account-content");
    if (!byAccountContent) {
      return;
    }
    
    // Mostrar loading
    byAccountContent.innerHTML = `
      <div class="flex items-center justify-center py-8">
        <div class="text-xs text-slate-500 dark:text-slate-400">Cargando datos por caja...</div>
      </div>
    `;
    
    try {
      const filters = getFilters();
      const apiUrl = dashboardRoot.dataset.dashboardUrl;
      
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          slug: "cash_flow_by_account",
          filters: filters,
        }),
      });
      
      if (!response.ok) {
        throw new Error("Error al cargar datos por caja");
      }
      
      const payload = await response.json();
      const data = payload.data || [];
      const totals = payload.totals || {};
      
      // Renderizar tabla
      renderByAccountTable(data, totals);
      
      // Transformar datos por caja al formato del waterfall y actualizar el gráfico
      const waterfallData = transformByAccountToWaterfall(data, totals);
      updateWaterfallChart(waterfallData);
    } catch (error) {
      console.error("Error cargando datos por caja:", error);
      byAccountContent.innerHTML = `
        <div class="flex items-center justify-center py-8">
          <p class="text-xs text-red-400">Error al cargar datos por caja: ${error.message}</p>
        </div>
      `;
    }
  };
  
  // Transformar datos por caja al formato necesario para el gráfico waterfall
  const transformByAccountToWaterfall = (data, totals) => {
    const saldoInicial = totals.total_saldo_inicial || 0;
    const saldoFinal = totals.total_saldo_final || 0;
    
    // Crear estructura similar a la vista consolidada
    const waterfallData = [];
    
    // Saldo inicial
    waterfallData.push({
      period: "Saldo Inicial",
      mes_formato: "Saldo Inicial",
      operating_flow: 0,
      investing_flow: 0,
      financing_flow: 0,
      cash_variation: 0,
      cumulative: saldoInicial,
      type: "starting"
    });
    
    // Cada caja como un "período" en el gráfico
    let cumulative = saldoInicial;
    data.forEach((caja) => {
      const cashVariation = caja.cash_variation || 0;
      cumulative += cashVariation;
      
      waterfallData.push({
        period: caja.caja_nombre || "Sin nombre",
        mes_formato: caja.caja_nombre || "Sin nombre",
        operating_flow: caja.operating_flow || 0,
        investing_flow: caja.investing_flow || 0,
        financing_flow: caja.financing_flow || 0,
        cash_variation: cashVariation,
        cumulative: cumulative,
        type: "period"
      });
    });
    
    // Saldo final
    waterfallData.push({
      period: "Saldo Final",
      mes_formato: "Saldo Final",
      operating_flow: 0,
      investing_flow: 0,
      financing_flow: 0,
      cash_variation: 0,
      cumulative: saldoFinal,
      type: "ending"
    });
    
    return waterfallData;
  };
  
  // Actualizar el gráfico waterfall con los nuevos datos
  const updateWaterfallChart = (waterfallData) => {
    // Buscar el widget del waterfall
    const widgets = dashboardRoot.querySelectorAll("[data-widget-id]");
    widgets.forEach((widget) => {
      const widgetType = widget.dataset.widgetType;
      if (widgetType === "d3-waterfall") {
        const config = getWidgetConfig(widget);
        const cacheKey = widget.dataset.widgetId;
        
        // Actualizar cache
        widgetDataCache.set(cacheKey, { data: waterfallData, config });
        
        // Renderizar gráfico actualizado
        renderChart(widget, waterfallData, config);
      }
    });
  };
  
  const renderByAccountTable = (data, totals, container = null) => {
    // Si no se especifica contenedor, buscar el apropiado según el contexto
    let byAccountContent = container;
    if (!byAccountContent) {
      // Para cash_flow_waterfall (vista por caja desde toggle)
      byAccountContent = document.getElementById("by-account-content");
      // Para cash_flow_by_account (reporte directo)
      if (!byAccountContent) {
        byAccountContent = document.getElementById("by-account-table-content");
      }
    }
    if (!byAccountContent) {
      return;
    }
    
    if (!data || data.length === 0) {
      byAccountContent.innerHTML = `
        <div class="flex items-center justify-center py-8">
          <p class="text-xs text-slate-500 dark:text-slate-400">No hay datos disponibles para el período seleccionado.</p>
        </div>
      `;
      return;
    }
    
    // Formatear número como moneda
    const formatCurrency = (value) => {
      return new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value || 0);
    };
    
    // Crear tabla
    let tableHTML = `
      <div class="overflow-x-auto">
        <table class="min-w-full text-xs text-left bg-white dark:bg-slate-950 border border-slate-100 dark:border-slate-800 rounded-xl overflow-hidden">
          <thead class="bg-slate-50 dark:bg-slate-900/40 text-slate-500 dark:text-slate-300 uppercase tracking-wide">
            <tr>
              <th class="px-4 py-3 text-left">Caja</th>
              <th class="px-4 py-3 text-left">Tipo</th>
              <th class="px-4 py-3 text-right">Saldo Inicial</th>
              <th class="px-4 py-3 text-right">Flujo Operativo</th>
              <th class="px-4 py-3 text-right">Flujo Inversión</th>
              <th class="px-4 py-3 text-right">Flujo Financiamiento</th>
              <th class="px-4 py-3 text-right">Variación</th>
              <th class="px-4 py-3 text-right">Saldo Final</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
    `;
    
    data.forEach((row) => {
      const saldoInicial = parseFloat(row.saldo_inicial || 0);
      const operatingFlow = parseFloat(row.operating_flow || 0);
      const investingFlow = parseFloat(row.investing_flow || 0);
      const financingFlow = parseFloat(row.financing_flow || 0);
      const cashVariation = parseFloat(row.cash_variation || 0);
      const saldoFinal = parseFloat(row.saldo_final || 0);
      
      // Colores para valores positivos/negativos
      const operatingClass = operatingFlow >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
      const investingClass = investingFlow >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
      const financingClass = financingFlow >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
      const variationClass = cashVariation >= 0 ? "text-green-600 dark:text-green-400 font-semibold" : "text-red-600 dark:text-red-400 font-semibold";
      
      tableHTML += `
        <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
          <td class="px-4 py-3 text-slate-900 dark:text-white font-medium">${row.caja_nombre || "Sin Caja"}</td>
          <td class="px-4 py-3 text-slate-600 dark:text-slate-400">${row.caja_tipo || ""}</td>
          <td class="px-4 py-3 text-right text-slate-900 dark:text-white">${formatCurrency(saldoInicial)}</td>
          <td class="px-4 py-3 text-right ${operatingClass}">${formatCurrency(operatingFlow)}</td>
          <td class="px-4 py-3 text-right ${investingClass}">${formatCurrency(investingFlow)}</td>
          <td class="px-4 py-3 text-right ${financingClass}">${formatCurrency(financingFlow)}</td>
          <td class="px-4 py-3 text-right ${variationClass}">${formatCurrency(cashVariation)}</td>
          <td class="px-4 py-3 text-right text-slate-900 dark:text-white font-semibold">${formatCurrency(saldoFinal)}</td>
        </tr>
      `;
    });
    
    // Fila de totales
    if (totals && Object.keys(totals).length > 0) {
      const totalSaldoInicial = parseFloat(totals.total_saldo_inicial || 0);
      const totalOperating = parseFloat(totals.total_operating_flow || 0);
      const totalInvesting = parseFloat(totals.total_investing_flow || 0);
      const totalFinancing = parseFloat(totals.total_financing_flow || 0);
      const totalVariation = parseFloat(totals.total_cash_variation || 0);
      const totalSaldoFinal = parseFloat(totals.total_saldo_final || 0);
      
      const totalOperatingClass = totalOperating >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
      const totalInvestingClass = totalInvesting >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
      const totalFinancingClass = totalFinancing >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400";
      const totalVariationClass = totalVariation >= 0 ? "text-green-600 dark:text-green-400 font-bold" : "text-red-600 dark:text-red-400 font-bold";
      
      tableHTML += `
        <tr class="bg-slate-100 dark:bg-slate-800/50 border-t-2 border-slate-300 dark:border-slate-600 font-semibold">
          <td class="px-4 py-3 text-slate-900 dark:text-white" colspan="2">TOTAL</td>
          <td class="px-4 py-3 text-right text-slate-900 dark:text-white">${formatCurrency(totalSaldoInicial)}</td>
          <td class="px-4 py-3 text-right ${totalOperatingClass}">${formatCurrency(totalOperating)}</td>
          <td class="px-4 py-3 text-right ${totalInvestingClass}">${formatCurrency(totalInvesting)}</td>
          <td class="px-4 py-3 text-right ${totalFinancingClass}">${formatCurrency(totalFinancing)}</td>
          <td class="px-4 py-3 text-right ${totalVariationClass}">${formatCurrency(totalVariation)}</td>
          <td class="px-4 py-3 text-right text-slate-900 dark:text-white font-bold">${formatCurrency(totalSaldoFinal)}</td>
        </tr>
      `;
    }
    
    tableHTML += `
          </tbody>
        </table>
      </div>
    `;

    const srCf = window.SynapReportsResponsive;
    if (srCf) {
      const mobileHtml = srCf.buildMobileCardsHtml(data, [], {
        reportSlug: "cash_flow_by_account",
      });
      srCf.insertDualHtml(byAccountContent, mobileHtml, tableHTML);
    } else {
      byAccountContent.innerHTML = tableHTML;
    }
  };

  const STOCK_EXISTENCIAS_SEARCH_KEYS = [
    "nombre",
    "codigo_articulo",
    "id_manual",
    "codigo_barras",
    "deposito_nombre",
    "rubro_nombre",
    "subrubro_nombre",
  ];
  const STOCK_EXISTENCIAS_PAGE_SIZE = 150;
  const STOCK_EXISTENCIAS_FULL_LIMIT = 2147483647;
  const STOCK_EXISTENCIAS_ROW_HEIGHT = 40;
  const STOCK_EXISTENCIAS_VIRTUAL_BUFFER = 25;
  const stockExistenciasDataset = {
    rows: [],
    notes: [],
    totalRegistros: 0,
    hasMore: false,
    offset: 0,
    paginated: true,
  };
  let stockExistenciasSort = { col: "nombre", dir: "asc" };
  let stockExistenciasFetchInFlight = false;
  let stockExistenciasLoadMoreInFlight = false;

  const getStockExistenciasGroupFields = () => {
    const wrapGb = document.getElementById("stock_existencias_group_by_tags_container");
    const chipsRoot = wrapGb?.querySelector(".tags-chips");
    const stripRetired = (arr) => arr.filter((v) => v && v !== "marca");
    if (chipsRoot) {
      const chipEls = chipsRoot.querySelectorAll("[data-value]");
      if (chipEls.length) {
        return stripRetired(
          Array.from(chipEls)
            .map((el) => el.dataset.value)
            .filter(Boolean)
        );
      }
    }
    const sel = document.getElementById("stock_existencias_group_by");
    return stripRetired(sel ? Array.from(sel.selectedOptions).map((o) => o.value).filter(Boolean) : []);
  };

  const stockExistenciasNeedsFullFetch = () => getStockExistenciasGroupFields().length > 0;

  const enrichStockExistenciasFilters = (baseFilters) => {
    const out = { ...(baseFilters || {}) };
    const searchEl = document.getElementById("stock_existencias_busqueda");
    const q = searchEl ? String(searchEl.value || "").trim() : "";
    if (q.length >= 2) out.busqueda = q;
    out.sort_col = stockExistenciasSort.col;
    out.sort_dir = stockExistenciasSort.dir;
    if (stockExistenciasNeedsFullFetch()) out.agrupacion_activa = true;
    return out;
  };

  const fetchStockExistenciasData = async ({ offset = 0, append = false, silent = false } = {}) => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    const apiUrl = dashboardRoot?.dataset?.dashboardUrl;
    if (reportSlug !== "stock-existencias" || !apiUrl) return null;
    if (stockExistenciasFetchInFlight && !append) return null;
    if (append && stockExistenciasLoadMoreInFlight) return null;

    if (append) stockExistenciasLoadMoreInFlight = true;
    else stockExistenciasFetchInFlight = true;

    const fullFetch = stockExistenciasNeedsFullFetch();
    const limit = fullFetch ? STOCK_EXISTENCIAS_FULL_LIMIT : STOCK_EXISTENCIAS_PAGE_SIZE;
  const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), EXTENDED_REPORT_FETCH_TIMEOUT_MS);

    if (!silent && !append) {
      showReportsQueryLoadingModal("stock-existencias");
    }

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          slug: reportSlug,
          limit,
          offset,
          filters: enrichStockExistenciasFilters(getFilters()),
        }),
        signal: controller.signal,
      });
      if (!response.ok) {
        let errorMessage = "Error al cargar stock y existencias";
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || errorMessage;
        } catch (e) {
          /* ignore */
        }
        throw new Error(errorMessage);
      }
      const payload = await response.json();
      renderStockExistenciasTable(payload, { append });
      return payload;
    } catch (error) {
      if (!silent) {
        console.error("Error stock-existencias:", error);
        toast(error.message || "Error al cargar stock y existencias", "error");
      }
      return null;
    } finally {
      clearTimeout(timeoutId);
      stockExistenciasFetchInFlight = false;
      stockExistenciasLoadMoreInFlight = false;
      if (!silent && !append) {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => hideReportsQueryLoadingModal());
        });
      }
    }
  };

  window.refetchStockExistenciasData = () => fetchStockExistenciasData({ offset: 0, append: false });

  const maybeLoadMoreStockExistencias = (scrollEl) => {
    if (!stockExistenciasDataset.paginated || !stockExistenciasDataset.hasMore) return;
    if (stockExistenciasLoadMoreInFlight || stockExistenciasFetchInFlight) return;
    const threshold = 240;
    if (scrollEl.scrollTop + scrollEl.clientHeight < scrollEl.scrollHeight - threshold) return;
    fetchStockExistenciasData({
      offset: stockExistenciasDataset.rows.length,
      append: true,
      silent: true,
    });
  };

  const filterStockExistenciasBySearch = (rows, query) => {
    if (!Array.isArray(rows)) return [];
    const q = (query && String(query).trim()) || "";
    if (q.length < 2) return rows.slice();
    const ql = q.toLowerCase();
    return rows.filter((row) =>
      STOCK_EXISTENCIAS_SEARCH_KEYS.some((k) => {
        const val = row[k];
        if (val == null) return false;
        return String(val).toLowerCase().indexOf(ql) !== -1;
      })
    );
  };

  const sortStockExistenciasRows = (rows, col, dir) => {
    const m = dir === "asc" ? 1 : -1;
    const sorted = rows.slice();
    sorted.sort((a, b) => {
      const va = a[col];
      const vb = b[col];
      const sa = va == null ? "" : String(va);
      const sb = vb == null ? "" : String(vb);
      const opts =
        col === "id_manual" || col === "codigo_barras"
          ? { numeric: true, sensitivity: "base" }
          : { numeric: false, sensitivity: "base" };
      const cmp = sa.localeCompare(sb, "es", opts);
      if (cmp !== 0) return cmp * m;
      const ta = `${a.id_art ?? ""}-${a.id_deposito ?? ""}`;
      const tb = `${b.id_art ?? ""}-${b.id_deposito ?? ""}`;
      return ta < tb ? -1 : ta > tb ? 1 : 0;
    });
    return sorted;
  };

  const groupStockExistenciasKey = (row, mode) => {
    switch (mode) {
      case "deposito":
        return row.deposito_nombre || "—";
      case "articulo":
        return row.nombre || "—";
      case "rubro":
        return row.rubro_nombre || "—";
      case "subrubro":
        return row.subrubro_nombre || "—";
      default:
        return "";
    }
  };

  const STOCK_EXISTENCIAS_DIM_LABELS = {
    deposito: "Depósito",
    articulo: "Nombre artículo",
    rubro: "Rubro",
    subrubro: "Subrubro",
  };

  const sumStockExistenciasMetrics = (itemRows) => {
    return itemRows.reduce(
      (acc, row) => {
        acc.stock += Number(row.stock) || 0;
        acc.reservado += Number(row.reservado) || 0;
        acc.disponible += Number(row.disponible) || 0;
        return acc;
      },
      { stock: 0, reservado: 0, disponible: 0 }
    );
  };

  /**
   * Misma forma que groupTableDataGeneric (BO): árbol de grupos con totales por nivel.
   */
  const groupStockExistenciasToTree = (items, fields, lev) => {
    if (lev >= fields.length) {
      return items.map((row) => ({ type: "item", data: row, children: [] }));
    }
    const field = fields[lev];
    const grouped = {};
    items.forEach((row) => {
      const gk = groupStockExistenciasKey(row, field);
      const key = String(gk);
      if (!grouped[key]) {
        grouped[key] = {
          groupKey: key,
          groupValue: gk,
          groupField: field,
          items: [],
          totals: { stock: 0, reservado: 0, disponible: 0 },
        };
      }
      grouped[key].items.push(row);
    });
    Object.keys(grouped).forEach((k) => {
      const g = grouped[k];
      g.totals = sumStockExistenciasMetrics(g.items);
    });
    const keysSorted = Object.keys(grouped).sort((a, b) =>
      String(grouped[a].groupValue)
        .toLowerCase()
        .localeCompare(String(grouped[b].groupValue).toLowerCase(), "es")
    );
    const result = [];
    keysSorted.forEach((k) => {
      const g = grouped[k];
      const nested = groupStockExistenciasToTree(g.items, fields, lev + 1);
      result.push({ type: "group", data: g, children: nested });
    });
    return result;
  };

  const attachStockExistenciasGroupToggles = (container) => {
    if (!container) return;
    container.querySelectorAll("[data-se-group-toggle]").forEach((el) => {
      if (el._seStockToggleAttached) return;
      el._seStockToggleAttached = true;
      el.addEventListener("click", () => {
        const groupId = el.getAttribute("data-se-group-toggle");
        if (!groupId) return;
        const childrenRow = container.querySelector(`tr[data-se-group-parent="${groupId}"]`);
        if (!childrenRow) return;
        const isHidden = childrenRow.style.display === "none";
        childrenRow.style.display = isHidden ? "table-row" : "none";
        el.style.transform = isHidden ? "rotate(90deg)" : "rotate(0deg)";
      });
    });
  };

  const escStockHtml = (v) => {
    if (v == null) return "";
    return String(v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  };

  /** Código de barras: nunca notación científica (JSON puede traer number si el backend no forzó str). */
  const formatStockExistenciasBarras = (v) => {
    if (v == null || v === "") return "";
    if (typeof v === "string") return v.trim();
    const n = Number(v);
    if (!Number.isFinite(n)) return String(v);
    const t = Math.trunc(n);
    if (t === n && Number.isSafeInteger(t)) {
      return String(t);
    }
    const s = n.toLocaleString("fullwide", { useGrouping: false, maximumFractionDigits: 20 });
    return /[eE]/.test(s) ? String(v) : s;
  };

  function ensureStockExistenciasTableStylesOnce() {
    const id = "synap-stock-existencias-style-v2";
    document.getElementById("synap-stock-existencias-style-v1")?.remove();
    if (document.getElementById(id)) return;
    const st = document.createElement("style");
    st.id = id;
    st.textContent = `
.se-vo-stock-table > thead > tr > th {
  position: -webkit-sticky;
  position: sticky;
  top: 0;
}
.se-vo-stock-table td,
.se-vo-stock-table th {
  box-sizing: border-box;
  min-width: 0;
  overflow-wrap: break-word;
  word-break: break-word;
}
.se-vo-stock-table > thead > tr > th:nth-child(7),
.se-vo-stock-table > thead > tr > th:nth-child(8),
.se-vo-stock-table > thead > tr > th:nth-child(9),
.se-vo-stock-table > tbody > tr > td:nth-child(7),
.se-vo-stock-table > tbody > tr > td:nth-child(8),
.se-vo-stock-table > tbody > tr > td:nth-child(9) {
  text-align: right !important;
}
/* Solo filas de detalle: ID manual a la derecha (incluye tablas anidadas; filas de grupo sin esta clase). */
.se-vo-stock-table tbody tr.se-stock-detail-row > td:first-child {
  text-align: right !important;
}
.se-vo-stock-table.se-vo-stock-nested {
  width: 100%;
  max-width: 100%;
  min-width: 0;
  border-width: 0 !important;
}
`.trim();
    document.head.appendChild(st);
  }

  const renderStockExistenciasTableFromState = () => {
    const wrap = document.getElementById("stock-existencias-table-wrap");
    if (!wrap) return;
    ensureStockExistenciasTableStylesOnce();
    const rows = stockExistenciasDataset.rows || [];
    const notes = stockExistenciasDataset.notes || [];
    const paginated = stockExistenciasDataset.paginated;
    const searchEl = document.getElementById("stock_existencias_busqueda");
    const q = searchEl ? searchEl.value : "";
    let filtered = rows.slice();
    if (!paginated) {
      filtered = filterStockExistenciasBySearch(rows, q);
      filtered = sortStockExistenciasRows(filtered, stockExistenciasSort.col, stockExistenciasSort.dir);
    }

    const getGroupFieldsStock = getStockExistenciasGroupFields;

    const fmt = (v) => {
      const n = Number(v);
      if (Number.isFinite(n)) return n.toLocaleString("es-AR", { maximumFractionDigits: 4 });
      return v ?? "";
    };

    const thSticky =
      "sticky top-0 z-10 shadow-[0_1px_0_0_rgb(226_232_240)] dark:shadow-[0_1px_0_0_rgb(51_65_85)]";
    const thB =
      "border border-slate-200 dark:border-slate-600 px-2.5 py-2 text-[10px] font-bold uppercase tracking-wide align-middle";
    const thDoc = `${thB} ${thSticky} text-left bg-emerald-50 text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100`;
    const thDocIdManual = `${thB} ${thSticky} text-right bg-emerald-50 text-emerald-950 dark:bg-emerald-950/40 dark:text-emerald-100`;
    const thTxt = `${thB} ${thSticky} text-left bg-violet-50 text-violet-950 dark:bg-violet-950/35 dark:text-violet-100`;
    const thNum = `${thB} ${thSticky} text-right bg-sky-100 text-sky-950 dark:bg-sky-900/45 dark:text-sky-50`;

    const tdB =
      "border border-slate-200 dark:border-slate-600 px-2.5 py-2 text-xs align-top min-w-0 max-w-full break-words";
    const tdDoc = `${tdB} bg-emerald-50/30 dark:bg-emerald-950/15 text-slate-800 dark:text-slate-200`;
    const tdTxt = `${tdB} bg-violet-50/25 dark:bg-violet-950/15 text-slate-800 dark:text-slate-200`;
    const tdNum = `${tdB} text-right tabular-nums font-mono text-slate-900 dark:text-white`;
    const tdLow = `${tdB} border-red-300 bg-red-100 text-slate-900 dark:border-red-800 dark:bg-red-950/55 dark:text-red-50`;
    const tdLowNum = `${tdB} border-red-300 bg-red-100 text-right tabular-nums font-mono text-slate-900 dark:border-red-800 dark:bg-red-950/55 dark:text-red-50`;

    /** Anchos: cols 1–3 y numéricas base 1/9; stock/reservado/disponible −20 %; el exceso repartido en nombre, rubro, subrubro. */
    const STOCK_EXISTENCIAS_COLGROUP = `
<colgroup>
  <col style="width:11.111%" />
  <col style="width:11.111%" />
  <col style="width:11.111%" />
  <col style="width:13.333%" />
  <col style="width:13.333%" />
  <col style="width:13.333%" />
  <col style="width:8.889%" />
  <col style="width:8.889%" />
  <col style="width:8.889%" />
</colgroup>`;

    const sortHeader = (col, label, thClass) => {
      const active = stockExistenciasSort.col === col;
      const arrow =
        active && stockExistenciasSort.dir === "asc"
          ? " ↑"
          : active && stockExistenciasSort.dir === "desc"
            ? " ↓"
            : "";
      return `<th scope="col" data-sort-col="${col}" class="${thClass} cursor-pointer select-none hover:opacity-90">${escStockHtml(
        label
      )}${arrow}</th>`;
    };

    const stockRow = (r) => {
      const stk = Number(r.stock);
      const low = Number.isFinite(stk) && stk <= 0;
      const d = low ? tdLow : tdDoc;
      const t = low ? tdLow : tdTxt;
      const n = low ? tdLowNum : tdNum;
      const barras = escStockHtml(formatStockExistenciasBarras(r.codigo_barras));
      return `<tr class="se-stock-detail-row transition-colors hover:opacity-95 ${
        low ? "se-stock-row-low" : "hover:bg-slate-50/80 dark:hover:bg-slate-900/25"
      }">
        <td class="${d} text-right">${escStockHtml(r.id_manual)}</td>
        <td class="${d} font-mono" translate="no">${barras}</td>
        <td class="${d}">${escStockHtml(r.deposito_nombre)}</td>
        <td class="${t}">${escStockHtml(r.nombre)}</td>
        <td class="${t}">${escStockHtml(r.rubro_nombre)}</td>
        <td class="${t}">${escStockHtml(r.subrubro_nombre)}</td>
        <td class="${n}">${fmt(r.stock)}</td>
        <td class="${n}">${fmt(r.reservado)}</td>
        <td class="${n} font-medium text-emerald-700 dark:text-emerald-400">${fmt(r.disponible)}</td>
      </tr>`;
    };

    const NUM_COL_STOCK = 9;

    if (!filtered.length) {
      const qTrim = (q && String(q).trim()) || "";
      const msg =
        qTrim.length >= 2 && paginated
          ? "Ninguna fila coincide con la búsqueda (mínimo 2 caracteres)."
          : qTrim.length >= 2
            ? "Ninguna fila coincide con la búsqueda (mínimo 2 caracteres)."
            : notes[0] || "Sin datos para los filtros seleccionados.";
      wrap.innerHTML = `<p class="text-xs text-slate-500 dark:text-slate-400 py-4">${escStockHtml(msg)}</p>`;
      return;
    }

    const groupFields = getGroupFieldsStock();
    let bodyHtml = "";
    let pieAgrupado = "";
    const qTrim = (q && String(q).trim()) || "";
    const totalReg = stockExistenciasDataset.totalRegistros || filtered.length;
    const leyendaBusqueda =
      qTrim.length >= 2 && !paginated && rows.length
        ? ` · Mostrando ${filtered.length} de ${rows.length} filas`
        : "";
    const leyendaPaginacion = paginated
      ? ` · ${filtered.length} de ${totalReg} fila(s) cargadas${stockExistenciasDataset.hasMore ? " (desplazá para cargar más)" : ""}`
      : "";

    const renderStockExistenciasVirtualBody = (scrollEl, dataRows) => {
      const ROW_H = STOCK_EXISTENCIAS_ROW_HEIGHT;
      const BUF = STOCK_EXISTENCIAS_VIRTUAL_BUFFER;
      const scrollTop = scrollEl ? scrollEl.scrollTop : 0;
      const viewH = scrollEl ? scrollEl.clientHeight : ROW_H * 20;
      let start = Math.max(0, Math.floor(scrollTop / ROW_H) - BUF);
      let end = Math.min(dataRows.length, Math.ceil((scrollTop + viewH) / ROW_H) + BUF);
      const topPad = start * ROW_H;
      const bottomPad = Math.max(0, (dataRows.length - end) * ROW_H);
      let html = "";
      if (topPad > 0) {
        html += `<tr class="se-stock-virtual-spacer" aria-hidden="true"><td colspan="${NUM_COL_STOCK}" style="height:${topPad}px;padding:0;border:none;"></td></tr>`;
      }
      for (let i = start; i < end; i++) {
        html += stockRow(dataRows[i]);
      }
      if (bottomPad > 0) {
        html += `<tr class="se-stock-virtual-spacer" aria-hidden="true"><td colspan="${NUM_COL_STOCK}" style="height:${bottomPad}px;padding:0;border:none;"></td></tr>`;
      }
      return html;
    };

    const attachStockExistenciasVirtualScroll = (scrollEl, dataRows) => {
      if (!scrollEl || dataRows.length < 40) return;
      const onScroll = () => {
        const tbody = scrollEl.querySelector("#stock-existencias-tbody");
        if (tbody) {
          tbody.innerHTML = renderStockExistenciasVirtualBody(scrollEl, dataRows);
        }
        maybeLoadMoreStockExistencias(scrollEl);
      };
      if (scrollEl._seVirtualScrollHandler) {
        scrollEl.removeEventListener("scroll", scrollEl._seVirtualScrollHandler);
      }
      scrollEl._seVirtualScrollHandler = onScroll;
      scrollEl.addEventListener("scroll", onScroll, { passive: true });
      onScroll();
    };

    if (groupFields.length) {
      const grouped = groupStockExistenciasToTree(filtered, groupFields, 0);
      const numAgrupaciones = grouped.length;
      const collapsedDefault = true;
      let gid = 0;
      const nextGroupId = () => `se-stock-g-${++gid}`;

      const renderGroupedRowsBOStyle = (groupedData, level) => {
        let rowsHTML = "";
        groupedData.forEach((item) => {
          if (item.type === "group") {
            const g = item.data;
            const groupId = nextGroupId();
            const dimLabel = STOCK_EXISTENCIAS_DIM_LABELS[g.groupField] || g.groupField;
            const bgClass =
              level === 0
                ? "bg-slate-100 dark:bg-slate-800"
                : level === 1
                  ? "bg-slate-50 dark:bg-slate-900"
                  : "bg-slate-50/50 dark:bg-slate-800/50";
            const padLeft = level * 20 + 8;
            const gv = (g.groupValue != null ? String(g.groupValue) : "").substring(0, 80);
            const expandIcon = `<svg class="w-4 h-4 inline-block mr-2 align-middle cursor-pointer" data-se-group-toggle="${groupId}" style="transform: ${collapsedDefault ? "rotate(0deg)" : "rotate(90deg)"};" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 18l6-6-6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
            rowsHTML += `<tr class="${bgClass} se-stock-group-row">`;
            rowsHTML += `<td class="${tdB} ${bgClass} border border-slate-200 dark:border-slate-600" style="padding-left: ${padLeft}px;">${expandIcon}<span class="font-medium text-slate-700 dark:text-slate-300">${escStockHtml(
              dimLabel
            )}: ${escStockHtml(gv)}</span></td>`;
            for (let c = 1; c <= 5; c++) {
              rowsHTML += `<td class="${tdB} ${bgClass} border border-slate-200 dark:border-slate-600"></td>`;
            }
            rowsHTML += `<td class="${tdB} ${bgClass} border border-slate-200 dark:border-slate-600 text-right tabular-nums font-mono font-semibold text-sky-600 dark:text-sky-400">${fmt(g.totals.stock)}</td>`;
            rowsHTML += `<td class="${tdB} ${bgClass} border border-slate-200 dark:border-slate-600 text-right tabular-nums font-mono font-semibold text-sky-600 dark:text-sky-400">${fmt(g.totals.reservado)}</td>`;
            rowsHTML += `<td class="${tdB} ${bgClass} border border-slate-200 dark:border-slate-600 text-right tabular-nums font-mono font-semibold text-sky-600 dark:text-sky-400">${fmt(g.totals.disponible)}</td>`;
            rowsHTML += "</tr>";
            rowsHTML += `<tr class="se-stock-group-children" data-se-group-parent="${groupId}" style="${collapsedDefault ? "display:none" : ""}"><td colspan="${NUM_COL_STOCK}" class="p-0 border-0 align-top"><table class="se-vo-stock-table se-vo-stock-nested vo-jerarquia-table w-full max-w-full table-fixed border-collapse border-0 text-xs text-slate-900 dark:text-slate-100">${STOCK_EXISTENCIAS_COLGROUP}<tbody>`;
            rowsHTML += renderGroupedRowsBOStyle(item.children, level + 1);
            rowsHTML += "</tbody></table></td></tr>";
          } else {
            rowsHTML += stockRow(item.data);
          }
        });
        return rowsHTML;
      };

      bodyHtml = renderGroupedRowsBOStyle(grouped, 0);
      const labelsAgrupacion = groupFields
        .map((f) => STOCK_EXISTENCIAS_DIM_LABELS[f] || f)
        .join(" → ");
      pieAgrupado = `<p class="text-xs text-slate-400 dark:text-slate-500 mt-3">Stock y existencias. Agrupado por: ${escStockHtml(
        labelsAgrupacion
      )}. ${numAgrupaciones} agrupación${numAgrupaciones !== 1 ? "es" : ""}${leyendaBusqueda}.</p>`;
    } else if (paginated && filtered.length >= 40) {
      bodyHtml = renderStockExistenciasVirtualBody(null, filtered);
      pieAgrupado = `<p class="text-xs text-slate-400 dark:text-slate-500 mt-3">Mostrando ${filtered.length} fila(s)${leyendaPaginacion}.</p>`;
    } else {
      filtered.forEach((r) => {
        bodyHtml += stockRow(r);
      });
      pieAgrupado = `<p class="text-xs text-slate-400 dark:text-slate-500 mt-3">Mostrando ${filtered.length} fila(s)${leyendaBusqueda}${leyendaPaginacion}.</p>`;
    }

    const theadRow = `
            <tr>
              ${sortHeader("id_manual", "ID manual", thDocIdManual)}
              ${sortHeader("codigo_barras", "Código barras", thDoc)}
              <th class="${thDoc}">Depósito</th>
              ${sortHeader("nombre", "Nombre artículo", thTxt)}
              ${sortHeader("rubro_nombre", "Rubro", thTxt)}
              ${sortHeader("subrubro_nombre", "Subrubro", thTxt)}
              <th class="${thNum}">Stock</th>
              <th class="${thNum}">Reservado</th>
              <th class="${thNum}">Disponible</th>
            </tr>`;

    const tableScrollClass =
      "overflow-x-auto overflow-y-auto max-h-[min(72vh,48rem)] min-h-[12rem] overscroll-contain rounded-xl border border-slate-200 dark:border-slate-700 [scrollbar-gutter:stable] bg-white dark:bg-slate-950";

    const srStock = window.SynapReportsResponsive;
    const stockLabelMap = {
      id_manual: "ID manual",
      codigo_barras: "Código barras",
      deposito_nombre: "Depósito",
      nombre: "Nombre",
      rubro_nombre: "Rubro",
      subrubro_nombre: "Subrubro",
      stock: "Stock",
      reservado: "Reservado",
      disponible: "Disponible",
    };
    const stockKeys = Object.keys(stockLabelMap);
    const stockColumns = srStock
      ? srStock.buildColumnsFromKeys(stockKeys, stockLabelMap)
      : [];

    let html = "";
    if (srStock) {
      html += `<div class="synap-responsive-table-mobile lg:hidden space-y-2">${srStock.buildMobileCardsHtml(
        filtered,
        stockColumns,
        { reportSlug: "stock-existencias" },
      )}</div>`;
    }
    html += `
      <div id="stock-existencias-scroll" class="${tableScrollClass} hidden lg:block">
        <table id="stock-existencias-data-table" class="se-vo-stock-table vo-jerarquia-table w-full table-fixed border-collapse text-left text-[11px] sm:text-xs text-slate-900 dark:text-slate-100">
          ${STOCK_EXISTENCIAS_COLGROUP}
          <thead>${theadRow}</thead>
          <tbody id="stock-existencias-tbody">${bodyHtml}</tbody></table></div>`;
    html += pieAgrupado;
    if (notes.length) {
      html += `<p class="text-[10px] text-amber-700 dark:text-amber-400 mt-2">${notes.map(escStockHtml).join(" ")}</p>`;
    }
    wrap.innerHTML = html;

    if (groupFields.length) {
      attachStockExistenciasGroupToggles(wrap);
    } else if (paginated && filtered.length >= 40) {
      const scrollEl = document.getElementById("stock-existencias-scroll");
      attachStockExistenciasVirtualScroll(scrollEl, filtered);
    }

    if (stockExistenciasDataset._prevScrollTop != null) {
      const scrollEl = document.getElementById("stock-existencias-scroll");
      if (scrollEl) scrollEl.scrollTop = stockExistenciasDataset._prevScrollTop;
      stockExistenciasDataset._prevScrollTop = null;
    }

    wrap.querySelectorAll("th[data-sort-col]").forEach((th) => {
      th.addEventListener("click", () => {
        const col = th.getAttribute("data-sort-col");
        if (!col) return;
        if (stockExistenciasSort.col === col) {
          stockExistenciasSort.dir = stockExistenciasSort.dir === "asc" ? "desc" : "asc";
        } else {
          stockExistenciasSort.col = col;
          stockExistenciasSort.dir = "asc";
        }
        if (stockExistenciasDataset.paginated) {
          fetchStockExistenciasData({
            offset: 0,
            append: false,
          });
          return;
        }
        showReportsQueryLoadingModal("stock-existencias", {
          title: "Ordenando tabla",
          subtitle: "Aplicando el criterio de orden a todo el listado…",
        });
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            try {
              renderStockExistenciasTableFromState();
            } finally {
              hideReportsQueryLoadingModal();
            }
          });
        });
      });
    });
  };

  window.renderStockExistenciasTableFromState = renderStockExistenciasTableFromState;

  /**
   * Informe stock-existencias: detalle por depósito; búsqueda y orden en servidor (paginado).
   */
  const renderStockExistenciasTable = (payload, { append = false } = {}) => {
    const wrap = document.getElementById("stock-existencias-table-wrap");
    const summaryEl = document.getElementById("stock-existencias-filters-summary");
    if (!wrap) return;
    const incoming = payload.data || [];
    const meta = payload.meta || {};
    const fa = meta.filters_applied || {};
    if (append) {
      stockExistenciasDataset.rows = (stockExistenciasDataset.rows || []).concat(incoming);
    } else {
      stockExistenciasDataset.rows = incoming;
      if (fa.sort_col) {
        stockExistenciasSort = { col: fa.sort_col, dir: fa.sort_dir || "asc" };
      } else if (!stockExistenciasNeedsFullFetch()) {
        stockExistenciasSort = { col: "nombre", dir: "asc" };
      }
    }
    stockExistenciasDataset.notes = payload.notes || [];
    stockExistenciasDataset.totalRegistros = meta.total_registros ?? incoming.length;
    stockExistenciasDataset.hasMore = Boolean(meta.has_more);
    stockExistenciasDataset.offset = meta.offset ?? 0;
    stockExistenciasDataset.paginated = !fa.agrupacion_activa && !stockExistenciasNeedsFullFetch();

    if (summaryEl) {
      const parts = [];
      if (fa.depositos_incluidos && fa.depositos_incluidos.length) {
        parts.push(`${fa.depositos_incluidos.length} depósito(s) en stock`);
      } else {
        parts.push("Stock: todos los depósitos");
      }
      if (fa.marcas_incluidos && fa.marcas_incluidos.length) parts.push(`${fa.marcas_incluidos.length} marca(s)`);
      if (fa.rubros_incluidos && fa.rubros_incluidos.length) parts.push(`${fa.rubros_incluidos.length} rubro(s)`);
      if (fa.subrubros_incluidos && fa.subrubros_incluidos.length) {
        parts.push(`${fa.subrubros_incluidos.length} subrubro(s)`);
      }
      if (fa.incluir_stock_cero) parts.push("Incluye stock cero");
      if (stockExistenciasDataset.paginated && stockExistenciasDataset.totalRegistros) {
        parts.push(`${stockExistenciasDataset.totalRegistros} fila(s) en total`);
      }
      summaryEl.textContent = parts.length ? parts.join(" · ") : "";
    }

    if (!window.__stockExistenciasUiInit) {
      window.__stockExistenciasUiInit = true;
      const section = document.getElementById("stock-existencias-section");
      let searchT = null;
      if (section) {
        section.addEventListener("input", (e) => {
          if (e.target && e.target.id === "stock_existencias_busqueda") {
            if (searchT) clearTimeout(searchT);
            searchT = setTimeout(() => {
              if (stockExistenciasDataset.paginated) {
                fetchStockExistenciasData({ offset: 0, append: false });
              } else {
                renderStockExistenciasTableFromState();
              }
            }, 400);
          }
        });
      }
    }

    if (append) {
      const scrollEl = document.getElementById("stock-existencias-scroll");
      stockExistenciasDataset._prevScrollTop = scrollEl ? scrollEl.scrollTop : 0;
    } else {
      stockExistenciasDataset._prevScrollTop = null;
    }

    renderStockExistenciasTableFromState();
  };

  const getStorageKey = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!reportSlug) return null;
    return `report_filters_${reportSlug}`;
  };

  const reconcileMutualExclusiveTags = (sourceId, targetId) => {
    const source = document.getElementById(sourceId);
    const target = document.getElementById(targetId);
    if (!source || !target) return;
    const sourceValues = new Set(Array.from(source.selectedOptions).map((opt) => String(opt.value)));
    let changed = false;
    Array.from(target.options).forEach((opt) => {
      const val = String(opt.value || "");
      if (!val) return;
      if (opt.selected && sourceValues.has(val)) {
        opt.selected = false;
        changed = true;
      }
    });
    if (changed) {
      target.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };

  const saveFilters = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!reportSlug) return;
    const filters = getFilters();
    try {
      const storageKey = getStorageKey();
      if (storageKey) {
        localStorage.setItem(storageKey, JSON.stringify(filters));
      }
    } catch (e) {
      console.warn("No se pudieron guardar los filtros en localStorage:", e);
    }
  };

  const loadFilters = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!reportSlug) return null;
    try {
      const storageKey = getStorageKey();
      if (storageKey) {
        const saved = localStorage.getItem(storageKey);
      if (saved) {
        return JSON.parse(saved);
        }
      }
    } catch (e) {
      console.warn("No se pudieron cargar los filtros desde localStorage:", e);
    }
    return null;
  };

  /**
   * Desde Command Center u otro origen: ?fecha_inicio=&fecha_fin= (o atajo ?fecha= un día).
   * Tiene prioridad sobre localStorage para el rango del informe.
   */
  const applyPeriodFromQueryParams = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!reportSlug) return false;

    const allowed =
      isVentasNetasSlug(reportSlug) ||
      reportSlug === "cash_flow_waterfall" ||
      reportSlug === "cash_flow_by_account" ||
      reportSlug === "uninvoiced_remitos" ||
      isPedidosPendientesSlug(reportSlug) ||
      reportSlug === "sales_summary" ||
      reportSlug === "total-consolidado-operativo" ||
      reportSlug === "stock-existencias" ||
      isInformeBoDualPeriodo(reportSlug);
    if (!allowed) return false;

    let params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (e) {
      return false;
    }
    const iso = /^\d{4}-\d{2}-\d{2}$/;
    let fi = (params.get("fecha_inicio") || "").trim();
    let ff = (params.get("fecha_fin") || "").trim();
    const legacy = (params.get("fecha") || "").trim();
    if ((!fi || !ff) && legacy && iso.test(legacy)) {
      fi = ff = legacy;
    }
    if (!iso.test(fi) || !iso.test(ff)) return false;

    const periodoTipoSelect = document.getElementById("periodo_tipo");
    if (periodoTipoSelect) {
      periodoTipoSelect.value = "personalizado";
      periodoTipoSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
    const fechaInicioInput = document.getElementById("fecha_inicio");
    const fechaFinInput = document.getElementById("fecha_fin");
    if (fechaInicioInput) fechaInicioInput.value = fi;
    if (fechaFinInput) fechaFinInput.value = ff;

    if (isInformeBoDualPeriodo(reportSlug)) {
      const facSel = document.getElementById("periodo_tipo_facturacion");
      const fifEl = document.getElementById("fecha_inicio_facturacion");
      const fffEl = document.getElementById("fecha_fin_facturacion");
      if (facSel && fifEl && fffEl) {
        facSel.value = "personalizado";
        fifEl.value = fi;
        fffEl.value = ff;
        fifEl.disabled = false;
        fffEl.disabled = false;
        facSel.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }

    const suc = (params.get("sucursal") || "").trim();
    if (suc) {
      const sucSelect = document.getElementById("sucursales");
      if (sucSelect) {
        const option = sucSelect.querySelector(`option[value="${suc}"]`);
        if (option && !option.selected) {
          option.selected = true;
          setTimeout(() => {
            sucSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }
    }

    if (typeof saveFilters === "function") {
      saveFilters();
    }

    try {
      params.delete("fecha_inicio");
      params.delete("fecha_fin");
      params.delete("fecha");
      if (suc) params.delete("sucursal");
      const q = params.toString();
      const newUrl = window.location.pathname + (q ? `?${q}` : "") + window.location.hash;
      window.history.replaceState({}, "", newUrl);
    } catch (e) {
      /* noop */
    }
    return true;
  };

  /**
   * Desde el CRUD de objetivos de venta el enlace incluye ?fecha_inicio_facturacion=&fecha_fin_facturacion=
   * (intervalo del período editado). Solo se ajusta el rango de facturación/remitos; el de backorder
   * sigue viniendo de localStorage (última configuración).
   */
  const applyVentasObjetivosFacturacionFromQueryParams = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!isJerarquiaVentasBoFamiliaSlug(reportSlug)) return;

    let params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (e) {
      return;
    }
    const fi = (params.get("fecha_inicio_facturacion") || "").trim();
    const ff = (params.get("fecha_fin_facturacion") || "").trim();
    if (!fi || !ff) return;

    const iso = /^\d{4}-\d{2}-\d{2}$/;
    if (!iso.test(fi) || !iso.test(ff)) return;

    const fifEl = document.getElementById("fecha_inicio_facturacion");
    const fffEl = document.getElementById("fecha_fin_facturacion");
    const facSel = document.getElementById("periodo_tipo_facturacion");
    const root = document.getElementById("bo-period-filters-root");
    const row = root?.querySelector('[data-bo-period-row="facturacion"]');
    if (!fifEl || !fffEl || !facSel || !row) return;

    fifEl.value = fi;
    fffEl.value = ff;
    facSel.value = "personalizado";

    const buttons = row.querySelectorAll(".periodo-tipo-btn-bo");
    const activeClasses = ["active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md"];
    const inactiveClasses = ["border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300"];
    buttons.forEach((btn) => {
      const periodo = btn.dataset.periodo;
      if (periodo === "personalizado") {
        btn.classList.add(...activeClasses);
        inactiveClasses.forEach((c) => btn.classList.remove(c));
      } else {
        activeClasses.forEach((c) => btn.classList.remove(c));
        inactiveClasses.forEach((c) => btn.classList.add(c));
      }
    });

    fifEl.disabled = false;
    fffEl.disabled = false;

    facSel.dispatchEvent(new Event("change", { bubbles: true }));

    if (typeof syncBoDualSummaryPeriod === "function") {
      syncBoDualSummaryPeriod();
    }
    saveFilters();

    try {
      params.delete("fecha_inicio_facturacion");
      params.delete("fecha_fin_facturacion");
      const q = params.toString();
      const newUrl = window.location.pathname + (q ? `?${q}` : "") + window.location.hash;
      window.history.replaceState({}, "", newUrl);
    } catch (e) {
      /* noop */
    }
  };

  const applyFilters = (filters) => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!filters || !reportSlug) return;
    const allowed =
      isVentasNetasSlug(reportSlug) ||
      reportSlug === "cash_flow_waterfall" ||
      reportSlug === "cash_flow_by_account" ||
      reportSlug === "uninvoiced_remitos" ||
      isPedidosPendientesSlug(reportSlug) ||
      isLogisticaListaComprobantesRutasSlug(reportSlug) ||
      reportSlug === "sales_summary" ||
      reportSlug === "total-consolidado-operativo" ||
      reportSlug === "stock-existencias" ||
      isInformeBoDualPeriodo(reportSlug);
    if (!allowed) return;

    // Aplicar tipo de período y fechas
    const periodoTipoSelect = document.getElementById("periodo_tipo");
    if (periodoTipoSelect) {
      // Determinar el tipo de período basado en los filtros guardados
      if (filters.dia_actual) {
        periodoTipoSelect.value = "dia_actual";
      } else if (filters.mes_actual) {
        periodoTipoSelect.value = "mes_actual";
      } else if (filters.año_actual) {
        periodoTipoSelect.value = "año_actual";
      } else {
        periodoTipoSelect.value = "personalizado";
      }
      // Disparar evento para actualizar fechas
      periodoTipoSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
    
    // Aplicar fechas (se establecerán automáticamente según el tipo de período)
    if (filters.fecha_inicio) {
      const fechaInicioInput = document.getElementById("fecha_inicio");
      if (fechaInicioInput) {
        fechaInicioInput.value = filters.fecha_inicio;
      }
    }
    if (filters.fecha_fin) {
      const fechaFinInput = document.getElementById("fecha_fin");
      if (fechaFinInput) {
        fechaFinInput.value = filters.fecha_fin;
      }
    }

    const periodoTipoFacSelect = document.getElementById("periodo_tipo_facturacion");
    if (isInformeBoDualPeriodo(reportSlug) && periodoTipoFacSelect) {
      if (filters.dia_actual_facturacion) {
        periodoTipoFacSelect.value = "dia_actual";
      } else if (filters.mes_actual_facturacion) {
        periodoTipoFacSelect.value = "mes_actual";
      } else if (filters.año_actual_facturacion) {
        periodoTipoFacSelect.value = "año_actual";
      } else {
        periodoTipoFacSelect.value = filters.periodo_tipo_facturacion || "personalizado";
      }
      const fifEl = document.getElementById("fecha_inicio_facturacion");
      const fffEl = document.getElementById("fecha_fin_facturacion");
      if (fifEl) {
        if (filters.fecha_inicio_facturacion) {
          fifEl.value = filters.fecha_inicio_facturacion;
        } else if (filters.fecha_inicio) {
          fifEl.value = filters.fecha_inicio;
        }
      }
      if (fffEl) {
        if (filters.fecha_fin_facturacion) {
          fffEl.value = filters.fecha_fin_facturacion;
        } else if (filters.fecha_fin) {
          fffEl.value = filters.fecha_fin;
        }
      }
    }

    // Aplicar refresh_interval
    if (filters.refresh_interval) {
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) {
        refreshIntervalSelect.value = filters.refresh_interval;
        // Actualizar estado visual de los botones
        const buttons = document.querySelectorAll(".refresh-interval-btn");
        buttons.forEach((btn) => {
          const interval = btn.dataset.interval;
          if (interval === filters.refresh_interval) {
            btn.classList.add("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
            btn.classList.remove("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
          } else {
            btn.classList.remove("active", "border-sky-500", "bg-sky-50", "dark:bg-sky-900/20", "text-sky-700", "dark:text-sky-300", "shadow-md");
            btn.classList.add("border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800", "text-slate-700", "dark:text-slate-300");
          }
        });
        // Disparar evento change para actualizar tiempo real si está activo
        refreshIntervalSelect.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }

    // Aplicar filtros específicos de ventas_netas, uninvoiced_remitos, bo-stock-facturacion (punto_venta, sucursales)
    if (isVentasNetasSlug(reportSlug) || reportSlug === "uninvoiced_remitos" || reportSlug === "total-consolidado-operativo" || isInformeBoDualPeriodo(reportSlug)) {
      if (filters.punto_venta && Array.isArray(filters.punto_venta)) {
        const pvSelect = document.getElementById("punto_venta");
        if (pvSelect) {
          // Asegurar que las opciones estén seleccionadas
          filters.punto_venta.forEach((value) => {
            const option = pvSelect.querySelector(`option[value="${value}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          // Disparar evento para actualizar tags visuales
          setTimeout(() => {
            pvSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }

      if (filters.sucursales && Array.isArray(filters.sucursales)) {
        const sucSelect = document.getElementById("sucursales");
        if (sucSelect) {
          // Asegurar que las opciones estén seleccionadas
          filters.sucursales.forEach((value) => {
            const option = sucSelect.querySelector(`option[value="${value}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          // Disparar evento para actualizar tags visuales
          setTimeout(() => {
            sucSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }

      // Clientes a excluir (NOT IN) - Ventas Netas, Total Consolidado, Remitos, BO Stock Facturación
      if ((isVentasNetasSlug(reportSlug) || reportSlug === "total-consolidado-operativo" || reportSlug === "uninvoiced_remitos" || isInformeBoDualPeriodo(reportSlug)) && filters.clientes_excluidos && Array.isArray(filters.clientes_excluidos)) {
        const clientesSelect = document.getElementById("clientes_excluidos");
        if (clientesSelect) {
          filters.clientes_excluidos.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = clientesSelect.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          setTimeout(() => {
            clientesSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }

      if (
        isInformeVentasMarcasFamiliaSlug(reportSlug) &&
        filters.vendedores_excluidos &&
        Array.isArray(filters.vendedores_excluidos)
      ) {
        const vendSelect = document.getElementById("vendedores_excluidos");
        if (vendSelect) {
          filters.vendedores_excluidos.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = vendSelect.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          setTimeout(() => {
            vendSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }
      if (isInformeVentasMarcasFamiliaSlug(reportSlug) && filters.clientes_incluir && Array.isArray(filters.clientes_incluir)) {
        const clientesIncluirSelect = document.getElementById("clientes_incluir");
        if (clientesIncluirSelect) {
          filters.clientes_incluir.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = clientesIncluirSelect.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) option.selected = true;
          });
          setTimeout(() => {
            clientesIncluirSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }
      if (isInformeVentasMarcasFamiliaSlug(reportSlug) && filters.vendedores_incluir && Array.isArray(filters.vendedores_incluir)) {
        const vendedoresIncluirSelect = document.getElementById("vendedores_incluir");
        if (vendedoresIncluirSelect) {
          filters.vendedores_incluir.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = vendedoresIncluirSelect.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) option.selected = true;
          });
          setTimeout(() => {
            vendedoresIncluirSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }
      if (isJerarquiaVentasBoFamiliaSlug(reportSlug)) {
        const ordenarPorSelect = document.getElementById("ordenar_por");
        const ordenFormaSelect = document.getElementById("orden_forma");
        const sortFilters = normalizeJerarquiaSortFilters(reportSlug, filters.ordenar_por, filters.orden_forma);
        if (ordenarPorSelect) ordenarPorSelect.value = sortFilters.ordenarPor;
        if (ordenFormaSelect) ordenFormaSelect.value = sortFilters.ordenForma;
        filters.ordenar_por = sortFilters.ordenarPor;
        filters.orden_forma = sortFilters.ordenForma;
      }

      // Depósitos incluidos (BO y Objetivos vs BO)
      if (isInformeBoDualPeriodo(reportSlug) && filters.depositos_incluidos && Array.isArray(filters.depositos_incluidos)) {
        const depositosSelect = document.getElementById("depositos_incluidos");
        if (depositosSelect) {
          filters.depositos_incluidos.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = depositosSelect.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          setTimeout(() => {
            depositosSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }

      // Lista de precio (BO y Objetivos vs BO)
      if (isInformeBoDualPeriodo(reportSlug) && filters.lista_precio !== undefined && filters.lista_precio !== null) {
        const listaPrecioSelect = document.getElementById("lista_precio");
        if (listaPrecioSelect) {
          const v = String(filters.lista_precio);
          if (listaPrecioSelect.querySelector(`option[value="${v}"]`)) {
            listaPrecioSelect.value = v;
          }
        }
      }
      if (isVentasMarcasMensualSlug(reportSlug)) {
        const tagRestoreVmm = (arr, selectId) => {
          if (!arr || !Array.isArray(arr)) return;
          const sel = document.getElementById(selectId);
          if (!sel) return;
          arr.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = sel.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) option.selected = true;
          });
          setTimeout(() => sel.dispatchEvent(new Event("change", { bubbles: true })), 150);
        };
        tagRestoreVmm(filters.marcas_incluidos, "vmm_marcas_incluidos");
        tagRestoreVmm(filters.superarts_incluidos, "vmm_superarts_incluidos");
        if (filters.modo_unidades) {
          const modoHidden = document.getElementById("modo_unidades");
          const modoBtns = document.querySelectorAll("#vmm-modo-unidades-buttons .vmm-modo-btn");
          const m = filters.modo_unidades === "docenas" ? "docenas" : "packs";
          if (modoHidden) modoHidden.value = m;
          modoBtns.forEach((btn) => {
            const active = btn.getAttribute("data-modo-unidades") === m;
            btn.classList.toggle("border-sky-500", active);
            btn.classList.toggle("bg-sky-50", active);
            btn.classList.toggle("dark:bg-sky-900/20", active);
            btn.classList.toggle("text-sky-700", active);
            btn.classList.toggle("dark:text-sky-300", active);
            btn.classList.toggle("shadow-md", active);
            btn.classList.toggle("border-slate-300", !active);
            btn.classList.toggle("dark:border-slate-600", !active);
            btn.classList.toggle("bg-white", !active);
            btn.classList.toggle("dark:bg-slate-800", !active);
            btn.classList.toggle("text-slate-700", !active);
            btn.classList.toggle("dark:text-slate-300", !active);
          });
        }
        const tasaEl = document.getElementById("vmm_tasa_regalia_pct");
        if (tasaEl && filters.tasa_regalia_pct != null && filters.tasa_regalia_pct !== "") {
          tasaEl.value = filters.tasa_regalia_pct;
        }
        const tcEl = document.getElementById("vmm_tc");
        if (tcEl && filters.tc != null) {
          tcEl.value = filters.tc;
        }
        const coefEl = document.getElementById("vmm_coef_proyeccion");
        if (coefEl && filters.coef_proyeccion != null && filters.coef_proyeccion !== "") {
          coefEl.value = filters.coef_proyeccion;
        }
        const proyHidden = document.getElementById("vmm_incluir_proyeccion");
        const proyBtns = document.querySelectorAll("#vmm-proyeccion-buttons .vmm-proy-btn");
        if (proyHidden) {
          const on = filters.incluir_proyeccion === "1" || filters.incluir_proyeccion === 1;
          proyHidden.value = on ? "1" : "0";
          proyBtns.forEach((btn) => {
            const active = btn.getAttribute("data-incluir-proyeccion") === (on ? "1" : "0");
            btn.classList.toggle("border-sky-500", active);
            btn.classList.toggle("bg-sky-50", active);
            btn.classList.toggle("dark:bg-sky-900/20", active);
            btn.classList.toggle("text-sky-700", active);
            btn.classList.toggle("dark:text-sky-300", active);
            btn.classList.toggle("shadow-md", active);
            btn.classList.toggle("border-slate-300", !active);
            btn.classList.toggle("dark:border-slate-600", !active);
            btn.classList.toggle("bg-white", !active);
            btn.classList.toggle("dark:bg-slate-800", !active);
            btn.classList.toggle("text-slate-700", !active);
            btn.classList.toggle("dark:text-slate-300", !active);
          });
        }
        const cmpHidden = document.getElementById("vmm_modo_comparacion");
        if (cmpHidden && filters.modo_comparacion) {
          cmpHidden.value = filters.modo_comparacion === "comparar" ? "comparar" : "una";
          const cmpBtn = document.querySelector(
            `#vmm-modo-comparacion-buttons .vmm-cmp-btn[data-modo-comparacion="${cmpHidden.value}"]`
          );
          if (cmpBtn) cmpBtn.click();
        }
        if (filters.marca_a) {
          const ma = document.getElementById("vmm_marca_a");
          if (ma) ma.value = String(filters.marca_a);
        }
        if (filters.marca_b) {
          const mb = document.getElementById("vmm_marca_b");
          if (mb) mb.value = String(filters.marca_b);
        }
      }
      if (reportSlug === "ventas-objetivos-vs-bo") {
        const tagRestoreVoRubro = (arr, selectId) => {
          if (!arr || !Array.isArray(arr)) return;
          const sel = document.getElementById(selectId);
          if (!sel) return;
          arr.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = sel.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          setTimeout(() => {
            sel.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        };
        tagRestoreVoRubro(filters.rubros_incluidos, "vo_rubros_incluidos");
        tagRestoreVoRubro(filters.subrubros_incluidos, "vo_subrubros_incluidos");
      }
      if (isVentasCatalogoFiltersSlug(reportSlug)) {
        const tagRestoreVpa = (arr, selectId) => {
          if (!arr || !Array.isArray(arr)) return;
          const sel = document.getElementById(selectId);
          if (!sel) return;
          arr.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = sel.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          setTimeout(() => {
            sel.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        };
        VPA_CATALOG_FILTER_SPECS.forEach(([selectId, key]) => tagRestoreVpa(filters[key], selectId));
      }
    }

    if (reportSlug === "stock-existencias") {
      if (filters.depositos_incluidos && Array.isArray(filters.depositos_incluidos)) {
        const depositosSelect = document.getElementById("depositos_incluidos");
        if (depositosSelect) {
          filters.depositos_incluidos.forEach((value) => {
            const val = String(value ?? "").trim();
            if (!val) return;
            const option = depositosSelect.querySelector(`option[value="${val}"]`);
            if (option && !option.selected) {
              option.selected = true;
            }
          });
          setTimeout(() => {
            depositosSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }
      const tagRestoreStock = (arr, selectId) => {
        if (!arr || !Array.isArray(arr)) return;
        const sel = document.getElementById(selectId);
        if (!sel) return;
        arr.forEach((value) => {
          const val = String(value ?? "").trim();
          if (!val) return;
          const option = sel.querySelector(`option[value="${val}"]`);
          if (option && !option.selected) {
            option.selected = true;
          }
        });
        setTimeout(() => {
          sel.dispatchEvent(new Event("change", { bubbles: true }));
        }, 150);
      };
      tagRestoreStock(filters.marcas_incluidos, "marcas_incluidos");
      tagRestoreStock(filters.rubros_incluidos, "rubros_incluidos");
      tagRestoreStock(filters.subrubros_incluidos, "subrubros_incluidos");
      if (filters.incluir_stock_cero) {
        const isc = document.getElementById("incluir_stock_cero");
        if (isc) {
          isc.value = filters.incluir_stock_cero;
        }
      }
    }

    if (isLogisticaListaComprobantesRutasSlug(reportSlug)) {
      const estEl = document.getElementById("logistica_estado_entrega");
      if (estEl && filters.logistica_estado_entrega != null && filters.logistica_estado_entrega !== "") {
        const vals = Array.isArray(filters.logistica_estado_entrega)
          ? filters.logistica_estado_entrega.map((v) => String(v).trim()).filter(Boolean)
          : [String(filters.logistica_estado_entrega).trim()].filter(Boolean);
        Array.from(estEl.options).forEach((opt) => {
          opt.selected = vals.includes(opt.value);
        });
        setTimeout(() => {
          estEl.dispatchEvent(new Event("change", { bubbles: true }));
        }, 50);
      }
      const idCliEl = document.getElementById("logistica_id_cliente");
      if (idCliEl && filters.logistica_id_cliente != null && filters.logistica_id_cliente !== "") {
        const raw = filters.logistica_id_cliente;
        const codes = Array.isArray(raw) ? raw : [raw];
        const etiquetas =
          filters.logistica_cliente_etiquetas && typeof filters.logistica_cliente_etiquetas === "object"
            ? filters.logistica_cliente_etiquetas
            : {};
        idCliEl.innerHTML = "";
        codes.forEach((c) => {
          const code = String(c).trim();
          if (!code) return;
          let lab = etiquetas[code];
          if (lab == null || lab === "") {
            lab = !Array.isArray(raw) && filters.logistica_cliente_label ? filters.logistica_cliente_label : code;
          }
          const o = document.createElement("option");
          o.value = code;
          o.textContent = lab;
          o.selected = true;
          idCliEl.appendChild(o);
        });
        setTimeout(() => {
          idCliEl.dispatchEvent(new Event("change", { bubbles: true }));
        }, 50);
      }
    }

    // Aplicar filtros específicos de cash_flow_waterfall
    if (reportSlug === "cash_flow_waterfall") {
      // Caja - puede ser array o string único
      if (filters.id_caja) {
        const idCajaSelect = document.getElementById("id_caja");
        if (idCajaSelect) {
          // Si es array, seleccionar todas las opciones
          if (Array.isArray(filters.id_caja)) {
            filters.id_caja.forEach((value) => {
              const option = idCajaSelect.querySelector(`option[value="${value}"]`);
              if (option && !option.selected) {
                option.selected = true;
              }
            });
          } else {
            // Si es string único, seleccionar esa opción
            const option = idCajaSelect.querySelector(`option[value="${filters.id_caja}"]`);
            if (option) {
              option.selected = true;
            }
          }
          // Disparar evento para actualizar tags visuales
          setTimeout(() => {
            idCajaSelect.dispatchEvent(new Event("change", { bubbles: true }));
          }, 150);
        }
      }
    }
  };

  // Helper: prioriza fechas de los inputs (lo que ve el usuario). Solo recalcula si faltan.
  const setPeriodDatesFromForm = (filters, periodoTipo, fechaInicio, fechaFin) => {
    const today = new Date();
    const fallbackMes = () => {
      const first = new Date(today.getFullYear(), today.getMonth(), 1);
      const last = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      return [first.toISOString().split("T")[0], last.toISOString().split("T")[0]];
    };
    if (fechaInicio && fechaFin) {
      filters.fecha_inicio = fechaInicio;
      filters.fecha_fin = fechaFin;
      if (periodoTipo === "dia_actual") filters.dia_actual = true;
      else if (periodoTipo === "mes_actual") filters.mes_actual = true;
      else if (periodoTipo === "año_actual") filters.año_actual = true;
      return;
    }
    if (periodoTipo === "dia_actual") {
      const s = today.toISOString().split("T")[0];
      filters.fecha_inicio = s;
      filters.fecha_fin = s;
      filters.dia_actual = true;
    } else if (periodoTipo === "mes_actual") {
      const [a, b] = fallbackMes();
      filters.fecha_inicio = a;
      filters.fecha_fin = b;
      filters.mes_actual = true;
    } else if (periodoTipo === "año_actual") {
      const first = new Date(today.getFullYear(), 0, 1);
      const last = new Date(today.getFullYear(), 11, 31);
      filters.fecha_inicio = first.toISOString().split("T")[0];
      filters.fecha_fin = last.toISOString().split("T")[0];
      filters.año_actual = true;
    } else {
      const [a, b] = fallbackMes();
      filters.fecha_inicio = a;
      filters.fecha_fin = b;
    }
  };

  // Declarar getFilters en el scope global para que esté disponible en fetchDetailedMovements
  window.getFilters = () => {
    const filters = {};
    const currentReportSlug = dashboardRoot?.dataset?.reportSlug;
    
    if (isVentasNetasSlug(currentReportSlug)) {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      const puntoVentaSelect = document.getElementById("punto_venta");
      const sucursalesSelect = document.getElementById("sucursales");
      setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin);
      
      // Obtener refresh_interval del filtro
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) {
        filters.refresh_interval = refreshIntervalSelect.value;
      }
      
      if (puntoVentaSelect) {
        const selectedPVs = Array.from(puntoVentaSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        if (selectedPVs.length > 0) {
          filters.punto_venta = selectedPVs;
        }
      }
      
      if (sucursalesSelect) {
        const selectedSucursales = Array.from(sucursalesSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        if (selectedSucursales.length > 0) {
          filters.sucursales = selectedSucursales;
        }
      }
      const clientesExcluidosSelect = document.getElementById("clientes_excluidos");
      if (clientesExcluidosSelect) {
        const selectedClientes = Array.from(clientesExcluidosSelect.selectedOptions).map(opt => String(opt.value)).filter(v => v);
        filters.clientes_excluidos = selectedClientes;
      }
    } else if (currentReportSlug === "uninvoiced_remitos" || currentReportSlug === "total-consolidado-operativo") {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      const puntoVentaSelect = document.getElementById("punto_venta");
      const sucursalesSelect = document.getElementById("sucursales");
      const clientesExcluidosSelect = document.getElementById("clientes_excluidos");
      setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin);
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) filters.refresh_interval = refreshIntervalSelect.value;
      if (puntoVentaSelect) {
        const selectedPVs = Array.from(puntoVentaSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        if (selectedPVs.length > 0) filters.punto_venta = selectedPVs;
      }
      if (sucursalesSelect) {
        const selectedSucursales = Array.from(sucursalesSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        if (selectedSucursales.length > 0) filters.sucursales = selectedSucursales;
      }
      if (clientesExcluidosSelect) {
        const selectedClientes = Array.from(clientesExcluidosSelect.selectedOptions).map(opt => String(opt.value)).filter(v => v);
        filters.clientes_excluidos = selectedClientes;
      }
    } else if (isPedidosPendientesSlug(currentReportSlug)) {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin);
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) filters.refresh_interval = refreshIntervalSelect.value;
    } else if (isLogisticaListaComprobantesRutasSlug(currentReportSlug)) {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin);
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) filters.refresh_interval = refreshIntervalSelect.value;
      const estSel = document.getElementById("logistica_estado_entrega");
      if (estSel) {
        const estVals = Array.from(estSel.selectedOptions)
          .map((o) => String(o.value).trim())
          .filter((v) => v === "Si" || v === "No");
        if (estVals.length === 1) {
          filters.logistica_estado_entrega = estVals[0];
        }
      }
      const cliSel = document.getElementById("logistica_id_cliente");
      if (cliSel) {
        const opts = Array.from(cliSel.selectedOptions)
          .map((o) => ({
            id: String(o.value).trim(),
            text: String(o.textContent || "").trim(),
          }))
          .filter((o) => o.id);
        if (opts.length === 1) {
          filters.logistica_id_cliente = opts[0].id;
          filters.logistica_cliente_label = opts[0].text || opts[0].id;
        } else if (opts.length > 1) {
          filters.logistica_id_cliente = opts.map((o) => o.id);
          filters.logistica_cliente_etiquetas = Object.fromEntries(
            opts.map((o) => [o.id, o.text || o.id]),
          );
        }
      }
    } else if (currentReportSlug === "sales_summary") {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin);
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) filters.refresh_interval = refreshIntervalSelect.value;
    } else if (isInformeBoDualPeriodo(currentReportSlug)) {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const periodoTipoFac = document.getElementById("periodo_tipo_facturacion")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      const fechaInicioFac = document.getElementById("fecha_inicio_facturacion")?.value;
      const fechaFinFac = document.getElementById("fecha_fin_facturacion")?.value;
      const puntoVentaSelect = document.getElementById("punto_venta");
      const sucursalesSelect = document.getElementById("sucursales");
      const depositosIncluidosSelect = document.getElementById("depositos_incluidos");
      const clientesExcluidosSelect = document.getElementById("clientes_excluidos");
      setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin);
      filters.periodo_tipo_facturacion = periodoTipoFac;
      filters.fecha_inicio_facturacion = fechaInicioFac;
      filters.fecha_fin_facturacion = fechaFinFac;
      delete filters.dia_actual_facturacion;
      delete filters.mes_actual_facturacion;
      delete filters.año_actual_facturacion;
      if (periodoTipoFac === "dia_actual") {
        filters.dia_actual_facturacion = true;
      } else if (periodoTipoFac === "mes_actual") {
        filters.mes_actual_facturacion = true;
      } else if (periodoTipoFac === "año_actual") {
        filters.año_actual_facturacion = true;
      }
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) filters.refresh_interval = refreshIntervalSelect.value;
      if (puntoVentaSelect) {
        const selectedPVs = Array.from(puntoVentaSelect.selectedOptions).map((opt) => opt.value).filter((v) => v);
        if (selectedPVs.length > 0) filters.punto_venta = selectedPVs;
      }
      if (sucursalesSelect) {
        const selectedSucursales = Array.from(sucursalesSelect.selectedOptions).map((opt) => opt.value).filter((v) => v);
        if (selectedSucursales.length > 0) filters.sucursales = selectedSucursales;
      }
      if (depositosIncluidosSelect) {
        const selectedDepositos = Array.from(depositosIncluidosSelect.selectedOptions).map((opt) => String(opt.value)).filter((v) => v);
        if (selectedDepositos.length > 0) filters.depositos_incluidos = selectedDepositos;
      }
      if (clientesExcluidosSelect) {
        const selectedClientes = Array.from(clientesExcluidosSelect.selectedOptions).map((opt) => String(opt.value)).filter((v) => v);
        filters.clientes_excluidos = selectedClientes;
      }
      const vendedoresExcluidosSelect = document.getElementById("vendedores_excluidos");
      const vendedoresIncluirSelect = document.getElementById("vendedores_incluir");
      const clientesIncluirSelect = document.getElementById("clientes_incluir");
      if (vendedoresExcluidosSelect && isInformeVentasMarcasFamiliaSlug(currentReportSlug)) {
        const selectedVend = Array.from(vendedoresExcluidosSelect.selectedOptions)
          .map((opt) => String(opt.value))
          .filter((v) => v);
        if (selectedVend.length > 0) {
          filters.vendedores_excluidos = selectedVend;
        }
      }
      if (clientesIncluirSelect && isInformeVentasMarcasFamiliaSlug(currentReportSlug)) {
        const selectedCliInc = Array.from(clientesIncluirSelect.selectedOptions)
          .map((opt) => String(opt.value))
          .filter((v) => v);
        if (selectedCliInc.length > 0) {
          filters.clientes_incluir = selectedCliInc;
        }
      }
      if (vendedoresIncluirSelect && isInformeVentasMarcasFamiliaSlug(currentReportSlug)) {
        const selectedVendInc = Array.from(vendedoresIncluirSelect.selectedOptions)
          .map((opt) => String(opt.value))
          .filter((v) => v);
        if (selectedVendInc.length > 0) {
          filters.vendedores_incluir = selectedVendInc;
        }
      }
      const listaPrecioSelect = document.getElementById("lista_precio");
      if (listaPrecioSelect) {
        const v = listaPrecioSelect.value;
        if (v !== "" && v !== undefined) filters.lista_precio = parseInt(v, 10);
      }
      if (currentReportSlug === "ventas-objetivos-vs-bo") {
        const rubVo = document.getElementById("vo_rubros_incluidos");
        const subVo = document.getElementById("vo_subrubros_incluidos");
        if (rubVo) {
          const sr = Array.from(rubVo.selectedOptions)
            .map((opt) => String(opt.value))
            .filter((v) => v);
          if (sr.length > 0) filters.rubros_incluidos = sr;
        }
        if (subVo) {
          const ss = Array.from(subVo.selectedOptions)
            .map((opt) => String(opt.value))
            .filter((v) => v);
          if (ss.length > 0) filters.subrubros_incluidos = ss;
        }
      }
      if (isVentasCatalogoFiltersSlug(currentReportSlug)) {
        VPA_CATALOG_FILTER_SPECS.forEach(([selectId, key]) =>
          appendTagMultiFilter(selectId, filters, key)
        );
      }
      if (isVentasMarcasMensualSlug(currentReportSlug)) {
        VMM_FILTER_SPECS.forEach(([selectId, key]) =>
          appendTagMultiFilter(selectId, filters, key)
        );
        const modoEl = document.getElementById("modo_unidades");
        if (modoEl && modoEl.value) {
          filters.modo_unidades = modoEl.value;
        }
        const tasaEl = document.getElementById("vmm_tasa_regalia_pct");
        if (tasaEl && tasaEl.value !== "") {
          filters.tasa_regalia_pct = tasaEl.value;
        }
        const tcEl = document.getElementById("vmm_tc");
        if (tcEl && tcEl.value.trim() !== "") {
          filters.tc = tcEl.value.trim();
        }
        const proyEl = document.getElementById("vmm_incluir_proyeccion");
        filters.incluir_proyeccion = proyEl && proyEl.value === "1" ? "1" : "0";
        const coefEl = document.getElementById("vmm_coef_proyeccion");
        if (coefEl && coefEl.value !== "") {
          filters.coef_proyeccion = coefEl.value;
        }
        const cmpEl = document.getElementById("vmm_modo_comparacion");
        if (cmpEl && cmpEl.value) {
          filters.modo_comparacion = cmpEl.value;
        }
        const marcaA = document.getElementById("vmm_marca_a");
        if (marcaA && marcaA.value) {
          filters.marca_a = marcaA.value;
        }
        const marcaB = document.getElementById("vmm_marca_b");
        if (marcaB && marcaB.value) {
          filters.marca_b = marcaB.value;
        }
      }
      if (isJerarquiaVentasBoFamiliaSlug(currentReportSlug)) {
        const ordenarPorSelect = document.getElementById("ordenar_por");
        const ordenFormaSelect = document.getElementById("orden_forma");
        const sortFilters = normalizeJerarquiaSortFilters(
          currentReportSlug,
          ordenarPorSelect?.value,
          ordenFormaSelect?.value
        );
        filters.ordenar_por = sortFilters.ordenarPor;
        filters.orden_forma = sortFilters.ordenForma;
      }
    } else if (currentReportSlug === "stock-existencias") {
      const depositosIncluidosSelect = document.getElementById("depositos_incluidos");
      const marcasSel = document.getElementById("marcas_incluidos");
      const rubrosSel = document.getElementById("rubros_incluidos");
      const subrubrosSel = document.getElementById("subrubros_incluidos");
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) filters.refresh_interval = refreshIntervalSelect.value;
      if (depositosIncluidosSelect) {
        const selectedDepositos = Array.from(depositosIncluidosSelect.selectedOptions)
          .map((opt) => String(opt.value))
          .filter((v) => v);
        if (selectedDepositos.length > 0) filters.depositos_incluidos = selectedDepositos;
      }
      if (marcasSel) {
        const sm = Array.from(marcasSel.selectedOptions)
          .map((opt) => String(opt.value))
          .filter((v) => v);
        if (sm.length > 0) filters.marcas_incluidos = sm;
      }
      if (rubrosSel) {
        const sr = Array.from(rubrosSel.selectedOptions)
          .map((opt) => String(opt.value))
          .filter((v) => v);
        if (sr.length > 0) filters.rubros_incluidos = sr;
      }
      if (subrubrosSel) {
        const ss = Array.from(subrubrosSel.selectedOptions)
          .map((opt) => String(opt.value))
          .filter((v) => v);
        if (ss.length > 0) filters.subrubros_incluidos = ss;
      }
      const isc = document.getElementById("incluir_stock_cero");
      if (isc) filters.incluir_stock_cero = isc.value;
    } else if (
      currentReportSlug === "cash_flow_waterfall" ||
      currentReportSlug === "cash_flow_by_account" ||
      currentReportSlug === "cash_flow_detailed_movements"
    ) {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      const idCajaSelect = document.getElementById("id_caja");
      setPeriodDatesFromForm(filters, periodoTipo, fechaInicio, fechaFin);
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) filters.refresh_interval = refreshIntervalSelect.value;
      if (idCajaSelect) {
        const selectedCajas = Array.from(idCajaSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        if (selectedCajas.length > 0) filters.id_caja = selectedCajas;
      }
    } else {
      // Filtros genéricos para otros reportes
      const dateFrom = document.querySelector('[name="date_from"]')?.value;
      const dateTo = document.querySelector('[name="date_to"]')?.value;
      if (dateFrom) filters.date_from = dateFrom;
      if (dateTo) filters.date_to = dateTo;
    }
    
    return filters;
  };

  const showLoadingAnimation = () => {
    const widgets = dashboardRoot.querySelectorAll("[data-widget-content]");
    widgets.forEach((container) => {
      const loadingOverlay = document.createElement("div");
      loadingOverlay.className = "absolute inset-0 bg-slate-900/80 flex items-center justify-center z-10";
      loadingOverlay.id = "loading-overlay";
      loadingOverlay.innerHTML = `
        <div class="flex flex-col items-center gap-3">
          <div class="w-8 h-8 border-4 border-sky-500 border-t-transparent rounded-full animate-spin"></div>
          <p class="text-xs text-slate-200 tracking-[0.2em] uppercase">Actualizando...</p>
        </div>
      `;
      const parent = container.parentElement;
      if (parent) {
        parent.style.position = "relative";
        parent.appendChild(loadingOverlay);
      }
    });
  };

  const hideLoadingAnimation = () => {
    const loadingOverlays = document.querySelectorAll("#loading-overlay");
    loadingOverlays.forEach((overlay) => {
      overlay.style.opacity = "0";
      overlay.style.transition = "opacity 0.3s ease-out";
      setTimeout(() => overlay.remove(), 300);
    });
  };

  /** Informes legacy que comparten el modal fullscreen de carga (dashboard_detail.html). */
  const usesReportsQueryLoadingModal = (slug) => {
    if (!slug) return false;
    if (
      slug === "stock-existencias" ||
      slug === "cash_flow_detailed_movements" ||
      slug === "bo-stock-facturacion" ||
      slug === "ventas-objetivos-vs-bo" ||
      slug === "ventas-por-vendedor" ||
      slug === "ventas-por-articulo" ||
      slug === "ventas-marcas-mensual"
    ) {
      return true;
    }
    if (isVentasNetasSlug(slug)) return true;
    if (isLogisticaListaComprobantesRutasSlug(slug)) return true;
    return false;
  };

  const REPORTS_QUERY_LOADING_LABELS = {
    "stock-existencias": {
      title: "Cargando stock y existencias",
      subtitle: "Consultando la base y preparando la tabla con el resultado completo…",
    },
    "bo-stock-facturacion": {
      title: "Cargando Backorder vs stock vs facturación",
      subtitle: "Procesando datos del informe BO (puede tardar en bases grandes)…",
    },
    "ventas-objetivos-vs-bo": {
      title: "Cargando objetivos de ventas vs BO",
      subtitle: "Sincronizando facturación, remitos y backorder…",
    },
    "ventas-por-vendedor": {
      title: "Cargando ventas por vendedor",
      subtitle: "Consultando facturación y jerarquía (puede tardar en bases grandes)…",
    },
    "ventas-por-articulo": {
      title: "Cargando ventas por artículo",
      subtitle: "Consultando facturación por artículo, proveedor y cliente…",
    },
    "ventas-marcas-mensual": {
      title: "Cargando ventas marcas mensual",
      subtitle: "Consultando matriz vendedor × cliente por mes…",
    },
    ventas_netas: {
      title: "Cargando ventas netas",
      subtitle: "Procesando el dashboard de ventas…",
    },
    "ventas-netas": {
      title: "Cargando ventas netas",
      subtitle: "Procesando el dashboard de ventas…",
    },
    "comprobantes-rutas": {
      title: "Cargando comprobantes en ruta",
      subtitle: "Consultando remitos y preparando la tabla…",
    },
    "mayoristapp-lista-comprobantes-rutas": {
      title: "Cargando comprobantes en ruta",
      subtitle: "Consultando remitos y preparando la tabla…",
    },
  };

  /** Muestra el modal fullscreen de carga. `labelsOverride` permite título/subtítulo distintos (p. ej. orden local en stock-existencias). */
  const showReportsQueryLoadingModal = (slug, labelsOverride = null) => {
    const el = document.getElementById("reports-legacy-query-loading-modal");
    if (!el) return;
    const defaults = { title: "Cargando datos", subtitle: "Espera un momento…" };
    const base = (slug && REPORTS_QUERY_LOADING_LABELS[slug]) || defaults;
    const labels = labelsOverride
      ? {
          title: labelsOverride.title ?? base.title,
          subtitle: labelsOverride.subtitle ?? base.subtitle,
        }
      : base;
    const titleEl = document.getElementById("reports-query-loading-title");
    const subEl = document.getElementById("reports-query-loading-subtitle");
    if (titleEl) titleEl.textContent = labels.title;
    if (subEl) subEl.textContent = labels.subtitle;
    el.classList.remove("hidden");
    el.classList.add("flex", "items-center", "justify-center");
    el.setAttribute("aria-hidden", "false");
    el.setAttribute("aria-busy", "true");
  };

  const hideReportsQueryLoadingModal = () => {
    const el = document.getElementById("reports-legacy-query-loading-modal");
    if (!el) return;
    el.classList.remove("flex", "items-center", "justify-center");
    el.classList.add("hidden");
    el.setAttribute("aria-hidden", "true");
    el.setAttribute("aria-busy", "false");
  };

  let fetchDashboardDataInFlight = false;
  /** Si llega otra petición mientras hay fetch en curso, se reprograma una al terminar (evita perder refetch tras cargar opciones async, p. ej. rutas en logística). */
  let fetchDashboardDataPending = false;
  const FETCH_TIMEOUT_MS = 120000; // 2 min para reportes pesados (ej. BO con administranet89)
  /** 5 min: informes BO y stock paginado (cargas largas con agrupación). */
  const EXTENDED_REPORT_FETCH_TIMEOUT_MS = 300000;
  /** Movimientos detallados de caja: traer todos los registros del período. */
  const CASH_FLOW_DETAILED_MOVEMENTS_API_LIMIT = 10000;

  const usesExtendedQueryTimeout = (slug) =>
    slug === "stock-existencias" ||
    slug === "cash_flow_detailed_movements" ||
    slug === "bo-stock-facturacion" ||
    slug === "ventas-objetivos-vs-bo" ||
    slug === "ventas-por-vendedor" ||
    slug === "ventas-por-articulo" ||
    slug === "ventas-marcas-mensual" ||
    isLogisticaListaComprobantesRutasSlug(slug);

  const fetchDashboardData = async (isAutoRefresh = false) => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    const apiUrl = dashboardRoot?.dataset?.dashboardUrl;
    if (!reportSlug || !apiUrl) {
      return;
    }
    if (fetchDashboardDataInFlight) {
      fetchDashboardDataPending = true;
      return;
    }
    fetchDashboardDataInFlight = true;
    const controller = new AbortController();
    const fetchTimeoutMs = usesExtendedQueryTimeout(reportSlug)
      ? EXTENDED_REPORT_FETCH_TIMEOUT_MS
      : FETCH_TIMEOUT_MS;
    const timeoutId = setTimeout(() => controller.abort(), fetchTimeoutMs);
    try {
      if (usesReportsQueryLoadingModal(reportSlug)) {
        showReportsQueryLoadingModal(reportSlug);
      }
      // Solo mostrar animación de carga si no es una actualización automática
      if (!isAutoRefresh) {
        showLoadingAnimation();
      }
      
      const filters =
        reportSlug === "stock-existencias"
          ? enrichStockExistenciasFilters(getFilters())
          : getFilters();

      if (isVentasMarcasMensualSlug(reportSlug)) {
        const cmpErr =
          window.ventasMarcasMensualHandler &&
          typeof window.ventasMarcasMensualHandler.validateCompareFilters === "function"
            ? window.ventasMarcasMensualHandler.validateCompareFilters(filters)
            : "";
        if (cmpErr) {
          if (!isAutoRefresh) {
            if (typeof window.ventasMarcasMensualHandler?.showSynapAviso === "function") {
              window.ventasMarcasMensualHandler.showSynapAviso(cmpErr, "error");
            } else {
              toast(cmpErr, "error");
            }
          }
          hideReportsQueryLoadingModal();
          if (!isAutoRefresh) hideLoadingAnimation();
          fetchDashboardDataInFlight = false;
          return;
        }
      }

      const queryLimit =
        reportSlug === "stock-existencias"
          ? stockExistenciasNeedsFullFetch()
            ? STOCK_EXISTENCIAS_FULL_LIMIT
            : STOCK_EXISTENCIAS_PAGE_SIZE
          : reportSlug === "cash_flow_detailed_movements"
            ? CASH_FLOW_DETAILED_MOVEMENTS_API_LIMIT
            : 200;

      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          slug: reportSlug,
          limit: queryLimit,
          offset: reportSlug === "stock-existencias" ? 0 : 0,
          filters: filters,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        let errorMessage = "Error al cargar los datos del dashboard";
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorData.error || errorMessage;
          if (errorData.error_type) {
            errorMessage += ` (${errorData.error_type})`;
          }
        } catch (e) {
          // Si no se puede parsear el JSON, usar el mensaje por defecto
        }
        console.error("Error response:", response.status, errorMessage);
        throw new Error(errorMessage);
      }

      const payload = await response.json();
      
      // Guardar filtros después de obtener datos exitosamente
      saveFilters();
      
      // Ocultar animación de carga antes de renderizar
      if (!isAutoRefresh) {
        hideLoadingAnimation();
      }
      
      // Pequeño delay para suavizar la transición
      setTimeout(() => {
        const currentReportSlug = dashboardRoot?.dataset?.reportSlug;
        // La matriz VMM tiene sus propios KPIs. Evitar que el resumen genérico
        // pueda fallar antes de que su handler procese la respuesta y cierre
        // el modal de carga.
        if (!isVentasMarcasMensualSlug(currentReportSlug)) {
          renderSummary(payload.meta || {}, payload.totals || {});
        }
        let hasErrorNote = false;
        
        if (currentReportSlug === "cash_flow_by_account") {
          const tableContent = document.getElementById("by-account-table-content");
          if (tableContent) {
            renderByAccountTable(payload.data || [], payload.totals || {}, tableContent);
          }
        } else if (currentReportSlug === "bo-stock-facturacion") {
          try {
            console.log("[dashboard.js] Procesando respuesta para bo-stock-facturacion:", payload);
            const boResponse = {
              data: payload.data || [],
              totals: payload.totals || {},
              meta: payload.meta || {},
              notes: payload.notes || []
            };
            const filtersApplied = (payload.meta && payload.meta.filters_applied) ? payload.meta.filters_applied : {};
            const boFiltersSummaryEl = document.getElementById("bo-filters-summary");
            if (boFiltersSummaryEl) {
              const parts = [];
              if (filtersApplied.lista_precio_label) parts.push("Lista de precio: " + filtersApplied.lista_precio_label);
              if (filtersApplied.sucursales && filtersApplied.sucursales.length) parts.push(filtersApplied.sucursales.length + " sucursal(es)");
              if (filtersApplied.depositos_incluidos && filtersApplied.depositos_incluidos.length) parts.push(filtersApplied.depositos_incluidos.length + " depósito(s) incluidos");
              if (filtersApplied.clientes_excluidos && filtersApplied.clientes_excluidos.length) parts.push(filtersApplied.clientes_excluidos.length + " cliente(s) excluidos");
              boFiltersSummaryEl.textContent = parts.length ? "Filtros: " + parts.join(" · ") : "";
            }
            if (window.boStockFacturacionHandler && typeof window.boStockFacturacionHandler.processData === 'function') {
              window.boStockFacturacionHandler.processData(boResponse);
            }
            document.dispatchEvent(new CustomEvent('reportDataLoaded', {
              detail: { slug: 'bo-stock-facturacion', response: boResponse }
            }));
            const errNote = (payload.notes || []).find(n => /error|tiempo|timeout|interrupted|max_execution|superó/i.test(String(n)));
            if (errNote) {
              hasErrorNote = true;
              if (!isAutoRefresh) toast(errNote, "error");
            }
          } finally {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                hideReportsQueryLoadingModal();
              });
            });
          }
        } else if (isVentasMarcasMensualSlug(currentReportSlug)) {
          try {
            const vmmResponse = {
              data: payload.data || [],
              totals: payload.totals || {},
              meta: payload.meta || {},
              notes: payload.notes || [],
            };
            if (
              window.ventasMarcasMensualHandler &&
              typeof window.ventasMarcasMensualHandler.processData === "function"
            ) {
              window.ventasMarcasMensualHandler.processData(vmmResponse);
            } else {
              console.error(
                "[dashboard] ventasMarcasMensualHandler no está definido; ¿cargó ventas_marcas_mensual.js?"
              );
            }
            document.dispatchEvent(
              new CustomEvent("reportDataLoaded", {
                detail: { slug: currentReportSlug, response: vmmResponse },
              })
            );
            const errNoteVmm = (payload.notes || []).find((n) =>
              /error|tiempo|timeout|interrupted|max_execution|superó/i.test(String(n))
            );
            if (errNoteVmm) {
              hasErrorNote = true;
              if (!isAutoRefresh) toast(errNoteVmm, "error");
            }
          } finally {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                hideReportsQueryLoadingModal();
              });
            });
          }
        } else if (isJerarquiaVentasBoFamiliaSlug(currentReportSlug)) {
          try {
            const voResponse = {
              data: payload.data || [],
              totals: payload.totals || {},
              meta: payload.meta || {},
              notes: payload.notes || []
            };
            const filtersApplied = (payload.meta && payload.meta.filters_applied) ? payload.meta.filters_applied : {};
            const voFiltersSummaryEl = document.getElementById("vo-filters-summary");
            if (voFiltersSummaryEl) {
              const parts = [];
              if (filtersApplied.lista_precio_label) {
                parts.push("Lista de precio: " + filtersApplied.lista_precio_label);
              } else if (filtersApplied.lista_precio !== undefined && filtersApplied.lista_precio !== null) {
                parts.push("Lista de precio: " + String(filtersApplied.lista_precio));
              }
              if (filtersApplied.sucursales && filtersApplied.sucursales.length) parts.push(filtersApplied.sucursales.length + " sucursal(es)");
              if (filtersApplied.depositos_incluidos && filtersApplied.depositos_incluidos.length) parts.push(filtersApplied.depositos_incluidos.length + " depósito(s) incluidos");
              if (filtersApplied.clientes_excluidos && filtersApplied.clientes_excluidos.length) parts.push(filtersApplied.clientes_excluidos.length + " cliente(s) excluidos");
              if (filtersApplied.vendedores_excluidos && filtersApplied.vendedores_excluidos.length) {
                parts.push(filtersApplied.vendedores_excluidos.length + " vendedor(es) excluidos");
              }
              voFiltersSummaryEl.textContent = parts.length ? "Filtros: " + parts.join(" · ") : "";
            }
            if (currentReportSlug === "ventas-por-articulo") {
              if (window.ventasPorArticuloHandler && typeof window.ventasPorArticuloHandler.processData === "function") {
                try {
                  window.ventasPorArticuloHandler.processData(voResponse);
                } catch (e) {
                  console.error("[dashboard] ventas por artículo processData:", e);
                }
              } else {
                console.error("[dashboard] ventasPorArticuloHandler no está definido; ¿cargó ventas_por_articulo.js?");
              }
            } else if (window.objetivosVentasBoHandler && typeof window.objetivosVentasBoHandler.processData === "function") {
              try {
                window.objetivosVentasBoHandler.processData(voResponse);
              } catch (e) {
                console.error("[dashboard] jerarquía ventas vendedor processData:", e);
              }
            } else {
              console.error("[dashboard] objetivosVentasBoHandler no está definido; ¿cargó objetivos_ventas_bo.js?");
            }
            document.dispatchEvent(new CustomEvent("reportDataLoaded", {
              detail: { slug: currentReportSlug, response: voResponse }
            }));
            const errNoteVo = (payload.notes || []).find(n => /error|tiempo|timeout|interrupted|max_execution|superó/i.test(String(n)));
            if (errNoteVo) {
              hasErrorNote = true;
              if (!isAutoRefresh) toast(errNoteVo, "error");
            }
          } finally {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                hideReportsQueryLoadingModal();
              });
            });
          }
        } else if (currentReportSlug === "stock-existencias") {
          try {
            renderStockExistenciasTable(payload);
          } finally {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                hideReportsQueryLoadingModal();
              });
            });
          }
          const errNoteSe = (payload.notes || []).find(n => /error|tiempo|timeout|interrupted|max_execution|superó/i.test(String(n)));
          if (errNoteSe) {
            hasErrorNote = true;
            if (!isAutoRefresh) toast(errNoteSe, "error");
          }
        } else if (currentReportSlug === "cash_flow_detailed_movements") {
          try {
            if (window.cashFlowDetailedMovementsHandler?.processData) {
              window.cashFlowDetailedMovementsHandler.processData(payload);
            }
            renderSummary(payload.meta || {}, payload.totals || {});
          } finally {
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                hideReportsQueryLoadingModal();
              });
            });
          }
          const errNoteCfdm = (payload.notes || []).find((n) =>
            /error|tiempo|timeout|interrupted|max_execution|superó/i.test(String(n))
          );
          if (errNoteCfdm) {
            hasErrorNote = true;
            if (!isAutoRefresh) toast(errNoteCfdm, "error");
          }
        } else {
          try {
            renderWidgets(payload);
            if (currentReportSlug === "cash_flow_waterfall" && typeof window.fetchDetailedMovements === "function") {
              window.fetchDetailedMovements();
            }
          } finally {
            if (usesReportsQueryLoadingModal(currentReportSlug)) {
              requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                  hideReportsQueryLoadingModal();
                });
              });
            }
          }
        }
        
        if (!isAutoRefresh && !hasErrorNote && !usesReportsQueryLoadingModal(currentReportSlug)) {
          toast("Datos del dashboard actualizados");
        }
      }, 100);
    } catch (error) {
      if (!isAutoRefresh) {
        hideLoadingAnimation();
      }
      if (usesReportsQueryLoadingModal(reportSlug)) {
        hideReportsQueryLoadingModal();
      }
      console.error("Error en fetchDashboardData:", error);
      let errorMsg = error.message || "Error al sincronizar datos";
      if (error.name === "AbortError") {
        errorMsg = "Tiempo de espera agotado. El reporte tarda demasiado (base de datos grande o consultas lentas). Pruebe un período más corto o filtros.";
      }
      // VMM: no dejar KPIs/matriz en "Cargando..." si el fetch falla.
      if (
        isVentasMarcasMensualSlug(reportSlug) &&
        window.ventasMarcasMensualHandler &&
        typeof window.ventasMarcasMensualHandler.processData === "function"
      ) {
        window.ventasMarcasMensualHandler.processData({
          data: [],
          totals: {},
          meta: {
            extra: {
              modo_unidades: "packs",
              meses: [],
              kpis: {
                unidades: 0,
                facturacion: 0,
                precio_medio: 0,
                regalias: 0,
                regalias_tc: 0,
              },
              filas: [],
            },
          },
          notes: [errorMsg],
        });
      }
      if (!isAutoRefresh) {
        toast(errorMsg, "error");
      }
    } finally {
      clearTimeout(timeoutId);
      fetchDashboardDataInFlight = false;
      if (fetchDashboardDataPending) {
        fetchDashboardDataPending = false;
        void fetchDashboardData(isAutoRefresh);
      }
    }
  };

  // Exponer para que el template (tags filter) pueda recargar datos en reportes legacy
  window.fetchDashboardData = fetchDashboardData;

  window.addEventListener("orientationchange", () => {
    showWorkspace(workspaceState.current);
  });

  // Configurar botón de autoactualizar
  const refreshButton = document.querySelector("[data-refresh-dashboard]");
  if (refreshButton) {
    // Remover listeners anteriores si existen para evitar duplicados
    const newRefreshButton = refreshButton.cloneNode(true);
    refreshButton.parentNode.replaceChild(newRefreshButton, refreshButton);
    newRefreshButton.addEventListener("click", () => {
      fetchDashboardData();
    });
  }

  // Configurar botón de tiempo real
  const initializeRealtime = () => {
    const realtimeButton = document.querySelector("[data-realtime-toggle]");
    if (!realtimeButton) return;

    // Obtener refresh_interval del filtro o del reporte desde el DOM (usar función global si está disponible)
    const getCurrentRefreshInterval = () => {
      if (typeof getCurrentRefreshIntervalValue === 'function') {
        return getCurrentRefreshIntervalValue();
      }
      // Fallback
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect && refreshIntervalSelect.value) {
        return refreshIntervalSelect.value;
      }
      return dashboardRoot?.dataset.reportRefreshInterval || "interval_10m"; // Valor declarativo por defecto
    };
    
    // Calcular intervalo en milisegundos (usar función global si está disponible)
    const getRefreshIntervalMsLocal = (interval) => {
      if (typeof getRefreshIntervalMs === 'function') {
        return getRefreshIntervalMs(interval);
      }
      // Fallback
      switch (interval) {
        case "interval_30s":
        case "realtime":
          return 30000; // 30 segundos
        case "interval_5m":
        case "hourly":
          return 300000; // 5 minutos
        case "interval_10m":
        case "daily":
          return 600000; // 10 minutos
        case "interval_1h":
        case "weekly":
          return 3600000; // 1 hora
        case "interval_2h":
        case "monthly":
          return 7200000; // 2 horas
        default:
          return 600000; // 10 minutos por defecto
      }
    };

    const startRealtime = (intervalMs) => {
      stopRealtime(); // Asegurar que no hay intervalos duplicados
      realtimeInterval = setInterval(() => {
        fetchDashboardData(true); // Pasar true para indicar que es auto-refresh
      }, intervalMs);
    };

    const stopRealtime = () => {
      if (realtimeInterval) {
        clearInterval(realtimeInterval);
        realtimeInterval = null;
      }
    };

    // Mismo comportamiento y estilo que pedidos-pendientes (declarativos): emerald cuando activo, rose cuando inactivo, "Detener tiempo real" / "Tiempo real"
    const updateRealtimeUI = (active) => {
      const label = realtimeButton.querySelector("[data-realtime-label]");
      const indicator = realtimeButton.querySelector("[data-realtime-indicator]");
      const icon = realtimeButton.querySelector("[data-realtime-icon]");
      if (active) {
        realtimeButton.classList.remove("text-slate-600", "dark:text-slate-400", "bg-slate-100", "dark:bg-slate-800", "hover:bg-slate-200", "dark:hover:bg-slate-700", "border-slate-300", "dark:border-slate-600", "text-rose-600", "dark:text-rose-400", "bg-rose-50", "dark:bg-rose-900/20", "hover:bg-rose-100", "dark:hover:bg-rose-900/30", "border-rose-300", "dark:border-rose-700");
        realtimeButton.classList.add("text-emerald-700", "dark:text-emerald-400", "bg-emerald-50", "dark:bg-emerald-900/20", "hover:bg-emerald-100", "dark:hover:bg-emerald-900/30", "border-emerald-300", "dark:border-emerald-700", "border");
        if (indicator) {
          indicator.classList.remove("opacity-0");
          indicator.classList.add("bg-emerald-500", "dark:bg-emerald-400");
          indicator.classList.remove("bg-rose-500", "dark:bg-rose-400");
        }
        if (label) label.textContent = "Detener tiempo real";
        if (icon) {
          icon.innerHTML = '<path d="M6 6h12v12H6z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
          icon.classList.remove("text-rose-600", "dark:text-rose-400");
          icon.classList.add("text-emerald-600", "dark:text-emerald-400");
        }
      } else {
        realtimeButton.classList.remove("text-emerald-700", "dark:text-emerald-400", "bg-emerald-50", "dark:bg-emerald-900/20", "hover:bg-emerald-100", "dark:hover:bg-emerald-900/30", "border-emerald-300", "dark:border-emerald-700", "text-slate-600", "dark:text-slate-400", "bg-slate-100", "dark:bg-slate-800", "hover:bg-slate-200", "dark:hover:bg-slate-700", "border-slate-300", "dark:border-slate-600");
        realtimeButton.classList.add("text-rose-600", "dark:text-rose-400", "bg-rose-50", "dark:bg-rose-900/20", "hover:bg-rose-100", "dark:hover:bg-rose-900/30", "border-rose-300", "dark:border-rose-700", "border");
        if (indicator) {
          indicator.classList.add("opacity-0");
          indicator.classList.add("bg-rose-500", "dark:bg-rose-400");
          indicator.classList.remove("bg-emerald-500", "dark:bg-emerald-400");
        }
        if (label) label.textContent = "Tiempo real";
        if (icon) {
          icon.innerHTML = '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
          icon.classList.remove("text-emerald-600", "dark:text-emerald-400");
          icon.classList.add("text-rose-600", "dark:text-rose-400");
        }
      }
      realtimeButton.setAttribute("data-realtime-active", String(active));
    };

    // Cargar estado guardado (misma clave que pedidos-pendientes/declarativos: workspace_realtime_${reportSlug})
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    const realtimeStorageKey = reportSlug ? `workspace_realtime_${reportSlug}` : null;
    if (reportSlug) {
      const savedRealtimeState = realtimeStorageKey ? localStorage.getItem(realtimeStorageKey) : null;
      if (savedRealtimeState === "true") {
        realtimeActive = true;
        updateRealtimeUI(true);
        const currentInterval = getCurrentRefreshInterval();
        startRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
      } else {
        realtimeActive = false;
        updateRealtimeUI(false);
      }
    } else {
      realtimeActive = false;
      updateRealtimeUI(false);
    }

    const toggleRealtime = () => {
      realtimeActive = !realtimeActive;
      if (realtimeActive) {
        const currentInterval = getCurrentRefreshInterval();
        startRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
        if (realtimeStorageKey) localStorage.setItem(realtimeStorageKey, "true");
      } else {
        stopRealtime();
        if (realtimeStorageKey) localStorage.setItem(realtimeStorageKey, "false");
      }
      updateRealtimeUI(realtimeActive);
    };

    // Escuchar cambios en el select de refresh_interval para actualizar el intervalo si tiempo real está activo
    const refreshIntervalSelect = document.getElementById("refresh_interval");
    if (refreshIntervalSelect) {
      refreshIntervalSelect.addEventListener("change", () => {
        if (realtimeActive) {
          const currentInterval = getCurrentRefreshInterval();
          startRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
          // Guardar filtros para persistir el cambio
          saveFilters();
        } else {
          // Guardar filtros aunque no esté activo el tiempo real
          saveFilters();
        }
      });
    }

    realtimeButton.addEventListener("click", toggleRealtime);
    
    // Limpiar intervalo al salir de la página
    window.addEventListener("beforeunload", () => {
      stopRealtime();
    });
  };

  initializeRealtime();
  
  // Configurar botón de exportación a Excel
  const exportButton = document.querySelector("[data-export-excel]");
  if (exportButton) {
    const newExportButton = exportButton.cloneNode(true);
    exportButton.parentNode.replaceChild(newExportButton, exportButton);
    const EXPORT_SCOPE_DROPDOWN_ID = "reports-export-scope-dropdown";

    function closeExportScopeDropdown() {
      const el = document.getElementById(EXPORT_SCOPE_DROPDOWN_ID);
      if (el) el.remove();
    }

    function createExportScopeDropdown(onPick) {
      closeExportScopeDropdown();
      const rect = newExportButton.getBoundingClientRect();
      const menu = document.createElement("div");
      menu.id = EXPORT_SCOPE_DROPDOWN_ID;
      menu.className =
        "fixed z-[10000] min-w-[11rem] rounded-lg border border-slate-200 bg-white p-1 shadow-xl dark:border-slate-700 dark:bg-slate-800";
      menu.style.top = `${Math.round(rect.bottom + 6)}px`;
      menu.style.left = `${Math.round(rect.left)}px`;
      menu.innerHTML = `
        <button type="button" data-export-scope="resumen"
          class="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-100 dark:hover:bg-slate-700">
          Resumen
          <span class="text-[10px] text-slate-400 dark:text-slate-500">Hasta cliente</span>
        </button>
        <button type="button" data-export-scope="detallado"
          class="mt-1 flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-100 dark:hover:bg-slate-700">
          Detallado
          <span class="text-[10px] text-slate-400 dark:text-slate-500">Árbol completo</span>
        </button>
      `;
      menu.addEventListener("click", (ev) => {
        const btn = ev.target && ev.target.closest ? ev.target.closest("[data-export-scope]") : null;
        if (!btn) return;
        const scope = btn.getAttribute("data-export-scope");
        closeExportScopeDropdown();
        onPick(scope === "detallado" ? "detallado" : "resumen");
      });
      document.body.appendChild(menu);
      const onDocClick = (ev) => {
        if (menu.contains(ev.target) || newExportButton.contains(ev.target)) return;
        closeExportScopeDropdown();
        document.removeEventListener("mousedown", onDocClick);
      };
      document.addEventListener("mousedown", onDocClick);
    }

    async function performExcelExport(excelScope) {
      try {
        // Mostrar indicador de carga
        const originalContent = newExportButton.innerHTML;
        newExportButton.disabled = true;
        newExportButton.innerHTML = `
          <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">Exportando...</span>
        `;

        // Obtener filtros actuales
        const reportSlug = dashboardRoot?.dataset.reportSlug;
        if (!reportSlug) {
          throw new Error("No se pudo determinar el reporte");
        }

        // Construir filtros desde el DOM
        const filters = {};
        const filtersContainer = document.querySelector("[data-filters-container]");

        if (filtersContainer) {
          // Obtener fechas
          const fechaInicioInput = filtersContainer.querySelector('input[name="fecha_inicio"]');
          const fechaFinInput = filtersContainer.querySelector('input[name="fecha_fin"]');

          if (fechaInicioInput && fechaInicioInput.value) {
            filters.fecha_inicio = fechaInicioInput.value;
          }
          if (fechaFinInput && fechaFinInput.value) {
            filters.fecha_fin = fechaFinInput.value;
          }

          // Obtener período tipo
          const periodoTipoBtn = filtersContainer.querySelector('.periodo-tipo-btn.active');
          if (periodoTipoBtn) {
            const periodo = periodoTipoBtn.dataset.periodo;
            if (periodo === 'dia_actual') {
              filters.dia_actual = true;
            } else if (periodo === 'mes_actual') {
              filters.mes_actual = true;
            } else if (periodo === 'año_actual') {
              filters.año_actual = true;
            }
          }

          // Obtener otros filtros según el reporte
          if (isVentasNetasSlug(reportSlug) || reportSlug === 'uninvoiced_remitos' || reportSlug === 'total-consolidado-operativo' || isInformeBoDualPeriodo(reportSlug)) {
            const puntoVentaSelect = filtersContainer.querySelector('select[name="punto_venta"]');
            const sucursalesSelect = filtersContainer.querySelector('select[name="sucursales"]');

            if (puntoVentaSelect && puntoVentaSelect.value) {
              filters.punto_venta = Array.from(puntoVentaSelect.selectedOptions).map(opt => opt.value);
            }
            if (sucursalesSelect && sucursalesSelect.value) {
              filters.sucursales = Array.from(sucursalesSelect.selectedOptions).map(opt => opt.value);
            }
            if (isInformeBoDualPeriodo(reportSlug)) {
              const depositosIncluidosSelect = filtersContainer.querySelector('select[name="depositos_incluidos"]');
              const clientesExcluidosSelect = filtersContainer.querySelector('select[name="clientes_excluidos"]');
              const listaPrecioSelect = filtersContainer.querySelector('select[name="lista_precio"]');
              const fif = filtersContainer.querySelector('input[name="fecha_inicio_facturacion"]');
              const fff = filtersContainer.querySelector('input[name="fecha_fin_facturacion"]');
              const ptf = filtersContainer.querySelector('#periodo_tipo_facturacion');
              if (fif && fif.value) filters.fecha_inicio_facturacion = fif.value;
              if (fff && fff.value) filters.fecha_fin_facturacion = fff.value;
              if (ptf && ptf.value) filters.periodo_tipo_facturacion = ptf.value;
              if (depositosIncluidosSelect && depositosIncluidosSelect.selectedOptions.length) {
                filters.depositos_incluidos = Array.from(depositosIncluidosSelect.selectedOptions).map(opt => String(opt.value)).filter(v => v);
              }
              if (clientesExcluidosSelect && clientesExcluidosSelect.selectedOptions.length) {
                filters.clientes_excluidos = Array.from(clientesExcluidosSelect.selectedOptions).map(opt => String(opt.value)).filter(v => v);
              }
              if (isInformeVentasMarcasFamiliaSlug(reportSlug)) {
                const vendedoresExcluidosSelect = filtersContainer.querySelector('select[name="vendedores_excluidos"]');
                if (vendedoresExcluidosSelect && vendedoresExcluidosSelect.selectedOptions.length) {
                  filters.vendedores_excluidos = Array.from(vendedoresExcluidosSelect.selectedOptions)
                    .map((opt) => String(opt.value))
                    .filter((v) => v);
                }
                const clientesIncluirSelect = filtersContainer.querySelector('select[name="clientes_incluir"]');
                if (clientesIncluirSelect && clientesIncluirSelect.selectedOptions.length) {
                  filters.clientes_incluir = Array.from(clientesIncluirSelect.selectedOptions)
                    .map((opt) => String(opt.value))
                    .filter((v) => v);
                }
                const vendedoresIncluirSelect = filtersContainer.querySelector('select[name="vendedores_incluir"]');
                if (vendedoresIncluirSelect && vendedoresIncluirSelect.selectedOptions.length) {
                  filters.vendedores_incluir = Array.from(vendedoresIncluirSelect.selectedOptions)
                    .map((opt) => String(opt.value))
                    .filter((v) => v);
                }
                const ordenarPorSelect = filtersContainer.querySelector("#ordenar_por");
                const ordenFormaSelect = filtersContainer.querySelector("#orden_forma");
                const sortFilters = normalizeJerarquiaSortFilters(
                  reportSlug,
                  ordenarPorSelect?.value,
                  ordenFormaSelect?.value
                );
                filters.ordenar_por = sortFilters.ordenarPor;
                filters.orden_forma = sortFilters.ordenForma;
              }
              if (listaPrecioSelect && listaPrecioSelect.value !== "" && listaPrecioSelect.value !== undefined) {
                const lp = parseInt(listaPrecioSelect.value, 10);
                if (!Number.isNaN(lp)) filters.lista_precio = lp;
              }
              if (reportSlug === "ventas-objetivos-vs-bo") {
                const rubVo = filtersContainer.querySelector('select[name="rubros_incluidos"]');
                const subVo = filtersContainer.querySelector('select[name="subrubros_incluidos"]');
                if (rubVo && rubVo.selectedOptions.length) {
                  filters.rubros_incluidos = Array.from(rubVo.selectedOptions)
                    .map((opt) => String(opt.value))
                    .filter((v) => v);
                }
                if (subVo && subVo.selectedOptions.length) {
                  filters.subrubros_incluidos = Array.from(subVo.selectedOptions)
                    .map((opt) => String(opt.value))
                    .filter((v) => v);
                }
              }
              if (isVentasCatalogoFiltersSlug(reportSlug)) {
                VPA_CATALOG_FILTER_SPECS.forEach(([selectId, key]) => {
                  const sel = filtersContainer.querySelector(`select[name="${key}"]`);
                  if (sel && sel.selectedOptions.length) {
                    filters[key] = Array.from(sel.selectedOptions)
                      .map((opt) => String(opt.value))
                      .filter((v) => v);
                  }
                });
              }
            }
          }

          if (reportSlug === 'comprobantes-rutas' || reportSlug === 'mayoristapp-lista-comprobantes-rutas') {
            const est = filtersContainer.querySelector('#logistica_estado_entrega');
            if (est) {
              const estVals = Array.from(est.selectedOptions)
                .map((o) => String(o.value).trim())
                .filter((v) => v === 'Si' || v === 'No');
              if (estVals.length === 1) {
                filters.logistica_estado_entrega = estVals[0];
              }
            }
            const cliSel = filtersContainer.querySelector('#logistica_id_cliente');
            if (cliSel) {
              const opts = Array.from(cliSel.selectedOptions)
                .map((o) => ({
                  id: String(o.value).trim(),
                  text: String(o.textContent || "").trim(),
                }))
                .filter((o) => o.id);
              if (opts.length === 1) {
                filters.logistica_id_cliente = opts[0].id;
                filters.logistica_cliente_label = opts[0].text || opts[0].id;
              } else if (opts.length > 1) {
                filters.logistica_id_cliente = opts.map((o) => o.id);
                filters.logistica_cliente_etiquetas = Object.fromEntries(
                  opts.map((o) => [o.id, o.text || o.id]),
                );
              }
            }
          }
        }

        if (excelScope && isJerarquiaVentasBoFamiliaSlug(reportSlug)) {
          filters.excel_scope = excelScope;
        }

        if (
          (reportSlug === "cash_flow_detailed_movements" ||
            reportSlug === "cash_flow_waterfall" ||
            reportSlug === "cash_flow_by_account") &&
          typeof window.getFilters === "function"
        ) {
          Object.assign(filters, window.getFilters());
        }

        if (reportSlug === "ventas-marcas-mensual" && typeof window.getFilters === "function") {
          Object.assign(filters, window.getFilters());
        }

        const baseEmpresa = dashboardRoot?.dataset.baseEmpresa || null;

        // Construir payload
        const payload = {
          slug: reportSlug,
          filters: filters,
          base_empresa: baseEmpresa,
        };

        // Llamar a la API de exportación
        const apiUrl = `/api/reports/export/?type=xlsx`;
        const response = await fetch(apiUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify(payload),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: "Error al exportar el reporte" }));
          throw new Error(errorData.detail || "Error al exportar el reporte");
        }

        // Descargar el archivo
        const blob = await response.blob();
        const dlName =
          response.headers.get("Content-Disposition")?.match(/filename="([^"]+)"/)?.[1] ||
          `${reportSlug}_${new Date().toISOString().split("T")[0]}.xlsx`;
        let downloaded = false;
        if (
          reportSlug === "ventas-marcas-mensual" &&
          typeof window.vmmDownloadExportBlob === "function"
        ) {
          downloaded = window.vmmDownloadExportBlob(blob, dlName);
        } else {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = dlName;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          downloaded = true;
        }
        if (!downloaded) {
          throw new Error("No se pudo iniciar la descarga del archivo Excel.");
        }

        // Mostrar mensaje de éxito
        const lbl = excelScope === "detallado" ? " (Detallado)" : excelScope === "resumen" ? " (Resumen)" : "";
        toast(`Reporte exportado exitosamente${lbl}`, "success");

        // Restaurar botón
        newExportButton.disabled = false;
        newExportButton.innerHTML = originalContent;
      } catch (error) {
        console.error("Error exportando reporte:", error);
        toast(`Error al exportar: ${error.message}`, "error");

        // Restaurar botón
        newExportButton.disabled = false;
        newExportButton.innerHTML = `
          <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 3v12m0 0l-4-4m4 4l4-4M3 21h18" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">Exportar Excel</span>
        `;
      }
    }

    newExportButton.addEventListener("click", async () => {
      const reportSlug = dashboardRoot?.dataset.reportSlug || "";
      if (isJerarquiaVentasBoFamiliaSlug(reportSlug)) {
        createExportScopeDropdown((scope) => {
          performExcelExport(scope);
        });
        return;
      }
      performExcelExport(null);
    });
  }
  
  // Inicializar tiempo real para workspace
  if (isWorkspaceMode) {
    // Para la vista TV, también inicializar tiempo real aunque no tenga los controles visibles
    // Esto asegura que use la misma configuración guardada en localStorage
    if (isWorkspaceTv) {
      // Inicializar tiempo real para TV usando la configuración guardada
      initializeWorkspaceRealtimeForTV();
    } else {
      // Para la vista normal, usar los controles visibles
      initializeWorkspaceRealtime();
      setupRefreshIntervalButtons();
    }
  }

  if (isWorkspaceMode) {
    fetchWorkspaceData();
  } else {
    const initialSlug = dashboardRoot?.dataset?.reportSlug;
    if (usesReportsQueryLoadingModal(initialSlug)) {
      showReportsQueryLoadingModal(initialSlug);
    }
    // Cargar opciones de filtros primero
    loadFilterOptions().then(() => {
      setupPeriodoTipo();
      setupBoDualPeriodoTipo();
      applyPeriodFromQueryParams();
      applyVentasObjetivosFacturacionFromQueryParams();
      setupRefreshIntervalButtons();
      setupCashFlowFilters();
      const slugAfterFilters = dashboardRoot?.dataset?.reportSlug;
      if (isInformeBoDualPeriodo(slugAfterFilters)) {
        const sinRecargaAutoPorFiltros = isInformeQuerySoloManualORealtime(slugAfterFilters);
        const lp = document.getElementById("lista_precio");
        if (lp && !lp.dataset.boListaPrecioWired) {
          lp.dataset.boListaPrecioWired = "1";
          lp.addEventListener("change", () => {
            if (sinRecargaAutoPorFiltros) {
              if (typeof saveFilters === "function") saveFilters();
              return;
            }
            if (typeof window.fetchDashboardData === "function") {
              window.fetchDashboardData();
            }
          });
        }
        const ordenarPor = document.getElementById("ordenar_por");
        if (ordenarPor && !ordenarPor.dataset.boOrdenarPorWired) {
          ordenarPor.dataset.boOrdenarPorWired = "1";
          ordenarPor.addEventListener("change", () => {
            if (typeof saveFilters === "function") {
              saveFilters();
            }
            if (sinRecargaAutoPorFiltros) return;
            if (typeof window.fetchDashboardData === "function") {
              window.fetchDashboardData();
            }
          });
        }
        const ordenForma = document.getElementById("orden_forma");
        if (ordenForma && !ordenForma.dataset.boOrdenFormaWired) {
          ordenForma.dataset.boOrdenFormaWired = "1";
          ordenForma.addEventListener("change", () => {
            if (typeof saveFilters === "function") {
              saveFilters();
            }
            if (sinRecargaAutoPorFiltros) return;
            if (typeof window.fetchDashboardData === "function") {
              window.fetchDashboardData();
            }
          });
        }
      }
      fetchDashboardData();
    }).catch((err) => {
      hideReportsQueryLoadingModal();
      console.error("[dashboard] Error cargando filtros iniciales:", err);
      toast("No se pudieron cargar filtros iniciales", "error");
    });
  }
}

// Función para actualizar el tema automáticamente según el horario
const updateThemeBasedOnTime = () => {
  const now = new Date();
  const hour = now.getHours();
  const html = document.documentElement;
  
  // Modo oscuro: entre las 18:00 (6 PM) y las 8:00 (8 AM)
  // Modo claro: entre las 8:00 (8 AM) y las 18:00 (6 PM)
  const shouldBeDark = hour >= 18 || hour < 8;
  const isCurrentlyDark = html.classList.contains('dark');
  
  // Solo actualizar si el cambio es necesario y no hay una preferencia manual guardada
  const manualTheme = localStorage.getItem('theme');
  if (manualTheme === 'dark' || manualTheme === 'light') {
    // Si hay una preferencia manual, respetarla y no cambiar automáticamente
    return;
  }
  
  if (shouldBeDark && !isCurrentlyDark) {
    html.classList.add('dark');
    // Re-renderizar gráficos para aplicar el nuevo tema
    reRenderAllCharts();
  } else if (!shouldBeDark && isCurrentlyDark) {
    html.classList.remove('dark');
    // Re-renderizar gráficos para aplicar el nuevo tema
    reRenderAllCharts();
  }
};

// Función para re-renderizar todos los gráficos cuando cambia el tema
const reRenderAllCharts = () => {
  const widgets = document.querySelectorAll('[data-widget-id]');
  widgets.forEach((widget) => {
    const widgetId = widget.dataset.widgetId;
    const cached = widgetDataCache.get(widgetId);
    if (cached && cached.data) {
      try {
        const config = cached.config || getWidgetConfig(widget);
        if (config) {
          renderWidgetChart(widget, cached.data, config, cached.meta || {});
        }
      } catch (error) {
        console.warn('Error re-rendering chart for widget', widgetId, error);
      }
    }
  });

  if (isWorkspaceMode && workspaceState.initialized) {
    const workspaceWidgets = document.querySelectorAll('[data-widget-wrapper]');
    workspaceWidgets.forEach((wrapper) => {
      const widget = wrapper.querySelector('[data-widget-id]');
      if (widget) {
        const cached = widgetDataCache.get(widget.dataset.widgetId);
        if (cached && cached.data) {
          try {
            const config = cached.config || getWidgetConfig(widget);
            if (config) {
              renderWidgetChart(widget, cached.data, config, cached.meta || {});
            }
          } catch (error) {
            console.warn('Error re-rendering workspace chart for widget', widget.dataset.widgetId, error);
          }
        }
      }
    });
  }
};

// Inicializar actualización automática del tema
if (dashboardRoot) {
  // Actualizar inmediatamente al cargar
  updateThemeBasedOnTime();
  
  // Actualizar cada minuto para detectar cambios de horario
  setInterval(updateThemeBasedOnTime, 60000); // 60000 ms = 1 minuto
}


