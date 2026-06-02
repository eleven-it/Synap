/**
 * Movimientos detallados de flujo de caja (informe cash_flow_detailed_movements)
 * y panel embebido en cash_flow_waterfall.
 */
(function () {
  "use strict";

  const SLUG_STANDALONE = "cash_flow_detailed_movements";
  const SLUG_WATERFALL = "cash_flow_waterfall";
  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== SLUG_STANDALONE && reportSlug !== SLUG_WATERFALL) {
    return;
  }
  const isStandalone = reportSlug === SLUG_STANDALONE;

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
        return new Intl.NumberFormat("es-AR", {
          style: "currency",
          currency: "ARS",
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }).format(n);
      } catch (e) {
        return `$${n.toFixed(2)}`;
      }
    }
    return value;
  };

  const isCurrencyField = (fieldName) => {
    const normalized = String(fieldName).toLowerCase().trim();
    if (normalized === "total_movimientos") return false;
    const currencyFields = [
      "ingreso", "egreso", "importe_neto", "monto", "importe", "saldo",
    ];
    return currencyFields.some((f) => normalized.includes(f));
  };

  const getCsrfToken = () => {
    if (typeof window.getCsrfToken === "function") return window.getCsrfToken();
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  };

  function formatDateForSummary(dateStr) {
    if (!dateStr) return "—";
    const p = String(dateStr).split("-");
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : dateStr;
  }

  function syncFiltersSummary(meta) {
    const el = document.getElementById("cf-detailed-movements-filters-summary");
    if (!el) return;
    const applied = (meta && meta.filters_applied) || {};
  const fi = applied.fecha_inicio || document.getElementById("fecha_inicio")?.value;
  const ff = applied.fecha_fin || document.getElementById("fecha_fin")?.value;
    const parts = [];
    if (fi && ff) parts.push(`Período: ${formatDateForSummary(fi)} al ${formatDateForSummary(ff)}`);
    if (applied.cajas && applied.cajas.length) {
      parts.push(`${applied.cajas.length} caja(s)`);
    }
    const n = (meta && meta.row_count) || (detailedMovementsState.data && detailedMovementsState.data.length);
    if (n) parts.push(`${n} movimiento(s)`);
    el.textContent = parts.join(" · ");
  }

  function showTableVisible() {
    const tableWrapper = document.querySelector("[data-detailed-movements-table-wrapper]");
    if (tableWrapper) tableWrapper.classList.remove("hidden");
    const cardsHost = document.querySelector("[data-detailed-movements-cards-host]");
    if (cardsHost && isNarrowCfViewport()) cardsHost.classList.remove("hidden");
  }

  function renderFromState(page, pageSize, groupByFields, searchQuery) {
    renderDetailedMovementsTable(
      detailedMovementsState.data,
      page || 1,
      pageSize || detailedMovementsState.pageSize || 50,
      groupByFields || detailedMovementsState.groupBy || [],
      searchQuery !== undefined ? searchQuery : detailedMovementsState.searchQuery || ""
    );
  }

  function processStandalonePayload(payload) {
    const section = document.getElementById("detailed-movements-section");
    if (!section) return;
    const rows = (payload && payload.data) || [];
    detailedMovementsState.data = rows;
    detailedMovementsState.totalItems = rows.length;
    syncFiltersSummary(payload.meta || {});
    if (!rows.length) {
      const host = document.querySelector("[data-detailed-movements-table-host]");
      if (host) {
        host.innerHTML = '<p class="text-sm text-slate-500 dark:text-slate-400 text-center py-8">No hay movimientos en el período seleccionado.</p>';
      }
      return;
    }
    showTableVisible();
    renderFromState(1, 50, [], "");
    setTimeout(() => {
      if (!detailedMovementsState.controlsInitialized) {
        setupDetailedMovementsControls();
        detailedMovementsState.controlsInitialized = true;
      }
    }, 100);
  }

// Estado de paginación y filtros para movimientos detallados
let detailedMovementsState = {
  data: [], // Datos originales
  filteredData: [], // Datos filtrados por búsqueda
  groupedData: [], // Datos agrupados
  currentPage: 1,
  pageSize: 50,
  totalItems: 0,
  searchQuery: "",
  groupBy: [], // Array de campos de agrupación
  searchSuggestions: [],
  controlsInitialized: false,
};

// Función para filtrar datos por búsqueda
const filterMovementsBySearch = (data, searchQuery) => {
  if (!searchQuery || searchQuery.length < 3) {
    return data;
  }
  
  const query = searchQuery.toLowerCase().trim();
  return data.filter(row => {
    // Buscar en múltiples campos
    const searchableFields = [
      row.contraparte || "",
      row.detalle || "",
      row.tipo_comprobante || "",
      row.nro_comprobante || "",
      row.medio_pago || "",
      row.flujo_tipo || "",
      row.flujo_subcategoria || "",
      row.caja_origen_nombre || "",
      row.caja_destino_nombre || "",
      row.nombre_sucursal || "",
    ];
    
    return searchableFields.some(field => 
      field.toLowerCase().includes(query)
    );
  });
};

// Función para generar sugerencias de búsqueda
const generateSearchSuggestions = (data, query) => {
  if (!query || query.length < 3) {
    return [];
  }
  
  const queryLower = query.toLowerCase();
  const suggestions = new Set();
  const maxSuggestions = 10;
  
  data.forEach(row => {
    // Sugerencias de clientes/proveedores
    if (row.contraparte && row.contraparte.toLowerCase().includes(queryLower)) {
      suggestions.add(row.contraparte);
    }
    // Sugerencias de detalles
    if (row.detalle && row.detalle.toLowerCase().includes(queryLower)) {
      const words = row.detalle.split(/\s+/).filter(w => w.toLowerCase().includes(queryLower));
      words.forEach(w => suggestions.add(w));
    }
    // Sugerencias de tipo de comprobante
    if (row.tipo_comprobante && row.tipo_comprobante.toLowerCase().includes(queryLower)) {
      suggestions.add(row.tipo_comprobante);
    }
    
    if (suggestions.size >= maxSuggestions) return;
  });
  
  return Array.from(suggestions).slice(0, maxSuggestions);
};

