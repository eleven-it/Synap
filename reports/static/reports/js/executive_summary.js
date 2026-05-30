/**
 * Panel Resumen ejecutivo (ventas): KPIs, gráficos d3, modal clasificación PV.
 */
(function () {
  const cfg = window.EXEC_CONFIG || {};
  const summaryUrl = cfg.summaryUrl || "";
  const pvCanalUrl = cfg.pvCanalUrl || "";

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

  function debounceRedrawCharts() {
    if (resizeChartsTimer) clearTimeout(resizeChartsTimer);
    resizeChartsTimer = setTimeout(() => {
      resizeChartsTimer = null;
      if (cachedChartData) renderCharts(cachedChartData);
    }, 120);
  }

  function ensureChartResizeObserver() {
    if (typeof ResizeObserver === "undefined") return;
    if (chartResizeObserver) return;
    const h = el("exec-chart-hora");
    const d = el("exec-chart-7d");
    if (!h && !d) return;
    chartResizeObserver = new ResizeObserver(() => debounceRedrawCharts());
    if (h) chartResizeObserver.observe(h);
    if (d) chartResizeObserver.observe(d);
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

  function staggerKpiGrid() {
    const grid = el("exec-kpi-grid");
    if (!grid) return;
    grid.querySelectorAll(":scope > div").forEach((node, i) => {
      node.classList.add("exec-kpi-animate");
      node.style.animationDelay = `${i * 50}ms`;
    });
  }

  function renderKpis(data) {
    const grid = el("exec-kpi-grid");
    if (!grid || !data.kpis) return;
    const k = data.kpis;
    const split = data.split_mayorista_minorista || {};
    const gearBtn = `
      <button type="button" id="exec-open-pv-modal" class="inline-flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500 shadow-sm transition hover:border-purple-300 hover:bg-purple-50 hover:text-purple-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 dark:border-slate-600 dark:bg-slate-800 dark:hover:border-purple-600 dark:hover:bg-purple-950/50 dark:hover:text-purple-300" title="Configurar puntos de venta">
        <span class="material-icons text-xl" aria-hidden="true">settings</span>
      </button>`;
    grid.innerHTML = [
      kpiCard("Ventas del día", fmtMoney.format(k.ventas_netas_dia || 0), {
        icon: "payments",
        accent: "sky",
        span: "sm:col-span-2 xl:col-span-2",
        valueClass: "text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl",
      }),
      kpiCard("Vs ayer", vsAyerValueHtml(k), { icon: "compare_arrows", accent: "indigo" }),
      kpiCard("Vs mismo día sem. ant.", pctValueHtml(k.pct_vs_misma_semana_anterior), {
        icon: "date_range",
        accent: "purple",
      }),
      kpiCard("Tickets", `${(k.tickets ?? 0).toLocaleString("es-AR")}`, { icon: "confirmation_number", accent: "emerald" }),
      kpiCard("Ticket promedio", k.ticket_promedio != null ? fmtMoney.format(k.ticket_promedio) : "N/D", {
        icon: "functions",
        accent: "amber",
      }),
      kpiCard("Unidades vendidas", `${(k.unidades_vendidas ?? 0).toLocaleString("es-AR")}`, {
        icon: "inventory_2",
        accent: "slate",
      }),
      `<div class="group relative overflow-hidden rounded-2xl border border-slate-200/90 bg-gradient-to-br from-white via-slate-50/80 to-slate-100/50 p-4 shadow-md shadow-slate-200/40 transition duration-300 hover:-translate-y-0.5 hover:shadow-lg dark:border-slate-700 dark:from-slate-900 dark:via-slate-900 dark:to-slate-950 dark:shadow-black/30 sm:col-span-2 xl:col-span-2">
        <div class="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-gradient-to-br from-purple-400/20 to-indigo-500/10 blur-2xl"></div>
        <div class="relative flex items-start justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <span class="material-icons flex-shrink-0 rounded-xl bg-gradient-to-br from-purple-500/15 to-indigo-500/10 p-2 text-purple-600 dark:text-purple-400" aria-hidden="true">store_mall_directory</span>
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 dark:text-slate-400">Mayorista / Salón</p>
              <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-500">Según clasificación de PV</p>
            </div>
          </div>
          ${gearBtn}
        </div>
        <div class="relative mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div class="rounded-xl border border-amber-200/80 bg-amber-50/60 px-3 py-2.5 dark:border-amber-900/50 dark:bg-amber-950/30">
            <span class="text-[10px] font-bold uppercase tracking-wide text-amber-800 dark:text-amber-200">Mayorista</span>
            <p class="mt-1 text-base font-bold text-slate-900 dark:text-white">${fmtMoney.format(split.mayorista || 0)}</p>
          </div>
          <div class="rounded-xl border border-emerald-200/80 bg-emerald-50/60 px-3 py-2.5 dark:border-emerald-900/50 dark:bg-emerald-950/30">
            <span class="text-[10px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-200">Minorista</span>
            <p class="mt-1 text-base font-bold text-slate-900 dark:text-white">${fmtMoney.format(split.minorista || 0)}</p>
          </div>
          <div class="rounded-xl border border-slate-200 bg-slate-100/80 px-3 py-2.5 dark:border-slate-600 dark:bg-slate-800/50">
            <span class="text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300">Sin asignar</span>
            <p class="mt-1 text-base font-bold text-slate-900 dark:text-white">${fmtMoney.format(split.sin_asignar || 0)}</p>
          </div>
        </div>
      </div>`,
    ].join("");
    const btn = el("exec-open-pv-modal");
    if (btn) btn.addEventListener("click", openPvModal);
    staggerKpiGrid();
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
      return `<div class="mb-6"><h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 artículos</h3><p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">${escapeHtml(emptyMsg)}</p></div>`;
    }
    const head = `
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
    const cards = `
      <div class="mb-6 space-y-2 lg:hidden">
        <h3 class="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 artículos</h3>
        ${rows
          .map(
            (r) => `
          <div class="rounded-xl border border-slate-200/90 bg-white/95 px-3 py-2.5 shadow-sm dark:border-slate-600 dark:bg-slate-900/80">
            <div class="flex items-start justify-between gap-2">
              <span class="font-mono text-xs font-semibold text-sky-700 dark:text-sky-300">${escapeHtml(r.codigo_articulo || "—")}</span>
              <span class="text-sm font-bold tabular-nums text-slate-900 dark:text-white">${fmtMoney.format(Number(r.importe_neto ?? 0))}</span>
            </div>
            <p class="mt-1 text-sm leading-snug text-slate-700 dark:text-slate-200">${escapeHtml(r.descripcion || "—")}</p>
            <p class="mt-1 text-xs text-slate-500 dark:text-slate-400"><span class="font-medium">Unidades</span> ${Number(r.unidades ?? 0).toLocaleString("es-AR", { maximumFractionDigits: 4 })}</p>
          </div>`,
          )
          .join("")}
      </div>`;
    return head + cards;
  }

  function renderRentabilidad(data) {
    const notaEl = el("exec-rentabilidad-nota");
    const kGrid = el("exec-margen-kpis");
    const tablas = el("exec-margen-tablas");
    if (!kGrid || !tablas) return;

    const meta = data.meta || {};
    if (notaEl) {
      notaEl.textContent =
        "Rentabilidad por renglón de facturación (PrecioNetoxR / costo normalizado en unidad base).";
    }

    const mb = data.margen_bruto || {};
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

    const rubros = (data.margen_por_rubro || []).slice(0, 10);
    const subrub = (data.margen_por_subrubro || []).slice(0, 10);
    const topProductos = (data.top_productos || []).slice(0, 10);

    function tablaMargenRubros(rows) {
      if (!rows.length) {
        return `<div class="mb-6"><h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por rubro</h3><p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">Sin movimientos con importe en rubros para el día.</p></div>`;
      }
      const head = `
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
      const cards = `
        <div class="mb-6 space-y-2 lg:hidden">
          <h3 class="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por rubro</h3>
          ${rows
            .map(
              (r) => `
            <div class="rounded-xl border border-slate-200/90 bg-white/95 px-3 py-2.5 shadow-sm dark:border-slate-600 dark:bg-slate-900/80">
              <p class="text-sm font-semibold text-slate-900 dark:text-white">${escapeHtml(r.nombre_rubro || "—")}</p>
              <div class="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-300">
                <div><span class="font-medium">Venta</span><br/><span class="tabular-nums">${fmtMoney.format(Number(r.venta_neta ?? 0))}</span></div>
                <div><span class="font-medium">Costo</span><br/><span class="tabular-nums">${fmtMoney.format(Number(r.costo_neto ?? 0))}</span></div>
                <div><span class="font-medium">Margen</span><br/><span class="tabular-nums font-semibold text-slate-900 dark:text-white">${fmtMoney.format(Number(r.margen_absoluto ?? 0))}</span></div>
                <div><span class="font-medium">% s/ venta</span><br/>${fmtMargenSobreVentaPct(r.pct_sobre_venta)}</div>
              </div>
            </div>`,
            )
            .join("")}
        </div>`;
      return head + cards;
    }

    function tablaMargenSubrubros(rows) {
      if (!rows.length) {
        return `<div><h3 class="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por subrubro</h3><p class="py-4 text-center text-sm text-slate-500 dark:text-slate-400">Sin movimientos con importe en subrubros para el día.</p></div>`;
      }
      const head = `
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
      const cards = `
        <div class="space-y-2 lg:hidden">
          <h3 class="text-xs font-bold uppercase tracking-wide text-slate-500 dark:text-slate-400">Top 10 por subrubro</h3>
          ${rows
            .map(
              (r) => `
            <div class="rounded-xl border border-slate-200/90 bg-white/95 px-3 py-2.5 shadow-sm dark:border-slate-600 dark:bg-slate-900/80">
              <p class="text-sm font-semibold text-slate-900 dark:text-white">${escapeHtml(r.nombre_subrubro || "—")}</p>
              <p class="text-xs text-slate-500 dark:text-slate-400">${escapeHtml(r.nombre_rubro || "—")}</p>
              <div class="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-300">
                <div><span class="font-medium">Venta</span><br/><span class="tabular-nums">${fmtMoney.format(Number(r.venta_neta ?? 0))}</span></div>
                <div><span class="font-medium">Costo</span><br/><span class="tabular-nums">${fmtMoney.format(Number(r.costo_neto ?? 0))}</span></div>
                <div><span class="font-medium">Margen</span><br/><span class="tabular-nums font-semibold text-slate-900 dark:text-white">${fmtMoney.format(Number(r.margen_absoluto ?? 0))}</span></div>
                <div><span class="font-medium">% s/ venta</span><br/>${fmtMargenSobreVentaPct(r.pct_sobre_venta)}</div>
              </div>
            </div>`,
            )
            .join("")}
        </div>`;
      return head + cards;
    }

    tablas.innerHTML = `<div class="max-w-full">${tablaTopArticulos(topProductos, data.meta || {})}${tablaMargenRubros(rubros)}${tablaMargenSubrubros(subrub)}</div>`;
    updateTopOrdenBadge(data.meta || {});
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
        if (cachedChartData) renderCharts(cachedChartData);
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

    const xScale = d3.scalePoint().domain(xDomain).range([0, iw]).padding(kind === "hora" ? 0.42 : 0.45);
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

  function fillSucursalesSelect(list, selectedValue) {
    const sel = el("exec-sucursal-select");
    if (!sel) return;
    const cur =
      selectedValue !== undefined && selectedValue !== null && String(selectedValue).trim() !== ""
        ? String(selectedValue).trim()
        : sel.value || "";
    sel.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = "Todas las sucursales";
    sel.appendChild(optAll);
    (list || []).forEach((s) => {
      const o = document.createElement("option");
      o.value = String(s.id_sucursal);
      o.textContent = s.nombre_sucursal || `Sucursal ${s.id_sucursal}`;
      sel.appendChild(o);
    });
    const match = [...sel.options].some((op) => op.value === cur);
    sel.value = match ? cur : "";
  }

  function renderCharts(data) {
    cachedChartData = data;
    ensureChartResizeObserver();

    const hora = (data.serie_horaria || []).map((d) => ({
      hora: `${d.hora} h`,
      ventas_netas: d.ventas_netas,
    }));
    drawLineChart("exec-chart-hora", hora, "hora", "ventas_netas", (v) => v, {
      stroke: "rgb(14 165 233)",
      strokeEnd: "rgb(59 130 246)",
      gradientId: "execAreaHora",
      kind: "hora",
    });

    const s7 = (data.serie_7_dias || []).map((d) => ({
      fecha: (d.fecha || "").slice(5),
      ventas_netas: d.ventas_netas,
    }));
    drawLineChart("exec-chart-7d", s7, "fecha", "ventas_netas", (v) => v, {
      stroke: "rgb(99 102 241)",
      strokeEnd: "rgb(168 85 247)",
      gradientId: "execArea7d",
      kind: "7d",
    });
  }

  async function loadSummary() {
    const fin = el("exec-fecha-input");
    const suc = el("exec-sucursal-select");
    const topO = el("exec-top-orden");
    const qs = new URLSearchParams();
    if (fin && fin.value) qs.set("fecha", fin.value);
    if (suc && suc.value) qs.set("sucursal", suc.value);
    if (topO && topO.value) qs.set("top_orden", topO.value);
    const wantedSuc = suc && suc.value ? suc.value : "";
    showError("");
    setLoading(true);
    try {
      const res = await fetch(`${summaryUrl}?${qs.toString()}`, { credentials: "same-origin" });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      fillSucursalesSelect(data.sucursales_disponibles, wantedSuc || (data.meta && data.meta.cod_sucursal_filtro));
      if (topO && data.meta && data.meta.top_productos_orden) {
        topO.value = data.meta.top_productos_orden === "unidades" ? "unidades" : "importe_neto";
      }
      renderKpis(data);
      renderCharts(data);
      renderRentabilidad(data);
    } catch (e) {
      showError(e.message || "Error al cargar el resumen.");
    } finally {
      setLoading(false);
    }
  }

  /* ——— Modal PV ——— */
  let dragSrc = null;

  function pvLi(pv) {
    const id = pv.id_pv;
    const label = pv.label || `PV ${id}`;
    return `<li draggable="true" data-id-pv="${id}" class="exec-pv-item flex cursor-grab items-center justify-between gap-2 rounded-lg border border-slate-200/90 bg-white/95 px-2.5 py-2 text-xs shadow-sm transition hover:border-slate-300 hover:shadow dark:border-slate-600 dark:bg-slate-900/90 dark:hover:border-slate-500">
      <span class="min-w-0 truncate font-medium text-slate-800 dark:text-slate-100">${label}</span>
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
      const t = ev.target.closest(".exec-pv-item");
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
    (col.mayorista || []).forEach((pv) => {
      may.insertAdjacentHTML("beforeend", pvLi(pv));
    });
    (col.sin_asignar || []).forEach((pv) => {
      cen.insertAdjacentHTML("beforeend", pvLi(pv));
    });
    (col.minorista || []).forEach((pv) => {
      min.insertAdjacentHTML("beforeend", pvLi(pv));
    });
    updateCounts();
    [may, cen, min].forEach(attachDnD);
  }

  async function openPvModal() {
    const modal = el("exec-modal-pv");
    if (!modal) return;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
    try {
      const res = await fetch(pvCanalUrl, { credentials: "same-origin" });
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
      const data = await res.json();
      fillModalColumns(data.columnas || {});
    } catch (e) {
      alert(e.message || "No se pudieron cargar los puntos de venta.");
    }
  }

  function closePvModal() {
    const modal = el("exec-modal-pv");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }

  async function savePvModal() {
    const mayorista = Array.from(el("exec-col-mayorista").querySelectorAll(".exec-pv-item")).map((li) =>
      parseInt(li.getAttribute("data-id-pv"), 10)
    );
    const minorista = Array.from(el("exec-col-minorista").querySelectorAll(".exec-pv-item")).map((li) =>
      parseInt(li.getAttribute("data-id-pv"), 10)
    );
    const csrftoken = getCookie("csrftoken");
    try {
      const res = await fetch(pvCanalUrl, {
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
      loadSummary();
    } catch (e) {
      alert(e.message || "Error al guardar la clasificación.");
    }
  }

  function init() {
    const fin = el("exec-fecha-input");
    if (fin && !fin.value) {
      const t = new Date();
      fin.value = t.toISOString().slice(0, 10);
    }
    el("exec-refresh-btn")?.addEventListener("click", loadSummary);
    el("exec-sucursal-select")?.addEventListener("change", loadSummary);
    el("exec-top-orden")?.addEventListener("change", loadSummary);
    el("exec-modal-close")?.addEventListener("click", closePvModal);
    el("exec-modal-cancel")?.addEventListener("click", closePvModal);
    el("exec-modal-save")?.addEventListener("click", savePvModal);
    el("exec-modal-pv")?.addEventListener("click", (ev) => {
      const btn = ev.target.closest(".exec-pv-nudge");
      if (!btn) return;
      ev.preventDefault();
      const li = btn.closest(".exec-pv-item");
      const dir = btn.getAttribute("data-dir");
      const map = {
        mayorista: el("exec-col-mayorista"),
        centro: el("exec-col-centro"),
        minorista: el("exec-col-minorista"),
      };
      const target = map[dir];
      if (li && target) moveItem(li, target);
    });
    loadSummary();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
