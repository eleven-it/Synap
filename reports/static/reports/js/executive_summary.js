/**
 * Panel Resumen ejecutivo (ventas): KPIs, gráficos d3, modal clasificación por sucursal.
 */
(function () {
  const cfg = window.EXEC_CONFIG || {};
  const summaryUrl = cfg.summaryUrl || "";
  const sucursalCanalUrl = cfg.sucursalCanalUrl || cfg.pvCanalUrl || "";
  let sucursalesTagsReady = false;
  let puntosVentaTagsReady = false;
  const FILTERS_API_URL = "/api/reports/filters/";

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }

  const fmtMoney = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  });

  function fmtPct(v) {
    if (v === null || v === undefined || Number.isNaN(v)) return "N/D";
    const sign = v > 0 ? "+" : "";
    return `${sign}${v.toFixed(2)} %`;
  }

  /** Porcentaje de margen sobre venta (sin signo forzado salvo el numérico). */
  function fmtMargenSobreVentaPct(v) {
    if (v === null || v === undefined || Number.isNaN(v)) return "N/D";
    return `${Number(v).toFixed(2)} %`;
  }

  const el = (id) => document.getElementById(id);

  /** Última carga de la API para redibujar gráficos al cambiar viewport. */
  let cachedChartData = null;
  let chartResizeObserver = null;
  let resizeChartsTimer = null;

  const SECCIONES = [
    {
      key: "consolidado",
      label: "Consolidado",
      accent: "indigo",
      icon: "hub",
      editableAnio: true,
      showGear: true,
      subtitle: "Suma mayorista + minorista (solo sucursales clasificadas)",
    },
    { key: "mayorista", label: "Mayorista", accent: "amber", icon: "warehouse" },
    { key: "minorista", label: "Minorista (Salón)", accent: "emerald", icon: "storefront" },
  ];

  function formatFechaEs(iso) {
    if (!iso || typeof iso !== "string") return "";
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
    if (!m) return iso;
    return `${m[3]}/${m[2]}/${m[1]}`;
  }

  function debounceRedrawCharts() {
    if (resizeChartsTimer) clearTimeout(resizeChartsTimer);
    resizeChartsTimer = setTimeout(() => {
      resizeChartsTimer = null;
      if (cachedChartData) renderAllCharts(cachedChartData);
    }, 120);
  }

  function ensureChartResizeObserver() {
    if (typeof ResizeObserver === "undefined") return;
    if (chartResizeObserver) return;
    const root = el("exec-secciones");
    if (!root) return;
    chartResizeObserver = new ResizeObserver(() => debounceRedrawCharts());
    chartResizeObserver.observe(root);
    window.addEventListener("orientationchange", debounceRedrawCharts, { passive: true });
  }

  function setLoading(show) {
    const n = el("exec-loading");
    if (n) n.classList.toggle("hidden", !show);
  }

  function showError(msg) {
    const box = el("exec-error");
    if (!box) return;
    box.textContent = msg || "";
    box.classList.toggle("hidden", !msg);
  }

  /** @typedef {{ icon?: string, accent?: string, span?: string, valueClass?: string }} KpiOpts */

  const KPI_THEME = {
    sky: {
      bar: "from-sky-500 to-cyan-400",
      icon: "bg-sky-500/15 text-sky-600 dark:bg-sky-500/20 dark:text-sky-400",
    },
    indigo: {
      bar: "from-indigo-500 to-violet-500",
      icon: "bg-indigo-500/15 text-indigo-600 dark:bg-indigo-500/20 dark:text-indigo-400",
    },
    emerald: {
      bar: "from-emerald-500 to-teal-500",
      icon: "bg-emerald-500/15 text-emerald-600 dark:bg-emerald-500/20 dark:text-emerald-400",
    },
    amber: {
      bar: "from-amber-500 to-orange-500",
      icon: "bg-amber-500/15 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300",
    },
    purple: {
      bar: "from-purple-500 to-indigo-600",
      icon: "bg-purple-500/15 text-purple-600 dark:bg-purple-500/20 dark:text-purple-400",
    },
    slate: {
      bar: "from-slate-500 to-slate-600",
      icon: "bg-slate-500/15 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
    },
    teal: {
      bar: "from-teal-500 to-emerald-500",
      icon: "bg-teal-500/15 text-teal-600 dark:bg-teal-500/20 dark:text-teal-400",
    },
  };

  /**
   * @param {string} title
   * @param {string} valueHtml
   * @param {KpiOpts} [opts]
   */
  function kpiCard(title, valueHtml, opts) {
    const o = opts || {};
    const icon = o.icon || "insights";
    const key = o.accent && KPI_THEME[o.accent] ? o.accent : "sky";
    const theme = KPI_THEME[key];
    const span = o.span || "";
    const vc = o.valueClass || "text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl";
    return `
      <div class="group relative overflow-hidden rounded-2xl border border-slate-200/90 bg-white p-4 shadow-md shadow-slate-200/40 transition duration-300 hover:-translate-y-0.5 hover:border-slate-300 hover:shadow-lg dark:border-slate-700/90 dark:bg-slate-900 dark:shadow-black/25 dark:hover:border-slate-600 ${span}">
        <div class="pointer-events-none absolute inset-y-0 left-0 w-1 bg-gradient-to-b ${theme.bar} opacity-95"></div>
        <div class="flex items-start justify-between gap-2 pl-1">
          <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">${title}</p>
          <span class="material-icons flex-shrink-0 rounded-xl ${theme.icon} p-1.5 text-lg leading-none" aria-hidden="true">${icon}</span>
        </div>
        <div class="mt-2 pl-1 ${vc}">${valueHtml}</div>
      </div>`;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pctValueHtml(v) {
    if (v === null || v === undefined || Number.isNaN(v)) {
      return `<span class="text-slate-400">N/D</span>`;
    }
    const up = v > 0;
    const down = v < 0;
    const badgeCls = up
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300"
      : down
        ? "bg-red-100 text-red-800 dark:bg-red-950/80 dark:text-red-300"
        : "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
    const ic = up ? "trending_up" : down ? "trending_down" : "trending_flat";
    return `
      <div class="flex flex-wrap items-center gap-2">
        <span>${fmtPct(v)}</span>
        <span class="inline-flex items-center gap-0.5 rounded-lg px-2 py-0.5 text-xs font-semibold ${badgeCls}">
          <span class="material-icons text-sm leading-none" aria-hidden="true">${ic}</span>
        </span>
      </div>`;
  }

  /** KPI «Vs ayer»: porcentaje existente + diferencia en moneda (``gap_vs_ayer_monto``). */
  function vsAyerValueHtml(k) {
    const pctBlock = pctValueHtml(k.pct_vs_ayer);
    const gap = k.gap_vs_ayer_monto;
    if (gap === null || gap === undefined || Number.isNaN(Number(gap))) {
      return pctBlock;
    }
    const gapNum = Number(gap);
    const up = gapNum > 0;
    const down = gapNum < 0;
    const subCls = up
      ? "text-emerald-700 dark:text-emerald-300"
      : down
        ? "text-red-700 dark:text-red-300"
        : "text-slate-600 dark:text-slate-400";
    const gapTxt = fmtMoney.format(gapNum);
    return `
      <div class="flex flex-col gap-1.5">
        ${pctBlock}
        <div class="text-sm font-semibold tabular-nums ${subCls}">${gapTxt} <span class="font-normal text-slate-500 dark:text-slate-400">vs ayer</span></div>
      </div>`;
  }

  function staggerKpiGrid(sectionKey) {
    const grid = el(`exec-kpi-grid-${sectionKey}`);
    if (!grid) return;
    grid.querySelectorAll(":scope > div").forEach((node, i) => {
      node.classList.add("exec-kpi-animate");
      node.style.animationDelay = `${i * 50}ms`;
    });
  }

  function vsSemanaValueHtml(k) {
    const pctBlock = pctValueHtml(k.pct_vs_misma_semana_anterior);
    const gap = k.gap_vs_misma_semana_anterior_monto;
    if (gap === null || gap === undefined || Number.isNaN(Number(gap))) return pctBlock;
    const gapNum = Number(gap);
    const up = gapNum > 0;
    const down = gapNum < 0;
    const subCls = up
      ? "text-emerald-700 dark:text-emerald-300"
      : down
        ? "text-red-700 dark:text-red-300"
        : "text-slate-600 dark:text-slate-400";
    return `
      <div class="flex flex-col gap-1.5">
        ${pctBlock}
        <div class="text-sm font-semibold tabular-nums ${subCls}">${fmtMoney.format(gapNum)} <span class="font-normal text-slate-500 dark:text-slate-400">vs sem. ant.</span></div>
      </div>`;
  }

  function vsAnioAnteriorValueHtml(k, editable, meta) {
    const pctBlock = pctValueHtml(k.pct_vs_anio_anterior);
    const gap = k.gap_vs_anio_anterior_monto;
    const fechaComp =
      k.fecha_comparacion_anio_anterior || meta?.fecha_comparacion_anio_anterior_aplicada || "";
    const ventasRef = k.ventas_anio_anterior_monto;
    let gapBlock = "";
    if (gap !== null && gap !== undefined && !Number.isNaN(Number(gap))) {
      const gapNum = Number(gap);
      const up = gapNum > 0;
      const down = gapNum < 0;
      const subCls = up
        ? "text-emerald-700 dark:text-emerald-300"
        : down
          ? "text-red-700 dark:text-red-300"
          : "text-slate-600 dark:text-slate-400";
      gapBlock = `<div class="text-sm font-semibold tabular-nums ${subCls}">${fmtMoney.format(gapNum)} <span class="font-normal text-slate-500 dark:text-slate-400">vs fecha elegida</span></div>`;
    }
    const refTxt =
      ventasRef != null && !Number.isNaN(Number(ventasRef))
        ? `Referencia: ${fmtMoney.format(Number(ventasRef))} el ${formatFechaEs(fechaComp)}`
        : `Fecha de referencia: ${formatFechaEs(fechaComp)}`;
    if (editable) {
      const val = fechaComp || meta?.fecha_comparacion_anio_anterior_defecto || "";
      return `
        <div class="flex flex-col gap-2">
          ${pctBlock}
          ${gapBlock}
          <label class="text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400" for="exec-fecha-comparacion-anio">Fecha de comparación</label>
          <input type="date" id="exec-fecha-comparacion-anio" value="${escapeHtml(val)}" class="w-full max-w-[11rem] rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm text-slate-900 shadow-sm focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-400/30 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" title="Elegí el día del año anterior (o promocional) para comparar en las tres secciones" />
          <p class="text-xs leading-snug text-slate-500 dark:text-slate-400">${escapeHtml(refTxt)}. Cambiá la fecha y se recalcula todo el panel.</p>
        </div>`;
    }
    return `
      <div class="flex flex-col gap-1.5">
        ${pctBlock}
        ${gapBlock}
        <p class="text-xs text-slate-500 dark:text-slate-400">${escapeHtml(refTxt)}</p>
      </div>`;
  }

  function renderKpiGridHtml(k, opts) {
    const o = opts || {};
    const meta = o.meta || {};
    return [
      kpiCard("Ventas del día", fmtMoney.format(k.ventas_netas_dia || 0), {
        icon: "payments",
        accent: "sky",
        span: "sm:col-span-2 xl:col-span-2",
        valueClass: "text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl",
      }),
      kpiCard("Vs ayer", vsAyerValueHtml(k), { icon: "compare_arrows", accent: "indigo" }),
      kpiCard("Vs mismo día sem. ant.", vsSemanaValueHtml(k), { icon: "date_range", accent: "purple" }),
      kpiCard(
        "Mismo día año anterior",
        vsAnioAnteriorValueHtml(k, !!o.editableAnio, meta),
        { icon: "history", accent: "teal", span: o.editableAnio ? "sm:col-span-2 xl:col-span-2" : "" },
      ),
      kpiCard("Tickets", `${(k.tickets ?? 0).toLocaleString("es-AR")}`, { icon: "confirmation_number", accent: "emerald" }),
      kpiCard("Ticket promedio", k.ticket_promedio != null ? fmtMoney.format(k.ticket_promedio) : "N/D", {
        icon: "functions",
        accent: "amber",
      }),
      kpiCard("Unidades vendidas", `${(k.unidades_vendidas ?? 0).toLocaleString("es-AR")}`, {
        icon: "inventory_2",
        accent: "slate",
      }),
    ].join("");
  }

  function updateSinClasificarBanner(meta) {
    const banner = el("exec-sin-clasificar");
    if (!banner) return;
    if (meta?.sin_sucursales_clasificadas) {
      banner.textContent =
        "No hay sucursales clasificadas como mayorista o minorista. Usá el engranaje en Consolidado para configurarlas.";
      banner.classList.remove("hidden");
    } else {
      banner.classList.add("hidden");
      banner.textContent = "";
    }
  }

  function sectionHeaderHtml(cfg) {
    const theme = KPI_THEME[cfg.accent] || KPI_THEME.sky;
    const gear = cfg.showGear
      ? `<button type="button" id="exec-open-pv-modal" class="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white/90 text-slate-500 shadow-sm transition hover:border-purple-300 hover:bg-purple-50 hover:text-purple-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 dark:border-slate-600 dark:bg-slate-800/90 dark:hover:border-purple-600 dark:hover:bg-purple-950/50 dark:hover:text-purple-300" title="Clasificar sucursales">
        <span class="material-icons text-xl" aria-hidden="true">settings</span>
      </button>`
      : "";
    const sub = cfg.subtitle
      ? `<p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">${escapeHtml(cfg.subtitle)}</p>`
      : "";
    return `
      <div class="mb-4 flex flex-wrap items-start justify-between gap-3 border-b border-slate-200/90 pb-3 dark:border-slate-700">
        <div class="flex min-w-0 items-start gap-3">
          <span class="material-icons rounded-xl p-2 text-2xl ${theme.icon}" aria-hidden="true">${cfg.icon}</span>
          <div>
            <h2 class="text-lg font-bold tracking-tight text-slate-900 dark:text-white sm:text-xl">${escapeHtml(cfg.label)}</h2>
            ${sub}
          </div>
        </div>
        ${gear}
      </div>`;
  }

  function sectionChartsHtml(sectionKey) {
    return `
      <div class="mb-8 grid grid-cols-1 gap-5 lg:grid-cols-2 lg:gap-6">
        <div class="group flex flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-md shadow-slate-200/40 transition hover:border-sky-200 hover:shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:shadow-black/30 dark:hover:border-sky-800">
          <div class="flex flex-shrink-0 items-center gap-2 border-b border-slate-100 bg-gradient-to-r from-sky-50/90 to-transparent px-4 py-3 dark:border-slate-700 dark:from-sky-950/50">
            <span class="material-icons text-xl text-sky-600 dark:text-sky-400" aria-hidden="true">schedule</span>
            <h3 class="text-sm font-bold text-slate-900 dark:text-white sm:text-base">Ventas por hora</h3>
            <span class="ml-auto rounded-md bg-sky-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-sky-800 dark:bg-sky-900/60 dark:text-sky-200">Hoy</span>
          </div>
          <div id="exec-chart-hora-${sectionKey}" class="exec-chart-wrap w-full min-h-[200px] flex-1 overflow-x-hidden bg-slate-50/50 p-1 sm:min-h-[240px] sm:p-2 dark:bg-slate-950/30"></div>
        </div>
        <div class="group flex flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-md shadow-slate-200/40 transition hover:border-indigo-200 hover:shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:shadow-black/30 dark:hover:border-indigo-800">
          <div class="flex flex-shrink-0 items-center gap-2 border-b border-slate-100 bg-gradient-to-r from-indigo-50/90 to-transparent px-4 py-3 dark:border-slate-700 dark:from-indigo-950/50">
            <span class="material-icons text-xl text-indigo-600 dark:text-indigo-400" aria-hidden="true">date_range</span>
            <h3 class="text-sm font-bold text-slate-900 dark:text-white sm:text-base">Últimos 7 días</h3>
            <span class="ml-auto rounded-md bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-800 dark:bg-indigo-900/60 dark:text-indigo-200">Tendencia</span>
          </div>
          <div id="exec-chart-7d-${sectionKey}" class="exec-chart-wrap w-full min-h-[200px] flex-1 overflow-x-hidden bg-slate-50/50 p-1 sm:min-h-[240px] sm:p-2 dark:bg-slate-950/30"></div>
        </div>
        <div class="group flex flex-col overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-md shadow-slate-200/40 transition hover:border-violet-200 hover:shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:shadow-black/30 dark:hover:border-violet-800 lg:col-span-2">
          <div class="flex flex-shrink-0 items-center gap-2 border-b border-slate-100 bg-gradient-to-r from-violet-50/90 to-transparent px-4 py-3 dark:border-slate-700 dark:from-violet-950/50">
            <span class="material-icons text-xl text-violet-600 dark:text-violet-400" aria-hidden="true">bar_chart</span>
            <h3 class="text-sm font-bold text-slate-900 dark:text-white sm:text-base">Día de referencia vs fecha comparación</h3>
            <span class="ml-auto rounded-md bg-violet-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-800 dark:bg-violet-900/60 dark:text-violet-200">Ventas netas</span>
          </div>
          <div id="exec-chart-yoy-${sectionKey}" class="exec-chart-wrap w-full min-h-[220px] flex-1 overflow-x-hidden bg-slate-50/50 p-1 sm:min-h-[240px] sm:p-2 dark:bg-slate-950/30" role="img" aria-label="Gráfico comparativo de ventas del día de referencia y la fecha de comparación año anterior"></div>
        </div>
      </div>`;
  }

  function sectionRentabilidadShellHtml(sectionKey, showTopBadge) {
    const badge = showTopBadge
      ? `<span id="exec-top-orden-badge" class="rounded-md bg-cyan-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-cyan-900 dark:bg-cyan-900/50 dark:text-cyan-100" title="Criterio de ranking del Top 10 artículos">Venta neta</span>`
      : "";
    return `
      <div class="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-md shadow-slate-200/40 dark:border-slate-700 dark:bg-slate-900 dark:shadow-black/30">
        <div class="flex flex-shrink-0 flex-col gap-1 border-b border-slate-100 bg-gradient-to-r from-teal-50/90 to-transparent px-4 py-3 dark:border-slate-700 dark:from-teal-950/40 sm:flex-row sm:items-center sm:gap-3">
          <div class="flex items-center gap-2">
            <span class="material-icons text-xl text-teal-600 dark:text-teal-400" aria-hidden="true">account_balance_wallet</span>
            <h3 class="text-sm font-bold text-slate-900 dark:text-white sm:text-base">Rentabilidad del día</h3>
          </div>
          ${badge}
          <p id="exec-rentabilidad-nota-${sectionKey}" class="text-xs leading-snug text-slate-500 dark:text-slate-400 sm:ml-auto sm:max-w-xl sm:text-right"></p>
        </div>
        <div id="exec-margen-kpis-${sectionKey}" class="grid grid-cols-1 gap-3 p-3 sm:grid-cols-2 sm:gap-4 sm:p-4 lg:grid-cols-3"></div>
        <div id="exec-margen-tablas-${sectionKey}" class="hidden border-t border-slate-100 bg-slate-50/50 p-2 sm:p-4 lg:block dark:border-slate-700 dark:bg-slate-950/30" role="region" aria-label="Top 10 artículos, rubros y subrubros (solo escritorio)"></div>
      </div>`;
  }

  function renderSecciones(data) {
    const root = el("exec-secciones");
    if (!root) return;
    const meta = data.meta || {};
    const secciones = data.secciones || {};
    updateSinClasificarBanner(meta);

    root.innerHTML = SECCIONES.map((cfg, idx) => {
      const seccion = secciones[cfg.key] || {};
      const k = seccion.kpis || {};
      return `
        <section id="exec-section-${cfg.key}" class="exec-section rounded-2xl border border-slate-200/60 bg-slate-50/30 p-4 shadow-sm dark:border-slate-700/60 dark:bg-slate-950/20 sm:p-5" aria-labelledby="exec-section-title-${cfg.key}">
          ${sectionHeaderHtml(cfg)}
          <div class="mb-6 grid grid-cols-1 gap-3 min-[400px]:grid-cols-2 sm:gap-4 xl:grid-cols-4" id="exec-kpi-grid-${cfg.key}"></div>
          ${sectionChartsHtml(cfg.key)}
          ${sectionRentabilidadShellHtml(cfg.key, idx === 0)}
        </section>`;
    }).join("");

    SECCIONES.forEach((cfg) => {
      const seccion = secciones[cfg.key] || {};
      const k = seccion.kpis || {};
      const grid = el(`exec-kpi-grid-${cfg.key}`);
      if (grid) {
        grid.innerHTML = renderKpiGridHtml(k, {
          editableAnio: cfg.editableAnio,
          meta,
        });
        staggerKpiGrid(cfg.key);
      }
      renderRentabilidadSection(cfg.key, seccion, meta, cfg.key === "consolidado");
    });
  }

  function updateTopOrdenBadge(meta) {
    const badge = el("exec-top-orden-badge");
    if (!badge) return;
    const orden = meta && meta.top_productos_orden === "unidades" ? "unidades" : "importe_neto";
    badge.classList.remove("hidden");
    if (orden === "unidades") {
      badge.textContent = "Top 10 · unidades";
      badge.title = "Artículos ordenados por cantidad neta vendida (renglón factura − NC)";
    } else {
      badge.textContent = "Top 10 · venta neta";
      badge.title = "Artículos ordenados por suma de PrecioNetoxR por renglón (FA − NC)";
    }
  }

  function tablaTopArticulos(rows, meta) {
    const topOrd = el("exec-top-orden")?.value || meta?.top_productos_orden || "importe_neto";
    if (!rows.length) {
      const emptyMsg =
        topOrd === "unidades"
          ? "Sin artículos con unidades o importe en el día seleccionado."
          : "Sin artículos con importe en el día seleccionado.";
      return `<div class="mb-6 hidden lg:block"><h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 artículos</h3><p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">${escapeHtml(emptyMsg)}</p></div>`;
    }
    return `
      <div class="mb-6 hidden overflow-x-auto lg:block">
        <h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 artículos</h3>
        <table class="w-full min-w-[36rem] border-collapse text-left text-sm">
          <thead>
            <tr class="border-b border-slate-200 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400 dark:border-slate-600 dark:text-slate-500">
              <th scope="col" class="pb-2 pl-1 font-medium">Código</th>
              <th scope="col" class="pb-2 font-medium">Descripción</th>
              <th scope="col" class="pb-2 text-right font-medium">Unidades</th>
              <th scope="col" class="pb-2 pr-1 text-right font-medium">Importe neto</th>
            </tr>
          </thead>
          <tbody>
            ${rows
              .map(
                (r) => `
              <tr class="border-b border-slate-100 dark:border-slate-800">
                <td class="py-2.5 pl-1 font-mono text-xs text-slate-700 dark:text-slate-300">${escapeHtml(r.codigo_articulo || "—")}</td>
                <td class="py-2.5 pr-2 text-slate-800 dark:text-slate-100">${escapeHtml(r.descripcion || "—")}</td>
                <td class="py-2.5 text-right tabular-nums text-slate-700 dark:text-slate-200">${Number(r.unidades ?? 0).toLocaleString("es-AR", { maximumFractionDigits: 4 })}</td>
                <td class="py-2.5 pr-1 text-right font-medium tabular-nums text-slate-900 dark:text-white">${fmtMoney.format(Number(r.importe_neto ?? 0))}</td>
              </tr>`,
              )
              .join("")}
          </tbody>
        </table>
      </div>`;
  }

  function renderRentabilidadSection(sectionKey, seccion, meta, updateBadge) {
    const notaEl = el(`exec-rentabilidad-nota-${sectionKey}`);
    const kGrid = el(`exec-margen-kpis-${sectionKey}`);
    const tablas = el(`exec-margen-tablas-${sectionKey}`);
    if (!kGrid || !tablas) return;

    if (notaEl) {
      notaEl.textContent =
        "Rentabilidad por renglón de facturación (PrecioNetoxR / costo normalizado en unidad base).";
    }

    const mb = seccion.margen_bruto || {};
    const vn = Number(mb.venta_neta_lineas ?? 0);
    const cn = Number(mb.costo_neto_lineas ?? 0);
    const ma = Number(mb.margen_absoluto ?? vn - cn);
    const pct = mb.pct_sobre_venta_lineas;

    kGrid.innerHTML = [
      kpiCard("Venta neta (líneas)", fmtMoney.format(vn), {
        icon: "receipt_long",
        accent: "teal",
        span: "",
        valueClass: "text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl",
      }),
      kpiCard("Costo neto (líneas)", fmtMoney.format(cn), {
        icon: "inventory",
        accent: "slate",
        valueClass: "text-xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-2xl",
      }),
      kpiCard("Margen bruto", `${fmtMoney.format(ma)} · ${fmtMargenSobreVentaPct(pct)}`, {
        icon: "savings",
        accent: "emerald",
        valueClass: "text-lg font-bold tracking-tight text-slate-900 dark:text-white sm:text-xl",
      }),
    ].join("");

    const rubros = (seccion.margen_por_rubro || []).slice(0, 10);
    const subrub = (seccion.margen_por_subrubro || []).slice(0, 10);
    const topProductos = (seccion.top_productos || []).slice(0, 10);

    function tablaMargenRubros(rows) {
      if (!rows.length) {
        return `<div class="mb-6 hidden lg:block"><h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por rubro</h3><p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">Sin movimientos con importe en rubros para el día.</p></div>`;
      }
      return `
        <div class="mb-6 hidden overflow-x-auto lg:block">
          <h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por rubro</h3>
          <table class="w-full min-w-[32rem] border-collapse text-left text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400 dark:border-slate-600 dark:text-slate-500">
                <th class="pb-2 pl-1 font-medium">Rubro</th>
                <th class="pb-2 text-right font-medium">Venta neta</th>
                <th class="pb-2 text-right font-medium">Costo</th>
                <th class="pb-2 text-right font-medium">Margen</th>
                <th class="pb-2 pr-1 text-right font-medium">% s/ venta</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map(
                  (r) => `
                <tr class="border-b border-slate-100 dark:border-slate-800">
                  <td class="py-2.5 pl-1 text-slate-800 dark:text-slate-100">${escapeHtml(r.nombre_rubro || "—")}</td>
                  <td class="py-2.5 text-right tabular-nums text-slate-700 dark:text-slate-200">${fmtMoney.format(Number(r.venta_neta ?? 0))}</td>
                  <td class="py-2.5 text-right tabular-nums text-slate-700 dark:text-slate-200">${fmtMoney.format(Number(r.costo_neto ?? 0))}</td>
                  <td class="py-2.5 text-right font-medium tabular-nums text-slate-900 dark:text-white">${fmtMoney.format(Number(r.margen_absoluto ?? 0))}</td>
                  <td class="py-2.5 pr-1 text-right tabular-nums text-slate-600 dark:text-slate-300">${fmtMargenSobreVentaPct(r.pct_sobre_venta)}</td>
                </tr>`,
                )
                .join("")}
            </tbody>
          </table>
        </div>`;
    }

    function tablaMargenSubrubros(rows) {
      if (!rows.length) {
        return `<div class="hidden lg:block"><h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por subrubro</h3><p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">Sin movimientos con importe en subrubros para el día.</p></div>`;
      }
      return `
        <div class="hidden overflow-x-auto lg:block">
          <h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por subrubro</h3>
          <table class="w-full min-w-[36rem] border-collapse text-left text-sm">
            <thead>
              <tr class="border-b border-slate-200 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400 dark:border-slate-600 dark:text-slate-500">
                <th class="pb-2 pl-1 font-medium">Subrubro</th>
                <th class="pb-2 font-medium">Rubro</th>
                <th class="pb-2 text-right font-medium">Venta neta</th>
                <th class="pb-2 text-right font-medium">Costo</th>
                <th class="pb-2 text-right font-medium">Margen</th>
                <th class="pb-2 pr-1 text-right font-medium">% s/ venta</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map(
                  (r) => `
                <tr class="border-b border-slate-100 dark:border-slate-800">
                  <td class="py-2.5 pl-1 text-slate-800 dark:text-slate-100">${escapeHtml(r.nombre_subrubro || "—")}</td>
                  <td class="py-2.5 text-slate-600 dark:text-slate-400">${escapeHtml(r.nombre_rubro || "—")}</td>
                  <td class="py-2.5 text-right tabular-nums text-slate-700 dark:text-slate-200">${fmtMoney.format(Number(r.venta_neta ?? 0))}</td>
                  <td class="py-2.5 text-right tabular-nums text-slate-700 dark:text-slate-200">${fmtMoney.format(Number(r.costo_neto ?? 0))}</td>
                  <td class="py-2.5 text-right font-medium tabular-nums text-slate-900 dark:text-white">${fmtMoney.format(Number(r.margen_absoluto ?? 0))}</td>
                  <td class="py-2.5 pr-1 text-right tabular-nums text-slate-600 dark:text-slate-300">${fmtMargenSobreVentaPct(r.pct_sobre_venta)}</td>
                </tr>`,
                )
                .join("")}
            </tbody>
          </table>
        </div>`;
    }

    tablas.innerHTML = `<div class="max-w-full">${tablaTopArticulos(topProductos, meta || {})}${tablaMargenRubros(rubros)}${tablaMargenSubrubros(subrub)}</div>`;
    if (updateBadge) updateTopOrdenBadge(meta || {});
  }

  /**
   * Eje Y compacto en pantallas angostas (menos anchura para el área del gráfico).
   */
  function formatYAxisTick(n, compact) {
    const x = +n;
    if (x >= 1e6) return compact ? `${Math.round(x / 1e6)}M` : `${(x / 1e6).toFixed(1)}M`;
    if (x >= 1e3) return `${Math.round(x / 1e3)}k`;
    return `${Math.round(x)}`;
  }

  /**
   * En móvil, menos etiquetas en el eje horario para evitar solapamiento.
   * @param {string[]} xDomain
   * @param {number} width
   * @returns {string[] | null} null = mostrar todas (d3 decide).
   */
  function subsampledHourTickValues(xDomain, width) {
    const n = xDomain.length;
    if (n <= 1) return null;
    if (width >= 768) return null;
    const maxTicks = width < 380 ? 6 : width < 520 ? 8 : 12;
    const step = Math.max(1, Math.ceil(n / maxTicks));
    const out = [];
    for (let i = 0; i < n; i += step) out.push(xDomain[i]);
    if (out[out.length - 1] !== xDomain[n - 1]) out.push(xDomain[n - 1]);
    return out;
  }

  /**
   * @param {string} containerId
   * @param {object[]} series
   * @param {string} xKey
   * @param {string} yKey
   * @param {(v: string) => string} [xLabelFn]
   * @param {{ stroke: string; strokeEnd: string; gradientId: string; kind?: 'hora' | '7d' }} theme
   */
  function drawLineChart(containerId, series, xKey, yKey, xLabelFn, theme) {
    const container = el(containerId);
    if (!container || typeof d3 === "undefined") return;
    let w = container.clientWidth || container.parentElement?.clientWidth || 320;
    if (w < 16) {
      requestAnimationFrame(() => {
        if (cachedChartData) renderAllCharts(cachedChartData);
      });
      return;
    }
    container.innerHTML = "";
    const kind = theme.kind || "7d";
    const narrow = w < 640;
    const compact = w < 400;
    const chartH = compact ? 210 : narrow ? 240 : 280;
    const left = narrow ? (compact ? 36 : 40) : 52;
    const right = narrow ? 6 : 14;
    const top = 10;
    const xDomain = series.map((d) => d[xKey]);
    const hourTicks = kind === "hora" ? subsampledHourTickValues(xDomain, w) : null;
    const horaHorizontal = kind === "hora" && hourTicks != null;
    const sevenHorizontal = kind === "7d" && narrow;
    const bottom =
      kind === "hora"
        ? horaHorizontal
          ? 36
          : narrow
            ? 48
            : 44
        : sevenHorizontal
          ? 32
          : narrow
            ? 34
            : 38;
    const margin = { top, right, bottom, left };
    const h = chartH;
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    const svg = d3
      .select(container)
      .append("svg")
      .attr("width", w)
      .attr("height", h)
      .attr("class", "exec-chart-svg block max-w-full");

    const defs = svg.append("defs");
    const gid = theme.gradientId || "execGrad";
    const grad = defs
      .append("linearGradient")
      .attr("id", gid)
      .attr("x1", "0")
      .attr("y1", "0")
      .attr("x2", "0")
      .attr("y2", "1");
    grad.append("stop").attr("offset", "0%").attr("stop-color", theme.stroke).attr("stop-opacity", 0.35);
    grad.append("stop").attr("offset", "100%").attr("stop-color", theme.strokeEnd || theme.stroke).attr("stop-opacity", 0.02);

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

    const yMax = d3.max(series, (d) => +d[yKey]) || 1;

    const pointPadding = kind === "hora" ? 0.42 : 0.45;
    const xScale = d3.scalePoint().domain(xDomain).range([0, iw]).padding(pointPadding);
    const yScale = d3.scaleLinear().domain([0, yMax * 1.08]).nice().range([ih, 0]);

    const yTickCount = compact ? 4 : 5;
    const gridLines = yScale.ticks(yTickCount);
    g.append("g")
      .attr("class", "grid-y")
      .selectAll("line")
      .data(gridLines)
      .join("line")
      .attr("x1", 0)
      .attr("x2", iw)
      .attr("y1", (d) => yScale(d))
      .attr("y2", (d) => yScale(d))
      .attr("stroke", "currentColor")
      .attr("stroke-opacity", 0.06)
      .attr("class", "text-slate-400");

    const area = d3
      .area()
      .x((d) => xScale(d[xKey]))
      .y0(ih)
      .y1((d) => yScale(+d[yKey]))
      .curve(d3.curveMonotoneX);

    const line = d3
      .line()
      .x((d) => xScale(d[xKey]))
      .y((d) => yScale(+d[yKey]))
      .curve(d3.curveMonotoneX);

    g.append("path").datum(series).attr("fill", `url(#${gid})`).attr("d", area);

    g.append("path")
      .datum(series)
      .attr("fill", "none")
      .attr("stroke", theme.stroke)
      .attr("stroke-width", narrow ? 2 : 2.5)
      .attr("stroke-linecap", "round")
      .attr("stroke-linejoin", "round")
      .attr("d", line);

    const baseLabel = xLabelFn || ((v) => v);
    const xAxis = d3.axisBottom(xScale);
    if (hourTicks) xAxis.tickValues(hourTicks);
    if (kind === "hora" && hourTicks) {
      xAxis.tickFormat((v) => {
        const m = String(v).match(/^(\d+)/);
        return m ? m[1] : String(v);
      });
    } else {
      xAxis.tickFormat(baseLabel);
    }

    const xg = g.append("g").attr("transform", `translate(0,${ih})`).call(xAxis);
    const xTexts = xg.selectAll("text");
    const fs = compact ? "9px" : "10px";
    xTexts.attr("font-size", fs);
    if (horaHorizontal) {
      xTexts.attr("transform", null).style("text-anchor", "middle").attr("dy", "0.85em");
    } else if (sevenHorizontal) {
      xTexts.attr("transform", null).style("text-anchor", "middle").attr("dy", "0.85em");
    } else {
      xTexts.attr("transform", "rotate(-40)").style("text-anchor", "end").attr("dx", "-0.35em").attr("dy", "0.45em");
    }

    const yg = g.append("g").call(
      d3
        .axisLeft(yScale)
        .ticks(yTickCount)
        .tickFormat((v) => formatYAxisTick(v, narrow))
    );
    yg.selectAll("text").attr("font-size", fs);

    const ptR = compact ? 2.5 : narrow ? 3 : 4;
    g.selectAll("circle.pt")
      .data(series)
      .join("circle")
      .attr("class", "pt")
      .attr("cx", (d) => xScale(d[xKey]))
      .attr("cy", (d) => yScale(+d[yKey]))
      .attr("r", ptR)
      .attr("fill", theme.stroke)
      .attr("stroke", "#fff")
      .attr("stroke-width", narrow ? 1 : 1.5)
      .style("filter", "drop-shadow(0 1px 2px rgb(0 0 0 / 0.12))");
  }

  /**
   * Barras: ventas del día de referencia vs ventas del día elegido en el KPI año anterior.
   */
  function drawBarCompareYoY(containerId, kpis, fechaRef, meta) {
    const container = el(containerId);
    if (!container || typeof d3 === "undefined") return;
    let w = container.clientWidth || container.parentElement?.clientWidth || 320;
    if (w < 16) {
      requestAnimationFrame(() => {
        if (cachedChartData) renderAllCharts(cachedChartData);
      });
      return;
    }
    container.innerHTML = "";
    const k = kpis || {};
    const refVal = Number(k.ventas_netas_dia ?? 0);
    const compVal = Number(k.ventas_anio_anterior_monto ?? 0);
    const fechaComp =
      k.fecha_comparacion_anio_anterior || meta?.fecha_comparacion_anio_anterior_aplicada || "";
    const bars = [
      {
        id: "ref",
        caption: "Día de referencia",
        fecha: formatFechaEs(fechaRef),
        value: refVal,
        fill: "rgb(14 165 233)",
        fillEnd: "rgb(59 130 246)",
      },
      {
        id: "comp",
        caption: "Fecha comparación",
        fecha: formatFechaEs(fechaComp),
        value: compVal,
        fill: "rgb(139 92 246)",
        fillEnd: "rgb(217 70 239)",
      },
    ];

    const narrow = w < 640;
    const compact = w < 400;
    const chartH = compact ? 220 : narrow ? 240 : 260;
    const margin = { top: 28, right: narrow ? 10 : 20, bottom: compact ? 56 : 64, left: narrow ? 48 : 60 };
    const h = chartH;
    const iw = w - margin.left - margin.right;
    const ih = h - margin.top - margin.bottom;

    const svg = d3
      .select(container)
      .append("svg")
      .attr("width", w)
      .attr("height", h)
      .attr("class", "exec-chart-svg block max-w-full");

    const defs = svg.append("defs");
    bars.forEach((b) => {
      const gid = `execBarYoY-${containerId}-${b.id}`;
      const grad = defs
        .append("linearGradient")
        .attr("id", gid)
        .attr("x1", "0")
        .attr("y1", "0")
        .attr("x2", "0")
        .attr("y2", "1");
      grad.append("stop").attr("offset", "0%").attr("stop-color", b.fill).attr("stop-opacity", 0.95);
      grad.append("stop").attr("offset", "100%").attr("stop-color", b.fillEnd).attr("stop-opacity", 0.75);
      b.gradientId = gid;
    });

    const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);
    const yMax = Math.max(refVal, compVal, 1);
    const xScale = d3.scaleBand().domain(bars.map((b) => b.id)).range([0, iw]).padding(0.38);
    const yScale = d3.scaleLinear().domain([0, yMax * 1.12]).nice().range([ih, 0]);
    const fs = compact ? "9px" : "10px";
    const yTickCount = compact ? 4 : 5;

    g.append("g")
      .attr("class", "grid-y")
      .selectAll("line")
      .data(yScale.ticks(yTickCount))
      .join("line")
      .attr("x1", 0)
      .attr("x2", iw)
      .attr("y1", (d) => yScale(d))
      .attr("y2", (d) => yScale(d))
      .attr("stroke", "currentColor")
      .attr("stroke-opacity", 0.06)
      .attr("class", "text-slate-400");

    const barG = g.selectAll("g.bar").data(bars).join("g").attr("class", "bar");

    barG
      .append("rect")
      .attr("x", (d) => xScale(d.id))
      .attr("y", (d) => yScale(d.value))
      .attr("width", xScale.bandwidth())
      .attr("height", (d) => ih - yScale(d.value))
      .attr("rx", narrow ? 6 : 8)
      .attr("fill", (d) => `url(#${d.gradientId})`);

    barG
      .append("text")
      .attr("x", (d) => (xScale(d.id) || 0) + xScale.bandwidth() / 2)
      .attr("y", (d) => yScale(d.value) - 6)
      .attr("text-anchor", "middle")
      .attr("font-size", compact ? "10px" : "11px")
      .attr("font-weight", "600")
      .attr("fill", "currentColor")
      .attr("class", "text-slate-800 dark:text-slate-100")
      .text((d) => fmtMoney.format(d.value));

    g.append("g")
      .attr("transform", `translate(0,${ih})`)
      .selectAll("g.xlab")
      .data(bars)
      .join("g")
      .attr("class", "xlab")
      .attr("transform", (d) => `translate(${(xScale(d.id) || 0) + xScale.bandwidth() / 2},0)`)
      .each(function (d) {
        const node = d3.select(this);
        node
          .append("text")
          .attr("y", 14)
          .attr("text-anchor", "middle")
          .attr("font-size", fs)
          .attr("font-weight", "600")
          .attr("fill", "currentColor")
          .attr("class", "text-slate-700 dark:text-slate-200")
          .text(d.fecha);
        node
          .append("text")
          .attr("y", compact ? 26 : 28)
          .attr("text-anchor", "middle")
          .attr("font-size", compact ? "8px" : "9px")
          .attr("fill", "currentColor")
          .attr("class", "text-slate-500 dark:text-slate-400")
          .text(d.caption);
      });

    const yg = g.append("g").call(
      d3
        .axisLeft(yScale)
        .ticks(yTickCount)
        .tickFormat((v) => formatYAxisTick(v, narrow))
    );
    yg.selectAll("text").attr("font-size", fs);

    const pct = k.pct_vs_anio_anterior;
    if (pct !== null && pct !== undefined && !Number.isNaN(Number(pct))) {
      g.append("text")
        .attr("x", iw)
        .attr("y", 0)
        .attr("text-anchor", "end")
        .attr("font-size", compact ? "10px" : "11px")
        .attr("font-weight", "600")
        .attr("fill", Number(pct) >= 0 ? "rgb(5 150 105)" : "rgb(220 38 38)")
        .text(`${Number(pct) > 0 ? "+" : ""}${Number(pct).toFixed(2)} % vs fecha comparación`);
    }
  }

  function updateSucursalesFilterHint(count) {
    const hint = el("exec-sucursales-hint");
    const search = el("exec_sucursales_search");
    if (!hint) return;
    if (count > 0) {
      hint.textContent =
        "Sin selección: todas las clasificadas. Las no clasificadas no entran al informe.";
      if (search) {
        search.disabled = false;
        search.placeholder = "Buscar sucursal…";
      }
    } else {
      hint.innerHTML =
        'No hay sucursales clasificadas. Usá el engranaje en <strong>Consolidado</strong> para asignar mayorista o minorista.';
      if (search) {
        search.disabled = true;
        search.placeholder = "Clasificá sucursales primero";
      }
    }
  }

  function fillSucursalesTagsOptions(list, preserveSelected) {
    const sel = el("exec_sucursales");
    if (!sel) return;
    const prev = preserveSelected
      ? new Set(Array.from(sel.selectedOptions).map((o) => o.value))
      : new Set();
    sel.innerHTML = "";
    (list || []).forEach((s) => {
      const sid = s.id_sucursal != null ? s.id_sucursal : s.value;
      if (sid === "" || sid == null) return;
      const o = document.createElement("option");
      o.value = String(sid);
      o.textContent =
        s.nombre_sucursal || s.label || `Sucursal ${sid}`;
      if (prev.has(o.value)) o.selected = true;
      sel.appendChild(o);
    });
    updateSucursalesFilterHint((list || []).length);
    ensureSucursalesTagsInit();
  }

  function ensureSucursalesTagsInit(retry = 0) {
    if (sucursalesTagsReady) return;
    const initFn =
      typeof window.initializeTagsFilter === "function"
        ? window.initializeTagsFilter
        : typeof window.execInitSucursalesTags === "function"
          ? window.execInitSucursalesTags
          : null;
    if (initFn) {
      if (initFn === window.execInitSucursalesTags) {
        window.execInitSucursalesTags();
      } else {
        window.initializeTagsFilter("exec_sucursales", "sucursales");
      }
      sucursalesTagsReady = true;
      return;
    }
    if (retry < 40) {
      setTimeout(() => ensureSucursalesTagsInit(retry + 1), 50);
    }
  }

  /** Carga opciones del filtro (clasificadas) antes del primer informe. */
  async function loadSucursalesFilterOptions() {
    const hint = el("exec-sucursales-hint");
    if (hint) hint.textContent = "Cargando sucursales…";

    let list = [];
    if (sucursalCanalUrl) {
      try {
        const res = await fetch(sucursalCanalUrl, { credentials: "same-origin" });
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.sucursales_clasificadas) && data.sucursales_clasificadas.length) {
            list = data.sucursales_clasificadas;
          } else {
            const col = data.columnas || {};
            list = [...(col.mayorista || []), ...(col.minorista || [])];
          }
        }
      } catch {
        /* fallback abajo */
      }
    }

    fillSucursalesTagsOptions(list, false);
  }

  function selectedSucursalesIds() {
    const sel = el("exec_sucursales");
    if (!sel) return [];
    return Array.from(sel.selectedOptions)
      .map((o) => o.value)
      .filter((v) => v && v !== "");
  }

  function selectedPuntoVentaIds() {
    const sel = el("exec_punto_venta");
    if (!sel) return [];
    return Array.from(sel.selectedOptions)
      .map((o) => o.value)
      .filter((v) => v && v !== "");
  }

  function fillPuntoVentaTagsOptions(list, preserveSelected) {
    const sel = el("exec_punto_venta");
    if (!sel) return;
    const prev = preserveSelected
      ? new Set(Array.from(sel.selectedOptions).map((o) => o.value))
      : new Set();
    sel.innerHTML = "";
    (list || []).forEach((item) => {
      const pid = item.id != null ? item.id : item.value;
      if (pid === "" || pid == null) return;
      const o = document.createElement("option");
      o.value = String(pid);
      o.textContent = item.nombre || item.label || `PV ${pid}`;
      if (prev.has(o.value)) o.selected = true;
      sel.appendChild(o);
    });
    ensurePuntoVentaTagsInit();
  }

  function ensurePuntoVentaTagsInit(retry = 0) {
    if (puntosVentaTagsReady) return;
    if (typeof window.initializeTagsFilter === "function") {
      window.initializeTagsFilter("exec_punto_venta", "puntos_venta");
      puntosVentaTagsReady = true;
      return;
    }
    if (retry < 40) {
      setTimeout(() => ensurePuntoVentaTagsInit(retry + 1), 50);
    }
  }

  async function loadPuntoVentaFilterOptions() {
    const hint = el("exec-pv-hint");
    if (hint) hint.textContent = "Cargando puntos de venta…";
    try {
      const res = await fetch(`${FILTERS_API_URL}?type=puntos_venta`, {
        credentials: "same-origin",
      });
      if (res.ok) {
        const data = await res.json();
        fillPuntoVentaTagsOptions(data.puntos_venta || [], true);
        if (hint) hint.textContent = "Vacío = todos los puntos de venta";
        return;
      }
    } catch (e) {
      /* opcional */
    }
    fillPuntoVentaTagsOptions([], false);
    if (hint) hint.textContent = "No se pudieron cargar los puntos de venta";
  }

  function renderSectionCharts(sectionKey, seccion, fechaRef, meta) {
    const hora = (seccion.serie_horaria || []).map((d) => ({
      hora: `${d.hora} h`,
      ventas_netas: d.ventas_netas,
    }));
    drawLineChart(`exec-chart-hora-${sectionKey}`, hora, "hora", "ventas_netas", (v) => v, {
      stroke: "rgb(14 165 233)",
      strokeEnd: "rgb(59 130 246)",
      gradientId: `execAreaHora-${sectionKey}`,
      kind: "hora",
    });

    const s7 = (seccion.serie_7_dias || []).map((d) => ({
      fecha: (d.fecha || "").slice(5),
      ventas_netas: d.ventas_netas,
    }));
    drawLineChart(`exec-chart-7d-${sectionKey}`, s7, "fecha", "ventas_netas", (v) => v, {
      stroke: "rgb(99 102 241)",
      strokeEnd: "rgb(168 85 247)",
      gradientId: `execArea7d-${sectionKey}`,
      kind: "7d",
    });

    drawBarCompareYoY(`exec-chart-yoy-${sectionKey}`, seccion.kpis || {}, fechaRef, meta);
  }

  function renderAllCharts(data) {
    cachedChartData = data;
    ensureChartResizeObserver();
    const secciones = data.secciones || {};
    const fechaRef = data.fecha_referencia || "";
    const meta = data.meta || {};
    SECCIONES.forEach(({ key }) => {
      const seccion = secciones[key];
      if (seccion) renderSectionCharts(key, seccion, fechaRef, meta);
    });
  }

  function applyPeriodFromUrl() {
    let params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (e) {
      return;
    }
    const iso = /^\d{4}-\d{2}-\d{2}$/;
    let fi = (params.get("fecha_inicio") || "").trim();
    let ff = (params.get("fecha_fin") || "").trim();
    const legacy = (params.get("fecha") || "").trim();
    if ((!fi || !ff) && legacy && iso.test(legacy)) {
      fi = ff = legacy;
    }
    const fin = el("exec-fecha-input");
    if (!fin) return;
    if (fi && ff && iso.test(fi) && iso.test(ff)) {
      fin.value = ff;
    } else if (legacy && iso.test(legacy)) {
      fin.value = legacy;
    }
  }

  async function loadSummary() {
    const fin = el("exec-fecha-input");
    const topO = el("exec-top-orden");
    const qs = new URLSearchParams();
    if (fin && fin.value) {
      qs.set("fecha_inicio", fin.value);
      qs.set("fecha_fin", fin.value);
    }
    selectedSucursalesIds().forEach((id) => qs.append("sucursales", id));
    selectedPuntoVentaIds().forEach((id) => qs.append("punto_venta", id));
    if (topO && topO.value) qs.set("top_orden", topO.value);
    const fcAnio = el("exec-fecha-comparacion-anio");
    if (fcAnio && fcAnio.value) qs.set("fecha_comparacion", fcAnio.value);
    showError("");
    setLoading(true);
    try {
      const res = await fetch(`${summaryUrl}?${qs.toString()}`, { credentials: "same-origin" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      fillSucursalesTagsOptions(data.sucursales_disponibles, true);
      if (topO && data.meta && data.meta.top_productos_orden) {
        topO.value = data.meta.top_productos_orden === "unidades" ? "unidades" : "importe_neto";
      }
      renderSecciones(data);
      renderAllCharts(data);
      const scopeEl = el("exec-scope-sucursal-pv");
      if (scopeEl && typeof window.formatSucursalPvScopeText === "function") {
        scopeEl.textContent = window.formatSucursalPvScopeText({
          sucursalesId: "exec_sucursales",
          puntoVentaId: "exec_punto_venta",
        });
      }
      const fc = el("exec-fecha-comparacion-anio");
      if (fc && data.meta?.fecha_comparacion_anio_anterior_aplicada) {
        fc.value = data.meta.fecha_comparacion_anio_anterior_aplicada;
      }
    } catch (e) {
      showError(e.message || "Error al cargar el resumen.");
    } finally {
      setLoading(false);
    }
  }

  /* ——— Modal sucursales ——— */
  let dragSrc = null;

  function sucLi(s) {
    const id = s.id_sucursal;
    const label = s.label || s.nombre_sucursal || `Sucursal ${id}`;
    return `<li draggable="true" data-id-sucursal="${id}" class="exec-suc-item flex cursor-grab items-center justify-between gap-2 rounded-lg border border-slate-200/90 bg-white/95 px-2.5 py-2 text-xs shadow-sm transition hover:border-slate-300 hover:shadow dark:border-slate-600 dark:bg-slate-900/90 dark:hover:border-slate-500">
      <span class="min-w-0 truncate font-medium text-slate-800 dark:text-slate-100">${escapeHtml(label)}</span>
      <span class="flex shrink-0 gap-0.5">
        <button type="button" class="exec-pv-nudge rounded-md p-1 text-slate-500 transition hover:bg-amber-100 hover:text-amber-900 dark:hover:bg-amber-950 dark:hover:text-amber-200" data-dir="mayorista" title="A mayorista">«</button>
        <button type="button" class="exec-pv-nudge rounded-md p-1 text-slate-500 transition hover:bg-slate-200 dark:hover:bg-slate-700" data-dir="centro" title="Sin asignar">○</button>
        <button type="button" class="exec-pv-nudge rounded-md p-1 text-slate-500 transition hover:bg-emerald-100 hover:text-emerald-900 dark:hover:bg-emerald-950 dark:hover:text-emerald-200" data-dir="minorista" title="A minorista">»</button>
      </span>
    </li>`;
  }

  function updateCounts() {
    el("exec-count-may").textContent = el("exec-col-mayorista").children.length;
    el("exec-count-centro").textContent = el("exec-col-centro").children.length;
    el("exec-count-min").textContent = el("exec-col-minorista").children.length;
  }

  function moveItem(li, targetUl) {
    if (!li || !targetUl) return;
    targetUl.appendChild(li);
    updateCounts();
  }

  function attachDnD(ul) {
    ul.addEventListener("dragstart", (ev) => {
      const t = ev.target.closest(".exec-suc-item");
      if (!t) return;
      dragSrc = t;
      ev.dataTransfer.effectAllowed = "move";
    });
    ul.addEventListener("dragover", (ev) => {
      ev.preventDefault();
      ev.dataTransfer.dropEffect = "move";
    });
    ul.addEventListener("drop", (ev) => {
      ev.preventDefault();
      const ulDrop = ev.currentTarget;
      if (dragSrc && ulDrop) moveItem(dragSrc, ulDrop);
      dragSrc = null;
    });
  }

  function fillModalColumns(col) {
    const may = el("exec-col-mayorista");
    const cen = el("exec-col-centro");
    const min = el("exec-col-minorista");
    [may, cen, min].forEach((u) => {
      u.innerHTML = "";
    });
    (col.mayorista || []).forEach((s) => {
      may.insertAdjacentHTML("beforeend", sucLi(s));
    });
    (col.sin_asignar || []).forEach((s) => {
      cen.insertAdjacentHTML("beforeend", sucLi(s));
    });
    (col.minorista || []).forEach((s) => {
      min.insertAdjacentHTML("beforeend", sucLi(s));
    });
    updateCounts();
    [may, cen, min].forEach(attachDnD);
  }

  async function openSucursalModal() {
    const modal = el("exec-modal-pv");
    if (!modal) return;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    try {
      const res = await fetch(sucursalCanalUrl, { credentials: "same-origin" });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
      const data = await res.json();
      fillModalColumns(data.columnas || {});
    } catch (e) {
      alert(e.message || "No se pudieron cargar las sucursales.");
    }
  }

  function closePvModal() {
    const modal = el("exec-modal-pv");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }

  async function savePvModal() {
    const mayorista = Array.from(el("exec-col-mayorista").querySelectorAll(".exec-suc-item")).map((li) =>
      parseInt(li.getAttribute("data-id-sucursal"), 10)
    );
    const minorista = Array.from(el("exec-col-minorista").querySelectorAll(".exec-suc-item")).map((li) =>
      parseInt(li.getAttribute("data-id-sucursal"), 10)
    );
    const csrftoken = getCookie("csrftoken");
    try {
      const res = await fetch(sucursalCanalUrl, {
        method: "PUT",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          ...(csrftoken ? { "X-CSRFToken": csrftoken } : {}),
        },
        body: JSON.stringify({ mayorista, minorista }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      closePvModal();
      await loadSucursalesFilterOptions();
      loadSummary();
    } catch (e) {
      alert(e.message || "Error al guardar la clasificación.");
    }
  }

  async function init() {
    applyPeriodFromUrl();
    const fin = el("exec-fecha-input");
    if (fin && !fin.value) {
      const t = new Date();
      fin.value = t.toISOString().slice(0, 10);
    }
    el("exec-refresh-btn")?.addEventListener("click", loadSummary);
    el("exec-top-orden")?.addEventListener("change", loadSummary);
    el("exec_sucursales")?.addEventListener("change", loadSummary);
    el("exec_punto_venta")?.addEventListener("change", loadSummary);
    el("exec-secciones")?.addEventListener("change", (ev) => {
      if (ev.target && ev.target.id === "exec-fecha-comparacion-anio") loadSummary();
    });
    el("exec-secciones")?.addEventListener("click", (ev) => {
      if (ev.target.closest("#exec-open-pv-modal")) openSucursalModal();
    });
    el("exec-modal-close")?.addEventListener("click", closePvModal);
    el("exec-modal-cancel")?.addEventListener("click", closePvModal);
    el("exec-modal-save")?.addEventListener("click", savePvModal);
    el("exec-modal-pv")?.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".exec-pv-nudge");
      if (!btn) return;
      ev.preventDefault();
      const li = btn.closest(".exec-suc-item");
      const dir = btn.getAttribute("data-dir");
      const map = {
        mayorista: el("exec-col-mayorista"),
        centro: el("exec-col-centro"),
        minorista: el("exec-col-minorista"),
      };
      const target = map[dir];
      if (li && target) moveItem(li, target);
    });
    await loadSucursalesFilterOptions();
    await loadPuntoVentaFilterOptions();
    loadSummary();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
