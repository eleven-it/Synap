// Comentario: Controlador básico para dashboards interactivos con gráficos D3.

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
    "cash_flow_waterfall", 
    "cash_flow_by_account",
    "uninvoiced_remitos",
    "pending_orders",
    "sales_summary"
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
  fullscreen: null,
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
  if (typeof value === "number") {
    try {
      return new Intl.NumberFormat(
        "es-AR",
        {
          style: "currency",
          currency: "ARS",
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }
      ).format(value);
    } catch (e) {
      return `$${value.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ".").replace(".", ",")}`;
    }
  }
  return value;
};

const isCurrencyField = (fieldName) => {
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
        if (cached) {
          renderChart(widget, cached.data, cached.config);
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
  if (!workspaceControls.fullscreen) {
    return;
  }
  workspaceControls.fullscreen.innerHTML = isActive
    ? `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 9H5V5M5 19l4-4m6 0h4v4m0-14l-4 4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> Salir de pantalla completa`
    : `<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 8V4h4M4 4l5 5M20 16v4h-4m4 0l-5-5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> Pantalla completa`;
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
    .attr("fill", COLORS[0]);
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

  const xField = config.x_field || Object.keys(data[0])[0];
  const valueField = config.y_field || config.value_field || discoverNumericFields(data)[0];
  if (!valueField) {
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas numéricas.</p>";
    return;
  }

  const stackField =
    config.stack_field || Object.keys(data[0]).find((key) => key !== xField && key !== valueField && typeof data[0][key] === "string");
  const grouped = d3.group(data, (row) => row[xField] ?? "Sin categoría");
  const keys = Array.from(new Set(Array.from(grouped.values()).flat().map((row) => row[stackField] ?? "Total")));

  const stackedData = Array.from(grouped, ([key, rows]) => {
    const base = { x: key };
    keys.forEach((stackKey) => {
      base[stackKey] = rows
        .filter((row) => (row[stackField] ?? "Total") === stackKey)
        .reduce((sum, row) => sum + (Number(row[valueField]) || 0), 0);
    });
    return base;
  });

  const { width, height } = getBounding(container);
  const margin = { top: 24, right: 24, bottom: 40, left: 56 };
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
    .attr("rx", 6);
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
  const margin = { top: 24, right: 24, bottom: 40, left: 72 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const xScale = d3
    .scaleBand()
    .domain(nodes.map((node) => node.key))
    .range([margin.left, margin.left + innerWidth])
    .padding(0.4);

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

  svg
    .append("g")
    .attr("transform", `translate(0, ${margin.top + innerHeight})`)
    .attr("class", "text-[10px] text-slate-300 font-medium")
    .call(d3.axisBottom(xScale));

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
  const numericFields = config.fields || discoverNumericFields(data);
  console.log("[renderCards] Campos numéricos encontrados:", numericFields);
  if (!numericFields.length) {
    console.warn("[renderCards] No se encontraron campos numéricos");
    container.innerHTML = "<p class=\"text-xs text-slate-200\">Sin métricas</p>";
    return;
  }
  const row = data[0] || {};
  console.log("[renderCards] Fila de datos:", row);

  const wrapper = d3.select(container).html("");
  
  // Detectar si es sales_summary para usar un layout especial
  // Buscar el reportSlug desde el widget o desde dashboardRoot
  let reportSlug = dashboardRoot?.dataset?.reportSlug;
  if (!reportSlug && container) {
    // Buscar el widget padre que contiene el data-report-slug
    // En workspace, el section tiene data-report-slug
    // En dashboard detail, el widget tiene data-widget-id y el dashboardRoot tiene data-report-slug
    const widgetElement = container.closest("section[data-report-slug]") || 
                         container.closest("[data-report-slug]");
    if (widgetElement && widgetElement.dataset && widgetElement.dataset.reportSlug) {
      reportSlug = widgetElement.dataset.reportSlug;
    }
  }
  const isSalesSummary = reportSlug === "sales_summary";
  
  // Para sales_summary: grid de 2x2
  // Para otros: grid normal
  const gridClass = isSalesSummary
    ? "grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 h-full"
    : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 sm:gap-4 h-full";
  
  const grid = wrapper
    .append("div")
    .attr("class", gridClass);

  // Para sales_summary, ordenar las tarjetas: Ventas Netas, Remitos, Pedidos, Total Consolidado
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

const widgetRenderers = {
  "d3-line": (container, data, config) => renderLineChart(container, data, config),
  "d3-line-area": (container, data, config) => renderLineChart(container, data, config, true),
  "d3-bar": (container, data, config) => renderBarChart(container, data, config),
  "d3-bar-grouped": (container, data, config) => renderGroupedBarChart(container, data, config),
  "d3-bar-stacked": (container, data, config) => renderStackedBarChart(container, data, config),
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

const renderTable = (widgetElement, data, options = {}) => {
  const show = options.show ?? false;
  const target = widgetElement.querySelector("[data-widget-table-wrapper]") || widgetElement;

  if (!show) {
    target.classList.add("hidden");
    return;
  }

  target.innerHTML = "";

  if (!data || !data.length) {
    const emptyMessage = widgetElement.dataset.emptyLabel || "Sin datos disponibles.";
    target.innerHTML = `<p class="text-sm text-slate-500 dark:text-slate-400">${emptyMessage}</p>`;
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
  const excludedColumns = ["id_sucursal", "id_punto_venta", "mes"];
  
  const fieldKeys = Object.keys(data[0]).filter((key) => !excludedColumns.includes(key));
  
  // Mapeo de términos en inglés a español
  const headerTranslations = {
    "period": "PERÍODO",
    "mes_formato": "MES",
    "mes": "MES",
    "operating_flow": "FLUJO OPERATIVO",
    "investing_flow": "FLUJO DE INVERSIÓN",
    "financing_flow": "FLUJO DE FINANCIAMIENTO",
    "cash_variation": "VARIACIÓN DE CAJA",
    "cumulative": "ACUMULADO",
    "type": "TIPO",
    "operating_ingresos": "INGRESOS OPERATIVOS",
    "operating_egresos": "EGRESOS OPERATIVOS"
  };
  
  fieldKeys.forEach((key) => {
    const th = document.createElement("th");
    const isCurrency = isCurrencyField(key);
    th.className = `px-4 py-3 ${isCurrency ? "text-right" : ""}`;
    
    // Usar traducción si existe, sino convertir a formato legible
    let headerText = headerTranslations[key.toLowerCase()];
    if (!headerText) {
      headerText = key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
    }
    
    th.textContent = headerText;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  tbody.className = "divide-y divide-slate-100 dark:divide-slate-800";

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
  data.slice(0, maxRows).forEach((row) => {
    const tr = document.createElement("tr");
    tr.className =
      "hover:bg-slate-50/70 dark:hover:bg-slate-900/60 transition-colors";
    
    // Resaltar filas de saldo inicial y final
    if (isCashFlowWaterfall && (row.type === "starting" || row.type === "ending")) {
      tr.className += " bg-blue-50 dark:bg-blue-900/20";
    }
    
    fieldKeys.forEach((key, index) => {
      const value = row[key];
      const td = document.createElement("td");
      const isCurrency = isCurrencyField(key);
      td.className = `px-4 py-3 text-slate-700 dark:text-slate-200 ${isCurrency ? "text-right font-medium" : ""}`;
      
      // Formatear valores
      if (value === null || value === undefined || value === "") {
        td.textContent = "";
      } else if (key.toLowerCase() === "type" || key.toLowerCase() === "tipo") {
        // Traducir valores de tipo al español
        const typeTranslations = {
          "starting": "Inicial",
          "period": "Período",
          "ending": "Final"
        };
        td.textContent = typeTranslations[value.toLowerCase()] || value;
      } else if (isCurrency) {
        td.textContent = formatCurrency(value);
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
    tbody.appendChild(tr);
  });

  // Agregar fila de totales solo si hay columnas monetarias y no es cash_flow_waterfall ni sales_summary
  // Para cash_flow_waterfall, el Saldo Final ya es el resultado final, no tiene sentido sumar acumulados
  // Para sales_summary, los totales ya se muestran en las tarjetas, no es necesario duplicarlos en la tabla
  const reportSlug = dashboardRoot?.dataset?.reportSlug || widgetElement?.dataset?.reportSlug;
  const shouldShowTotals = Object.keys(totals).length > 0 && !isCashFlowWaterfall && reportSlug !== "sales_summary";
  
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
  target.appendChild(table);

  if (show) {
    target.classList.remove("hidden");
  }
};

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

// Función para renderizar tabla de movimientos detallados
const renderDetailedMovementsTable = (data, page = 1, pageSize = 50, groupByFields = [], searchQuery = "") => {
  const tableWrapper = document.querySelector("[data-detailed-movements-table-wrapper]");
  if (!tableWrapper) {
    console.error("No se encontró el contenedor de la tabla de movimientos detallados");
    return;
  }
  
  // Limpiar contenido previo de paginación si existe
  const existingTable = tableWrapper.querySelector("table");
  if (existingTable) {
    existingTable.remove();
  }

  if (!data || !data.length) {
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
        <div class="flex items-center justify-between">
          <span class="font-semibold flex items-center">
            ${expandIcon}
            ${groupLabel}: <span class="font-normal">${groupValue}</span>
          </span>
          <span class="text-xs font-normal">
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
            initializeTagsFilter("detailed-movements-group-by", "group_by");
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

// Función para cargar movimientos detallados
const fetchDetailedMovements = async () => {
  const section = document.getElementById("detailed-movements-section");
  const contentArea = document.querySelector("[data-detailed-movements-content]");
  if (!section || !contentArea) return;

  try {
    contentArea.innerHTML = `
      <div class="h-full w-full grid place-content-center text-xs text-slate-200 tracking-[0.2em] uppercase">
        Cargando movimientos detallados...
      </div>
    `;

    // Usar getFilters global o la función local si está disponible
    const getFiltersFunc = window.getFilters || getFilters;
    const filters = getFiltersFunc ? getFiltersFunc() : {};
    const reportSlug = dashboardRoot?.dataset.reportSlug;

    if (!reportSlug || reportSlug !== "cash_flow_waterfall") {
      return;
    }

    const apiUrl = dashboardRoot?.dataset.dashboardUrl;
    if (!apiUrl) return;

    const response = await fetch(apiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        slug: "cash_flow_detailed_movements",
        limit: 10000, // Obtener todos los movimientos
        filters: filters,
      }),
    });

    if (!response.ok) {
      throw new Error("Error al cargar movimientos detallados");
    }

    const payload = await response.json();

    if (payload.data && payload.data.length > 0) {
      // Guardar los datos en el estado global para que estén disponibles cuando se haga clic en el botón
      detailedMovementsState.data = payload.data;
      detailedMovementsState.totalItems = payload.data.length;
      
      // Mostrar sección
      section.classList.remove("hidden");
      
      // Renderizar tabla inicialmente oculta
      const tableWrapper = document.querySelector("[data-detailed-movements-table-wrapper]");
      if (tableWrapper) {
        tableWrapper.classList.add("hidden");
      }

      // Actualizar contenido
      contentArea.innerHTML = `
        <div class="text-center py-4">
          <p class="text-xs text-slate-300">${payload.data.length} movimientos encontrados</p>
          <p class="text-[10px] text-slate-400 mt-1">Haz clic en "Ver tabla" para ver los detalles</p>
        </div>
      `;

      // Configurar toggle de tabla
      const toggleButton = document.querySelector("[data-toggle-detailed-table]");
      if (toggleButton && tableWrapper) {
        // Remover event listeners anteriores si existen
        const newToggleButton = toggleButton.cloneNode(true);
        toggleButton.parentNode.replaceChild(newToggleButton, toggleButton);
        
        newToggleButton.onclick = () => {
          const currentTableWrapper = document.querySelector("[data-detailed-movements-table-wrapper]");
          if (!currentTableWrapper) {
            console.error("No se encontró el contenedor de la tabla");
            return;
          }
          
          const isHidden = currentTableWrapper.classList.contains("hidden");
          if (isHidden) {
            currentTableWrapper.classList.remove("hidden");
            // Usar los datos guardados en el estado global
            if (detailedMovementsState.data && detailedMovementsState.data.length > 0) {
              // Obtener valores actuales de los controles
              const searchInput = document.getElementById("detailed-movements-search");
              const groupBySelect = document.getElementById("detailed-movements-group-by");
              const searchQuery = searchInput?.value || "";
              // Obtener array de campos seleccionados
              const groupByFields = groupBySelect ? Array.from(groupBySelect.selectedOptions).map(opt => opt.value).filter(v => v) : [];
              
              renderDetailedMovementsTable(detailedMovementsState.data, 1, 50, groupByFields, searchQuery);
              // Inicializar controles después de que la tabla esté visible
              setTimeout(() => {
                setupDetailedMovementsControls();
              }, 150);
            } else {
              console.error("No hay datos disponibles en detailedMovementsState");
              currentTableWrapper.innerHTML = `
                <div class="text-center py-8">
                  <p class="text-sm text-red-500 dark:text-red-400">Error: No hay datos disponibles</p>
                </div>
              `;
            }
            newToggleButton.innerHTML = `
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M4 5h16M4 10h16M4 15h16M8 20h8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Ocultar tabla
            `;
          } else {
            currentTableWrapper.classList.add("hidden");
            newToggleButton.innerHTML = `
              <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M4 5h16M4 10h16M4 15h16M4 20h10" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              Ver tabla
            `;
          }
        };
      } else {
        console.error("No se encontró el botón toggle o el contenedor de tabla", { toggleButton, tableWrapper });
      }
    } else {
      section.classList.add("hidden");
      detailedMovementsState.data = [];
      detailedMovementsState.totalItems = 0;
    }
  } catch (error) {
    console.error("Error cargando movimientos detallados:", error);
    if (contentArea) {
      contentArea.innerHTML = `
        <div class="text-center py-4">
          <p class="text-xs text-red-400">Error al cargar movimientos detallados</p>
        </div>
      `;
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
  const tableWrapper = document.querySelector("[data-detailed-movements-table-wrapper]");
  
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
        if (typeof initializeTagsFilter === "function") {
          // Inicializar componente de tags
          try {
            initializeTagsFilter("detailed-movements-group-by", "group_by");
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
            if (typeof initializeTagsFilter === "function" && container.dataset.initialized !== "true") {
              try {
                initializeTagsFilter("detailed-movements-group-by", "group_by");
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

const renderSummary = (meta, totals) => {
  const summaryContainer = document.querySelector("[data-summary-container]");
  const summaryGrid = document.querySelector("[data-summary-grid]");
  if (!summaryContainer || !summaryGrid) {
    return;
  }

  const reportSlug = dashboardRoot?.dataset?.reportSlug;
  const isSalesSummary = reportSlug === "sales_summary";

  // Actualizar el período en el título
  const summaryPeriodElement = document.getElementById("summary-period");
  if (summaryPeriodElement) {
    const fechaInicio = document.getElementById("fecha_inicio")?.value;
    const fechaFin = document.getElementById("fecha_fin")?.value;
    if (fechaInicio && fechaFin) {
      // Formatear fechas: de YYYY-MM-DD a DD-MM-YYYY
      const formatDate = (dateStr) => {
        const [year, month, day] = dateStr.split('-');
        return `${day}-${month}-${year}`;
      };
      summaryPeriodElement.textContent = `Periodo ${formatDate(fechaInicio)} al ${formatDate(fechaFin)}`;
    } else {
      summaryPeriodElement.textContent = "";
    }
  }

  summaryGrid.innerHTML = "";

  // Para sales_summary, no mostrar las tarjetas en el resumen superior
  // Solo mostrar la información de última actualización
  if (isSalesSummary) {
    // Agregar solo la información de última actualización
    const lastUpdateContainer = document.createElement("div");
    lastUpdateContainer.id = "last-update-time";
    lastUpdateContainer.className = "flex flex-col items-end justify-center text-right col-span-full";
    lastUpdateContainer.innerHTML = `
      <span class="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        Última actualización:
      </span>
      <span data-update-date-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
      <span data-update-time-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
    `;
    summaryGrid.appendChild(lastUpdateContainer);
    updateLastUpdateTime();
    summaryContainer.classList.remove("hidden");
    return;
  }

  // Ordenar las claves para mostrar en un orden específico
  // Excluir campos que ya se muestran en otras tarjetas (operating_ingresos, operating_egresos, cash_variation_sum_movements)
  const excludedKeys = ["operating_ingresos", "operating_egresos", "cash_variation_sum_movements"];
  
  // Orden específico para ventas_netas: ventas_brutas, notas_credito, ventas_netas
  const isVentasNetasReport = reportSlug === "ventas_netas";
  const order = isVentasNetasReport
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

  let ventasNetasCard = null;
  let financingFlowCard = null;
  let cashVariationCard = null;
  let saldoFinalCard = null;
  
  totalKeys.forEach((key) => {
    const card = document.createElement("div");
    const isCurrency = isCurrencyField(key);
    const keyLower = key.toLowerCase();
    
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
      subtitle = `<p class="text-[9px] ${textColorClass} opacity-75 mt-1 text-right">Ing: ${formatCurrency(ingresos)} | Egr: ${formatCurrency(egresos)}</p>`;
    }
    
    // Formatear el label según la key
    let displayLabel = toTitle(key);
    if (isTotalRemitos) {
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
      displayLabel = "PEDIDOS PENDIENTES";
    } else if (isTotalConsolidado) {
      displayLabel = "TOTAL CONSOLIDADO";
    }
    
    card.innerHTML = `
        <p class="text-[10px] uppercase tracking-[0.25em] ${textColorClass} mb-2">${displayLabel}</p>
        <p class="text-xl font-semibold text-right">${isCurrency ? formatCurrency(totals[key]) : formatNumber(totals[key])}</p>
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

  // Agregar hora de última actualización
  if (isVentasNetasReport && ventasNetasCard) {
    // Para ventas_netas: insertar después de VENTAS NETAS (4ta posición: VENTAS BRUTAS, NOTAS DE CRÉDITO, VENTAS NETAS, Última actualización)
    const lastUpdateContainer = document.createElement("div");
    lastUpdateContainer.id = "last-update-time";
    lastUpdateContainer.className = "flex flex-col items-end justify-center text-right";
    lastUpdateContainer.innerHTML = `
      <span class="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        Última actualización:
      </span>
      <span data-update-date-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
      <span data-update-time-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
    `;
    
    // Insertar después de la tarjeta de VENTAS NETAS (que es la 3ra tarjeta en el orden)
    ventasNetasCard.parentNode.insertBefore(lastUpdateContainer, ventasNetasCard.nextSibling);
    
    // Actualizar hora de última actualización
    updateLastUpdateTime();
  } else if (ventasNetasCard && !isVentasNetasReport) {
    // Para otros reportes que tengan ventas_netas: alineada verticalmente con VENTAS NETAS
    const lastUpdateContainer = document.createElement("div");
    lastUpdateContainer.id = "last-update-time";
    lastUpdateContainer.className = "flex flex-col items-end justify-center text-right";
    lastUpdateContainer.innerHTML = `
      <span class="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        Última actualización:
      </span>
      <span data-update-date-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
      <span data-update-time-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
    `;
    
    // Insertar después de la tarjeta de VENTAS NETAS
    ventasNetasCard.parentNode.insertBefore(lastUpdateContainer, ventasNetasCard.nextSibling);
    
    // Actualizar hora de última actualización
    updateLastUpdateTime();
  } else if (saldoFinalCard) {
    // Para cash_flow_waterfall: ubicar en el octavo cuadrante (posición 8 del grid)
    // El grid tiene 4 columnas, así que el octavo cuadrante es la 4ta columna de la 2da fila
    
    // Primero, insertar un elemento vacío en la posición 7 (si no existe) para dejar espacio
    const currentChildren = Array.from(summaryGrid.children);
    const currentCount = currentChildren.length;
    
    // Si hay menos de 7 elementos, agregar elementos vacíos hasta llegar a 7
    while (currentChildren.length < 7) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "hidden"; // Oculto pero ocupa espacio en el grid
      summaryGrid.appendChild(emptyDiv);
      currentChildren.push(emptyDiv);
    }
    
    // Ahora insertar la última actualización en la posición 8 (octavo cuadrante)
    const lastUpdateContainer = document.createElement("div");
    lastUpdateContainer.id = "last-update-time";
    lastUpdateContainer.className = "flex flex-col items-end justify-center text-right";
    lastUpdateContainer.innerHTML = `
      <span class="text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
        Última actualización:
      </span>
      <span data-update-date-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
      <span data-update-time-text class="text-sm font-semibold text-slate-700 dark:text-slate-200"></span>
    `;
    
    // Insertar en la posición 8 del grid (después del 7mo elemento)
    if (summaryGrid.children.length >= 7) {
      summaryGrid.insertBefore(lastUpdateContainer, summaryGrid.children[7]);
    } else {
      summaryGrid.appendChild(lastUpdateContainer);
    }
    
    // Actualizar hora de última actualización
    updateLastUpdateTime();
  }

  summaryContainer.classList.remove("hidden");
};

const updateLastUpdateTime = () => {
  const lastUpdateElement = document.getElementById("last-update-time");
  if (!lastUpdateElement) {
    return;
  }
  
  const updateDateText = lastUpdateElement.querySelector("[data-update-date-text]");
  const updateTimeText = lastUpdateElement.querySelector("[data-update-time-text]");
  
  if (!updateDateText || !updateTimeText) {
    return;
  }

  const now = new Date();
  
  // Formatear fecha: "Jueves, 20 de noviembre de 2025"
  const dateOptions = {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  };
  const dateString = now.toLocaleDateString("es-AR", dateOptions);
  // Capitalizar primera letra del día y mes
  const formattedDate = dateString.charAt(0).toUpperCase() + dateString.slice(1);
  
  // Formatear hora: "15:01:45" (con segundos)
  const timeString = now.toLocaleTimeString("es-AR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false, // Formato 24 horas
  });
  
  updateDateText.textContent = formattedDate;
  updateTimeText.textContent = timeString;
};

const renderWidgets = (payload) => {
  if (isWorkspaceMode) {
    return;
  }
  if (!workspaceState.initialized) {
    setupWorkspaces();
  }
  const widgets = dashboardRoot.querySelectorAll("[data-widget-id]");
  widgets.forEach((widget) => {
    const config = getWidgetConfig(widget);
    const cacheKey = widget.dataset.widgetId;
    widgetDataCache.set(cacheKey, { data: payload.data, config });

    const widgetType = widget.dataset.widgetType;
    
    // Si es pivot-table, solo mostrar tabla (sin gráfico)
    if (widgetType === "pivot-table") {
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

  if (!resizeObserver && "ResizeObserver" in window) {
    resizeObserver = new ResizeObserver((entries) => {
      entries.forEach((entry) => {
        const widget = entry.target;
        const cacheKey = widget.dataset.widgetId;
        if (!cacheKey || !widgetDataCache.has(cacheKey)) {
          return;
        }
        const { data, config } = widgetDataCache.get(cacheKey);
        renderChart(widget, data, config);
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
  const slugs = wrappers.map(w => w.dataset.widgetSlug).filter(Boolean);
  
  if (slugs.length === 0) {
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
      body: JSON.stringify({ items: slugs }),
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
    const wrapper = document.createElement("div");
    wrapper.dataset.widgetWrapper = "true";
    wrapper.dataset.widgetIndex = String(index);
    wrapper.dataset.widgetSlug = slot.slug;
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

    section.innerHTML = `
      <header class="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
        <div class="flex items-center gap-2 flex-1">
          <!-- Handler visual para drag & drop -->
          <button type="button"
                  class="cursor-move text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
                  title="Arrastrar para reordenar"
                  style="pointer-events: none;">
            ⠿
          </button>
          <div class="flex flex-col gap-1">
            <h2 class="text-sm font-semibold text-slate-900 dark:text-white">${slot.name}</h2>
            <span class="text-[10px] text-slate-500 dark:text-slate-400">
              Última actualización: <span data-workspace-last-update>—</span>
            </span>
          </div>
        </div>
        <div class="flex items-center gap-2 text-[11px]">
          <a href="/reports/dashboard/${slot.slug}/" target="_blank" rel="noopener"
             class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white transition">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M7 7h10v10M17 7l-8 8" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Abrir
          </a>
          <button type="button" data-remove-from-workspace data-report-slug="${slot.slug}"
                  class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-rose-500 hover:text-rose-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-rose-400 transition">
            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M6 6l12 12M6 18L18 6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Quitar
          </button>
        </div>
      </header>
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

const attachWorkspaceRemovalHandlers = () => {
  if (!workspaceApiUrl) {
    return;
  }
  const buttons = dashboardRoot.querySelectorAll("[data-remove-from-workspace]");
  buttons.forEach((button) => {
    const slug = button.dataset.reportSlug;
    if (!slug) {
      return;
    }
    button.addEventListener("click", async () => {
      if (button.dataset.loading === "true") {
        return;
      }
      button.dataset.loading = "true";
      button.classList.add("opacity-60", "pointer-events-none");
      try {
        const response = await fetch(workspaceApiUrl, {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({ slug }),
        });
        if (!response.ok) {
          const detail = await response.json().catch(() => ({}));
          throw new Error(detail.detail || "No se pudo quitar el informe");
        }
        const payload = await response.json();
        setWorkspaceCount(payload.count ?? "-");
        toast("Informe eliminado del workspace");
        fetchWorkspaceData();
      } catch (error) {
        console.error(error);
        toast(error.message || "No se pudo quitar", "error");
        button.classList.remove("opacity-60", "pointer-events-none");
        button.dataset.loading = "false";
      }
    });
  });
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
  const config = getWidgetConfig(widget);
  console.log(`[loadWorkspaceSlot] Config para ${slot.slug}:`, config);
  
  // Mostrar animación de carga (siempre, incluso en auto-refresh para mejor UX)
  showWorkspaceWidgetLoading(widget);
  
  try {
    // Aumentar el límite para reportes que muestran tablas con detalles
    const isTableReport = slot.slug === "uninvoiced_remitos" || slot.slug === "pending_orders";
    const limit = isTableReport ? 1000 : 200;
    const requestBody = { slug: slot.slug, limit: limit };
    
    // Intentar cargar filtros guardados desde localStorage usando el slug del reporte
    // Esto aplica tanto para reportes declarativos como legacy
    let savedFilters = null;
    try {
      const storageKey = `report_filters_${slot.slug}`;
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
        // Incluir todos los campos excepto refresh_interval y otros metadatos
        if (key !== 'refresh_interval' && key !== 'realtime_active') {
          actualFilters[key] = savedFilters[key];
        }
      });
      // Solo usar si hay filtros reales (no solo metadatos)
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
        requestBody.filters = reportConfig.filters;
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
          "pending_orders",
          "sales_summary"
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
      
      // Limpiar solo el contenido (mantener header)
      const contentWrapper = widget.querySelector(".relative");
      if (contentWrapper) {
        contentWrapper.innerHTML = '';
      } else {
        // Si no existe el wrapper, crear uno
        const newWrapper = document.createElement("div");
        newWrapper.className = "relative";
        newWrapper.style.minHeight = "350px";
        widget.appendChild(newWrapper);
      }
      
      // Crear contenedor limpio para WidgetEngine dentro del wrapper
      const engineContainer = document.createElement("div");
      // En modo TV, usar flexbox para que las tablas se expandan correctamente
      if (isWorkspaceTv) {
        engineContainer.className = "w-full h-full flex flex-col";
        engineContainer.setAttribute("data-workspace-tv", "true");
      } else {
        engineContainer.className = "w-full h-full";
      }
      engineContainer.setAttribute("data-workspace-mode", "true"); // Marcar para que WidgetEngine oculte headers
      const wrapper = widget.querySelector(".relative") || widget;
      wrapper.appendChild(engineContainer);
      
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
    widgetDataCache.set(widgetId, { data, config });
    
    // Actualizar el título con el conteo para reportes específicos
    const reportSlug = slot.slug;
    if (reportSlug === "pending_orders" || reportSlug === "uninvoiced_remitos") {
      const titleElement = widget.querySelector("header h2");
      if (titleElement) {
        const baseName = slot.name;
        const count = data.length;
        titleElement.textContent = `${baseName}: ${count}`;
      }
    }
    
    const widgetType = widget.dataset.widgetType;
    
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
        if (reportSlug === "pending_orders" || reportSlug === "uninvoiced_remitos") {
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
  workspaceControls.fullscreen = document.querySelector("[data-fullscreen-toggle]");
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
  if (workspaceControls.fullscreen) {
    workspaceControls.fullscreen.addEventListener("click", toggleFullScreen);
    setFullscreenButtonState(false);
  }
  document.addEventListener("fullscreenchange", syncFullscreenState);
};

// Función para inicializar componentes de tags (debe estar en scope global antes del bloque if)
  const initializeTagsFilter = (fieldId, fieldType) => {
    const select = document.getElementById(fieldId);
    const container = document.getElementById(`${fieldId}_tags_container`);
    const chipsContainer = container?.querySelector(".tags-chips");
    const input = document.getElementById(`${fieldId}_search`);
    const dropdown = document.getElementById(`${fieldId}_dropdown`);
    
    if (!select || !container || !chipsContainer || !input || !dropdown) {
      return;
    }
    
    let allOptions = [];
    let selectedValues = new Set();
    let selectedIndex = -1;
    let searchTimeout = null;
    
    // Renderizar chips seleccionados
    const renderChips = () => {
      chipsContainer.innerHTML = "";
      selectedValues.forEach((value) => {
        const option = allOptions.find((opt) => opt.value === value);
        if (option) {
          const chip = document.createElement("div");
          chip.className = "inline-flex items-center gap-1 px-2 py-1 bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200 rounded-full text-xs font-medium";
          chip.dataset.value = value;
          
          const chipText = document.createElement("span");
          chipText.textContent = option.label;
          chip.appendChild(chipText);
          
          const chipRemove = document.createElement("button");
          chipRemove.type = "button";
          chipRemove.className = "ml-1 hover:text-sky-600 dark:hover:text-sky-300 focus:outline-none";
          chipRemove.innerHTML = "×";
          chipRemove.addEventListener("click", (e) => {
            e.stopPropagation();
            removeTag(value);
          });
          chip.appendChild(chipRemove);
          
          chipsContainer.appendChild(chip);
        }
      });
    };
    
    // Agregar tag
    const addTag = (value) => {
      if (!selectedValues.has(value)) {
        selectedValues.add(value);
        const option = select.querySelector(`option[value="${value}"]`);
        if (option) {
          option.selected = true;
        }
        renderChips();
        input.value = "";
        hideDropdown();
        updateSelect();
      }
    };
    
    // Remover tag
    const removeTag = (value) => {
      selectedValues.delete(value);
      const option = select.querySelector(`option[value="${value}"]`);
      if (option) {
        option.selected = false;
      }
      renderChips();
      updateSelect();
    };
    
    // Actualizar select hidden
    const updateSelect = () => {
      Array.from(select.options).forEach((opt) => {
        opt.selected = selectedValues.has(opt.value);
      });
      // Disparar evento change para que los filtros se actualicen
      select.dispatchEvent(new Event("change", { bubbles: true }));
      // Guardar filtros cuando cambian los tags
      if (typeof saveFilters === "function") {
        saveFilters();
      }
    };
    
    // Mostrar dropdown
    const showDropdown = () => {
      dropdown.classList.remove("hidden");
    };
    
    // Ocultar dropdown
    const hideDropdown = () => {
      dropdown.classList.add("hidden");
      selectedIndex = -1;
    };
    
    // Renderizar dropdown
    const renderDropdown = (results, query) => {
      dropdown.innerHTML = "";
      
      if (results.length === 0) {
        const noResults = document.createElement("div");
        noResults.className = "px-3 py-2 text-xs text-slate-500 dark:text-slate-400";
        noResults.textContent = query ? "No se encontraron resultados" : "Escribe para buscar...";
        dropdown.appendChild(noResults);
        return;
      }
      
      results.forEach((item, index) => {
        const isSelected = selectedValues.has(item.value);
        const itemDiv = document.createElement("div");
        itemDiv.className = `px-3 py-2 text-xs cursor-pointer transition-colors ${
          index === selectedIndex
            ? "bg-sky-100 dark:bg-sky-900"
            : "hover:bg-slate-100 dark:hover:bg-slate-700"
        } ${isSelected ? "bg-sky-50 dark:bg-sky-950" : ""}`;
        itemDiv.dataset.value = item.value;
        
        const itemContent = document.createElement("div");
        itemContent.className = "flex items-center justify-between";
        
        const itemLabel = document.createElement("span");
        itemLabel.className = isSelected ? "font-medium text-sky-700 dark:text-sky-300" : "text-slate-700 dark:text-slate-300";
        itemLabel.textContent = item.label;
        itemContent.appendChild(itemLabel);
        
        if (isSelected) {
          const checkIcon = document.createElement("span");
          checkIcon.className = "text-sky-600 dark:text-sky-400";
          checkIcon.textContent = "✓";
          itemContent.appendChild(checkIcon);
        }
        
        itemDiv.appendChild(itemContent);
        
        itemDiv.addEventListener("click", () => {
          if (isSelected) {
            removeTag(item.value);
          } else {
            addTag(item.value);
          }
        });
        
        dropdown.appendChild(itemDiv);
      });
      
      showDropdown();
    };
    
    // Buscar opciones
    const searchOptions = (query) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        const filtered = allOptions.filter((opt) =>
          opt.label.toLowerCase().includes(query.toLowerCase())
        );
        renderDropdown(filtered, query);
      }, 150);
    };
    
    // Event listeners
    input.addEventListener("input", (e) => {
      const query = e.target.value.trim();
      if (query.length > 0) {
        searchOptions(query);
      } else {
        renderDropdown(allOptions.slice(0, 20), "");
      }
    });
    
    input.addEventListener("focus", () => {
      if (input.value.trim().length === 0) {
        renderDropdown(allOptions.slice(0, 20), "");
      } else {
        searchOptions(input.value.trim());
      }
    });
    
    input.addEventListener("keydown", (e) => {
      const items = dropdown.querySelectorAll("[data-value]");
      
      if (e.key === "ArrowDown") {
        e.preventDefault();
        selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
        items[selectedIndex]?.scrollIntoView({ block: "nearest" });
        renderDropdown(
          allOptions.filter((opt) =>
            opt.label.toLowerCase().includes(input.value.toLowerCase())
          ),
          input.value
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selectedIndex = Math.max(selectedIndex - 1, -1);
        if (selectedIndex >= 0) {
          items[selectedIndex]?.scrollIntoView({ block: "nearest" });
        }
        renderDropdown(
          allOptions.filter((opt) =>
            opt.label.toLowerCase().includes(input.value.toLowerCase())
          ),
          input.value
        );
      } else if (e.key === "Enter" && selectedIndex >= 0 && items[selectedIndex]) {
        e.preventDefault();
        const value = items[selectedIndex].dataset.value;
        if (selectedValues.has(value)) {
          removeTag(value);
        } else {
          addTag(value);
        }
      } else if (e.key === "Escape") {
        hideDropdown();
        input.blur();
      }
    });
    
    // Cerrar dropdown al hacer clic fuera
    document.addEventListener("click", (e) => {
      if (!container.contains(e.target)) {
        hideDropdown();
      }
    });
    
    // Cargar opciones desde el select
    const loadOptions = () => {
      allOptions = Array.from(select.options)
        .filter((opt) => opt.value !== "")
        .map((opt) => ({
          value: opt.value,
          label: opt.textContent,
        }));
      
      // Cargar selecciones existentes
      Array.from(select.selectedOptions).forEach((opt) => {
        if (opt.value) {
          selectedValues.add(opt.value);
        }
      });
      
      renderChips();
    };
    
    // Observar cambios en el select para actualizar chips
    const observer = new MutationObserver(() => {
      loadOptions();
    });
    observer.observe(select, { childList: true, subtree: true });
    
    // Escuchar cambios en el select para actualizar tags visuales
    select.addEventListener("change", () => {
      loadOptions();
    });
    
    // Cargar opciones iniciales
    loadOptions();
  };
  
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

  const updateWorkspaceRealtimeUI = (active) => {
    const label = realtimeButton.querySelector("[data-realtime-label]");
    const indicator = realtimeButton.querySelector("[data-realtime-indicator]");
    const icon = realtimeButton.querySelector("[data-realtime-icon]");
    
    if (active) {
      realtimeButton.classList.remove("text-slate-400", "hover:text-slate-300", "border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800");
      realtimeButton.classList.add("text-green-500", "hover:text-green-400", "bg-green-500/10", "border-green-500");
      if (label) label.textContent = "Tiempo real";
      if (indicator) {
        indicator.classList.remove("opacity-0");
        indicator.classList.add("opacity-100", "animate-pulse");
      }
      if (icon) {
        icon.setAttribute("stroke", "currentColor");
      }
    } else {
      realtimeButton.classList.remove("text-green-500", "hover:text-green-400", "bg-green-500/10", "border-green-500");
      realtimeButton.classList.add("text-slate-400", "hover:text-slate-300", "border-slate-300", "dark:border-slate-600", "bg-white", "dark:bg-slate-800");
      if (label) label.textContent = "Tiempo real";
      if (indicator) {
        indicator.classList.add("opacity-0");
        indicator.classList.remove("opacity-100", "animate-pulse");
      }
      if (icon) {
        icon.setAttribute("stroke", "currentColor");
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
    
    if (reportSlug !== "ventas_netas" && reportSlug !== "cash_flow_waterfall" && reportSlug !== "cash_flow_by_account" && reportSlug !== "uninvoiced_remitos") {
      return;
    }
    
    try {
      // Cargar puntos de venta
      const pvResponse = await fetch(`${apiUrl.replace('/query/', '/filters/')}?type=puntos_venta`, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      // Cargar filtros guardados ANTES de cargar las opciones
      const savedFilters = loadFilters();
      
      if (pvResponse.ok) {
        const pvData = await pvResponse.json();
        const pvSelect = document.getElementById("punto_venta");
        if (pvSelect) {
          pvSelect.innerHTML = "";
          pvData.puntos_venta?.forEach((pv) => {
            const option = document.createElement("option");
            option.value = pv.value;
            option.textContent = pv.label;
            // Marcar como seleccionado si está en los filtros guardados
            if (savedFilters && savedFilters.punto_venta && Array.isArray(savedFilters.punto_venta)) {
              if (savedFilters.punto_venta.includes(pv.value)) {
                option.selected = true;
              }
            }
            pvSelect.appendChild(option);
          });
          // Inicializar componente de tags (ya con las selecciones aplicadas)
          initializeTagsFilter("punto_venta", "puntos_venta");
        }
      }
      
      // Cargar sucursales
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
            // Marcar como seleccionado si está en los filtros guardados
            if (savedFilters && savedFilters.sucursales && Array.isArray(savedFilters.sucursales)) {
              if (savedFilters.sucursales.includes(suc.value)) {
                option.selected = true;
              }
            }
            sucSelect.appendChild(option);
          });
          // Inicializar componente de tags (ya con las selecciones aplicadas)
          initializeTagsFilter("sucursales", "sucursales");
        }
      }
      
      // Aplicar otros filtros guardados (fechas, mes actual)
      if (savedFilters) {
        applyFilters(savedFilters);
      }
    } catch (error) {
      console.error("Error cargando opciones de filtros:", error);
    }
    
    // Cargar cajas para cash_flow_waterfall y cash_flow_by_account
    if (reportSlug === "cash_flow_waterfall" || reportSlug === "cash_flow_by_account") {
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

  const setupPeriodoTipo = () => {
    const buttons = document.querySelectorAll(".periodo-tipo-btn");
    const periodoTipoSelect = document.getElementById("periodo_tipo");
    const fechaInicioInput = document.getElementById("fecha_inicio");
    const fechaFinInput = document.getElementById("fecha_fin");
    
    // Solo aplicar si existen estos elementos (ventas_netas, cash_flow_waterfall, cash_flow_by_account, uninvoiced_remitos o pending_orders)
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (reportSlug !== "ventas_netas" && reportSlug !== "cash_flow_waterfall" && reportSlug !== "cash_flow_by_account" && reportSlug !== "uninvoiced_remitos" && reportSlug !== "pending_orders" && reportSlug !== "sales_summary") {
      return;
    }
    if (!buttons.length || !periodoTipoSelect || !fechaInicioInput || !fechaFinInput) {
      return;
    }
    
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
      if (summaryPeriodElement && fechaInicioInput.value && fechaFinInput.value) {
        const formatDate = (dateStr) => {
          const [year, month, day] = dateStr.split('-');
          return `${day}-${month}-${year}`;
        };
        summaryPeriodElement.textContent = `Periodo ${formatDate(fechaInicioInput.value)} al ${formatDate(fechaFinInput.value)}`;
      }
      
      // Guardar filtros cuando cambia
      saveFilters();
      
      // Si estamos en vista por caja, recargar datos (solo para cash_flow_waterfall)
      const reportSlug = dashboardRoot?.dataset?.reportSlug;
      if (reportSlug === "cash_flow_waterfall") {
        const savedViewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
        if (savedViewType === "por_caja") {
          fetchByAccountData();
        }
      } else if (reportSlug === "cash_flow_by_account" || reportSlug === "sales_summary") {
        // Para cash_flow_by_account y sales_summary, recargar datos directamente
        fetchDashboardData();
      }
    };
    
    // Inicializar estado basado en el select oculto
    // reportSlug ya está declarado arriba, no redeclarar
    
    // En workspace, cash_flow_waterfall y cash_flow_by_account siempre deben mostrar mes en curso
    if (isWorkspaceMode && (reportSlug === "cash_flow_waterfall" || reportSlug === "cash_flow_by_account")) {
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
    fechaInicioInput.addEventListener("change", () => {
      if (periodoTipoSelect.value === "personalizado") {
      saveFilters();
        // Actualizar período en el título
        const summaryPeriodElement = document.getElementById("summary-period");
        if (summaryPeriodElement && fechaInicioInput.value && fechaFinInput.value) {
          const formatDate = (dateStr) => {
            const [year, month, day] = dateStr.split('-');
            return `${day}-${month}-${year}`;
          };
          summaryPeriodElement.textContent = `Periodo ${formatDate(fechaInicioInput.value)} al ${formatDate(fechaFinInput.value)}`;
        }
        // Si estamos en vista por caja, recargar datos
        const reportSlug = dashboardRoot?.dataset?.reportSlug;
        if (reportSlug === "cash_flow_waterfall") {
          const savedViewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
          if (savedViewType === "por_caja") {
            fetchByAccountData();
          }
        } else if (reportSlug === "sales_summary") {
          fetchDashboardData();
        }
      }
    });
    fechaFinInput.addEventListener("change", () => {
      if (periodoTipoSelect.value === "personalizado") {
      saveFilters();
        // Actualizar período en el título
        const summaryPeriodElement = document.getElementById("summary-period");
        if (summaryPeriodElement && fechaInicioInput.value && fechaFinInput.value) {
          const formatDate = (dateStr) => {
            const [year, month, day] = dateStr.split('-');
            return `${day}-${month}-${year}`;
          };
          summaryPeriodElement.textContent = `Periodo ${formatDate(fechaInicioInput.value)} al ${formatDate(fechaFinInput.value)}`;
        }
        // Si estamos en vista por caja, recargar datos
        const reportSlug = dashboardRoot?.dataset?.reportSlug;
        if (reportSlug === "cash_flow_waterfall") {
          const savedViewType = localStorage.getItem(`view_type_${reportSlug}`) || "consolidada";
          if (savedViewType === "por_caja") {
            fetchByAccountData();
          }
        } else if (reportSlug === "sales_summary") {
          fetchDashboardData();
        }
      }
    });
  };

  const setupCashFlowFilters = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (reportSlug !== "cash_flow_waterfall" && reportSlug !== "cash_flow_by_account") {
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
    
    byAccountContent.innerHTML = tableHTML;
  };

  const getStorageKey = () => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!reportSlug) return null;
    return `report_filters_${reportSlug}`;
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

  const applyFilters = (filters) => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (!filters || !reportSlug || (reportSlug !== "ventas_netas" && reportSlug !== "cash_flow_waterfall" && reportSlug !== "cash_flow_by_account")) return;

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

    // Aplicar filtros específicos de ventas_netas
    if (reportSlug === "ventas_netas") {
      // Los puntos de venta y sucursales ya se aplicaron al crear las opciones
      // Solo necesitamos disparar eventos para actualizar los tags visuales si ya están inicializados
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

  // Declarar getFilters en el scope global para que esté disponible en fetchDetailedMovements
  window.getFilters = () => {
    const filters = {};
    const currentReportSlug = dashboardRoot?.dataset?.reportSlug;
    
    if (currentReportSlug === "ventas_netas") {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      const puntoVentaSelect = document.getElementById("punto_venta");
      const sucursalesSelect = document.getElementById("sucursales");
      
      // Establecer fechas según el tipo de período seleccionado
      const today = new Date();
      if (periodoTipo === "dia_actual") {
        const todayStr = today.toISOString().split('T')[0];
        filters.fecha_inicio = todayStr;
        filters.fecha_fin = todayStr;
        filters.dia_actual = true;
      } else if (periodoTipo === "mes_actual") {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.mes_actual = true;
      } else if (periodoTipo === "año_actual") {
        const firstDay = new Date(today.getFullYear(), 0, 1);
        const lastDay = new Date(today.getFullYear(), 11, 31);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.año_actual = true;
      } else {
        // Personalizado: usar las fechas ingresadas manualmente
      if (fechaInicio && fechaFin) {
        filters.fecha_inicio = fechaInicio;
        filters.fecha_fin = fechaFin;
        } else {
          // Si no hay fechas, usar mes actual por defecto
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        }
      }
      
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
    } else if (currentReportSlug === "uninvoiced_remitos") {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      const puntoVentaSelect = document.getElementById("punto_venta");
      const sucursalesSelect = document.getElementById("sucursales");
      
      // Establecer fechas según el tipo de período seleccionado
      const today = new Date();
      if (periodoTipo === "dia_actual") {
        const todayStr = today.toISOString().split('T')[0];
        filters.fecha_inicio = todayStr;
        filters.fecha_fin = todayStr;
        filters.dia_actual = true;
      } else if (periodoTipo === "mes_actual") {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.mes_actual = true;
      } else if (periodoTipo === "año_actual") {
        const firstDay = new Date(today.getFullYear(), 0, 1);
        const lastDay = new Date(today.getFullYear(), 11, 31);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.año_actual = true;
      } else {
        // Personalizado: usar las fechas ingresadas manualmente
      if (fechaInicio && fechaFin) {
        filters.fecha_inicio = fechaInicio;
        filters.fecha_fin = fechaFin;
        } else {
          // Si no hay fechas, usar mes actual por defecto
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        }
      }
      
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
    } else if (currentReportSlug === "pending_orders") {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      
      // Establecer fechas según el tipo de período seleccionado
        const today = new Date();
      if (periodoTipo === "dia_actual") {
        const todayStr = today.toISOString().split('T')[0];
        filters.fecha_inicio = todayStr;
        filters.fecha_fin = todayStr;
        filters.dia_actual = true;
      } else if (periodoTipo === "mes_actual") {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.mes_actual = true;
      } else if (periodoTipo === "año_actual") {
        const firstDay = new Date(today.getFullYear(), 0, 1);
        const lastDay = new Date(today.getFullYear(), 11, 31);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.año_actual = true;
      } else {
        // Personalizado: usar las fechas ingresadas manualmente
        if (fechaInicio && fechaFin) {
          filters.fecha_inicio = fechaInicio;
          filters.fecha_fin = fechaFin;
        } else {
          // Si no hay fechas, usar mes actual por defecto
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        }
      }
      
      // Obtener refresh_interval del filtro
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) {
        filters.refresh_interval = refreshIntervalSelect.value;
      }
    } else if (currentReportSlug === "sales_summary") {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      
      // Establecer fechas según el tipo de período seleccionado
      const today = new Date();
      if (periodoTipo === "dia_actual") {
        const todayStr = today.toISOString().split('T')[0];
        filters.fecha_inicio = todayStr;
        filters.fecha_fin = todayStr;
        filters.dia_actual = true;
      } else if (periodoTipo === "mes_actual") {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.mes_actual = true;
      } else if (periodoTipo === "año_actual") {
        const firstDay = new Date(today.getFullYear(), 0, 1);
        const lastDay = new Date(today.getFullYear(), 11, 31);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.año_actual = true;
      } else {
        // Personalizado: usar las fechas ingresadas manualmente
        if (fechaInicio && fechaFin) {
          filters.fecha_inicio = fechaInicio;
          filters.fecha_fin = fechaFin;
        } else {
          // Si no hay fechas, usar mes actual por defecto
          const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
          const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
          filters.fecha_inicio = firstDay.toISOString().split('T')[0];
          filters.fecha_fin = lastDay.toISOString().split('T')[0];
        }
      }
      
      // Obtener refresh_interval del filtro
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) {
        filters.refresh_interval = refreshIntervalSelect.value;
      }
    } else if (currentReportSlug === "cash_flow_waterfall" || currentReportSlug === "cash_flow_by_account") {
      const periodoTipo = document.getElementById("periodo_tipo")?.value || "personalizado";
      const fechaInicio = document.getElementById("fecha_inicio")?.value;
      const fechaFin = document.getElementById("fecha_fin")?.value;
      const idCajaSelect = document.getElementById("id_caja");
      
      // Establecer fechas según el tipo de período seleccionado
      const today = new Date();
      if (periodoTipo === "dia_actual") {
        const todayStr = today.toISOString().split('T')[0];
        filters.fecha_inicio = todayStr;
        filters.fecha_fin = todayStr;
        filters.dia_actual = true;
      } else if (periodoTipo === "mes_actual") {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.mes_actual = true;
      } else if (periodoTipo === "año_actual") {
        const firstDay = new Date(today.getFullYear(), 0, 1);
        const lastDay = new Date(today.getFullYear(), 11, 31);
        filters.fecha_inicio = firstDay.toISOString().split('T')[0];
        filters.fecha_fin = lastDay.toISOString().split('T')[0];
        filters.año_actual = true;
      } else {
        // Personalizado: usar las fechas ingresadas manualmente
        if (fechaInicio && fechaFin) {
          filters.fecha_inicio = fechaInicio;
          filters.fecha_fin = fechaFin;
        } else {
          // Si no hay fechas, usar mes actual por defecto
          const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
          const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
          filters.fecha_inicio = firstDay.toISOString().split('T')[0];
          filters.fecha_fin = lastDay.toISOString().split('T')[0];
        }
      }
      
      // Obtener refresh_interval del filtro
      const refreshIntervalSelect = document.getElementById("refresh_interval");
      if (refreshIntervalSelect) {
        filters.refresh_interval = refreshIntervalSelect.value;
      }
      
      // Caja (opcional) - puede ser array si se seleccionan múltiples
      if (idCajaSelect) {
        const selectedCajas = Array.from(idCajaSelect.selectedOptions).map(opt => opt.value).filter(v => v);
        if (selectedCajas.length > 0) {
          filters.id_caja = selectedCajas;
        }
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

  const fetchDashboardData = async (isAutoRefresh = false) => {
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    const apiUrl = dashboardRoot?.dataset?.dashboardUrl;
    if (!reportSlug || !apiUrl) {
      return;
    }
    try {
      // Solo mostrar animación de carga si no es una actualización automática
      if (!isAutoRefresh) {
        showLoadingAnimation();
      }
      
      const filters = getFilters();
      
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          slug: reportSlug,
          limit: 200,
          filters: filters,
        }),
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
        renderSummary(payload.meta || {}, payload.totals || {});
        
        const currentReportSlug = dashboardRoot?.dataset?.reportSlug;
        
        // Para cash_flow_by_account, renderizar tabla directamente en lugar de widgets
        if (currentReportSlug === "cash_flow_by_account") {
          const tableContent = document.getElementById("by-account-table-content");
          if (tableContent) {
            renderByAccountTable(payload.data || [], payload.totals || {}, tableContent);
          }
        } else {
          // Para otros reportes, usar widgets normales
        renderWidgets(payload);
          
          // Cargar movimientos detallados si es cash_flow_waterfall
          if (currentReportSlug === "cash_flow_waterfall") {
            fetchDetailedMovements();
          }
        }
        
        // Solo mostrar toast si no es una actualización automática
        if (!isAutoRefresh) {
          toast("Datos del dashboard actualizados");
        }
      }, 100);
    } catch (error) {
      if (!isAutoRefresh) {
        hideLoadingAnimation();
      }
      console.error("Error en fetchDashboardData:", error);
      const errorMsg = error.message || "Error al sincronizar datos";
      // Solo mostrar error si no es auto-refresh o si es un error crítico
      if (!isAutoRefresh) {
        toast(errorMsg, "error");
      }
    }
  };

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

    const updateRealtimeUI = (active) => {
      const label = realtimeButton.querySelector("[data-realtime-label]");
      const indicator = realtimeButton.querySelector("[data-realtime-indicator]");
      const icon = realtimeButton.querySelector("[data-realtime-icon]");
      
      if (active) {
        realtimeButton.classList.remove("text-slate-400", "hover:text-slate-300");
        realtimeButton.classList.add("text-green-500", "hover:text-green-400", "bg-green-500/10");
        if (label) label.textContent = "Tiempo real";
        if (indicator) {
          indicator.classList.remove("opacity-0");
          indicator.classList.add("opacity-100", "animate-pulse");
        }
        if (icon) {
          icon.setAttribute("stroke", "currentColor");
        }
      } else {
        realtimeButton.classList.remove("text-green-500", "hover:text-green-400", "bg-green-500/10");
        realtimeButton.classList.add("text-white", "hover:text-white/90");
        if (label) label.textContent = "Tiempo real";
        if (indicator) {
          indicator.classList.add("opacity-0");
          indicator.classList.remove("opacity-100", "animate-pulse");
        }
        if (icon) {
          icon.setAttribute("stroke", "currentColor");
        }
      }
      realtimeButton.setAttribute("data-realtime-active", String(active));
    };

    // Cargar estado guardado
    const reportSlug = dashboardRoot?.dataset?.reportSlug;
    if (reportSlug) {
      const savedRealtimeState = localStorage.getItem(`realtime_${reportSlug}`);
      if (savedRealtimeState === "true") {
        realtimeActive = true;
        updateRealtimeUI(true);
        const currentInterval = getCurrentRefreshInterval();
        startRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
      } else {
        // Inicializar como inactivo con color blanco
        realtimeActive = false;
        updateRealtimeUI(false);
      }
    } else {
      // Si no hay reportSlug, inicializar como inactivo
      realtimeActive = false;
      updateRealtimeUI(false);
    }

    const toggleRealtime = () => {
      realtimeActive = !realtimeActive;
      
      if (realtimeActive) {
        const currentInterval = getCurrentRefreshInterval();
        startRealtime((typeof getRefreshIntervalMs === 'function' ? getRefreshIntervalMs : getRefreshIntervalMsLocal)(currentInterval));
        localStorage.setItem(`realtime_${reportSlug}`, "true");
      } else {
        stopRealtime();
        localStorage.setItem(`realtime_${reportSlug}`, "false");
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
    newExportButton.addEventListener("click", async () => {
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
          if (reportSlug === 'ventas_netas' || reportSlug === 'uninvoiced_remitos') {
            const puntoVentaSelect = filtersContainer.querySelector('select[name="punto_venta"]');
            const sucursalesSelect = filtersContainer.querySelector('select[name="sucursales"]');
            
            if (puntoVentaSelect && puntoVentaSelect.value) {
              filters.punto_venta = Array.from(puntoVentaSelect.selectedOptions).map(opt => opt.value);
            }
            if (sucursalesSelect && sucursalesSelect.value) {
              filters.sucursales = Array.from(sucursalesSelect.selectedOptions).map(opt => opt.value);
            }
          }
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
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${reportSlug}_${new Date().toISOString().split('T')[0]}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        // Mostrar mensaje de éxito
        toast("Reporte exportado exitosamente", "success");
        
        // Restaurar botón
        newExportButton.disabled = false;
        newExportButton.innerHTML = originalContent;
      } catch (error) {
        console.error("Error exportando reporte:", error);
        toast(`Error al exportar: ${error.message}`, "error");
        
        // Restaurar botón
        newExportButton.disabled = false;
        const originalContent = newExportButton.innerHTML;
        newExportButton.innerHTML = `
          <svg class="w-3.5 h-3.5 sm:w-4 sm:h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 3v12m0 0l-4-4m4 4l4-4M3 21h18" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <span class="hidden sm:inline">Exportar Excel</span>
        `;
      }
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
    // Cargar opciones de filtros primero
    loadFilterOptions().then(() => {
      setupPeriodoTipo();
      setupRefreshIntervalButtons();
      setupCashFlowFilters();
      fetchDashboardData();
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
  // Buscar todos los widgets y re-renderizarlos
  const widgets = document.querySelectorAll('[data-widget-id]');
  widgets.forEach((widget) => {
    const widgetId = widget.dataset.widgetId;
    const cachedData = widgetDataCache.get(widgetId);
    if (cachedData && cachedData.data) {
      try {
        const config = getWidgetConfig(widget);
        if (config) {
          renderChart(widget, cachedData.data, config);
        }
      } catch (error) {
        console.warn('Error re-rendering chart for widget', widgetId, error);
      }
    }
  });
  
  // También re-renderizar widgets en modo workspace si están activos
  if (isWorkspaceMode && workspaceState.initialized) {
    // Los widgets en workspace se actualizan automáticamente cuando se recarga el workspace
    // pero podemos forzar una actualización si es necesario
    const workspaceWidgets = document.querySelectorAll('[data-widget-wrapper]');
    workspaceWidgets.forEach((wrapper) => {
      const widget = wrapper.querySelector('[data-widget-id]');
      if (widget) {
        const widgetId = widget.dataset.widgetId;
        const cachedData = widgetDataCache.get(widgetId);
        if (cachedData && cachedData.data) {
          try {
            const config = getWidgetConfig(widget);
            if (config) {
              renderChart(widget, cachedData.data, config);
            }
          } catch (error) {
            console.warn('Error re-rendering workspace chart for widget', widgetId, error);
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


