/**
 * Tablas de informes: vista tarjetas en móvil (< lg), tabla sin cambios en escritorio.
 * Reutilizable desde dashboard.js, WidgetEngine y auto-mejora de tablas dinámicas (BO, etc.).
 */
(function (global) {
  "use strict";

  const NARROW_MQ = "(max-width: 1023px)";
  const MOBILE_MAX_ROWS = 250;
  const CARD_ARTICLE_CLASS =
    "rounded-xl border border-slate-200/90 bg-white/95 p-3 shadow-sm dark:border-slate-600 dark:bg-slate-900/80";
  const DESKTOP_WRAP_CLASS =
    "synap-responsive-table-desktop hidden lg:block overflow-x-auto -mx-1 px-1 sm:mx-0 sm:px-0";
  const MOBILE_WRAP_CLASS = "synap-responsive-table-mobile lg:hidden space-y-2";

  function isNarrowViewport() {
    return global.matchMedia(NARROW_MQ).matches;
  }

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function humanizeKey(key) {
    return String(key || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function buildColumnsFromKeys(keys, labelMap) {
    const labels = labelMap || {};
    return (keys || []).map((key) => ({
      key,
      label: labels[key] || labels[key.toLowerCase()] || humanizeKey(key),
    }));
  }

  function defaultFormatCell(key, value) {
    if (value == null || value === "") return "—";
    if (typeof value === "number") {
      const k = String(key).toLowerCase();
      if (
        k.includes("monto") ||
        k.includes("importe") ||
        k.includes("total") ||
        k.includes("ventas") ||
        k.includes("credito") ||
        k.includes("brutas") ||
        k.includes("netas") ||
        k.includes("flow") ||
        k.includes("cumulative") ||
        k.includes("precio") ||
        k.includes("subtotal")
      ) {
        try {
          return new Intl.NumberFormat("es-AR", {
            style: "currency",
            currency: "ARS",
            minimumFractionDigits: 2,
          }).format(value);
        } catch (_e) {
          /* fallthrough */
        }
      }
      return new Intl.NumberFormat("es-AR", { maximumFractionDigits: 4 }).format(value);
    }
    return escHtml(String(value));
  }

  function genericCardHtml(row, columns, formatCell) {
    const fmt = formatCell || defaultFormatCell;
    const cols = columns || [];
    if (!cols.length) return "";

    const moneyKeys = new Set();
    const titleParts = [];
    cols.forEach((c, i) => {
      const v = row[c.key];
      const k = String(c.key).toLowerCase();
      const isMoney =
        typeof v === "number" &&
        (k.includes("monto") ||
          k.includes("importe") ||
          k.includes("total") ||
          k.includes("ventas") ||
          k.includes("subtotal") ||
          k.includes("precio") ||
          k.includes("netas") ||
          k.includes("brutas") ||
          k.includes("flow"));
      if (isMoney) moneyKeys.add(c.key);
      else if (titleParts.length < 2 && v != null && v !== "") {
        titleParts.push({ label: c.label, text: fmt(c.key, v) });
      }
    });

    let moneyCol = cols.find((c) => moneyKeys.has(c.key));
    let moneyHtml = "";
    if (moneyCol) {
      moneyHtml = `<p class="shrink-0 text-right text-sm font-bold tabular-nums text-sky-700 dark:text-sky-300">${fmt(
        moneyCol.key,
        row[moneyCol.key],
      )}</p>`;
    }

    const titleHtml =
      titleParts.length > 0
        ? titleParts
            .map(
              (p, idx) =>
                `<p class="${idx === 0 ? "text-sm font-bold leading-snug text-slate-900 dark:text-white" : "mt-0.5 text-xs text-slate-500 dark:text-slate-400"}">${p.text}</p>`,
            )
            .join("")
        : `<p class="text-sm font-semibold text-slate-900 dark:text-white">${fmt(cols[0].key, row[cols[0].key])}</p>`;

    const detailCols = cols.filter(
      (c) => !moneyKeys.has(c.key) && !titleParts.some((t) => t.label === c.label),
    );
    const detailHtml = detailCols
      .slice(0, 8)
      .map((c) => {
        const val = fmt(c.key, row[c.key]);
        if (val === "—") return "";
        return `<div><dt class="font-medium text-slate-500 dark:text-slate-500">${escHtml(c.label)}</dt><dd class="tabular-nums text-slate-800 dark:text-slate-200">${val}</dd></div>`;
      })
      .filter(Boolean)
      .join("");

    return `
      <article class="${CARD_ARTICLE_CLASS}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">${titleHtml}</div>
          ${moneyHtml}
        </div>
        ${
          detailHtml
            ? `<dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-400 sm:grid-cols-3">${detailHtml}</dl>`
            : ""
        }
      </article>`;
  }

  const fmtMoneyArs = (value) => {
    try {
      return new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        minimumFractionDigits: 2,
      }).format(Number(value) || 0);
    } catch (_e) {
      return String(value ?? "—");
    }
  };

  function pedidosPendientesCardHtml(row) {
    const nro = escHtml(row.nro_comprobante ?? "—");
    const cliente = escHtml(row.nombre_cliente || "Sin nombre");
    const fecha = escHtml(row.fecha || "—");
    const estado = escHtml(row.estado || "—");
    const importe = fmtMoneyArs(row.subtotal_desc);
    return `
      <article class="${CARD_ARTICLE_CLASS}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <p class="text-sm font-bold text-slate-900 dark:text-white">Nº ${nro}</p>
            <p class="mt-1 text-sm text-slate-800 dark:text-slate-200">${cliente}</p>
          </div>
          <p class="shrink-0 text-sm font-bold tabular-nums text-sky-700 dark:text-sky-300">${importe}</p>
        </div>
        <dl class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
          <div><dt class="inline font-medium">Fecha</dt> <dd class="inline">${fecha}</dd></div>
          <div><dt class="inline font-medium">Estado</dt> <dd class="inline">${estado}</dd></div>
        </dl>
      </article>`;
  }

  function stockExistenciaCardHtml(row) {
    const stk = Number(row.stock);
    const low = Number.isFinite(stk) && stk <= 0;
    const border = low
      ? "border-red-300 dark:border-red-800"
      : "border-slate-200/90 dark:border-slate-600";
    const fmt = (v) => {
      const n = Number(v);
      return Number.isFinite(n)
        ? n.toLocaleString("es-AR", { maximumFractionDigits: 4 })
        : "—";
    };
    return `
      <article class="${CARD_ARTICLE_CLASS} ${border}">
        <p class="font-mono text-xs font-semibold text-sky-700 dark:text-sky-300">${escHtml(row.id_manual || "—")}</p>
        <p class="mt-1 text-sm font-semibold leading-snug text-slate-900 dark:text-white">${escHtml(row.nombre || "—")}</p>
        <p class="text-xs text-slate-500 dark:text-slate-400">${escHtml(row.deposito_nombre || "")} · ${escHtml(row.rubro_nombre || "")}</p>
        <dl class="mt-2 grid grid-cols-3 gap-2 text-xs">
          <div><dt class="font-medium text-slate-500">Stock</dt><dd class="tabular-nums font-semibold">${fmt(row.stock)}</dd></div>
          <div><dt class="font-medium text-slate-500">Reserv.</dt><dd class="tabular-nums">${fmt(row.reservado)}</dd></div>
          <div><dt class="font-medium text-slate-500">Disp.</dt><dd class="tabular-nums text-emerald-700 dark:text-emerald-400">${fmt(row.disponible)}</dd></div>
        </dl>
      </article>`;
  }

  function cashFlowByAccountCardHtml(row) {
    const variacion = Number(row.cash_variation || 0);
    const varCls =
      variacion >= 0
        ? "text-emerald-700 dark:text-emerald-300"
        : "text-red-700 dark:text-red-300";
    return `
      <article class="${CARD_ARTICLE_CLASS}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <p class="text-sm font-bold text-slate-900 dark:text-white">${escHtml(row.caja_nombre || "Sin caja")}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">${escHtml(row.caja_tipo || "")}</p>
          </div>
          <p class="shrink-0 text-sm font-bold tabular-nums ${varCls}">${fmtMoneyArs(variacion)}</p>
        </div>
        <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
          <div><dt class="font-medium">Saldo ini.</dt><dd class="tabular-nums">${fmtMoneyArs(row.saldo_inicial)}</dd></div>
          <div><dt class="font-medium">Saldo fin.</dt><dd class="tabular-nums font-semibold">${fmtMoneyArs(row.saldo_final)}</dd></div>
          <div><dt class="font-medium">Operativo</dt><dd class="tabular-nums">${fmtMoneyArs(row.operating_flow)}</dd></div>
          <div><dt class="font-medium">Inversión</dt><dd class="tabular-nums">${fmtMoneyArs(row.investing_flow)}</dd></div>
        </dl>
      </article>`;
  }

  function ventasMarcaSuperartCardHtml(row) {
    const nombre =
      row.nombre_marca || row.nombre_superart || row.nombre_articulo || "—";
    const packs = row.packs != null ? String(row.packs) : "—";
    const docenas = row.docenas != null ? String(row.docenas) : "—";
    const childCount = (row.children || []).length;
    const esAjuste = Boolean(row.es_ajuste_cabecera);
    const titleClass = esAjuste
      ? "text-sm font-semibold italic text-amber-900 dark:text-amber-200"
      : "text-sm font-bold text-slate-900 dark:text-white";
    let sub = "";
    if (esAjuste) {
      sub =
        row.tipo === "marca"
          ? "FA/NC de cabecera sin mercadería (alinea con Ventas Netas)"
          : row.tipo === "superart"
            ? `${childCount} cliente(s)`
            : "Importe de cabecera";
    } else if (row.tipo === "marca") {
      sub = `${childCount} SuperArt(s)`;
    } else if (row.tipo === "superart") {
      sub = `${childCount} artículo(s)`;
    }
    return `
      <article class="${CARD_ARTICLE_CLASS}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <p class="${titleClass}">${escHtml(nombre)}</p>
            ${sub ? `<p class="text-xs text-slate-500 dark:text-slate-400">${escHtml(sub)}</p>` : ""}
          </div>
          <p class="shrink-0 text-sm font-bold tabular-nums text-sky-700 dark:text-sky-300">${fmtMoneyArs(row.facturacion)}</p>
        </div>
        <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
          <div><dt class="font-medium">Packs</dt><dd class="tabular-nums">${escHtml(packs)}</dd></div>
          <div><dt class="font-medium">Docenas</dt><dd class="tabular-nums">${escHtml(docenas)}</dd></div>
        </dl>
      </article>`;
  }

  function ventasArticuloCardHtml(row) {
    const esAjuste = Boolean(row.es_ajuste_cabecera);
    const titleClass = esAjuste
      ? "text-sm font-semibold italic text-amber-900 dark:text-amber-200"
      : "text-sm font-bold text-slate-900 dark:text-white";
    const sub = esAjuste
      ? "FA/NC de cabecera sin mercadería (alinea con Ventas Netas)"
      : `${(row.children || []).length} proveedor(es)`;
    return `
      <article class="${CARD_ARTICLE_CLASS}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <p class="${titleClass}">${escHtml(row.nombre_articulo || "Artículo")}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">${escHtml(sub)}</p>
          </div>
          <p class="shrink-0 text-sm font-bold tabular-nums text-sky-700 dark:text-sky-300">${fmtMoneyArs(row.facturacion)}</p>
        </div>
        <dl class="mt-2 text-xs text-slate-600 dark:text-slate-400">
          <div><dt class="inline font-medium">Unidades</dt> <dd class="inline tabular-nums">${escHtml(
            String(row.cantidades_vendidas ?? "—"),
          )}</dd></div>
        </dl>
      </article>`;
  }

  function objetivosVendedorCardHtml(row, compact) {
    const nombre = escHtml(row.nombre_vendedor || row.nombre || "Vendedor");
    if (compact) {
      return `
      <article class="${CARD_ARTICLE_CLASS}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1"><p class="text-sm font-bold text-slate-900 dark:text-white">${nombre}</p></div>
          <p class="shrink-0 text-sm font-bold tabular-nums text-sky-700 dark:text-sky-300">${fmtMoneyArs(row.facturacion)}</p>
        </div>
        <p class="mt-1 text-xs text-slate-500">Unidades: <span class="tabular-nums font-medium">${escHtml(String(row.cantidades_vendidas ?? "—"))}</span></p>
      </article>`;
    }
    return `
      <article class="${CARD_ARTICLE_CLASS}">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <p class="text-sm font-bold text-slate-900 dark:text-white">${nombre}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400">${row.total_clientes != null ? `${row.total_clientes} cliente(s)` : ""}</p>
          </div>
          <p class="shrink-0 text-sm font-bold tabular-nums text-sky-700 dark:text-sky-300">${fmtMoneyArs(row.total ?? row.facturacion)}</p>
        </div>
        <dl class="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
          <div><dt class="font-medium">Objetivo</dt><dd class="tabular-nums">${fmtMoneyArs(row.objetivo)}</dd></div>
          <div><dt class="font-medium">Facturación</dt><dd class="tabular-nums">${fmtMoneyArs(row.facturacion)}</dd></div>
          <div><dt class="font-medium">BO total</dt><dd class="tabular-nums">${fmtMoneyArs(row.backorder_total)}</dd></div>
          <div><dt class="font-medium">Falta</dt><dd class="tabular-nums">${fmtMoneyArs(row.falta)}</dd></div>
        </dl>
      </article>`;
  }

  const CARD_RENDERERS = {
    "pedidos-pendientes": pedidosPendientesCardHtml,
    pending_orders: pedidosPendientesCardHtml,
    "stock-existencias": stockExistenciaCardHtml,
    cash_flow_by_account: cashFlowByAccountCardHtml,
  };

  function resolveCardFn(opts, columns) {
    const slug = opts.reportSlug;
    if (slug && CARD_RENDERERS[slug]) {
      return (row) => CARD_RENDERERS[slug](row, opts.compactMetrics);
    }
    if (opts.cardHtml) return opts.cardHtml;
    return (row) => genericCardHtml(row, columns, opts.formatCell || defaultFormatCell);
  }

  function buildMobileCardsHtml(rows, columns, options) {
    const opts = options || {};
    const formatCell = opts.formatCell || defaultFormatCell;
    const cardFn = resolveCardFn(opts, columns);
    const maxRows = opts.maxRows != null ? opts.maxRows : MOBILE_MAX_ROWS;
    const slice = (rows || []).slice(0, maxRows);
    if (!slice.length) {
      return '<p class="py-3 text-sm text-slate-500 dark:text-slate-400">Sin datos disponibles.</p>';
    }
    let html = slice.map((row) => cardFn(row)).join("");
    if ((rows || []).length > slice.length) {
      html += `<p class="text-xs text-slate-400 dark:text-slate-500 pt-1">Mostrando ${slice.length} de ${rows.length} registros.</p>`;
    }
    return html;
  }

  /**
   * Monta tabla (escritorio) + tarjetas (móvil) en un contenedor vacío.
   */
  function mountDualTableView(target, tableEl, mobileOpts) {
    if (!target) return;
    target.innerHTML = "";
    const root = document.createElement("div");
    root.className = "synap-responsive-table-root min-w-0";

    const desk = document.createElement("div");
    desk.className = DESKTOP_WRAP_CLASS;
    desk.appendChild(tableEl);

    const mob = document.createElement("div");
    mob.className = MOBILE_WRAP_CLASS;
    const columns = mobileOpts.columns || [];
    mob.innerHTML = buildMobileCardsHtml(mobileOpts.rows || [], columns, mobileOpts);

    root.appendChild(mob);
    root.appendChild(desk);
    target.appendChild(root);

    if (mobileOpts.footerEl) {
      target.appendChild(mobileOpts.footerEl);
    }
  }

  function isDataRow(tr) {
    if (!tr || tr.querySelector("[colspan]") && tr.children.length === 1) {
      const td = tr.querySelector("td[colspan]");
      if (td && Number(td.getAttribute("colspan")) > 2) return false;
    }
    if (tr.classList.contains("logistica-group-header")) return false;
    if (tr.classList.contains("bo-group-header")) return false;
    if (tr.dataset.groupHeader === "true") return false;
    const cells = tr.querySelectorAll("td");
    return cells.length >= 2;
  }

  function rowsFromDomTable(table) {
    const headers = [...table.querySelectorAll("thead th")].map((th) =>
      (th.textContent || "").trim(),
    );
    const out = [];
    table.querySelectorAll("tbody tr").forEach((tr) => {
      if (!isDataRow(tr)) return;
      const cells = [...tr.querySelectorAll("td")];
      const row = {};
      headers.forEach((label, i) => {
        if (!label) return;
        const key = `col_${i}`;
        row[key] = (cells[i]?.textContent || "").trim();
        row._labels = row._labels || {};
        row._labels[key] = label;
      });
      out.push(row);
    });
    return { headers, rows: out };
  }

  function shouldSkipAutoEnhanceWrap(wrap) {
    if (!wrap) return true;
    if (wrap.closest(".se-vo-stock-nested")) return true;
    if (wrap.closest(".synap-logistica-lista-cr-table table")) return true;
    if (wrap.closest("#vo-jerarquia-container")) return true;
    if (wrap.id === "stock-existencias-table-wrap") return true;
    return false;
  }

  /**
   * Jerarquías VO: tabla en escritorio, tarjetas resumidas en móvil.
   */
  function wrapJerarquiaDual(container, desktopHtml, mobileOpts) {
    if (!container) return;
    container.querySelectorAll(".synap-responsive-table-mobile").forEach((el) => el.remove());
    const mob = document.createElement("div");
    mob.className = MOBILE_WRAP_CLASS;
    const variant = mobileOpts.variant;
    let rows = mobileOpts.rows || [];
    let cardFn;
    if (variant === "ventas-articulo") {
      cardFn = (row) => ventasArticuloCardHtml(row);
    } else if (variant === "ventas-marca-superart") {
      cardFn = (row) => ventasMarcaSuperartCardHtml(row);
    } else if (variant === "objetivos-vendedor") {
      cardFn = (row) => objetivosVendedorCardHtml(row, mobileOpts.compactMetrics);
    } else {
      cardFn = (row) => genericCardHtml(row, mobileOpts.columns || [], mobileOpts.formatCell);
    }
    mob.innerHTML = buildMobileCardsHtml(rows, [], {
      cardHtml: cardFn,
      maxRows: mobileOpts.maxRows,
    });
    const desk = document.createElement("div");
    desk.className = "hidden lg:block overflow-x-auto overflow-y-auto max-h-[min(75vh,56rem)] min-h-[12rem] overscroll-contain";
    desk.innerHTML = desktopHtml;
    container.innerHTML = "";
    container.appendChild(mob);
    container.appendChild(desk);
  }

  function insertDualHtml(parent, mobileHtml, desktopHtml) {
    if (!parent) return;
    parent.innerHTML = `<div class="${MOBILE_WRAP_CLASS}">${mobileHtml}</div><div class="${DESKTOP_WRAP_CLASS}">${desktopHtml}</div>`;
  }

  function enhanceFromDomTable(tableWrap, options) {
    if (!tableWrap || tableWrap.dataset.synapResponsiveEnhanced === "1") return;
    if (shouldSkipAutoEnhanceWrap(tableWrap)) return;
    const table = tableWrap.querySelector(":scope > table") || tableWrap.querySelector("table");
    if (!table) return;
    const thead = table.querySelector("thead");
    const tbody = table.querySelector("tbody");
    if (!thead || !tbody) return;
    const thCount = thead.querySelectorAll("th").length;
    if (thCount < 2) return;

    tableWrap.dataset.synapResponsiveEnhanced = "1";
    tableWrap.classList.add("hidden", "lg:block");

    const parsed = rowsFromDomTable(table);
    const columns = parsed.headers.map((label, i) => ({
      key: `col_${i}`,
      label: label || `Col ${i + 1}`,
    }));
    const formatCell = (key, value) => escHtml(value);

    const mob = document.createElement("div");
    mob.className = MOBILE_WRAP_CLASS;
    mob.innerHTML = buildMobileCardsHtml(parsed.rows, columns, {
      formatCell,
      maxRows: options?.maxRows,
      reportSlug: options?.reportSlug,
    });
    tableWrap.parentNode.insertBefore(mob, tableWrap);
  }

  function enhanceWidgetTableContainer(container, opts) {
    if (!container) return;
    const tableWrap = container.querySelector(".overflow-x-auto, .overflow-auto");
    if (!tableWrap || tableWrap.dataset.synapResponsiveEnhanced === "1") return;

    const dimensions = opts.dimensions || [];
    const metrics = opts.metrics || [];
    const columns = [
      ...dimensions.map((d) => ({ key: d.name, label: d.label || humanizeKey(d.name) })),
      ...metrics.map((m) => ({ key: m.name, label: m.label || humanizeKey(m.name) })),
    ];
    if (!columns.length) return;

    const formatCell = (key, value) => {
      const dim = dimensions.find((d) => d.name === key);
      if (dim && opts.formatDimension) return escHtml(String(opts.formatDimension(value, dim)));
      const met = metrics.find((m) => m.name === key);
      if (met && opts.formatMetric) return escHtml(String(opts.formatMetric(value, met)));
      return defaultFormatCell(key, value);
    };

    tableWrap.dataset.synapResponsiveEnhanced = "1";
    tableWrap.classList.add("hidden", "lg:block");

    const mob = document.createElement("div");
    mob.className = MOBILE_WRAP_CLASS;
    mob.innerHTML = buildMobileCardsHtml(opts.rows || [], columns, {
      formatCell,
      reportSlug: opts.reportSlug,
    });
    tableWrap.parentNode.insertBefore(mob, tableWrap);
  }

  function scanAndEnhance(root) {
    if (!root || root.closest("[data-workspace-tv]")) return;
    root.querySelectorAll(".overflow-x-auto, .overflow-auto").forEach((wrap) => {
      if (wrap.closest(".synap-responsive-table-mobile")) return;
      if (wrap.closest(".synap-responsive-table-desktop")) return;
      if (wrap.dataset.synapResponsiveSkip === "1") return;
      if (shouldSkipAutoEnhanceWrap(wrap)) return;
      enhanceFromDomTable(wrap);
    });
  }

  let debounceTimer = null;
  function installAutoEnhance(root) {
    if (!root || root.dataset.synapResponsiveObs === "1") return;
    root.dataset.synapResponsiveObs = "1";
    const run = () => scanAndEnhance(root);
    run();
    const obs = new MutationObserver(() => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(run, 120);
    });
    obs.observe(root, { childList: true, subtree: true });
  }

  global.SynapReportsResponsive = {
    NARROW_MQ,
    MOBILE_MAX_ROWS,
    isNarrowViewport,
    escHtml,
    humanizeKey,
    buildColumnsFromKeys,
    defaultFormatCell,
    genericCardHtml,
    buildMobileCardsHtml,
    mountDualTableView,
    insertDualHtml,
    wrapJerarquiaDual,
    enhanceFromDomTable,
    enhanceWidgetTableContainer,
    scanAndEnhance,
    installAutoEnhance,
    CARD_RENDERERS,
  };

  global.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("dashboard-root");
    if (root) installAutoEnhance(root);
  });
})(window);