// Función para agrupar datos (soporta múltiples campos de agrupación)
const groupMovements = (data, groupByFields) => {
  if (!groupByFields || !Array.isArray(groupByFields) || groupByFields.length === 0 || !data || !data.length) {
    return data;
  }
  
  // Función recursiva para agrupar por múltiples niveles
  const groupByLevels = (items, fields, level = 0) => {
    if (level >= fields.length) {
      // Si no hay más niveles, retornar los items directamente como items finales
      return items.map(item => ({
        type: 'item',
        data: item,
      }));
    }
    
    const currentField = fields[level];
    const grouped = {};
    
    // Agrupar por el campo actual
    items.forEach(row => {
      const groupKey = row[currentField] || "Sin especificar";
      if (!grouped[groupKey]) {
        grouped[groupKey] = {
          groupKey,
          groupValue: groupKey,
          groupField: currentField,
          items: [], // Solo para calcular totales, no se usan en renderizado
          totals: {
            ingreso: 0,
            egreso: 0,
            importe_neto: 0,
            count: 0,
          }
        };
      }
      
      grouped[groupKey].items.push(row);
      grouped[groupKey].totals.ingreso += row.ingreso || 0;
      grouped[groupKey].totals.egreso += row.egreso || 0;
      grouped[groupKey].totals.importe_neto += row.importe_neto || 0;
      grouped[groupKey].totals.count += 1;
    });
    
    // Función para ordenar claves según el tipo de campo
    const sortKeys = (keys, fieldName) => {
      // Si el campo es "fecha", ordenar como fechas
      if (fieldName && (fieldName.toLowerCase() === 'fecha' || fieldName.toLowerCase().includes('fecha'))) {
        return keys.sort((a, b) => {
          // Intentar parsear fechas en formato DD/MM/YYYY
          const parseDate = (dateStr) => {
            if (!dateStr || dateStr === "Sin especificar") return new Date(0);
            // Intentar formato DD/MM/YYYY
            const parts = dateStr.split('/');
            if (parts.length === 3) {
              const day = parseInt(parts[0], 10);
              const month = parseInt(parts[1], 10);
              const year = parseInt(parts[2], 10);
              if (!isNaN(day) && !isNaN(month) && !isNaN(year)) {
                return new Date(year, month - 1, day);
              }
            }
            // Intentar formato YYYY-MM-DD
            const isoDate = new Date(dateStr);
            if (!isNaN(isoDate.getTime())) {
              return isoDate;
            }
            // Si no se puede parsear, retornar fecha mínima
            return new Date(0);
          };
          
          const dateA = parseDate(a);
          const dateB = parseDate(b);
          return dateA - dateB;
        });
      }
      // Para otros campos, ordenar alfabéticamente
      return keys.sort();
    };
    
    // Convertir a array y procesar cada grupo recursivamente
    const result = [];
    sortKeys(Object.keys(grouped), currentField).forEach(key => {
      const group = grouped[key];
      // Agrupar los items de este grupo por el siguiente nivel
      // Esto retornará grupos anidados o items finales
      const nestedGroups = groupByLevels(group.items, fields, level + 1);
      
      // Los items siempre están en los children (ya sean grupos o items finales)
      // Nunca mantener items directos en el grupo padre
      result.push({
        type: 'group',
        data: {
          ...group,
          items: [], // Siempre vacío - los items están en children
        },
        children: nestedGroups, // Contiene grupos anidados o items finales
      });
    });
    
    return result;
  };
  
  return groupByLevels(data, groupByFields);
};

