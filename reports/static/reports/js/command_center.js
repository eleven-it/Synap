/**
 * Command Center gerencial — consume API executive-dashboard.
 */
(function () {
  const cfg = window.CC_CONFIG || {};
  const fmtMoney = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
  });
  const fmtNum = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

  const el = (id) => document.getElementById(id);

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtQty(v) {
    if (v == null || v === "") return "0";
    return fmtNum.format(Number(v));
  }

  const EXISTENCIAS_SEARCH_MIN = 2;
  /** Detalle comp_ped en ventas: tarjetas en móvil, tabla en lg+. */
  const COMP_PED_DETAIL_KEYS = new Set(["pedidos_pendientes", "remitos_nf"]);
  const BACKORDER_DETAIL_KEYS = new Set(["backorder"]);
  const DETAIL_TABLE_WRAP_CLASS =
    "cc-detail-scroll -mx-3 overflow-x-auto px-3 sm:-mx-4 sm:px-4";
  const DETAIL_TABLE_WRAP_DESKTOP_CLASS =
    "cc-detail-scroll hidden lg:block lg:-mx-4 lg:overflow-x-auto lg:px-4";
  const DETAIL_CARDS_CLASS = "hidden space-y-2";
  const DETAIL_CARDS_MOBILE_CLASS = "block space-y-2 lg:hidden";
  const COMP_PED_COLUMNS = [
    { key: "nro_comprobante", label: "Nº comprobante" },
    { key: "fecha", label: "Fecha" },
    { key: "nombre_cliente", label: "Cliente" },
    { key: "codigo_cliente", label: "Cód. cliente" },
    { key: "estado", label: "Estado" },
    { key: "codigo_movimiento", label: "Movimiento" },
    { key: "subtotal_desc", label: "Importe" },
  ];
  const BACKORDER_COLUMNS = [
    { key: "codigo", label: "Código" },
    { key: "articulo", label: "Artículo" },
    { key: "categoria", label: "Rubro" },
    { key: "bo_qty", label: "Ud. BO" },
    { key: "bo_importe", label: "Importe BO" },
    { key: "disponible", label: "Disponible" },
    { key: "stock_actual", label: "Stock" },
    { key: "oc_pendiente", label: "OC pend." },
  ];
  let existenciasAbort = null;
  let existenciasDebounce = null;
  let existenciasSearchBound = false;

  function resetDetailPanelsLayout() {
    const tableWrap = el("cc-detail-table-wrap");
    const cards = el("cc-detail-cards");
    if (tableWrap) tableWrap.className = DETAIL_TABLE_WRAP_CLASS;
    if (cards) cards.className = DETAIL_CARDS_CLASS;
  }

  function formatTabularCell(key, value) {
    if (value == null || value === "") return "—";
    if (
      key === "subtotal_desc" ||
      key === "bo_importe" ||
      key.endsWith("_importe") ||
      (typeof value === "number" && (key.includes("monto") || key.includes("importe")))
    ) {
      return fmtMoney.format(Number(value));
    }
    if (typeof value === "number" && (key.includes("qty") || key.includes("stock") || key === "disponible" || key === "oc_pendiente")) {
      return fmtNum.format(Number(value));
    }
    return escHtml(String(value));
  }

  const formatCompPedCell = formatTabularCell;

  function compPedCardHtml(row) {
    const nro = escHtml(row.nro_comprobante ?? "—");
    const mov =
      row.codigo_movimiento != null && row.codigo_movimiento !== ""
        ? `Mov. ${escHtml(row.codigo_movimiento)}`
        : "";
    const cliente = escHtml(row.nombre_cliente || "Sin nombre");
    const codCli =
      row.codigo_cliente != null && row.codigo_cliente !== ""
        ? `<span class="text-slate-500 dark:text-slate-400"> · Cód. ${escHtml(row.codigo_cliente)}</span>`
        : "";
    const fecha = escHtml(row.fecha || "—");
    const estado = escHtml(row.estado || "—");
    const importe = formatCompPedCell("subtotal_desc", row.subtotal_desc);
    return `
        <article class="rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-800/50">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0 flex-1">
              <p class="text-sm font-bold leading-snug text-slate-900 dark:text-white">Nº ${nro}</p>
              ${mov ? `<p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">${mov}</p>` : ""}
            </div>
            <p class="shrink-0 text-right text-sm font-bold tabular-nums text-sky-700 dark:text-sky-300">${importe}</p>
          </div>
          <p class="mt-2 text-sm leading-snug text-slate-800 dark:text-slate-200">${cliente}${codCli}</p>
          <dl class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600 dark:text-slate-400">
            <div><dt class="sr-only">Fecha</dt><dd><span class="font-medium text-slate-500 dark:text-slate-500">Fecha</span> ${fecha}</dd></div>
            <div><dt class="sr-only">Estado</dt><dd><span class="font-medium text-slate-500 dark:text-slate-500">Estado</span> ${estado}</dd></div>
          </dl>
        </article>`;
  }

  function backorderCardHtml(row) {
    const cod = escHtml(row.codigo || "—");
    const nombre = escHtml(row.articulo || "Sin nombre");
    const rubro = escHtml(row.categoria || "—");
    const importe = formatTabularCell("bo_importe", row.bo_importe);
    const qty = formatTabularCell("bo_qty", row.bo_qty);
    return `
        <article class="rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-800/50">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0 flex-1">
              <p class="font-mono text-xs font-semibold text-sky-700 dark:text-sky-300">${cod}</p>
              <p class="mt-1 text-sm font-semibold leading-snug text-slate-900 dark:text-white">${nombre}</p>
              <p class="mt-0.5 text-xs text-slate-500 dark:text-slate-400">${rubro}</p>
            </div>
            <p class="shrink-0 text-right text-sm font-bold tabular-nums text-rose-700 dark:text-rose-300">${importe}</p>
          </div>
          <dl class="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-600 dark:text-slate-400 sm:grid-cols-4">
            <div><dt class="font-medium text-slate-500">Ud. BO</dt><dd class="tabular-nums">${qty}</dd></div>
            <div><dt class="font-medium text-slate-500">Stock</dt><dd class="tabular-nums">${formatTabularCell("stock_actual", row.stock_actual)}</dd></div>
            <div><dt class="font-medium text-slate-500">Disponible</dt><dd class="tabular-nums">${formatTabularCell("disponible", row.disponible)}</dd></div>
            <div><dt class="font-medium text-slate-500">OC pend.</dt><dd class="tabular-nums">${formatTabularCell("oc_pendiente", row.oc_pendiente)}</dd></div>
          </dl>
        </article>`;
  }

  function renderTabularDetail(data, columns, cardHtmlFn) {
    const total = data.total_registros ?? 0;
    let sumTxt = `${total} registro(s)`;
    if (data.total_monto != null) sumTxt += ` · Total ${fmtMoney.format(data.total_monto)}`;
    const summaryEl = el("cc-detail-summary");
    if (summaryEl) summaryEl.textContent = sumTxt;

    const filas = data.filas || [];
    const tableWrap = el("cc-detail-table-wrap");
    const cards = el("cc-detail-cards");
    const tbody = el("cc-detail-tbody");
    const thead = el("cc-detail-thead");

    if (tableWrap) tableWrap.className = DETAIL_TABLE_WRAP_DESKTOP_CLASS;
    if (cards) cards.className = DETAIL_CARDS_MOBILE_CLASS;

    if (!filas.length) {
      if (thead) thead.innerHTML = "";
      if (tbody) {
        tbody.innerHTML =
          '<tr><td class="py-4 text-slate-500" colspan="99">Sin registros en el período.</td></tr>';
      }
      if (cards) {
        cards.innerHTML =
          '<p class="py-4 text-sm text-slate-500 dark:text-slate-400">Sin registros en el período.</p>';
      }
      return;
    }

    if (thead && tbody) {
      thead.innerHTML =
        "<tr>" +
        columns
          .map(
            (c) =>
              `<th scope="col" class="px-2 py-2 whitespace-nowrap text-[10px] font-semibold uppercase tracking-wide">${c.label}</th>`,
          )
          .join("") +
        "</tr>";
      tbody.innerHTML = filas
        .map((row) => {
          const cells = columns
            .map((c) => {
              const wrapText = c.key === "nombre_cliente" || c.key === "articulo";
              const cls = wrapText
                ? "max-w-[12rem] break-words px-2 py-1.5 text-sm sm:max-w-[16rem]"
                : "whitespace-nowrap px-2 py-1.5 text-sm tabular-nums";
              return `<td class="${cls}">${formatTabularCell(c.key, row[c.key])}</td>`;
            })
            .join("");
          return `<tr class="border-b border-slate-100 dark:border-slate-800">${cells}</tr>`;
        })
        .join("");
    }

    if (cards) {
      cards.innerHTML = filas.map((row) => cardHtmlFn(row)).join("");
    }
  }

  function renderCompPedDetail(data) {
    renderTabularDetail(data, COMP_PED_COLUMNS, compPedCardHtml);
  }

  function renderBackorderDetail(data) {
    renderTabularDetail(data, BACKORDER_COLUMNS, backorderCardHtml);
  }

  function clearDetailContent() {
    const summaryEl = el("cc-detail-summary");
    if (summaryEl) summaryEl.textContent = "";
    const thead = el("cc-detail-thead");
    const tbody = el("cc-detail-tbody");
    if (thead) thead.innerHTML = "";
    if (tbody) tbody.innerHTML = "";
    const cards = el("cc-detail-cards");
    if (cards) cards.innerHTML = "";
    resetDetailPanelsLayout();
    const searchWrap = el("cc-detail-search-wrap");
    if (searchWrap) searchWrap.classList.add("hidden");
    const searchInput = el("cc-detail-search");
    if (searchInput) searchInput.value = "";
    updateExistenciasSearchClear();
    if (existenciasAbort) {
      existenciasAbort.abort();
      existenciasAbort = null;
    }
    if (existenciasDebounce) {
      clearTimeout(existenciasDebounce);
      existenciasDebounce = null;
    }
  }

  function updateExistenciasSearchClear() {
    const input = el("cc-detail-search");
    const clearBtn = el("cc-detail-search-clear");
    if (!input || !clearBtn) return;
    const hasText = Boolean(input.value.trim());
    clearBtn.classList.toggle("hidden", !hasText);
  }

  function setExistenciasSearchVisible(show) {
    const wrap = el("cc-detail-search-wrap");
    if (wrap) wrap.classList.toggle("hidden", !show);
  }

  function renderExistenciasDetail(data, opts) {
    const busqueda = (opts && opts.busqueda) || "";
    const filas = data.filas || [];
    const total = data.total_registros ?? 0;
    let sumStock = 0;
    let sumRes = 0;
    let sumDisp = 0;
    filas.forEach((r) => {
      sumStock += Number(r.stock) || 0;
      sumRes += Number(r.reservado) || 0;
      sumDisp += Number(r.disponible) || 0;
    });

    let sumTxt = `${total} línea(s) artículo·depósito`;
    if (filas.length) {
      sumTxt += ` · Stock ${fmtQty(sumStock)} · Reserv. ${fmtQty(sumRes)} · Disp. ${fmtQty(sumDisp)}`;
    }
    if (total > filas.length) {
      sumTxt += ` (mostrando ${filas.length})`;
    }
    if (busqueda) {
      sumTxt += ` · Búsqueda: «${busqueda}»`;
    }
    const summaryEl = el("cc-detail-summary");
    if (summaryEl) summaryEl.textContent = sumTxt;

    const tableWrap = el("cc-detail-table-wrap");
    const cards = el("cc-detail-cards");
    if (tableWrap) tableWrap.classList.add("hidden");

    if (!cards) return;

    if (!filas.length) {
      cards.classList.remove("hidden");
      const emptyMsg = busqueda
        ? `Ningún resultado para «${escHtml(busqueda)}».`
        : "Sin existencias con stock.";
      cards.innerHTML = `<p class="py-4 text-sm text-slate-500 dark:text-slate-400">${emptyMsg}</p>`;
      return;
    }

    cards.classList.remove("hidden");
    cards.innerHTML = filas
      .map((row) => {
        const nombre = escHtml(row.nombre || "—");
        const cod = row.codigo_articulo ? `Cód. ${escHtml(row.codigo_articulo)}` : "";
        const dep = escHtml(row.deposito_nombre || "");
        const meta = [cod, dep].filter(Boolean).join(" · ");
        return `
        <article class="rounded-xl border border-slate-200 bg-slate-50/80 p-3 dark:border-slate-700 dark:bg-slate-800/50">
          <p class="text-sm font-semibold leading-snug text-slate-900 dark:text-white">${nombre}</p>
          ${meta ? `<p class="mt-1 text-xs text-slate-500 dark:text-slate-400">${meta}</p>` : ""}
          <dl class="mt-2 grid grid-cols-3 gap-2 text-center">
            <div>
              <dt class="text-[10px] font-medium uppercase text-slate-400">Stock</dt>
              <dd class="text-sm font-bold tabular-nums text-slate-900 dark:text-white">${fmtQty(row.stock)}</dd>
            </div>
            <div>
              <dt class="text-[10px] font-medium uppercase text-slate-400">Reserv.</dt>
              <dd class="text-sm font-bold tabular-nums text-amber-700 dark:text-amber-300">${fmtQty(row.reservado)}</dd>
            </div>
            <div>
              <dt class="text-[10px] font-medium uppercase text-slate-400">Disp.</dt>
              <dd class="text-sm font-bold tabular-nums text-emerald-700 dark:text-emerald-300">${fmtQty(row.disponible)}</dd>
            </div>
          </dl>
        </article>`;
      })
      .join("");
  }

  function renderGenericDetailTable(data) {
    resetDetailPanelsLayout();
    const total = data.total_registros ?? 0;
    let sumTxt = `${total} registro(s)`;
    if (data.total_monto != null) sumTxt += ` · Total ${fmtMoney.format(data.total_monto)}`;
    const summaryEl = el("cc-detail-summary");
    if (summaryEl) summaryEl.textContent = sumTxt;

    const filas = data.filas || [];
    const tbody = el("cc-detail-tbody");
    const thead = el("cc-detail-thead");
    if (!tbody || !thead) return;

    if (!filas.length) {
      tbody.innerHTML =
        '<tr><td class="py-4 text-slate-500" colspan="99">Sin registros en el período.</td></tr>';
      return;
    }
    const keys = Object.keys(filas[0]);
    thead.innerHTML =
      "<tr>" +
      keys
        .map(
          (k) =>
            `<th scope="col" class="px-2 py-2 text-[10px] font-semibold uppercase tracking-wide">${k.replace(/_/g, " ")}</th>`,
        )
        .join("") +
      "</tr>";
    tbody.innerHTML = filas
      .map((row) => {
        return (
          '<tr class="border-b border-slate-100 dark:border-slate-800">' +
          keys
            .map((k) => {
              let v = row[k];
              if (
                typeof v === "number" &&
                (k.includes("monto") || k.includes("importe") || k === "subtotal_desc")
              ) {
                v = fmtMoney.format(v);
              }
              const wrap = /nombre|descripcion|articulo|cliente/i.test(k);
              const cls = wrap
                ? "max-w-[12rem] break-words px-2 py-1.5 text-sm"
                : "whitespace-nowrap px-2 py-1.5 text-sm tabular-nums";
              return `<td class="${cls}">${v ?? ""}</td>`;
            })
            .join("") +
          "</tr>"
        );
      })
      .join("");
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }

  function isoToDisplay(iso) {
    if (!iso) return "";
    const p = String(iso).slice(0, 10).split("-");
    if (p.length !== 3) return iso;
    return `${p[2]}/${p[1]}/${p[0]}`;
  }

  function todayIso() {
    const d = new Date();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
  }

  const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
  /** Persistencia local de filtros (mismo navegador / perfil). */
  const FILTERS_STORAGE_KEY = "synap_cc_filters_v2";
  const FILTERS_API_URL = "/api/reports/filters/";
  let filterTagsReady = false;
  /** Presentación unidades / unidades+docenas en tarjeta Inventario. */
  const INV_PRESENTACION_KEY = "synap_cc_inv_presentacion_v1";

  function readInvPresentacion() {
    try {
      const v = String(window.localStorage.getItem(INV_PRESENTACION_KEY) || "").trim();
      return v === "unidades_docenas" ? "unidades_docenas" : "unidades";
    } catch (e) {
      return "unidades";
    }
  }

  function persistInvPresentacion(modo) {
    const m = modo === "unidades_docenas" ? "unidades_docenas" : "unidades";
    try {
      window.localStorage.setItem(INV_PRESENTACION_KEY, m);
    } catch (e) {
      /* private mode / cuota */
    }
    return m;
  }

  function selectedFilterIds(selectId) {
    const sel = el(selectId);
    if (!sel) return [];
    return Array.from(sel.selectedOptions)
      .map((o) => o.value)
      .filter((v) => v && v !== "");
  }

  function readFilters() {
    const t = todayIso();
    const fi = el("cc-fecha-inicio")?.value || t;
    const ff = el("cc-fecha-fin")?.value || t;
    return {
      fecha_inicio: fi,
      fecha_fin: ff,
      sucursales: selectedFilterIds("sucursales"),
      puntos_venta: selectedFilterIds("punto_venta"),
    };
  }

  function loadPersistedFilters() {
    try {
      const raw = window.localStorage.getItem(FILTERS_STORAGE_KEY);
      if (!raw) {
        const legacyRaw = window.localStorage.getItem("synap_cc_filters_v1");
        if (legacyRaw) {
          const legacy = JSON.parse(legacyRaw);
          if (legacy && legacy.sucursal) {
            return {
              fecha_inicio: legacy.fecha_inicio || "",
              fecha_fin: legacy.fecha_fin || "",
              sucursales: [String(legacy.sucursal)],
              puntos_venta: [],
            };
          }
        }
        return null;
      }
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return null;
      const fi = String(parsed.fecha_inicio || "").trim();
      const ff = String(parsed.fecha_fin || "").trim();
      if (fi && !ISO_DATE.test(fi)) return null;
      if (ff && !ISO_DATE.test(ff)) return null;
      const sucursales = Array.isArray(parsed.sucursales)
        ? parsed.sucursales.map(String).filter(Boolean)
        : parsed.sucursal
          ? [String(parsed.sucursal)]
          : [];
      const puntos_venta = Array.isArray(parsed.puntos_venta)
        ? parsed.puntos_venta.map(String).filter(Boolean)
        : [];
      return {
        fecha_inicio: fi || "",
        fecha_fin: ff || "",
        sucursales,
        puntos_venta,
      };
    } catch (e) {
      return null;
    }
  }

  function persistFilters(filters) {
    const f = filters || readFilters();
    try {
      window.localStorage.setItem(
        FILTERS_STORAGE_KEY,
        JSON.stringify({
          fecha_inicio: f.fecha_inicio || "",
          fecha_fin: f.fecha_fin || "",
          sucursales: f.sucursales || [],
          puntos_venta: f.puntos_venta || [],
        }),
      );
    } catch (e) {
      /* private mode / cuota */
    }
  }

  /** Sincroniza querystring sin recargar (útil al F5 y enlaces compartidos). */
  function syncFiltersToUrl(filters) {
    const f = filters || readFilters();
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("fecha_inicio", f.fecha_inicio);
      url.searchParams.set("fecha_fin", f.fecha_fin);
      url.searchParams.delete("sucursal");
      url.searchParams.delete("sucursales");
      url.searchParams.delete("punto_venta");
      url.searchParams.delete("puntos_venta");
      (f.sucursales || []).forEach((id) => url.searchParams.append("sucursales", id));
      (f.puntos_venta || []).forEach((id) => url.searchParams.append("punto_venta", id));
      url.searchParams.delete("fecha");
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    } catch (e) {
      /* ignore */
    }
  }

  function appendFilterParams(q, filters) {
    const f = filters || readFilters();
    (f.sucursales || []).forEach((id) => q.append("sucursales", id));
    (f.puntos_venta || []).forEach((id) => q.append("punto_venta", id));
  }

  function buildQuery(extra) {
    const f = readFilters();
    const q = new URLSearchParams({
      fecha_inicio: f.fecha_inicio,
      fecha_fin: f.fecha_fin,
      ...(extra || {}),
    });
    appendFilterParams(q, f);
    return q.toString();
  }

  function rememberFilters() {
    const f = readFilters();
    persistFilters(f);
    syncFiltersToUrl(f);
    return f;
  }

  function isSingleDayPeriod(f) {
    return f && f.fecha_inicio === f.fecha_fin;
  }

  /** Enlaces a informes externos con el período y sucursal actuales. */
  function buildReportLink(baseUrl) {
    if (!baseUrl || baseUrl === "#") return baseUrl;
    const sep = baseUrl.includes("?") ? "&" : "?";
    return `${baseUrl}${sep}${buildQuery()}`;
  }

  function syncReportLinks() {
    document.querySelectorAll(".cc-report-link[data-base-url]").forEach((node) => {
      const base = node.getAttribute("data-base-url");
      if (base) node.setAttribute("href", buildReportLink(base));
    });
  }

  function applyPeriodFromUrl() {
    let params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch (e) {
      return false;
    }
    let fi = (params.get("fecha_inicio") || "").trim();
    let ff = (params.get("fecha_fin") || "").trim();
    const legacy = (params.get("fecha") || "").trim();
    if ((!fi || !ff) && legacy && ISO_DATE.test(legacy)) {
      fi = ff = legacy;
    }
    if (!ISO_DATE.test(fi) || !ISO_DATE.test(ff)) return false;
    const fiEl = el("cc-fecha-inicio");
    const ffEl = el("cc-fecha-fin");
    if (fiEl) fiEl.value = fi;
    if (ffEl) ffEl.value = ff;
    const pending = {
      sucursales: params.getAll("sucursales"),
      puntos_venta: params.getAll("punto_venta"),
    };
    const legacySuc = (params.get("sucursal") || "").trim();
    if (!pending.sucursales.length && legacySuc) {
      pending.sucursales = [legacySuc];
    }
    window.__ccPendingFilterIds = pending;
    return true;
  }

  function applyPendingFilterSelections() {
    const pending = window.__ccPendingFilterIds;
    if (!pending) return;
    [["sucursales", pending.sucursales], ["punto_venta", pending.puntos_venta]].forEach(
      ([selectId, ids]) => {
        const sel = el(selectId);
        if (!sel || !Array.isArray(ids) || !ids.length) return;
        Array.from(sel.options).forEach((opt) => {
          opt.selected = ids.includes(String(opt.value));
        });
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      },
    );
    delete window.__ccPendingFilterIds;
  }

  function applyPeriodFromStorage() {
    const saved = loadPersistedFilters();
    if (!saved) return false;
    const fiEl = el("cc-fecha-inicio");
    const ffEl = el("cc-fecha-fin");
    let applied = false;
    if (fiEl && saved.fecha_inicio && ISO_DATE.test(saved.fecha_inicio)) {
      fiEl.value = saved.fecha_inicio;
      applied = true;
    }
    if (ffEl && saved.fecha_fin && ISO_DATE.test(saved.fecha_fin)) {
      ffEl.value = saved.fecha_fin;
      applied = true;
    }
    if (saved.sucursales?.length || saved.puntos_venta?.length) {
      window.__ccPendingFilterIds = {
        sucursales: saved.sucursales || [],
        puntos_venta: saved.puntos_venta || [],
      };
    }
    return applied;
  }

  let waitModalLocks = 0;
  let ventasDiaCache = null;
  let areasCache = {};
  let dashboardLoadToken = 0;

  const WAIT_LABELS = {
    dashboard: {
      title: "Cargando Command Center",
      subtitle:
        "Consultando ventas, inventario, compras, manufactura, tesorería y cobros en AdministraNET…",
    },
    detail: {
      title: "Cargando detalle",
      subtitle: "Consultando registros del período seleccionado…",
    },
  };

  function setRefreshDisabled(disabled) {
    const btn = el("cc-refresh");
    if (btn) {
      btn.disabled = !!disabled;
      btn.setAttribute("aria-busy", disabled ? "true" : "false");
    }
  }

  function isMprEnabled() {
    return cfg.mprModuleActive === true;
  }

  function isAreaVisible(key) {
    const vis = cfg.areasVisible;
    if (!vis || typeof vis !== "object") return true;
    return vis[key] !== false;
  }

  function visibleAreaDefs() {
    return AREA_DEFS.filter((d) => isAreaVisible(d.key));
  }

  function dashboardWaitSubtitle() {
    const labelMap = {
      ventas: "ventas",
      inventario: "inventario",
      compras: "compras",
      manufactura: "manufactura",
      cruzados: "demanda pendiente",
      tesoreria: "tesorería",
      ventas_cobros: "cobros",
    };
    const parts = visibleAreaDefs()
      .map((d) => labelMap[d.key] || d.key)
      .filter(Boolean);
    if (!parts.length) return "Sin áreas habilitadas…";
    return `Consultando ${parts.join(", ")} en AdministraNET…`;
  }

  function showWaitModal(kind) {
    const modal = el("cc-wait-modal");
    if (!modal) return;
    waitModalLocks += 1;
    const labels = WAIT_LABELS[kind] || WAIT_LABELS.dashboard;
    const titleEl = el("cc-wait-title");
    const subEl = el("cc-wait-subtitle");
    if (titleEl) titleEl.textContent = labels.title;
    if (subEl) {
      subEl.textContent =
        kind === "dashboard" ? dashboardWaitSubtitle() : labels.subtitle;
    }
    modal.classList.remove("hidden");
    modal.classList.add("flex", "items-center", "justify-center");
    modal.setAttribute("aria-hidden", "false");
    modal.setAttribute("aria-busy", "true");
    document.body.classList.add("overflow-hidden");
    setRefreshDisabled(true);
  }

  function hideWaitModal() {
    waitModalLocks = Math.max(0, waitModalLocks - 1);
    if (waitModalLocks > 0) return;
    const modal = el("cc-wait-modal");
    if (!modal) return;
    modal.classList.add("hidden");
    modal.classList.remove("flex", "items-center", "justify-center");
    modal.setAttribute("aria-hidden", "true");
    modal.setAttribute("aria-busy", "false");
    document.body.classList.remove("overflow-hidden");
    setRefreshDisabled(false);
  }

  function setLoading(on) {
    if (on) showWaitModal("dashboard");
    else hideWaitModal();
  }

  function showError(msg) {
    const box = el("cc-error");
    if (!box) return;
    box.textContent = msg || "";
    box.classList.toggle("hidden", !msg);
  }

  function poblarSelectTags(selectId, items, valueKey, labelKey) {
    const sel = el(selectId);
    if (!sel || !Array.isArray(items)) return;
    const prev = new Set(selectedFilterIds(selectId));
    sel.innerHTML = "";
    items.forEach((item) => {
      const opt = document.createElement("option");
      const val = item[valueKey] != null ? item[valueKey] : item.value;
      opt.value = String(val);
      opt.textContent = String(item[labelKey] != null ? item[labelKey] : item.label || val);
      if (prev.has(opt.value)) opt.selected = true;
      sel.appendChild(opt);
    });
  }

  async function initFilterTags() {
    try {
      const [sucRes, pvRes] = await Promise.all([
        fetch(`${FILTERS_API_URL}?type=sucursales`, { credentials: "same-origin" }),
        fetch(`${FILTERS_API_URL}?type=puntos_venta`, { credentials: "same-origin" }),
      ]);
      const sucPayload = sucRes.ok ? await sucRes.json() : {};
      const pvPayload = pvRes.ok ? await pvRes.json() : {};
      poblarSelectTags("sucursales", sucPayload.sucursales || [], "value", "label");
      poblarSelectTags("punto_venta", pvPayload.puntos_venta || [], "value", "label");
      if (typeof window.initializeTagsFilter === "function") {
        window.initializeTagsFilter("sucursales", "sucursales");
        window.initializeTagsFilter("punto_venta", "puntos_venta");
        filterTagsReady = true;
      }
      applyPendingFilterSelections();
    } catch (e) {
      /* filtros opcionales */
    }
  }

  function kpiCard(label, value, theme) {
    const themes = {
      sky: "from-sky-500 to-cyan-400",
      indigo: "from-indigo-500 to-violet-500",
      emerald: "from-emerald-500 to-teal-500",
      amber: "from-amber-500 to-orange-500",
      purple: "from-purple-500 to-fuchsia-500",
      rose: "from-rose-500 to-pink-500",
    };
    const bar = themes[theme] || themes.sky;
    return `
      <div class="cc-card-animate min-w-0 overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div class="h-1 bg-gradient-to-r ${bar}"></div>
        <div class="px-3 py-3 sm:px-4">
          <p class="line-clamp-2 text-[10px] font-semibold uppercase leading-tight tracking-wide text-slate-500 dark:text-slate-400">${label}</p>
          <p class="mt-1 break-all text-base font-bold tabular-nums text-slate-900 dark:text-white sm:break-normal sm:text-lg">${value}</p>
        </div>
      </div>`;
  }

  function kpiCardLoading(label, theme) {
    return kpiCard(label, "…", theme);
  }

  function stripAreaMeta(payload) {
    if (!payload || typeof payload !== "object") return payload || {};
    const out = { ...payload };
    delete out.meta;
    return out;
  }

  function updatePeriodoLabel(loading) {
    const lbl = el("cc-periodo-label");
    if (!lbl) return;
    const f = readFilters();
    const sameDay = isSingleDayPeriod(f);
    const base = sameDay
      ? `Período: ${isoToDisplay(f.fecha_inicio)}`
      : `Período: ${isoToDisplay(f.fecha_inicio)} — ${isoToDisplay(f.fecha_fin)}`;
    const scope =
      typeof window.formatSucursalPvScopeText === "function"
        ? window.formatSucursalPvScopeText()
        : "";
    const full = scope ? `${base} · ${scope}` : base;
    lbl.textContent = loading ? `${full} · Cargando áreas…` : full;
  }

  function renderGlobalKpis(areas, ventasDia) {
    const grid = el("cc-global-kpis");
    if (!grid) return;
    const f = readFilters();
    const singleDay = isSingleDayPeriod(f);
    const a = areas || {};
    const v = a.ventas || {};
    const inv = a.inventario || {};
    const comp = a.compras || {};
    const mfg = a.manufactura || {};
    const cruz = a.cruzados || {};
    const vd = ventasDia?.kpis || {};
    const ventasFirstLabel = singleDay ? "Ventas netas (día)" : "Ventas netas (período)";
    const ventasFirstVal = singleDay
      ? ventasDia === null
        ? "…"
        : fmtMoney.format(vd.ventas_netas_dia || 0)
      : fmtMoney.format(v.ventas_netas || 0);

    const cards = [];
    if (isAreaVisible("ventas")) {
      cards.push(kpiCard(ventasFirstLabel, ventasFirstVal, "sky"));
      cards.push(
        kpiCard("Total operativo (período)", fmtMoney.format(v.total_operativo || 0), "indigo")
      );
    }
    if (isAreaVisible("inventario")) {
      cards.push(kpiCard("Valor stock", fmtMoney.format(inv.valor_stock || 0), "emerald"));
    }
    if (isAreaVisible("compras")) {
      cards.push(
        kpiCard("OC pendientes", fmtNum.format(comp.oc_pendientes_cantidad || 0), "amber")
      );
    }
    if (isAreaVisible("manufactura")) {
      cards.push(kpiCard("OPT atrasadas", fmtNum.format(mfg.opt_atrasadas || 0), "purple"));
    }
    if (isAreaVisible("cruzados")) {
      cards.push(kpiCard("Backorder", fmtMoney.format(cruz.backorder_importe || 0), "rose"));
    }
    grid.innerHTML = cards.length
      ? cards.join("")
      : `<p class="col-span-full text-sm text-slate-500 dark:text-slate-400">No hay KPIs globales: activá al menos un área.</p>`;
    Array.from(grid.querySelectorAll(".cc-card-animate")).forEach((node, i) => {
      node.style.animationDelay = `${i * 0.05}s`;
    });
  }

  function renderGlobalKpisLoading() {
    const grid = el("cc-global-kpis");
    if (!grid) return;
    const singleDay = isSingleDayPeriod(readFilters());
    const ventasLabel = singleDay ? "Ventas netas (día)" : "Ventas netas (período)";
    const loadingCards = [];
    if (isAreaVisible("ventas")) {
      loadingCards.push(kpiCardLoading(ventasLabel, "sky"));
      loadingCards.push(kpiCardLoading("Total operativo (período)", "indigo"));
    }
    if (isAreaVisible("inventario")) {
      loadingCards.push(kpiCardLoading("Valor stock", "emerald"));
    }
    if (isAreaVisible("compras")) {
      loadingCards.push(kpiCardLoading("OC pendientes", "amber"));
    }
    if (isAreaVisible("manufactura")) {
      loadingCards.push(kpiCardLoading("OPT atrasadas", "purple"));
    }
    if (isAreaVisible("cruzados")) {
      loadingCards.push(kpiCardLoading("Backorder", "rose"));
    }
    grid.innerHTML = loadingCards.join("");
  }

  const AREA_DEFS = [
    {
      key: "ventas",
      title: "Ventas",
      icon: "point_of_sale",
      color: "sky",
      metrics: (a) => [
        ["Ventas netas", fmtMoney.format(a.ventas_netas || 0)],
        ["Pedidos pend.", fmtMoney.format(a.pedidos_pendientes_monto || 0)],
        ["Remitos s/ fact.", fmtMoney.format(a.remitos_no_facturados_monto || 0)],
        ["Total operativo", fmtMoney.format(a.total_operativo || 0)],
      ],
      details: [
        { label: "Pedidos pendientes", urlKey: "pedidos_pendientes" },
        { label: "Remitos no facturados", urlKey: "remitos_nf" },
        { label: "Ventas marcas mensual", urlKey: "ventas_marcas_mensual", navigate: true },
      ],
    },
    {
      key: "inventario",
      title: "Inventario",
      icon: "inventory_2",
      color: "emerald",
      metrics: (a) => [
        ["Valor stock", fmtMoney.format(a.valor_stock || 0)],
        ["Con stock", fmtNum.format(a.productos_con_stock || 0)],
        ["Bajo mínimo", fmtNum.format(a.productos_bajo_minimo || 0)],
        ["Sin stock", fmtNum.format(a.productos_sin_stock || 0)],
      ],
      afterMetrics: (a) => renderInventarioDepositosBlock(a),
      details: [{ label: "Existencias", urlKey: "existencias" }],
    },
    {
      key: "compras",
      title: "Compras",
      icon: "shopping_cart",
      color: "amber",
      metrics: (a) => [
        ["OC pendientes", fmtNum.format(a.oc_pendientes_cantidad || 0)],
        ["Unidades OC", fmtNum.format(a.oc_pendientes_unidades || 0)],
        ["Importe OC", fmtMoney.format(a.oc_pendientes_importe || 0)],
      ],
      details: [],
    },
    {
      key: "manufactura",
      title: "Manufactura",
      icon: "precision_manufacturing",
      color: "purple",
      metrics: (a) => [
        ["Pedidos fábrica", fmtNum.format(a.pedidos_fabrica_pendientes || 0)],
        ["OPT atrasadas", fmtNum.format(a.opt_atrasadas || 0)],
        ["Uds. pendientes", fmtNum.format(a.unidades_pendientes_produccion || 0)],
        ["Urgencias", fmtNum.format(a.items_urgentes || 0)],
      ],
      details: [],
      linkMpr: true,
    },
    {
      key: "cruzados",
      title: "Demanda pendiente",
      subtitle:
        "Pendientes, reservas y cobertura vs facturación del período",
      icon: "pending_actions",
      color: "rose",
      metrics: (a) => [
        ["Backorder ($)", fmtMoney.format(a.backorder_importe || 0)],
        ["Unidades pendientes", fmtNum.format(a.backorder_unidades || 0)],
        ["Stock reservado", fmtNum.format(a.stock_reservado_unidades || 0)],
        [
          "Demanda cubierta (%)",
          a.demand_coverage_pct != null ? `${a.demand_coverage_pct} %` : "N/D",
        ],
      ],
      details: [{ label: "Detalle por artículo", urlKey: "backorder" }],
    },
    {
      key: "tesoreria",
      title: "Tesorería (caja)",
      subtitle: "Liquidez en caja; no incluye libro banco",
      icon: "account_balance_wallet",
      color: "teal",
      metrics: (a) => {
        const banco = a.banco;
        const bancoOk = banco && banco.disponible !== false;
        const notaBanco =
          !bancoOk && a.banco_disponible === false
            ? [["Nota", "Sin datos bancarios"]]
            : [];
        const drift = Math.abs(Number(a.drift_sistema) || 0);
        const saldoSistema =
          drift > 1 && a.saldo_final_sistema != null
            ? [["Saldo final (sistema BD)", fmtMoney.format(a.saldo_final_sistema || 0)]]
            : [];
        const filasCaja = [
          ["Saldo inicial (caja)", fmtMoney.format(a.saldo_inicial || 0)],
          ["Saldo final (caja)", fmtMoney.format(a.saldo_final || 0)],
          ["Variación neta", fmtMoney.format(a.variacion_neta || 0)],
          ["Ingresos operativos", fmtMoney.format(a.ingresos_operativos || 0)],
          ["Egresos operativos", fmtMoney.format(a.egresos_operativos || 0)],
          ["Ingresos ventas", fmtMoney.format(a.ingresos_ventas || 0)],
          ["Ingresos cobranzas", fmtMoney.format(a.ingresos_cobranzas || 0)],
          ["Egresos proveedores", fmtMoney.format(a.egresos_proveedores || 0)],
          ...saldoSistema,
        ];
        const filasBanco = bancoOk
          ? [
              ["— Libro banco —", "No sumar con caja"],
              ["Saldo banco inicial", fmtMoney.format(banco.saldo_banco_inicial || 0)],
              ["Saldo banco final", fmtMoney.format(banco.saldo_banco_final || 0)],
              ["Créditos período", fmtMoney.format(banco.creditos_periodo || 0)],
              ["Débitos período", fmtMoney.format(banco.debitos_periodo || 0)],
              [
                "Pend. conciliar",
                fmtNum.format(banco.pendiente_conciliar || 0),
              ],
            ]
          : notaBanco;
        return [...filasCaja, ...filasBanco];
      },
      details: [{ label: "Movimientos caja", urlKey: "movimientos_caja" }],
      linkCashFlow: true,
    },
    {
      key: "ventas_cobros",
      title: "Ventas por cobro",
      subtitle: "Facturado al emitir vs cobrado en caja",
      icon: "payments",
      color: "cyan",
      metrics: (a) => {
        const f = a.facturado_por_medio || {};
        const c = a.cobrado_caja_por_medio || {};
        return [
          ["Facturado (total)", fmtMoney.format(f.total || 0)],
          ["· Efectivo", fmtMoney.format(f.efectivo || 0)],
          ["· Tarjeta", fmtMoney.format(f.tarjeta || 0)],
          ["· Cta. cte.", fmtMoney.format(f.cuenta_corriente || 0)],
          ["Cobrado caja (total)", fmtMoney.format(c.total || 0)],
          ["· Efectivo", fmtMoney.format(c.efectivo || 0)],
          ["· Tarjeta", fmtMoney.format(c.tarjeta || 0)],
        ];
      },
      details: [{ label: "Detalle cobros", urlKey: "cobros_detalle" }],
    },
  ];

  function renderInventarioDepositosBlock(areaData) {
    const deps = Array.isArray(areaData?.depositos) ? areaData.depositos : [];
    const modo = readInvPresentacion();
    const showDocenas = modo === "unidades_docenas";
    const btnBase =
      "cc-inv-pres-btn inline-flex min-h-8 flex-1 items-center justify-center rounded-md px-2 py-1 text-[11px] font-medium transition-colors";
    const btnOn = "bg-emerald-600 text-white";
    const btnOff =
      "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700";

    const toggle = `
      <div class="mt-3 flex gap-1 rounded-lg border border-slate-100 p-0.5 dark:border-slate-700" role="group" aria-label="Presentación de cantidades">
        <button type="button" class="${btnBase} ${modo === "unidades" ? btnOn : btnOff}" data-inv-pres="unidades">Unidades</button>
        <button type="button" class="${btnBase} ${showDocenas ? btnOn : btnOff}" data-inv-pres="unidades_docenas">Unidades y docenas</button>
      </div>`;

    if (!deps.length) {
      return `${toggle}<p class="mt-2 text-[11px] text-slate-500 dark:text-slate-400">Sin depósitos con Stock = Sí.</p>`;
    }

    const headDoc = showDocenas
      ? `<th class="px-1 py-1.5 text-right font-medium">Docenas</th>`
      : "";
    const rows = deps
      .map((d) => {
        const nombre = escHtml(d.nombre || `Depósito ${d.id_deposito || ""}`);
        const uds = fmtNum.format(Number(d.unidades || 0));
        const doc = showDocenas
          ? `<td class="px-1 py-1.5 text-right tabular-nums text-slate-800 dark:text-slate-100">${fmtNum.format(Number(d.docenas || 0))}</td>`
          : "";
        return `<tr class="border-t border-slate-100 dark:border-slate-800">
          <td class="max-w-[9rem] truncate py-1.5 pr-2 text-slate-600 dark:text-slate-300" title="${nombre}">${nombre}</td>
          <td class="px-1 py-1.5 text-right tabular-nums font-medium text-slate-900 dark:text-white">${uds}</td>
          ${doc}
        </tr>`;
      })
      .join("");

    return `${toggle}
      <div class="mt-2 max-h-48 overflow-auto rounded-lg border border-slate-100 dark:border-slate-700">
        <table class="w-full text-[11px]">
          <thead class="sticky top-0 bg-slate-50 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
            <tr>
              <th class="py-1.5 pr-2 text-left font-medium">Depósito</th>
              <th class="px-1 py-1.5 text-right font-medium">Unidades</th>
              ${headDoc}
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
  }

  function areaCard(def, areaData, delayIdx) {
    const unavailable = areaData && areaData.disponible === false;
    const borderColor = {
      sky: "border-sky-200 dark:border-sky-800",
      emerald: "border-emerald-200 dark:border-emerald-800",
      amber: "border-amber-200 dark:border-amber-800",
      purple: "border-purple-200 dark:border-purple-800",
      rose: "border-rose-200 dark:border-rose-800",
      teal: "border-teal-200 dark:border-teal-800",
      cyan: "border-cyan-200 dark:border-cyan-800",
    }[def.color] || "border-slate-200";

    let body = "";
    if (unavailable) {
      body = `<p class="text-sm text-amber-700 dark:text-amber-300">${areaData.error?.mensaje || "Datos no disponibles"}</p>`;
    } else {
      const a = areaData || {};
      const rows = def.metrics(a)
        .map(
          ([k, val]) => `
        <div class="flex items-start justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0 dark:border-slate-800">
          <span class="min-w-0 shrink text-sm text-slate-500 dark:text-slate-400">${k}</span>
          <span class="shrink-0 text-right text-sm font-semibold tabular-nums text-slate-900 dark:text-white">${val}</span>
        </div>`
        )
        .join("");
      const extra = typeof def.afterMetrics === "function" ? def.afterMetrics(a) : "";
      body = `<div class="space-y-0">${rows}</div>${extra || ""}`;
    }

    const detailBtns = (def.details || [])
      .map(
        (d) => `
      <button type="button" class="cc-detail-btn inline-flex min-h-10 w-full items-center justify-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-[11px] font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 sm:w-auto sm:justify-start sm:py-1"
        data-url-key="${d.urlKey}" data-title="${def.title}: ${d.label}">
        ${d.label}
      </button>`
      )
      .join("");

    const mprBtn = def.linkMpr && isMprEnabled() && cfg.mprTableroUrl
      ? `<a href="${buildReportLink(cfg.mprTableroUrl)}" class="cc-report-link inline-flex min-h-10 w-full items-center justify-center rounded-lg border border-purple-300 bg-purple-50 px-2.5 py-2 text-[11px] font-medium text-purple-800 hover:bg-purple-100 dark:border-purple-700 dark:bg-purple-950/50 dark:text-purple-200 sm:w-auto sm:py-1" data-base-url="${cfg.mprTableroUrl}">Tablero MPR</a>`
      : "";

    const cashFlowBtn =
      def.linkCashFlow && cfg.cashFlowWaterfallUrl
        ? `<a href="${buildReportLink(cfg.cashFlowWaterfallUrl)}" class="cc-report-link inline-flex min-h-10 w-full items-center justify-center gap-1 rounded-lg border border-teal-300 bg-teal-50 px-2.5 py-2 text-[11px] font-medium text-teal-800 hover:bg-teal-100 dark:border-teal-700 dark:bg-teal-950/50 dark:text-teal-200 sm:w-auto sm:py-1" data-base-url="${cfg.cashFlowWaterfallUrl}"><span class="material-icons text-[14px]" aria-hidden="true">account_balance</span>Flujo de caja</a>`
        : "";

    return `
      <article data-area-key="${def.key}" class="cc-card-animate flex min-w-0 flex-col overflow-hidden rounded-2xl border ${borderColor} bg-white shadow-md dark:bg-slate-900" style="animation-delay:${delayIdx * 0.06}s">
        <header class="flex items-start gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-700">
          <span class="material-icons mt-0.5 text-xl text-slate-600 dark:text-slate-300" aria-hidden="true">${def.icon}</span>
          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-bold text-slate-900 dark:text-white">${def.title}</h2>
            ${
              def.subtitle
                ? `<p class="mt-0.5 text-[11px] leading-snug text-slate-500 dark:text-slate-400">${def.subtitle}</p>`
                : ""
            }
          </div>
        </header>
        <div class="flex-1 px-4 py-2">${body}</div>
        <footer class="flex flex-col gap-2 border-t border-slate-100 px-4 py-3 sm:flex-row sm:flex-wrap dark:border-slate-700">
          ${detailBtns}
          ${def.key === "ventas" ? `<a href="${buildReportLink(cfg.executiveSalesPageUrl || "#")}" class="cc-report-link inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-sky-600 px-2.5 py-2 text-[11px] font-medium text-white hover:bg-sky-500 sm:w-auto sm:py-1" data-base-url="${cfg.executiveSalesPageUrl || ""}">Panel del día</a>` : ""}
          ${cashFlowBtn}
          ${mprBtn}
        </footer>
      </article>`;
  }

  function areaCardSkeleton(def, delayIdx) {
    const borderColor = {
      sky: "border-sky-200 dark:border-sky-800",
      emerald: "border-emerald-200 dark:border-emerald-800",
      amber: "border-amber-200 dark:border-amber-800",
      purple: "border-purple-200 dark:border-purple-800",
      rose: "border-rose-200 dark:border-rose-800",
      teal: "border-teal-200 dark:border-teal-800",
      cyan: "border-cyan-200 dark:border-cyan-800",
    }[def.color] || "border-slate-200";

    return `
      <article data-area-key="${def.key}" class="cc-card-animate flex min-w-0 flex-col overflow-hidden rounded-2xl border ${borderColor} bg-white shadow-md dark:bg-slate-900" style="animation-delay:${delayIdx * 0.06}s" aria-busy="true">
        <header class="flex items-start gap-2 border-b border-slate-100 px-4 py-3 dark:border-slate-700">
          <span class="material-icons mt-0.5 text-xl text-slate-400 dark:text-slate-500" aria-hidden="true">${def.icon}</span>
          <div class="min-w-0 flex-1">
            <h2 class="text-sm font-bold text-slate-900 dark:text-white">${def.title}</h2>
            ${
              def.subtitle
                ? `<p class="mt-0.5 text-[11px] leading-snug text-slate-500 dark:text-slate-400">${def.subtitle}</p>`
                : ""
            }
          </div>
        </header>
        <div class="flex-1 space-y-3 px-4 py-4">
          ${[1, 2, 3, 4].map(() => '<div class="h-4 animate-pulse rounded bg-slate-200/80 dark:bg-slate-700/80"></div>').join("")}
        </div>
      </article>`;
  }

  function bindInventarioPresentacion(root) {
    const scope = root || el("cc-areas-grid");
    if (!scope) return;
    scope.querySelectorAll(".cc-inv-pres-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        persistInvPresentacion(btn.dataset.invPres);
        if (!areasCache.inventario) return;
        updateSingleAreaCard("inventario", areasCache.inventario);
      });
    });
  }

  function bindDetailButtons(root) {
    const scope = root || el("cc-areas-grid");
    scope?.querySelectorAll(".cc-detail-btn").forEach((btn) => {
      btn.addEventListener("click", () => openDetail(btn.dataset.urlKey, btn.dataset.title));
    });
    bindInventarioPresentacion(scope);
  }

  function renderAreasSkeleton() {
    const grid = el("cc-areas-grid");
    if (!grid) return;
    grid.innerHTML = visibleAreaDefs().map((def, i) => areaCardSkeleton(def, i)).join("");
  }

  function updateSingleAreaCard(key, areaData) {
    const grid = el("cc-areas-grid");
    if (!grid) return;
    const idx = visibleAreaDefs().findIndex((d) => d.key === key);
    if (idx < 0) return;
    const current = grid.querySelector(`[data-area-key="${key}"]`) || grid.children[idx];
    if (!current) return;
    const html = areaCard(visibleAreaDefs()[idx], areaData, idx);
    const wrap = document.createElement("div");
    wrap.innerHTML = html.trim();
    const next = wrap.firstElementChild;
    if (next) {
      next.dataset.areaKey = key;
      current.replaceWith(next);
      bindDetailButtons(grid);
    }
  }

  function renderAreas(data) {
    const grid = el("cc-areas-grid");
    if (!grid) return;
    const areas = data.areas || data || {};
    grid.innerHTML = visibleAreaDefs().map((def, i) => areaCard(def, areas[def.key], i)).join("");
    visibleAreaDefs().forEach((def, i) => {
      const node = grid.children[i];
      if (node) node.dataset.areaKey = def.key;
    });
    bindDetailButtons(grid);
  }

  async function fetchJson(url, options) {
    const csrftoken = getCookie("csrftoken");
    const headers = { Accept: "application/json" };
    if (csrftoken) headers["X-CSRFToken"] = csrftoken;
    const res = await fetch(url, {
      credentials: "same-origin",
      headers,
      ...(options || {}),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || `Error HTTP ${res.status}`);
    }
    return body;
  }

  function buildSummaryQuery() {
    const f = readFilters();
    const q = new URLSearchParams({
      fecha_inicio: f.fecha_inicio,
      fecha_fin: f.fecha_fin,
    });
    appendFilterParams(q, f);
    return q.toString();
  }

  async function loadExecutiveSummaryDeferred(loadToken) {
    if (!cfg.executiveSummaryUrl) return;
    if (!isSingleDayPeriod(readFilters())) return;
    ventasDiaCache = null;
    renderGlobalKpis(areasCache, null);
    try {
      const data = await fetchJson(`${cfg.executiveSummaryUrl}?${buildSummaryQuery()}`);
      if (loadToken !== dashboardLoadToken) return;
      ventasDiaCache = data;
      renderGlobalKpis(areasCache, ventasDiaCache);
    } catch (e) {
      console.warn("Resumen ventas del día:", e);
      if (loadToken !== dashboardLoadToken) return;
      ventasDiaCache = {};
      renderGlobalKpis(areasCache, ventasDiaCache);
    }
  }

  async function fetchArea(key, url, q, loadToken) {
    try {
      const payload = await fetchJson(`${url}?${q}`);
      if (loadToken !== dashboardLoadToken) return null;
      return { key, ok: true, data: stripAreaMeta(payload) };
    } catch (e) {
      if (loadToken !== dashboardLoadToken) return null;
      return {
        key,
        ok: false,
        data: {
          disponible: false,
          error: { tipo: "legacy_transient_failure", mensaje: e.message || "Error al cargar" },
        },
      };
    }
  }

  async function loadDashboardParallel(loadToken) {
    const areaUrls = cfg.areaUrls || {};
    const q = buildQuery();
    const tasks = visibleAreaDefs().map((def) => {
      const url = areaUrls[def.key];
      if (!url) return Promise.resolve(null);
      return fetchArea(def.key, url, q, loadToken).then(async (result) => {
        if (!result || loadToken !== dashboardLoadToken) return;
        if (def.key === "tesoreria" && result.ok && cfg.tesoreriaBancoUrl) {
          const bancoResult = await fetchArea(
            "tesoreria_banco",
            cfg.tesoreriaBancoUrl,
            q,
            loadToken,
          );
          if (bancoResult) {
            result.data.banco = bancoResult.data;
          }
        }
        areasCache[result.key] = result.data;
        updateSingleAreaCard(result.key, result.data);
        renderGlobalKpis(areasCache, ventasDiaCache);
      });
    });
    await Promise.allSettled(tasks);
  }

  async function loadDashboardMonolith() {
    if (!cfg.dashboardUrl) return;
    setLoading(true);
    showError("");
    try {
      const q = buildQuery();
      const data = await fetchJson(`${cfg.dashboardUrl}?${q}`);
      updatePeriodoLabel(false);
      areasCache = data.areas || {};
      let ventasDia = null;
      if (cfg.executiveSummaryUrl && isSingleDayPeriod(readFilters())) {
        try {
          ventasDia = await fetchJson(`${cfg.executiveSummaryUrl}?${buildSummaryQuery()}`);
        } catch (e) {
          console.warn("Resumen ventas del día:", e);
        }
      }
      ventasDiaCache = ventasDia;
      renderGlobalKpis(areasCache, ventasDiaCache);
      renderAreas({ areas: areasCache });
    } catch (e) {
      showError(e.message || "No se pudo cargar el Command Center.");
    } finally {
      setLoading(false);
    }
  }

  async function loadDashboard() {
    const areaUrls = cfg.areaUrls || {};
    const hasParallel = Object.keys(areaUrls).length > 0;
    if (!hasParallel && !cfg.dashboardUrl) return;

    rememberFilters();

    if (!hasParallel) {
      await loadDashboardMonolith();
      return;
    }

    dashboardLoadToken += 1;
    const loadToken = dashboardLoadToken;
    showError("");
    setRefreshDisabled(true);
    areasCache = {};
    ventasDiaCache = null;
    updatePeriodoLabel(true);
    renderGlobalKpisLoading();
    renderAreasSkeleton();

    void loadExecutiveSummaryDeferred(loadToken);

    try {
      await loadDashboardParallel(loadToken);
      if (loadToken !== dashboardLoadToken) return;
      updatePeriodoLabel(false);
      const loaded = Object.keys(areasCache).length;
      if (!loaded) {
        showError("No se pudieron cargar las áreas del Command Center.");
      }
    } catch (e) {
      if (loadToken !== dashboardLoadToken) return;
      showError(e.message || "No se pudo cargar el Command Center.");
    } finally {
      if (loadToken === dashboardLoadToken) {
        setRefreshDisabled(false);
      }
    }
  }

  function openModal(show) {
    const m = el("cc-detail-modal");
    if (!m) return;
    m.classList.toggle("hidden", !show);
    m.classList.toggle("flex", show);
    m.classList.toggle("flex-col", show);
    if (show) {
      document.body.classList.add("overflow-hidden");
    } else if (waitModalLocks === 0) {
      document.body.classList.remove("overflow-hidden");
    }
  }

  function bindExistenciasSearch() {
    if (existenciasSearchBound) return;
    existenciasSearchBound = true;
    const input = el("cc-detail-search");
    const clearBtn = el("cc-detail-search-clear");
    if (!input) return;

    input.addEventListener("input", () => {
      updateExistenciasSearchClear();
      const term = input.value.trim();
      if (existenciasDebounce) clearTimeout(existenciasDebounce);
      if (term.length === 1) {
        const summaryEl = el("cc-detail-summary");
        if (summaryEl) {
          summaryEl.textContent = "Escribí al menos 2 caracteres para buscar.";
        }
        return;
      }
      existenciasDebounce = setTimeout(() => {
        loadExistenciasDetail({ busqueda: term, silent: true });
      }, 350);
    });

    clearBtn?.addEventListener("click", () => {
      input.value = "";
      updateExistenciasSearchClear();
      loadExistenciasDetail({ busqueda: "", silent: true });
      input.focus();
    });
  }

  async function loadExistenciasDetail({ busqueda = "", silent = false } = {}) {
    const base = (cfg.detailUrls || {}).existencias;
    if (!base) return;

    const term = String(busqueda || "").trim();
    if (term.length > 0 && term.length < EXISTENCIAS_SEARCH_MIN) return;

    if (existenciasAbort) existenciasAbort.abort();
    existenciasAbort = new AbortController();

    const summaryEl = el("cc-detail-summary");
    if (silent && summaryEl) {
      summaryEl.textContent = "Buscando…";
    }

    const extra = { limit: "100", offset: "0" };
    if (term.length >= EXISTENCIAS_SEARCH_MIN) {
      extra.busqueda = term;
    }
    const q = buildQuery(extra);

    try {
      const data = await fetchJson(`${base}?${q}`, { signal: existenciasAbort.signal });
      renderExistenciasDetail(data, { busqueda: term });
    } catch (e) {
      if (e && e.name === "AbortError") return;
      const err = el("cc-detail-error");
      if (err) {
        err.textContent = e.message || "Error al cargar existencias.";
        err.classList.remove("hidden");
      }
    } finally {
      if (existenciasAbort && !existenciasAbort.signal.aborted) {
        existenciasAbort = null;
      }
    }
  }

  const NAVIGATE_DETAIL_KEYS = new Set(["ventas_marcas_mensual"]);

  async function openDetail(urlKey, title) {
    const base = (cfg.detailUrls || {})[urlKey];
    if (!base) return;
    const defDetail = visibleAreaDefs()
      .flatMap((d) => d.details || [])
      .find((d) => d.urlKey === urlKey);
    if (urlKey === "ventas_marcas_mensual" || NAVIGATE_DETAIL_KEYS.has(urlKey) || defDetail?.navigate) {
      window.location.href = buildReportLink(base);
      return;
    }
    openModal(true);
    el("cc-detail-title").textContent = title || "Detalle";
    el("cc-detail-error")?.classList.add("hidden");
    clearDetailContent();
    setExistenciasSearchVisible(urlKey === "existencias");
    if (urlKey === "existencias") {
      bindExistenciasSearch();
    }
    showWaitModal("detail");
    try {
      if (urlKey === "existencias") {
        await loadExistenciasDetail({ busqueda: "", silent: false });
        const input = el("cc-detail-search");
        if (input) {
          requestAnimationFrame(() => input.focus());
        }
      } else {
        const q = buildQuery({ limit: "100", offset: "0" });
        const data = await fetchJson(`${base}?${q}`);
        if (COMP_PED_DETAIL_KEYS.has(urlKey)) {
          renderCompPedDetail(data);
        } else if (BACKORDER_DETAIL_KEYS.has(urlKey)) {
          renderBackorderDetail(data);
        } else {
          renderGenericDetailTable(data);
        }
      }
    } catch (e) {
      const err = el("cc-detail-error");
      err.textContent = e.message || "Error al cargar detalle.";
      err.classList.remove("hidden");
    } finally {
      hideWaitModal();
    }
  }

  function initDates() {
    const fromUrl = applyPeriodFromUrl();
    const saved = loadPersistedFilters();
    if (!fromUrl && saved) {
      applyPeriodFromStorage();
    } else if (saved && (saved.sucursales?.length || saved.puntos_venta?.length)) {
      if (!window.__ccPendingFilterIds) {
        window.__ccPendingFilterIds = {
          sucursales: saved.sucursales || [],
          puntos_venta: saved.puntos_venta || [],
        };
      }
    }
    const t = todayIso();
    const fi = el("cc-fecha-inicio");
    const ff = el("cc-fecha-fin");
    if (fi && !fi.value) fi.value = t;
    if (ff && !ff.value) ff.value = t;
    const onFilterChange = () => {
      rememberFilters();
      syncReportLinks();
      updatePeriodoLabel(false);
    };
    fi?.addEventListener("change", onFilterChange);
    ff?.addEventListener("change", onFilterChange);
    el("sucursales")?.addEventListener("change", onFilterChange);
    el("punto_venta")?.addEventListener("change", onFilterChange);
    rememberFilters();
    syncReportLinks();
  }

  function showCcToast(message, tipo) {
    if (window.SynapMessages && typeof window.SynapMessages.show === "function") {
      window.SynapMessages.show(message, tipo || "success");
      return;
    }
    if (typeof window.mprShowAviso === "function") {
      window.mprShowAviso(message, tipo === "error" ? "error" : "ok");
      return;
    }
    const status = el("cc-areas-config-status");
    if (status) status.textContent = message;
  }

  function areaToggleButton(key, active) {
    const on = !!active;
    return `<button type="button"
      class="cc-area-toggle inline-flex min-h-9 min-w-[6.5rem] items-center justify-center rounded-lg px-3 py-1.5 text-xs font-semibold transition
        ${on
          ? "bg-emerald-600 text-white hover:bg-emerald-500"
          : "bg-slate-700 text-slate-200 hover:bg-slate-600"}"
      data-area-key="${escHtml(key)}"
      data-active="${on ? "1" : "0"}"
      aria-pressed="${on ? "true" : "false"}">
      ${on ? "Activo" : "Inactivo"}
    </button>`;
  }

  function renderAreasConfigPanel() {
    const list = el("cc-areas-config-list");
    if (!list || !cfg.canEditAreas) return;
    const labels = cfg.areaLabels || {};
    const stored = cfg.areasConfig || {};
    const keys = Object.keys(labels).length
      ? Object.keys(labels)
      : Object.keys(stored);
    list.innerHTML = keys
      .map((key) => {
        const label = labels[key] || key;
        const active = stored[key] !== false;
        const mprHint =
          key === "manufactura" && !isMprEnabled()
            ? `<span class="mt-1 block text-[10px] text-amber-300/90">Requiere módulo MPR activo para mostrarse.</span>`
            : "";
        return `<li class="flex items-center justify-between gap-3 rounded-lg border border-slate-700/80 bg-slate-900/60 px-3 py-2.5">
          <div class="min-w-0">
            <p class="text-sm font-medium text-slate-100">${escHtml(label)}</p>
            ${mprHint}
          </div>
          ${areaToggleButton(key, active)}
        </li>`;
      })
      .join("");
    list.querySelectorAll(".cc-area-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-area-key");
        if (!key) return;
        if (!cfg.areasConfig) cfg.areasConfig = {};
        cfg.areasConfig[key] = btn.getAttribute("data-active") !== "1";
        renderAreasConfigPanel();
      });
    });
  }

  function setAreasPanelOpen(open) {
    const panel = el("cc-areas-config-panel");
    const btn = el("cc-btn-areas-config");
    if (!panel) return;
    if (open) {
      panel.classList.remove("hidden");
      panel.removeAttribute("hidden");
      btn?.setAttribute("aria-expanded", "true");
      renderAreasConfigPanel();
    } else {
      panel.classList.add("hidden");
      panel.setAttribute("hidden", "");
      btn?.setAttribute("aria-expanded", "false");
    }
  }

  async function saveAreasConfig() {
    const url = cfg.areasApiUrl;
    if (!url) return;
    const saveBtn = el("cc-areas-config-save");
    const status = el("cc-areas-config-status");
    if (saveBtn) saveBtn.disabled = true;
    if (status) status.textContent = "Guardando…";
    try {
      const csrftoken = getCookie("csrftoken");
      const headers = {
        "Content-Type": "application/json",
        Accept: "application/json",
      };
      if (csrftoken) headers["X-CSRFToken"] = csrftoken;
      const res = await fetch(url, {
        method: "PATCH",
        headers,
        credentials: "same-origin",
        body: JSON.stringify({ areas: cfg.areasConfig || {} }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "No se pudo guardar la configuración.");
      }
      cfg.areasConfig = data.areas_config || cfg.areasConfig;
      cfg.areasVisible = data.areas || cfg.areasVisible;
      if (status) status.textContent = "Guardado.";
      showCcToast(data.message || "Áreas actualizadas.", "success");
      setAreasPanelOpen(false);
      // Recargar para filtrar URLs/tarjetas SSR y estado efectivo
      window.location.reload();
    } catch (e) {
      if (status) status.textContent = "";
      showCcToast(e.message || "Error al guardar.", "error");
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  function bindAreasConfig() {
    if (!cfg.canEditAreas) return;
    el("cc-btn-areas-config")?.addEventListener("click", () => {
      const panel = el("cc-areas-config-panel");
      const open = panel && (panel.hasAttribute("hidden") || panel.classList.contains("hidden"));
      setAreasPanelOpen(!!open);
    });
    el("cc-areas-config-close")?.addEventListener("click", () => setAreasPanelOpen(false));
    el("cc-areas-config-save")?.addEventListener("click", saveAreasConfig);
  }

  function bind() {
    el("cc-refresh")?.addEventListener("click", loadDashboard);
    el("cc-detail-close")?.addEventListener("click", () => openModal(false));
    el("cc-detail-modal")?.addEventListener("click", (ev) => {
      if (ev.target === el("cc-detail-modal")) openModal(false);
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") {
        openModal(false);
        setAreasPanelOpen(false);
      }
    });
    bindAreasConfig();
  }

  document.addEventListener("DOMContentLoaded", async () => {
    initDates();
    bind();
    await initFilterTags();
    loadDashboard();
  });
})();