function escCfText(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function isNarrowCfViewport() {
  return window.matchMedia("(max-width: 1023px)").matches;
}

function flattenCfGroupItems(item) {
  if (item.type === "item") return [item.data];
  const out = [];
  (item.children || []).forEach((ch) => {
    out.push(...flattenCfGroupItems(ch));
  });
  return out;
}

function movementCardHtml(row, flujoTranslations, subcategoriaTranslations) {
  const flujo = flujoTranslations[String(row.flujo_tipo || "").toLowerCase()] || row.flujo_tipo || "—";
  const sub = subcategoriaTranslations[String(row.flujo_subcategoria || "").toLowerCase()] || row.flujo_subcategoria || "—";
  const ing = row.ingreso != null && row.ingreso !== "" ? formatCurrency(row.ingreso) : null;
  const egr = row.egreso != null && row.egreso !== "" ? formatCurrency(row.egreso) : null;
  const neto = row.importe_neto != null && row.importe_neto !== "" ? formatCurrency(row.importe_neto) : "—";
  const netoNum = Number(row.importe_neto);
  const netoCls =
    netoNum > 0
      ? "text-emerald-700 dark:text-emerald-300"
      : netoNum < 0
        ? "text-red-700 dark:text-red-300"
        : "text-slate-700 dark:text-slate-200";
  return `
    <article class="rounded-xl border border-slate-200/90 bg-white/95 p-3 shadow-sm dark:border-slate-600 dark:bg-slate-900/80">
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0 flex-1">
          <p class="text-sm font-bold text-slate-900 dark:text-white">${escCfText(row.fecha || "—")} · ${escCfText(row.tipo_comprobante || "")} ${escCfText(row.nro_comprobante || "")}</p>
          <p class="mt-1 text-sm leading-snug text-slate-800 dark:text-slate-200">${escCfText(row.contraparte || row.detalle || "—")}</p>
          <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">${escCfText(flujo)} · ${escCfText(sub)}</p>
        </div>
        <p class="shrink-0 text-sm font-bold tabular-nums ${netoCls}">${neto}</p>
      </div>
      <dl class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
        ${ing ? `<div><dt class="inline font-medium">Ing.</dt> <dd class="inline tabular-nums text-emerald-700 dark:text-emerald-300">${ing}</dd></div>` : ""}
        ${egr ? `<div><dt class="inline font-medium">Egr.</dt> <dd class="inline tabular-nums text-red-700 dark:text-red-300">${egr}</dd></div>` : ""}
        ${row.medio_pago ? `<div><dt class="inline font-medium">Medio</dt> <dd class="inline">${escCfText(row.medio_pago)}</dd></div>` : ""}
        ${row.nombre_sucursal ? `<div><dt class="inline font-medium">Suc.</dt> <dd class="inline">${escCfText(row.nombre_sucursal)}</dd></div>` : ""}
      </dl>
    </article>`;
}

function groupSummaryCardHtml(group, headerTranslations) {
  const label = headerTranslations[group.groupField] || group.groupField;
  const value = group.groupValue || "Sin especificar";
  const ingCls = group.totals.ingreso > 0 ? "text-emerald-700 dark:text-emerald-300" : "";
  const egrCls = group.totals.egreso > 0 ? "text-red-700 dark:text-red-300" : "";
  return `
    <div class="rounded-xl border border-slate-300 bg-slate-100/90 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800/80">
      <p class="text-xs font-bold uppercase tracking-wide text-slate-700 dark:text-slate-200">${escCfText(label)}: <span class="font-normal normal-case">${escCfText(value)}</span></p>
      <p class="mt-1 text-[11px] leading-snug text-slate-600 dark:text-slate-400">
        ${group.totals.count} mov. ·
        <span class="${ingCls}">Ing. ${formatCurrency(group.totals.ingreso)}</span> ·
        <span class="${egrCls}">Egr. ${formatCurrency(group.totals.egreso)}</span> ·
        Neto ${formatCurrency(group.totals.importe_neto)}
      </p>
    </div>`;
}

function updateCfPaginationControls(page, pageSize, startIndex, endIndex, totalItemsForPagination, isGrouped) {
  const paginationInfo = document.getElementById("detailed-movements-pagination-info");
  const prevButton = document.getElementById("detailed-movements-prev");
  const nextButton = document.getElementById("detailed-movements-next");
  const pageSizeSelect = document.getElementById("detailed-movements-page-size");

  if (paginationInfo) {
    paginationInfo.textContent = `Mostrando ${startIndex + 1} - ${endIndex} de ${totalItemsForPagination} ${isGrouped ? "grupos" : "movimientos"}`;
  }
  if (prevButton) {
    prevButton.disabled = page === 1;
  }
  if (nextButton) {
    nextButton.disabled = endIndex >= totalItemsForPagination;
  }
  if (pageSizeSelect) {
    pageSizeSelect.value = pageSize;
  }
}

function renderDetailedMovementsMobile(
  paginatedData,
  {
    isGrouped,
    page,
    pageSize,
    groupByFields,
    searchQuery,
    data,
    startIndex,
    endIndex,
    totalItemsForPagination,
    headerTranslations,
    flujoTranslations,
    subcategoriaTranslations,
  },
) {
  const cardsHost = document.querySelector("[data-detailed-movements-cards-host]");
  const tableScroll = document.querySelector("[data-detailed-movements-table-scroll]");
  const tableWrapper = document.querySelector("[data-detailed-movements-table-host]");
  if (tableScroll) tableScroll.classList.add("hidden");
  if (tableWrapper) {
    const existingTable = tableWrapper.querySelector("table");
    if (existingTable) existingTable.remove();
  }
  if (!cardsHost) return;
  cardsHost.classList.remove("hidden");
  cardsHost.innerHTML = "";

  if (!paginatedData.length) {
    cardsHost.innerHTML =
      '<p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">No hay movimientos para mostrar.</p>';
    updateCfPaginationControls(page, pageSize, startIndex, endIndex, totalItemsForPagination, isGrouped);
    wireCfPaginationHandlers(page, pageSize, groupByFields, searchQuery, data);
    return;
  }

  if (isGrouped) {
    paginatedData.forEach((item) => {
      if (item.type !== "group") return;
      cardsHost.insertAdjacentHTML("beforeend", groupSummaryCardHtml(item.data, headerTranslations));
      const nested = document.createElement("div");
      nested.className = "mb-3 ml-1 space-y-2 border-l-2 border-slate-200 pl-3 dark:border-slate-600";
      flattenCfGroupItems(item).forEach((row) => {
        nested.insertAdjacentHTML("beforeend", movementCardHtml(row, flujoTranslations, subcategoriaTranslations));
      });
      if (nested.childElementCount) cardsHost.appendChild(nested);
    });
  } else {
    paginatedData.forEach((row) => {
      cardsHost.insertAdjacentHTML("beforeend", movementCardHtml(row, flujoTranslations, subcategoriaTranslations));
    });
  }

  updateCfPaginationControls(page, pageSize, startIndex, endIndex, totalItemsForPagination, isGrouped);
  wireCfPaginationHandlers(page, pageSize, groupByFields, searchQuery, data);
}

function wireCfPaginationHandlers(page, pageSize, groupByFields, searchQuery, data) {
  const prevButton = document.getElementById("detailed-movements-prev");
  const nextButton = document.getElementById("detailed-movements-next");
  const pageSizeSelect = document.getElementById("detailed-movements-page-size");
  const total = detailedMovementsState.totalItems || 0;

  if (prevButton) {
    prevButton.onclick = () => {
      if (page > 1) {
        renderDetailedMovementsTable(data, page - 1, pageSize, groupByFields, searchQuery);
      }
    };
  }
  if (nextButton) {
    nextButton.onclick = () => {
      const endIndex = Math.min(page * pageSize, total);
      if (endIndex < total) {
        renderDetailedMovementsTable(data, page + 1, pageSize, groupByFields, searchQuery);
      }
    };
  }
  if (pageSizeSelect) {
    pageSizeSelect.onchange = (e) => {
      renderDetailedMovementsTable(data, 1, parseInt(e.target.value, 10), groupByFields, searchQuery);
    };
  }
}

// Función para renderizar tabla de movimientos detallados
const renderDetailedMovementsTable = (data, page = 1, pageSize = 50, groupByFields = [], searchQuery = "") => {
  const tableWrapper = document.querySelector("[data-detailed-movements-table-host]");
  if (!tableWrapper) {
    console.error("No se encontró el contenedor de la tabla de movimientos detallados");
    return;
  }
  
  // Limpiar contenido previo de paginación si existe
  const existingTable = tableWrapper.querySelector("table");
  if (existingTable) {
    existingTable.remove();
  }

  const cardsHost = document.querySelector("[data-detailed-movements-cards-host]");
  if (!data || !data.length) {
    if (cardsHost) {
      cardsHost.innerHTML =
        '<p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">No hay movimientos detallados disponibles.</p>';
      cardsHost.classList.toggle("hidden", !isNarrowCfViewport());
    }
    const emptyMsg = tableWrapper.querySelector(".empty-message");
    if (!emptyMsg) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "empty-message text-center py-8";
      emptyDiv.innerHTML = `
        <p class="text-sm text-slate-500 dark:text-slate-400">No hay movimientos detallados disponibles.</p>
      `;
      tableWrapper.appendChild(emptyDiv);
    }
    return;
  }

  // Aplicar filtros
  let processedData = data;
  
  // Filtrar por búsqueda
  if (searchQuery && searchQuery.length >= 3) {
    processedData = filterMovementsBySearch(processedData, searchQuery);
  }
  
  // Agrupar si es necesario
  const isGrouped = Array.isArray(groupByFields) && groupByFields.length > 0;
  if (isGrouped) {
    processedData = groupMovements(processedData, groupByFields);
  }
  
  // Actualizar estado
  detailedMovementsState.filteredData = processedData;
  detailedMovementsState.currentPage = page;
  detailedMovementsState.pageSize = pageSize;
  detailedMovementsState.groupBy = groupByFields;
  detailedMovementsState.searchQuery = searchQuery;

  // Para paginación con grupos: solo paginar grupos de nivel superior (no items ni grupos anidados)
  let paginatedData = [];
  let totalItemsForPagination = 0;
  
  if (isGrouped) {
    // Solo contar y paginar grupos de nivel superior
    totalItemsForPagination = processedData.length;
    const startIndex = (page - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, totalItemsForPagination);
    paginatedData = processedData.slice(startIndex, endIndex);
    detailedMovementsState.totalItems = totalItemsForPagination;
  } else {
    // Sin agrupación: paginar items normalmente
    totalItemsForPagination = processedData.length;
    const startIndex = (page - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, totalItemsForPagination);
    paginatedData = processedData.slice(startIndex, endIndex);
    detailedMovementsState.totalItems = totalItemsForPagination;
  }
  
  const startIndex = (page - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalItemsForPagination);

  // Traducciones
  const headerTranslations = {
    "fecha": "FECHA",
    "tipo_comprobante": "TIPO COMP.",
    "tipo": "TIPO",
    "nro_comprobante": "NRO. COMP.",
    "moneda": "MONEDA",
    "ingreso": "INGRESO",
    "egreso": "EGRESO",
    "importe_neto": "IMPORTE NETO",
    "contraparte": "CLIENTE/PROVEEDOR",
    "flujo_tipo": "FLUJO",
    "flujo_subcategoria": "SUBCATEGORÍA",
    "medio_pago": "MEDIO DE PAGO",
    "caja_origen_nombre": "CAJA ORIGEN",
    "caja_destino_nombre": "CAJA DESTINO",
    "nombre_sucursal": "SUCURSAL",
    "detalle": "DETALLE",
    "gasto_nombre": "GASTO",
    "grupo_gasto_nombre": "GRUPO GASTO",
  };

  const flujoTranslations = {
    "operativo": "Operativo",
    "inversion": "Inversión",
    "financiamiento": "Financiamiento",
  };

  const subcategoriaTranslations = {
    "ingresos_ventas": "Cobros por Ventas",
    "ingresos_cobranzas": "Cobranzas",
    "ingresos_intereses": "Intereses Recibidos",
    "ingresos_otros": "Otros Ingresos Operativos",
    "egresos_proveedores": "Pagos a Proveedores",
    "egresos_sueldos": "Sueldos",
    "egresos_impuestos": "Impuestos",
    "egresos_servicios": "Servicios",
    "egresos_gastos": "Gastos Operativos Varios",
    "egresos_otros": "Otros Egresos Operativos",
    "otros": "Otros",
  };

  const tableScroll = document.querySelector("[data-detailed-movements-table-scroll]");
  if (isNarrowCfViewport()) {
    renderDetailedMovementsMobile(paginatedData, {
      isGrouped,
      page,
      pageSize,
      groupByFields,
      searchQuery,
      data,
      startIndex,
      endIndex,
      totalItemsForPagination,
      headerTranslations,
      flujoTranslations,
      subcategoriaTranslations,
    });
    return;
  }
  if (cardsHost) cardsHost.classList.add("hidden");
  if (tableScroll) tableScroll.classList.remove("hidden");

  // Definir columnas a mostrar (en orden)
  const columns = [
    "fecha",
    "tipo_comprobante",
    "nro_comprobante",
    "flujo_tipo",
    "flujo_subcategoria",
    "contraparte",
    "medio_pago",
    "ingreso",
    "egreso",
    "importe_neto",
    "caja_origen_nombre",
    "caja_destino_nombre",
    "nombre_sucursal",
    "detalle",
  ];

  // Crear tabla
  const table = document.createElement("table");
  table.className = "min-w-full text-[11px] text-left bg-white dark:bg-slate-950 border border-slate-100 dark:border-slate-800 rounded-xl overflow-hidden";

  // Header
  const thead = document.createElement("thead");
  thead.className = "bg-slate-50 dark:bg-slate-900/40 text-slate-500 dark:text-slate-300 uppercase tracking-wide";
  const headerRow = document.createElement("tr");

  columns.forEach((key) => {
    const th = document.createElement("th");
    const isCurrency = isCurrencyField(key);
    th.className = `px-3 py-2 text-left ${isCurrency ? "text-right" : ""} sticky top-0 bg-slate-50 dark:bg-slate-900/40 z-10`;
    th.textContent = headerTranslations[key] || key.replace(/_/g, " ").toUpperCase();
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");
  tbody.className = "divide-y divide-slate-100 dark:divide-slate-800";

  // Función recursiva para renderizar grupos anidados con colapsar/expandir
  const renderGroupItem = (item, level = 0, parentId = null) => {
    if (item.type === 'group') {
      const group = item.data;
      const groupId = `group-${level}-${group.groupKey}-${Math.random().toString(36).substr(2, 9)}`;
      const groupRow = document.createElement("tr");
      groupRow.id = groupId;
      groupRow.dataset.groupId = groupId;
      groupRow.dataset.level = level;
      groupRow.dataset.parentId = parentId || '';
      groupRow.dataset.isCollapsed = "true"; // Por defecto colapsado
      
      // Colores diferentes según el nivel de anidación
      let bgClass = "bg-slate-100 dark:bg-slate-800";
      if (level === 1) {
        bgClass = "bg-slate-50 dark:bg-slate-900";
      } else if (level >= 2) {
        bgClass = "bg-slate-25 dark:bg-slate-850";
      }
      groupRow.className = `${bgClass} font-semibold border-t-2 border-slate-300 dark:border-slate-600 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors`;
      
      const groupTd = document.createElement("td");
      groupTd.colSpan = columns.length;
      groupTd.className = "px-4 py-3 text-slate-900 dark:text-white";
      // Aplicar padding izquierdo según el nivel usando estilos inline
      const paddingLeft = level > 0 ? `${level * 16 + 16}px` : '16px';
      groupTd.style.paddingLeft = paddingLeft;
      
      const groupLabel = headerTranslations[group.groupField] || group.groupField.replace(/_/g, " ").toUpperCase();
      const groupValue = group.groupValue || "Sin especificar";
      
      // Icono de expandir/colapsar
      const expandIcon = `<svg class="w-4 h-4 inline-block mr-2 transition-transform" data-expand-icon viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M9 18l6-6-6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>`;
      
      // Colorear ingresos en verde y egresos en rojo en los totales
      const ingresoClass = group.totals.ingreso > 0 ? "text-green-600 dark:text-green-400 font-semibold" : "text-slate-600 dark:text-slate-400";
      const egresoClass = group.totals.egreso > 0 ? "text-red-600 dark:text-red-400 font-semibold" : "text-slate-600 dark:text-slate-400";
      const netoClass = group.totals.importe_neto > 0 ? "text-green-600 dark:text-green-400" : group.totals.importe_neto < 0 ? "text-red-600 dark:text-red-400" : "text-slate-600 dark:text-slate-400";
      
      groupTd.innerHTML = `
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <span class="font-semibold flex min-w-0 items-center">
            ${expandIcon}
            <span class="break-words">${groupLabel}: <span class="font-normal">${groupValue}</span></span>
          </span>
          <span class="text-xs font-normal leading-snug sm:text-right">
            <span class="text-slate-600 dark:text-slate-400">${group.totals.count} movimiento(s)</span> |
            <span class="${ingresoClass}">Ing: ${formatCurrency(group.totals.ingreso)}</span> |
            <span class="${egresoClass}">Egr: ${formatCurrency(group.totals.egreso)}</span> |
            <span class="${netoClass}">Neto: ${formatCurrency(group.totals.importe_neto)}</span>
          </span>
        </div>
      `;
      groupRow.appendChild(groupTd);
      tbody.appendChild(groupRow);
      
      // Event listener para expandir/colapsar
      groupRow.addEventListener("click", (e) => {
        e.stopPropagation();
        const isCollapsed = groupRow.dataset.isCollapsed === "true";
        const children = Array.from(tbody.querySelectorAll(`[data-parent-id="${groupId}"]`));
        
        if (isCollapsed) {
          // Expandir: mostrar solo hijos directos
          children.forEach(child => {
            if (child.dataset.parentId === groupId) {
              child.style.display = "";
            }
          });
          groupRow.dataset.isCollapsed = "false";
          const icon = groupRow.querySelector("[data-expand-icon]");
          if (icon) {
            icon.style.transform = "rotate(90deg)";
          }
        } else {
          // Colapsar: ocultar hijos (recursivamente)
          const collapseChildren = (parentId) => {
            const directChildren = Array.from(tbody.querySelectorAll(`[data-parent-id="${parentId}"]`));
            directChildren.forEach(child => {
              if (child.dataset.groupId) {
                // Es un grupo, colapsarlo también
                child.dataset.isCollapsed = "true";
                const childIcon = child.querySelector("[data-expand-icon]");
                if (childIcon) {
                  childIcon.style.transform = "rotate(0deg)";
                }
                collapseChildren(child.id);
              }
              child.style.display = "none";
            });
          };
          collapseChildren(groupId);
          groupRow.dataset.isCollapsed = "true";
          const icon = groupRow.querySelector("[data-expand-icon]");
          if (icon) {
            icon.style.transform = "rotate(0deg)";
          }
        }
      });
      
      // Renderizar hijos (grupos anidados o items) directamente en tbody pero ocultos
      // Los items directos del grupo (group.items) nunca se renderizan aquí porque están vacíos
      // Solo renderizamos los children, que pueden ser grupos anidados o items finales
      if (item.children && item.children.length > 0) {
        item.children.forEach(child => {
          renderGroupItem(child, level + 1, groupId);
        });
      }
      // NO renderizar group.items aquí - esos items ya están procesados en los children
      
      return groupRow;
    } else if (item.type === 'item') {
      // Renderizar fila normal
      const tr = createTableRow(item.data, columns, flujoTranslations, subcategoriaTranslations, headerTranslations);
      tr.dataset.parentId = parentId || '';
      if (level > 0) {
        const firstTd = tr.querySelector("td");
        if (firstTd) {
          const itemPaddingLeft = `${level * 16 + 16}px`;
          firstTd.style.paddingLeft = itemPaddingLeft;
        }
      }
      // Ocultar por defecto si tiene padre (está dentro de un grupo colapsado)
      if (parentId) {
        tr.style.display = "none";
      }
      tbody.appendChild(tr);
      return tr;
    }
    return null;
  };
  
  // Renderizar datos paginados
  if (isGrouped) {
    paginatedData.forEach((item) => {
      renderGroupItem(item, 0, null);
    });
  } else {
    paginatedData.forEach((row) => {
      const tr = createTableRow(row, columns, flujoTranslations, subcategoriaTranslations, headerTranslations);
      tbody.appendChild(tr);
    });
  }
  
  // Función auxiliar para crear una fila de tabla
  function createTableRow(row, columns, flujoTranslations, subcategoriaTranslations, headerTranslations) {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50/70 dark:hover:bg-slate-900/60 transition-colors";

    // Resaltar según tipo de flujo
    if (row.flujo_tipo === "operativo") {
      tr.className += " bg-blue-50/30 dark:bg-blue-900/10";
    } else if (row.flujo_tipo === "inversion") {
      tr.className += " bg-green-50/30 dark:bg-green-900/10";
    } else if (row.flujo_tipo === "financiamiento") {
      tr.className += " bg-purple-50/30 dark:bg-purple-900/10";
    }

    columns.forEach((key) => {
      const value = row[key];
      const td = document.createElement("td");
      const isCurrency = isCurrencyField(key);
      td.className = `px-3 py-2 text-slate-700 dark:text-slate-200 ${isCurrency ? "text-right font-medium" : ""}`;

      if (value === null || value === undefined || value === "") {
        td.textContent = "-";
        td.className += " text-slate-400 dark:text-slate-500";
      } else if (key === "flujo_tipo") {
        td.textContent = flujoTranslations[value.toLowerCase()] || value;
      } else if (key === "flujo_subcategoria") {
        td.textContent = subcategoriaTranslations[value.toLowerCase()] || value;
      } else if (key === "contraparte" || key === "detalle") {
        td.className += " max-w-[10rem] break-words sm:max-w-[14rem]";
        td.textContent = value;
      } else if (isCurrency) {
        td.textContent = formatCurrency(value);
        // Colorear según positivo/negativo
        if (key === "ingreso" && value > 0) {
          td.className += " text-green-600 dark:text-green-400";
        } else if (key === "egreso" && value > 0) {
          td.className += " text-red-600 dark:text-red-400";
        } else if (key === "importe_neto") {
          if (value > 0) {
            td.className += " text-green-600 dark:text-green-400";
          } else if (value < 0) {
            td.className += " text-red-600 dark:text-red-400";
          }
        }
      } else {
        td.textContent = value;
      }

      tr.appendChild(td);
    });
    
    return tr;
  }

  table.appendChild(tbody);

  // Actualizar controles de paginación
  const paginationInfo = document.getElementById("detailed-movements-pagination-info");
  const prevButton = document.getElementById("detailed-movements-prev");
  const nextButton = document.getElementById("detailed-movements-next");
  const pageSizeSelect = document.getElementById("detailed-movements-page-size");

  if (paginationInfo) {
    paginationInfo.textContent = `Mostrando ${startIndex + 1} - ${endIndex} de ${totalItemsForPagination} ${isGrouped ? 'grupos' : 'movimientos'}`;
  }

  if (prevButton) {
    prevButton.disabled = page === 1;
    prevButton.onclick = () => {
      if (page > 1) {
        renderDetailedMovementsTable(detailedMovementsState.data, page - 1, pageSize, groupByFields, searchQuery);
      }
    };
  }

  if (nextButton) {
    nextButton.disabled = endIndex >= totalItemsForPagination;
    nextButton.onclick = () => {
      if (endIndex < totalItemsForPagination) {
        renderDetailedMovementsTable(detailedMovementsState.data, page + 1, pageSize, groupByFields, searchQuery);
      }
    };
  }

  if (pageSizeSelect) {
    pageSizeSelect.value = pageSize;
    pageSizeSelect.onchange = (e) => {
      const newPageSize = parseInt(e.target.value);
      renderDetailedMovementsTable(detailedMovementsState.data, 1, newPageSize, groupByFields, searchQuery);
    };
  }

  // Renderizar tabla (ya se limpió arriba)
  tableWrapper.appendChild(table);
  
  // Configurar controles de búsqueda y agrupación (solo la primera vez)
  // Usar setTimeout para asegurar que el DOM esté listo y no interfiera con el foco
  setTimeout(() => {
    if (!detailedMovementsState.controlsInitialized) {
      setupDetailedMovementsControls();
      detailedMovementsState.controlsInitialized = true;
    } else {
      // Si ya está inicializado, verificar que el componente de tags esté funcionando
      const container = document.getElementById("detailed-movements-group-by_tags_container");
      if (container && container.dataset.initialized !== "true") {
        // Reintentar inicialización del componente de tags
        const groupBySelect = document.getElementById("detailed-movements-group-by");
        if (groupBySelect) {
          try {
            window.initializeTagsFilter("detailed-movements-group-by", "group_by");
            container.dataset.initialized = "true";
          } catch (error) {
            console.error("Error reintentando inicialización de tags:", error);
          }
        }
      }
    }
  }, 200);
  
  // Scroll suave hacia la tabla
  setTimeout(() => {
    tableWrapper.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, 100);
};

const attachTableToggle = (widget, data) => {
  const toggleButton = widget.querySelector("[data-toggle-table]");
  const tableWrapper = widget.querySelector("[data-widget-table-wrapper]");
  if (!toggleButton || !tableWrapper) return;

  const setButtonState = (label) => {
    toggleButton.innerHTML = label;
  };

  setButtonState(`
    <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    Ver tabla
  `);
  tableWrapper.classList.add("hidden");

  toggleButton.onclick = () => {
    const isHidden = tableWrapper.classList.contains("hidden");
    if (isHidden) {
      renderTable(widget, data, { show: true });
      setButtonState(`
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 5h16M4 10h16M4 15h16M8 20h8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Ocultar tabla
      `);
    } else {
      tableWrapper.classList.add("hidden");
      setButtonState(`
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Ver tabla
      `);
    }
  };
};

// Carga del panel embebido en cash_flow_waterfall (segunda petición con slug detallado)
const fetchDetailedMovements = async () => {
  const section = document.getElementById("detailed-movements-section");
  if (!section) return;

  const summaryBanner = document.querySelector("[data-detailed-movements-summary-banner]");
  const countEl = document.querySelector("[data-detailed-movements-count]");
  const tablePanel = document.querySelector("[data-detailed-movements-table-wrapper]");

  try {
    if (summaryBanner) summaryBanner.classList.remove("hidden");
    if (countEl) countEl.textContent = "Cargando movimientos detallados…";

    const getFiltersFunc = window.getFilters;
    const filters = getFiltersFunc ? getFiltersFunc() : {};
    const currentSlug = dashboardRoot?.dataset?.reportSlug;
    if (currentSlug !== SLUG_WATERFALL) return;

    const apiUrl = dashboardRoot?.dataset?.dashboardUrl;
    if (!apiUrl) return;

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        slug: SLUG_STANDALONE,
        limit: 10000,
        filters,
      }),
    });

    if (!response.ok) {
      throw new Error("Error al cargar movimientos detallados");
    }

    const payload = await response.json();
    const rows = (payload.data && payload.data.length) ? payload.data : [];

    if (rows.length > 0) {
      detailedMovementsState.data = rows;
      detailedMovementsState.totalItems = rows.length;
      section.classList.remove("hidden");
      if (tablePanel) tablePanel.classList.add("hidden");
      if (countEl) {
        countEl.textContent = `${rows.length} movimiento(s) encontrado(s). Hacé clic en «Ver tabla» para ver el detalle.`;
      }

      const toggleButton = document.querySelector("[data-toggle-detailed-table]");
      if (toggleButton && tablePanel) {
        const newToggleButton = toggleButton.cloneNode(true);
        toggleButton.parentNode.replaceChild(newToggleButton, toggleButton);

        newToggleButton.onclick = () => {
          const panel = document.querySelector("[data-detailed-movements-table-wrapper]");
          if (!panel) return;

          const isHidden = panel.classList.contains("hidden");
          if (isHidden) {
            panel.classList.remove("hidden");
            if (detailedMovementsState.data?.length) {
              const searchInput = document.getElementById("detailed-movements-search");
              const groupBySelect = document.getElementById("detailed-movements-group-by");
              const searchQuery = searchInput?.value || "";
              const groupByFields = groupBySelect
                ? Array.from(groupBySelect.selectedOptions).map((opt) => opt.value).filter((v) => v)
                : [];
              renderDetailedMovementsTable(detailedMovementsState.data, 1, 50, groupByFields, searchQuery);
              setTimeout(() => setupDetailedMovementsControls(), 150);
            }
            newToggleButton.innerHTML = `
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M4 5h16M4 10h16M4 15h16M8 20h8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Ocultar tabla
            `;
          } else {
            panel.classList.add("hidden");
            newToggleButton.innerHTML = `
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Ver tabla
            `;
          }
        };
      }
    } else {
      section.classList.add("hidden");
      detailedMovementsState.data = [];
      detailedMovementsState.totalItems = 0;
    }
  } catch (error) {
    console.error("Error cargando movimientos detallados:", error);
    if (countEl) {
      countEl.textContent = "Error al cargar movimientos detallados";
      countEl.classList.add("text-red-600", "dark:text-red-400");
    }
  }
};

// Función para configurar los controles de búsqueda y agrupación
const setupDetailedMovementsControls = () => {
  const searchInput = document.getElementById("detailed-movements-search");
  const groupBySelect = document.getElementById("detailed-movements-group-by");
  // Botón limpiar filtros eliminado
  // const clearFiltersBtn = document.getElementById("detailed-movements-clear-filters");
  const suggestionsDiv = document.getElementById("detailed-movements-search-suggestions");
  const tableWrapper = document.querySelector("[data-detailed-movements-table-host]");
  
  if (!searchInput || !tableWrapper) return;
  
  // Evitar múltiples inicializaciones - verificar si el wrapper ya tiene controles inicializados
  if (tableWrapper.dataset.controlsInitialized === "true") {
    return;
  }
  
  // Marcar como inicializado
  tableWrapper.dataset.controlsInitialized = "true";
  
  let searchTimeout = null;
  
  // Búsqueda predictiva con debounce
  searchInput.addEventListener("input", (e) => {
    const query = e.target.value.trim();
    
    // Limpiar timeout anterior
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }
    
    // Si tiene menos de 3 caracteres, ocultar sugerencias y no filtrar
    if (query.length < 3) {
      if (suggestionsDiv) {
        suggestionsDiv.classList.add("hidden");
      }
      detailedMovementsState.searchQuery = "";
      const currentGroupBy = groupBySelect ? Array.from(groupBySelect.selectedOptions).map(opt => opt.value).filter(v => v) : [];
      renderDetailedMovementsTable(
        detailedMovementsState.data,
        1,
        detailedMovementsState.pageSize,
        currentGroupBy,
        ""
      );
      return;
    }
    
    // Generar sugerencias
    if (suggestionsDiv && detailedMovementsState.data.length > 0) {
      const suggestions = generateSearchSuggestions(detailedMovementsState.data, query);
      detailedMovementsState.searchSuggestions = suggestions;
      
      if (suggestions.length > 0) {
        suggestionsDiv.innerHTML = suggestions.map(suggestion => `
          <div class="px-3 py-2 hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer text-xs text-slate-700 dark:text-slate-200"
               data-suggestion="${suggestion.replace(/"/g, '&quot;')}">
            ${suggestion}
          </div>
        `).join("");
        
        // Agregar event listeners a las sugerencias
        suggestionsDiv.querySelectorAll("[data-suggestion]").forEach(item => {
          item.addEventListener("click", () => {
            searchInput.value = item.dataset.suggestion;
            suggestionsDiv.classList.add("hidden");
            // Aplicar filtro inmediatamente
            detailedMovementsState.searchQuery = item.dataset.suggestion;
            const currentGroupBy = groupBySelect ? Array.from(groupBySelect.selectedOptions).map(opt => opt.value).filter(v => v) : [];
            renderDetailedMovementsTable(
              detailedMovementsState.data,
              1,
              detailedMovementsState.pageSize,
              currentGroupBy,
              item.dataset.suggestion
            );
          });
        });
        
        suggestionsDiv.classList.remove("hidden");
      } else {
        suggestionsDiv.classList.add("hidden");
      }
    }
    
    // Aplicar filtro con debounce (300ms)
    searchTimeout = setTimeout(() => {
      detailedMovementsState.searchQuery = query;
      const currentGroupBy = groupBySelect ? Array.from(groupBySelect.selectedOptions).map(opt => opt.value).filter(v => v) : [];
      renderDetailedMovementsTable(
        detailedMovementsState.data,
        1,
        detailedMovementsState.pageSize,
        currentGroupBy,
        query
      );
    }, 300);
  });
  
  // Ocultar sugerencias al hacer clic fuera (pero no si es el input)
  const hideSuggestionsHandler = (e) => {
    if (suggestionsDiv && !searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
      suggestionsDiv.classList.add("hidden");
    }
  };
  document.addEventListener("click", hideSuggestionsHandler);
  
  // Inicializar componente de tags para agrupación
  if (groupBySelect) {
    const container = document.getElementById("detailed-movements-group-by_tags_container");
    const input = document.getElementById("detailed-movements-group-by_search");
    const dropdown = document.getElementById("detailed-movements-group-by_dropdown");
    
    // Verificar que todos los elementos necesarios estén presentes
    if (container && input && dropdown) {
      // Verificar que el componente de tags no esté ya inicializado
      if (container.dataset.initialized !== "true") {
        // Verificar que initializeTagsFilter esté disponible
        if (typeof window.initializeTagsFilter === "function") {
          // Inicializar componente de tags
          try {
            window.initializeTagsFilter("detailed-movements-group-by", "group_by");
            container.dataset.initialized = "true";
            
            // Escuchar cambios en el select para actualizar la tabla
            groupBySelect.addEventListener("change", () => {
              const groupByFields = Array.from(groupBySelect.selectedOptions).map(opt => opt.value).filter(v => v);
              detailedMovementsState.groupBy = groupByFields;
              renderDetailedMovementsTable(
                detailedMovementsState.data,
                1,
                detailedMovementsState.pageSize,
                groupByFields,
                detailedMovementsState.searchQuery
              );
            });
          } catch (error) {
            console.error("Error inicializando componente de tags para agrupación:", error);
          }
        } else {
          // Si initializeTagsFilter no está disponible, intentar más tarde
          console.warn("initializeTagsFilter no está disponible aún, reintentando en 500ms...");
          setTimeout(() => {
            if (typeof window.initializeTagsFilter === "function" && container.dataset.initialized !== "true") {
              try {
                window.initializeTagsFilter("detailed-movements-group-by", "group_by");
                container.dataset.initialized = "true";
                
                // Escuchar cambios en el select para actualizar la tabla
                groupBySelect.addEventListener("change", () => {
                  const groupByFields = Array.from(groupBySelect.selectedOptions).map(opt => opt.value).filter(v => v);
                  detailedMovementsState.groupBy = groupByFields;
                  renderDetailedMovementsTable(
                    detailedMovementsState.data,
                    1,
                    detailedMovementsState.pageSize,
                    groupByFields,
                    detailedMovementsState.searchQuery
                  );
                });
              } catch (error) {
                console.error("Error en reintento de inicialización de tags:", error);
              }
            }
          }, 500);
        }
      }
    } else {
      console.warn("Elementos del componente de tags para agrupación no encontrados:", {
        container: !!container,
        input: !!input,
        dropdown: !!dropdown
      });
    }
  }
  
  // Botón limpiar filtros eliminado - funcionalidad removida
};

  window.cashFlowDetailedMovementsHandler = {
    processData: processStandalonePayload,
    fetchForWaterfall: fetchDetailedMovements,
    resetControls: () => {
      detailedMovementsState.controlsInitialized = false;
      const host = document.querySelector("[data-detailed-movements-table-host]");
      if (host) host.innerHTML = "";
      const wrap = document.querySelector("[data-detailed-movements-table-wrapper]");
      if (wrap) wrap.dataset.controlsInitialized = "false";
    },
  };

  window.fetchDetailedMovements = fetchDetailedMovements;
})();
