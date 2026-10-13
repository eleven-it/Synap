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
  let comercialDetail = null;
  let comercialDetailData = null;
  let stockDetail = null;
  let stockDetailData = null;
  let comercialSearchTimer = null;

  function resetDetailPanelsLayout() {
    const tableWrap = el("cc-detail-table-wrap");
    const cards = el("cc-detail-cards");
    if (tableWrap) tableWrap.className = DETAIL_TABLE_WRAP_CLASS;
    if (cards) cards.className = DETAIL_CARDS_CLASS;
  }

  function formatTabularCell(key, value) {
    if (value == null || value === "") return "—";
    if (
      key === "subtotal_desc" || key === "importe" || key === "venta" ||
      key === "costo" || key === "rentabilidad" ||
      key === "bo_importe" ||
      key.endsWith("_importe") ||
      (typeof value === "number" && (key.includes("monto") || key.includes("importe")))
    ) {
      return fmtMoney.format(Number(value));
    }
    if (typeof value === "number" && (key.includes("qty") || key.includes("stock") || key === "disponible" || key === "oc_pendiente" || key === "cantidad")) {
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

  function renderTabularDetail(data, columns, cardHtmlFn, totalFormatter = fmtMoney.format.bind(fmtMoney)) {
    const total = data.total_registros ?? 0;
    let sumTxt = `${total} registro(s)`;
    if (data.total_monto != null) sumTxt += ` · Total ${totalFormatter(data.total_monto)}`;
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
    el("cc-v45-detail-controls")?.classList.add("hidden");
    el("cc-v45-detail-controls")?.classList.remove("flex");
    el("cc-v45-pagination")?.classList.add("hidden");
    el("cc-v45-pagination")?.classList.remove("flex");
    comercialDetail = null;
    comercialDetailData = null;
    stockDetail = null;
    stockDetailData = null;
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
  const FILTERS_API_URL = cfg.filtersUrl;
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
      depositos: selectedFilterIds("depositos"),
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
              depositos: [],
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
      const depositos = Array.isArray(parsed.depositos)
        ? parsed.depositos.map(String).filter(Boolean)
        : [];
      return {
        fecha_inicio: fi || "",
        fecha_fin: ff || "",
        sucursales,
        puntos_venta,
        depositos,
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
          depositos: f.depositos || [],
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
      url.searchParams.delete("depositos");
      (f.sucursales || []).forEach((id) => url.searchParams.append("sucursales", id));
      (f.puntos_venta || []).forEach((id) => url.searchParams.append("punto_venta", id));
      (f.depositos || []).forEach((id) => url.searchParams.append("depositos", id));
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
    (f.depositos || []).forEach((id) => q.append("depositos", id));
  }

  function buildQuery(extra) {
    const f = readFilters();
    const q = new URLSearchParams({
      fecha_inicio: f.fecha_inicio,
      fecha_fin: f.fecha_fin,
      ...(extra || {}),
    });
    appendFilterParams(q, f);
    if (selectedAreaKey === "ventas" || selectedAreaKey === "resumen_general") {
      if (el("cc-incluir-impuestos")?.checked) q.set("incluir_impuestos", "1");
      if (el("cc-comparar-anterior")?.checked) q.set("comparar", "anterior");
    } else if (selectedAreaKey === "inventario") {
      q.set("presentacion", el("cc-stock-presentacion")?.value || "unidad");
      if (el("cc-stock-comparar")?.checked) q.set("comparar", "anterior");
    }
    if (selectedAreaKey === "gestion_contable" && el("cc-grupo-contable")?.value) {
      q.set("grupo_contable", el("cc-grupo-contable").value);
    }
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
      depositos: params.getAll("depositos"),
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
    [["sucursales", pending.sucursales], ["punto_venta", pending.puntos_venta], ["depositos", pending.depositos]].forEach(
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
    if (saved.sucursales?.length || saved.puntos_venta?.length || saved.depositos?.length) {
      window.__ccPendingFilterIds = {
        sucursales: saved.sucursales || [],
        puntos_venta: saved.puntos_venta || [],
        depositos: saved.depositos || [],
      };
    }
    return applied;
  }

  let waitModalLocks = 0;
  let areasCache = {};
  let dashboardLoadToken = 0;
  let selectedAreaKey = "";

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
    return key === selectedAreaKey && !!vis && vis[key] === true;
  }

  function visibleAreaDefs() {
    return AREA_DEFS.filter((d) => isAreaVisible(d.key));
  }

  function dashboardWaitSubtitle() {
    const labelMap = {
      resumen_general: "resumen gerencial",
      preparacion_pedidos: "preparación de pedidos",
      ventas: "ventas",
      inventario: "inventario",
      compras: "compras",
      financiero: "análisis financiero",
      gestion_contable: "gestión contable",
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
      const [sucRes, pvRes, depRes] = await Promise.all([
        fetch(`${FILTERS_API_URL}?type=sucursales`, { credentials: "same-origin" }),
        fetch(`${FILTERS_API_URL}?type=puntos_venta`, { credentials: "same-origin" }),
        fetch(`${FILTERS_API_URL}?type=depositos`, { credentials: "same-origin" }),
      ]);
      const sucPayload = sucRes.ok ? await sucRes.json() : {};
      const pvPayload = pvRes.ok ? await pvRes.json() : {};
      const depPayload = depRes.ok ? await depRes.json() : {};
      poblarSelectTags("sucursales", sucPayload.sucursales || [], "value", "label");
      poblarSelectTags("punto_venta", pvPayload.puntos_venta || [], "value", "label");
      poblarSelectTags("depositos", depPayload.depositos || [], "value", "label");
      if (typeof window.initializeTagsFilter === "function") {
        window.initializeTagsFilter("sucursales", "sucursales");
        window.initializeTagsFilter("punto_venta", "puntos_venta");
        window.initializeTagsFilter("depositos", "depositos");
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

  function stockValueLabel(area) {
    if (!area || area.disponible === false) return "No disponible";
    const value = area.kpis?.stock_valorizado ?? area.valor_stock;
    if (value == null) return "Sin permiso";
    return fmtMoney.format(value);
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

  function renderGlobalKpis(areas) {
    const grid = el("cc-global-kpis");
    if (!grid) return;
    const f = readFilters();
    const singleDay = isSingleDayPeriod(f);
    const a = areas || {};
    const resumen = a.resumen_general || {};
    const preparacion = a.preparacion_pedidos || {};
    const v = a.ventas || {};
    const inv = a.inventario || {};
    const comp = a.compras || {};
    const fin = a.financiero || {};
    const account = a.gestion_contable || {};
    const mfg = a.manufactura || {};
    const cruz = a.cruzados || {};
    const ventasFirstLabel = singleDay ? "Ventas netas (día)" : "Ventas netas (período)";
    const ventasFirstVal = v.disponible === false
      ? "No disponible"
      : fmtMoney.format(v.kpis?.ventas_netas ?? v.ventas_netas ?? 0);

    const cards = [];
    if (isAreaVisible("resumen_general")) {
      cards.push(kpiCard("Ventas del período", resumen.disponible === false ? "No disponible" : fmtMoney.format(resumen.kpis?.ventas ?? 0), "sky"));
      cards.push(kpiCard("Pedidos", resumen.disponible === false ? "No disponible" : fmtNum.format(resumen.kpis?.pedidos ?? 0), "indigo"));
    }
    if (isAreaVisible("preparacion_pedidos")) {
      cards.push(kpiCard("Pedidos ingresados", preparacion.disponible === false ? "No disponible" : fmtNum.format(preparacion.kpis?.pedidos_ingresados ?? 0), "sky"));
      cards.push(kpiCard("Pedidos pendientes", preparacion.disponible === false ? "No disponible" : fmtNum.format(preparacion.kpis?.pendientes ?? 0), "amber"));
    }
    if (isAreaVisible("ventas")) {
      cards.push(kpiCard(ventasFirstLabel, ventasFirstVal, "sky"));
      cards.push(kpiCard("Facturas", v.disponible === false ? "No disponible" : fmtNum.format(v.kpis?.facturas ?? 0), "indigo"));
    }
    if (isAreaVisible("inventario")) {
      cards.push(kpiCard("Valor stock", stockValueLabel(inv), "emerald"));
    }
    if (isAreaVisible("compras")) {
      cards.push(
        kpiCard("Compras netas", comp.disponible === false ? "No disponible" : fmtMoney.format(comp.kpis?.compras_netas ?? 0), "amber")
      );
    }
    if (isAreaVisible("financiero")) {
      cards.push(kpiCard("Flujo neto", fin.disponible === false ? "No disponible" : fmtMoney.format(fin.kpis?.flujo_neto ?? 0), "teal"));
      cards.push(kpiCard("Vencido a cobrar", fin.disponible === false ? "No disponible" : fmtMoney.format(fin.kpis?.vencido_cobrar ?? 0), "amber"));
    }
    if (isAreaVisible("gestion_contable")) {
      cards.push(kpiCard("Asientos", account.disponible === false ? "No disponible" : fmtNum.format(account.kpis?.asientos ?? 0), "indigo"));
      cards.push(kpiCard("Diferencia Debe/Haber", account.disponible === false ? "No disponible" : fmtMoney.format(account.kpis?.diferencia ?? 0), "emerald"));
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
    if (isAreaVisible("resumen_general")) {
      loadingCards.push(kpiCardLoading("Ventas del período", "sky"));
      loadingCards.push(kpiCardLoading("Pedidos", "indigo"));
    }
    if (isAreaVisible("preparacion_pedidos")) {
      loadingCards.push(kpiCardLoading("Pedidos ingresados", "sky"));
      loadingCards.push(kpiCardLoading("Pedidos pendientes", "amber"));
    }
    if (isAreaVisible("ventas")) {
      loadingCards.push(kpiCardLoading(ventasLabel, "sky"));
      loadingCards.push(kpiCardLoading("Facturas", "indigo"));
    }
    if (isAreaVisible("inventario")) {
      loadingCards.push(kpiCardLoading("Valor stock", "emerald"));
    }
    if (isAreaVisible("compras")) {
      loadingCards.push(kpiCardLoading("Compras netas", "amber"));
    }
    if (isAreaVisible("financiero")) {
      loadingCards.push(kpiCardLoading("Flujo neto", "emerald"));
      loadingCards.push(kpiCardLoading("Vencido a cobrar", "amber"));
    }
    if (isAreaVisible("gestion_contable")) {
      loadingCards.push(kpiCardLoading("Asientos", "indigo"));
      loadingCards.push(kpiCardLoading("Diferencia Debe/Haber", "emerald"));
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
      key: "resumen_general",
      title: "Resumen gerencial (V45)",
      icon: "dashboard",
      color: "sky",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        const count = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        return [
          ["Ventas", money("ventas")], ["Compras netas", money("compras_netas")],
          ["Cobranzas", money("cobranzas")], ["Pagos", money("pagos")],
          ["Presupuestos", count("presupuestos")], ["Pedidos", count("pedidos")],
          ["Facturas", count("facturas")], ["Remitos", count("remitos")],
          ["Vencimiento a cobrar", money("vencimiento_cobrar")],
          ["Vencimiento a pagar", money("vencimiento_pagar")],
          ["Efectivo actual", money("efectivo_actual")],
          ["Tarjetas actual", money("tarjetas_actual")],
          ["Cheques actual", money("cheques_actual")],
          ["Bancos actual", money("bancos_actual")],
          ["Venta cuenta corriente", money("venta_cuenta_corriente")],
          ["Compra cuenta corriente", money("compra_cuenta_corriente")],
        ];
      },
      afterMetrics: (a) => renderResumenV45Charts(a),
      details: [],
    },
    {
      key: "ventas",
      title: "Comercial · Ventas (V45)",
      icon: "point_of_sale",
      color: "sky",
      metrics: (a) => {
        const k = a.kpis || {};
        const m = (name) => k[name] == null ? "No disponible" : fmtMoney.format(k[name]);
        const n = (name) => k[name] == null ? "No disponible" : fmtNum.format(k[name]);
        const rows = [
          ["Ventas netas", m("ventas_netas")],
          ["Rentabilidad", k.rentabilidad == null ? "Sin permiso de costos" : m("rentabilidad")],
          ["Margen %", k.margen_porcentaje == null ? "Sin permiso de costos" : `${k.margen_porcentaje} %`],
          ["Ticket promedio", m("ticket_promedio")],
          ["Presupuestos", n("presupuestos")],
          ["Monto presupuestos", m("monto_presupuestos")],
          ["Pedidos", n("pedidos")],
          ["Monto pedidos", m("monto_pedidos")],
          ["Pedidos pendientes", n("pedidos_pendientes")],
          ["Monto pendiente", m("monto_pendientes")],
          ["Pedidos en remito", n("pedidos_en_remito")],
          ["Pedidos facturados", n("pedidos_facturados")],
          ["Remitos", n("remitos")],
          ["Facturas", n("facturas")],
          ["Créditos/devoluciones", m("creditos_devoluciones")],
          ["Notas de débito", m("notas_debito")],
        ];
        const keys = [
          "ventas_netas", "rentabilidad", "margen_porcentaje", "ticket_promedio",
          "presupuestos", "monto_presupuestos", "pedidos", "monto_pedidos",
          "pedidos_pendientes", "monto_pendientes", "pedidos_en_remito",
          "pedidos_facturados", "remitos", "facturas", "creditos_devoluciones", "notas_debito",
        ];
        return rows.map((row, index) => [...row, keys[index]]);
      },
      afterMetrics: (a) => renderComercialV45Comparison(a),
      details: [],
    },
    {
      key: "preparacion_pedidos",
      title: "Comercial · Preparación de pedidos (V45)",
      icon: "assignment_turned_in",
      color: "amber",
      metrics: (a) => {
        const k = a.kpis || {};
        const count = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        return [
          ["Pedidos ingresados", count("pedidos_ingresados")],
          ["Monto pedidos", money("monto_pedidos")],
          ["Pendientes", count("pendientes")],
          ["Monto pendiente", money("monto_pendiente")],
          ["En preparación", count("en_preparacion")],
          ["Preparados", count("preparados")],
          ["Backorder", count("backorder")],
          ["Monto backorder", money("monto_backorder")],
          ["En remito", count("en_remito")],
          ["Facturados", count("facturados")],
          ["Cerrados", count("cerrados")],
          ["Anulados", count("anulados")],
          ["Unidades pendientes", count("unidades_pendientes")],
          ["Tiempo promedio", k.tiempo_promedio == null ? "N/D" : `${fmtNum.format(k.tiempo_promedio)} h`],
          ["Monto facturado", money("monto_facturado")],
          ["Monto en remito", money("monto_en_remito")],
        ];
      },
      afterMetrics: (a) => renderPreparacionV45Charts(a),
      details: [],
    },
    {
      key: "inventario",
      title: "Abastecimiento · Stock (V45)",
      icon: "inventory_2",
      color: "emerald",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "Sin permiso de costos" : fmtMoney.format(k[key]);
        const qty = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        return [
          ["Stock valorizado", money("stock_valorizado"), "stock_valorizado"],
          ["Disponible", qty("unidades_disponibles"), "unidades_disponibles"],
          ["Artículos con stock", qty("articulos_con_stock"), "articulos_con_stock"],
          ["Stock negativo", qty("articulos_stock_negativo"), "articulos_stock_negativo"],
          ["Bajo mínimo", qty("bajo_minimo"), "bajo_minimo"],
          ["Punto pedido", qty("punto_pedido"), "punto_pedido"],
          ["Sobre máximo", qty("sobre_maximo"), "sobre_maximo"],
          ["Reservado", qty("stock_reservado"), "stock_reservado"],
          ["Pendiente recibir", qty("pendiente_recibir"), "pendiente_recibir"],
          ["Entradas período", qty("entradas_periodo"), "entradas_periodo"],
          ["Salidas período", qty("salidas_periodo"), "salidas_periodo"],
          ["Valor entradas", money("valor_entradas"), "valor_entradas"],
          ["Valor salidas", money("valor_salidas"), "valor_salidas"],
          ["Sin movimiento 90 días", qty("sin_movimiento_90d"), "sin_movimiento_90d"],
        ];
      },
      afterMetrics: (a) => renderStockV45Charts(a),
      details: [{ label: "Existencias", urlKey: "existencias" }],
    },
    {
      key: "compras",
      title: "Abastecimiento · Compras (V45)",
      icon: "shopping_cart",
      color: "amber",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        const count = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        return [
          ["Compras netas", money("compras_netas")],
          ["Facturas", count("facturas")],
          ["Ticket promedio", money("ticket_promedio")],
          ["Notas de crédito", count("notas_credito")],
          ["Órdenes de compra", count("ordenes_compra")],
          ["Monto en OC", money("monto_oc")],
          ["OC pendientes", count("oc_pendientes")],
          ["Monto pendiente", money("monto_pendiente")],
          ["OC parciales", count("oc_parciales")],
          ["Remitos recibidos", count("remitos_recibidos")],
          ["Remitos sin factura", count("remitos_sin_factura")],
          ["OC vencidas", count("oc_vencidas")],
          ["Proveedores", count("proveedores")],
          ["Plazo promedio", k.plazo_promedio == null ? "N/D" : `${fmtNum.format(k.plazo_promedio)} días`],
        ];
      },
      afterMetrics: (a) => renderComprasV45Charts(a),
      details: [],
    },
    {
      key: "financiero",
      title: "Análisis financiero (V45)",
      icon: "account_balance",
      color: "teal",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        return [
          ["Cobranzas", money("cobranzas")], ["Pagos", money("pagos")],
          ["Flujo neto", money("flujo_neto")],
          ["Saldo a cobrar", money("saldo_cobrar")],
          ["Saldo a pagar", money("saldo_pagar")],
          ["Vencido a cobrar", money("vencido_cobrar")],
          ["Vencido a pagar", money("vencido_pagar")],
          ["Efectivo", money("efectivo")], ["Tarjetas", money("tarjetas")],
          ["Cheques en cartera", money("cheques_cartera")],
          ["Cheques emitidos", money("cheques_emitidos")],
          ["Cheques rechazados", money("cheques_rechazados")],
          ["Bancos", money("bancos")],
          ["A cobrar +60 días", money("cobrar_mas_60")],
          ["A pagar +60 días", money("pagar_mas_60")],
        ];
      },
      afterMetrics: (a) => renderFinancieroV45Charts(a),
      details: [],
    },
    {
      key: "gestion_contable",
      title: "Gestión contable (V45)",
      icon: "account_balance_wallet",
      color: "purple",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        const count = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        return [
          ["Asientos", count("asientos")], ["Total Debe", money("total_debe")],
          ["Total Haber", money("total_haber")], ["Diferencia", money("diferencia")],
          ["Desbalanceados", count("desbalanceados")],
          ["Asientos manuales", count("manuales")],
          ["Asientos de proceso", count("proceso")],
          ["Resultado contable", money("resultado_contable")],
          ["Impuestos determinados", money("impuestos_determinados")],
          ["Impuestos a pagar", money("impuestos_pagar")],
          ["Saldos a favor", money("impuestos_favor")],
          ["Impuestos vencidos", money("impuestos_vencidos")],
          ["Períodos abiertos", count("periodos_abiertos")],
          ["Ejercicios abiertos", count("ejercicios_abiertos")],
        ];
      },
      afterMetrics: (a) => renderContableV45Charts(a),
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

  function renderContableV45Charts(areaData) {
    const rows = (areaData.serie_asientos?.filas || []).slice(-30);
    const maxValue = Math.max(1, ...rows.flatMap((row) => [Number(row.debe || 0), Number(row.haber || 0)]));
    const step = rows.length ? 304 / rows.length : 304;
    const width = Math.max(1, step / 2 - 1);
    const bars = rows.map((row, index) => {
      const debit = Math.max(0, Number(row.debe || 0)) / maxValue * 83;
      const credit = Math.max(0, Number(row.haber || 0)) / maxValue * 83;
      const x = 8 + index * step;
      return `<rect x="${x.toFixed(1)}" y="${(96 - debit).toFixed(1)}" width="${width.toFixed(1)}" height="${debit.toFixed(1)}" fill="#7c3aed" />
        <rect x="${(x + width).toFixed(1)}" y="${(96 - credit).toFixed(1)}" width="${width.toFixed(1)}" height="${credit.toFixed(1)}" fill="#14b8a6" />`;
    }).join("");
    const tableRows = rows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800"><th scope="row" class="px-2 py-1.5 text-left">${escHtml(row.fecha)}</th><td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.debe)}</td><td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.haber)}</td></tr>`).join("");
    const k = areaData.kpis || {};
    const tax = [
      ["Determinados", "impuestos_determinados"],
      ["A pagar", "impuestos_pagar"],
      ["A favor", "impuestos_favor"],
      ["Vencidos", "impuestos_vencidos"],
    ];
    const taxMax = Math.max(1, ...tax.map(([, key]) => Number(k[key] || 0)));
    const taxRows = tax.map(([label, key]) => `<div class="border-b border-slate-100 py-2 last:border-0 dark:border-slate-800"><p class="text-[11px]">${label}</p><div class="mt-1 h-2 rounded bg-slate-100 dark:bg-slate-800"><div class="h-2 rounded bg-amber-500" style="width:${Math.max(0, Number(k[key] || 0)) / taxMax * 100}%"></div></div><p class="mt-1 text-right text-xs font-semibold tabular-nums">${k[key] == null ? "N/D" : fmtMoney.format(k[key])}</p></div>`).join("");
    return `<div class="mt-4 grid gap-3 lg:grid-cols-2">
      <div class="rounded-lg border border-slate-200 p-2 dark:border-slate-700"><h3 class="text-xs font-semibold">Libro Diario · Debe y Haber</h3><svg viewBox="0 0 320 102" role="img" aria-label="Debe y Haber por período" class="mt-2 h-28 w-full"><line x1="8" y1="96" x2="312" y2="96" stroke="#94a3b8" />${bars}</svg><p class="text-[11px] text-slate-500">● Violeta: Debe · ● Turquesa: Haber</p>
        <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa</summary><div class="mt-2 max-h-60 overflow-auto"><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Debe</th><th class="px-2 py-2 text-right">Haber</th></tr></thead><tbody>${tableRows}</tbody></table></div></details>
      </div><div class="rounded-lg border border-slate-200 p-3 dark:border-slate-700"><h3 class="text-xs font-semibold">Situación fiscal · alcance general</h3>${taxRows}</div>
    </div><p class="mt-2 text-[11px] text-slate-500">Impuestos, períodos y ejercicios son generales para la empresa.</p>`;
  }

  function renderFinancieroV45Charts(areaData) {
    const rows = (areaData.serie_flujo?.filas || []).slice(-30);
    const maxFlow = Math.max(1, ...rows.flatMap((row) => [Number(row.cobranzas || 0), Number(row.pagos || 0)]));
    const step = rows.length ? 304 / rows.length : 304;
    const width = Math.max(1, step / 2 - 1);
    const bars = rows.map((row, index) => {
      const collected = Math.max(0, Number(row.cobranzas || 0)) / maxFlow * 83;
      const paid = Math.max(0, Number(row.pagos || 0)) / maxFlow * 83;
      const x = 8 + index * step;
      return `<rect x="${x.toFixed(1)}" y="${(96 - collected).toFixed(1)}" width="${width.toFixed(1)}" height="${collected.toFixed(1)}" fill="#0d9488" />
        <rect x="${(x + width).toFixed(1)}" y="${(96 - paid).toFixed(1)}" width="${width.toFixed(1)}" height="${paid.toFixed(1)}" fill="#f97316" />`;
    }).join("");
    const buckets = [
      ["Por vencer", "por_vencer"], ["0–7 días", "d0_7"],
      ["8–30 días", "d8_30"], ["31–60 días", "d31_60"],
      ["+60 días", "mas_60"],
    ];
    const receivable = areaData.aging?.cobrar || {};
    const payable = areaData.aging?.pagar || {};
    const maxAging = Math.max(1, ...buckets.flatMap(([, key]) => [Number(receivable[key] || 0), Number(payable[key] || 0)]));
    const agingRows = buckets.map(([name, key]) => `<div class="border-b border-slate-100 py-2 last:border-0 dark:border-slate-800">
      <p class="text-[11px] font-medium">${name}</p>
      <div class="mt-1 flex items-center gap-2"><div class="h-2 min-w-0 flex-1 rounded bg-slate-100 dark:bg-slate-800"><div class="h-2 rounded bg-teal-600" style="width:${Math.max(0, Number(receivable[key] || 0)) / maxAging * 100}%"></div></div><span class="w-24 text-right text-[10px] tabular-nums">${receivable[key] == null ? "N/D" : fmtMoney.format(receivable[key])}</span></div>
      <div class="mt-1 flex items-center gap-2"><div class="h-2 min-w-0 flex-1 rounded bg-slate-100 dark:bg-slate-800"><div class="h-2 rounded bg-orange-400" style="width:${Math.max(0, Number(payable[key] || 0)) / maxAging * 100}%"></div></div><span class="w-24 text-right text-[10px] tabular-nums">${payable[key] == null ? "N/D" : fmtMoney.format(payable[key])}</span></div>
    </div>`).join("");
    const seriesRows = rows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800"><th scope="row" class="px-2 py-1.5 text-left">${escHtml(row.fecha)}</th><td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.cobranzas)}</td><td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.pagos)}</td></tr>`).join("");
    return `<div class="mt-4 grid gap-3 lg:grid-cols-2">
      <div class="rounded-lg border border-slate-200 p-2 dark:border-slate-700"><h3 class="text-xs font-semibold">Flujo del período</h3><svg viewBox="0 0 320 102" role="img" aria-label="Cobranzas y pagos por período" class="mt-2 h-28 w-full"><line x1="8" y1="96" x2="312" y2="96" stroke="#94a3b8" />${bars}</svg><p class="text-[11px] text-slate-500">● Turquesa: cobranzas · ● Naranja: pagos</p>
        <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa</summary><div class="mt-2 max-h-60 overflow-auto"><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Cobranzas</th><th class="px-2 py-2 text-right">Pagos</th></tr></thead><tbody>${seriesRows}</tbody></table></div></details>
      </div>
      <div class="rounded-lg border border-slate-200 p-3 dark:border-slate-700"><h3 class="text-xs font-semibold">Antigüedad de saldos</h3><p class="text-[11px] text-slate-500">● Turquesa: cobrar · ● Naranja: pagar</p>${agingRows}</div>
    </div>`;
  }

  function renderComprasV45Charts(areaData) {
    const rows = (areaData.serie_evolucion?.filas || []).slice(-30);
    const maxValue = Math.max(1, ...rows.flatMap((row) => [Number(row.compras || 0), Number(row.ordenes || 0)]));
    const step = rows.length ? 304 / rows.length : 304;
    const width = Math.max(1, step / 2 - 1);
    const bars = rows.map((row, index) => {
      const buy = Math.max(0, Number(row.compras || 0)) / maxValue * 83;
      const order = Math.max(0, Number(row.ordenes || 0)) / maxValue * 83;
      const x = 8 + index * step;
      return `<rect x="${x.toFixed(1)}" y="${(96 - buy).toFixed(1)}" width="${width.toFixed(1)}" height="${buy.toFixed(1)}" fill="#d97706" />
        <rect x="${(x + width).toFixed(1)}" y="${(96 - order).toFixed(1)}" width="${width.toFixed(1)}" height="${order.toFixed(1)}" fill="#0284c7" />`;
    }).join("");
    const tableRows = rows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800">
      <th scope="row" class="px-2 py-1.5 text-left font-medium">${escHtml(row.fecha)}</th>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.compras)}</td>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.ordenes)}</td>
    </tr>`).join("");
    const previous = areaData.comparacion?.kpis?.compras_netas;
    return `<div class="mt-4 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
      <p class="text-xs font-semibold">Evolución de compras y OC · ${areaData.serie_evolucion?.agrupacion || "período"}</p>
      <svg viewBox="0 0 320 102" role="img" aria-label="Compras y órdenes de compra por período" class="mt-2 h-28 w-full"><line x1="8" y1="96" x2="312" y2="96" stroke="#94a3b8" />${bars}</svg>
      <p class="text-[11px] text-slate-500">🟠 Compras · 🔵 Órdenes de compra</p>
      <p class="mt-2 text-xs">Compras período anterior: <strong class="tabular-nums">${previous == null ? "No disponible" : fmtMoney.format(previous)}</strong></p>
      <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa</summary>
        <div class="mt-2 max-h-72 overflow-auto"><table class="w-full min-w-[30rem] text-xs"><thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Compras</th><th class="px-2 py-2 text-right">OC</th></tr></thead><tbody>${tableRows}</tbody></table></div>
      </details></div>`;
  }

  function renderPreparacionV45Charts(areaData) {
    const states = areaData.serie_estados || [];
    const amounts = areaData.serie_importes || [];
    const maxCount = Math.max(1, ...states.flatMap((row) => [Number(row.actual || 0), Number(row.anterior || 0)]));
    const maxAmount = Math.max(1, ...amounts.map((row) => Number(row.importe || 0)));
    const stateRows = states.map((row) => `<div class="border-b border-slate-100 py-2 last:border-0 dark:border-slate-800">
      <p class="text-xs font-medium">${escHtml(row.estado)}</p>
      <div class="mt-1 flex items-center gap-2 text-[11px]"><div class="h-2 min-w-0 flex-1 rounded bg-slate-100 dark:bg-slate-800"><div class="h-2 rounded bg-sky-600" style="width:${Math.max(0, Number(row.actual || 0)) / maxCount * 100}%"></div></div><span class="w-10 text-right tabular-nums">${fmtNum.format(row.actual)}</span></div>
      <div class="mt-1 flex items-center gap-2 text-[11px]"><div class="h-2 min-w-0 flex-1 rounded bg-slate-100 dark:bg-slate-800"><div class="h-2 rounded bg-orange-400" style="width:${Math.max(0, Number(row.anterior || 0)) / maxCount * 100}%"></div></div><span class="w-10 text-right tabular-nums">${fmtNum.format(row.anterior)}</span></div>
    </div>`).join("");
    const amountRows = amounts.map((row) => `<div class="border-b border-slate-100 py-2 last:border-0 dark:border-slate-800">
      <p class="text-xs font-medium">${escHtml(row.estado)}</p>
      <div class="mt-1 h-2 rounded bg-slate-100 dark:bg-slate-800"><div class="h-2 rounded bg-emerald-600" style="width:${Math.max(0, Number(row.importe || 0)) / maxAmount * 100}%"></div></div>
      <p class="mt-1 text-right text-xs font-semibold tabular-nums">${row.importe == null ? "No disponible" : fmtMoney.format(row.importe)}</p>
    </div>`).join("");
    return `<div class="mt-4 grid gap-3 lg:grid-cols-2">
      <section class="rounded-lg border border-slate-200 p-3 dark:border-slate-700"><h3 class="text-xs font-semibold">Estados · <span class="text-sky-600">actual</span> / <span class="text-orange-500">anterior</span></h3>${stateRows}</section>
      <section class="rounded-lg border border-slate-200 p-3 dark:border-slate-700"><h3 class="text-xs font-semibold">Importes por estado</h3>${amountRows}</section>
    </div>`;
  }

  function renderResumenV45Charts(areaData) {
    const series = (areaData.series?.filas || []).slice(-30);
    const chart = (title, left, right, leftLabel, rightLabel) => {
      const maxValue = Math.max(1, ...series.flatMap((row) => [
        Number(row[left] || 0), Number(row[right] || 0),
      ]));
      const step = series.length ? 304 / series.length : 304;
      const width = Math.max(1, step / 2 - 1);
      const bars = series.map((row, index) => {
        const leftHeight = Math.max(0, Number(row[left] || 0)) / maxValue * 83;
        const rightHeight = Math.max(0, Number(row[right] || 0)) / maxValue * 83;
        const x = 8 + index * step;
        return `<rect x="${x.toFixed(1)}" y="${(96 - leftHeight).toFixed(1)}" width="${width.toFixed(1)}" height="${leftHeight.toFixed(1)}" fill="#0284c7" />
          <rect x="${(x + width).toFixed(1)}" y="${(96 - rightHeight).toFixed(1)}" width="${width.toFixed(1)}" height="${rightHeight.toFixed(1)}" fill="#f97316" />`;
      }).join("");
      return `<div class="min-w-0 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
        <p class="text-xs font-semibold">${title}</p>
        <svg viewBox="0 0 320 102" role="img" aria-label="${title}" class="mt-2 h-28 w-full"><line x1="8" y1="96" x2="312" y2="96" stroke="#94a3b8" />${bars}</svg>
        <p class="text-[11px] text-slate-500">🔵 ${leftLabel} · 🟠 ${rightLabel}</p>
      </div>`;
    };
    const prior = areaData.comparacion?.kpis || {};
    const current = areaData.kpis || {};
    const fields = ["ventas", "compras_netas", "cobranzas", "pagos", "presupuestos", "pedidos", "facturas", "remitos", "venta_cuenta_corriente", "compra_cuenta_corriente"];
    const names = ["Ventas", "Compras netas", "Cobranzas", "Pagos", "Presupuestos", "Pedidos", "Facturas", "Remitos", "Venta cta. cte.", "Compra cta. cte."];
    const countKeys = new Set(["presupuestos", "pedidos", "facturas", "remitos"]);
    const format = (key, value) => value == null ? "No disponible" : countKeys.has(key) ? fmtNum.format(value) : fmtMoney.format(value);
    const rows = fields.map((key, index) => `<tr class="border-t border-slate-100 dark:border-slate-800">
      <th scope="row" class="px-2 py-1.5 text-left font-medium">${names[index]}</th>
      <td class="px-2 py-1.5 text-right tabular-nums">${format(key, current[key])}</td>
      <td class="px-2 py-1.5 text-right tabular-nums">${format(key, prior[key])}</td>
      <td class="px-2 py-1.5 text-right tabular-nums">${format(key, areaData.comparacion?.diferencias?.[key])}</td>
    </tr>`).join("");
    const seriesRows = series.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800">
      <th scope="row" class="px-2 py-1.5 text-left font-medium">${escHtml(row.fecha)}</th>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.ventas)}</td>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.compras)}</td>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.cobranzas)}</td>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.pagos)}</td>
    </tr>`).join("");
    return `<div class="mt-4 grid gap-3 lg:grid-cols-2">
      ${chart("Gestión comercial", "ventas", "compras", "Ventas", "Compras")}
      ${chart("Tesorería", "cobranzas", "pagos", "Cobranzas", "Pagos")}
    </div><details class="mt-3"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Ver serie completa (${areaData.series?.agrupacion || "período"})</summary>
      <div class="mt-2 max-h-80 overflow-auto"><table class="w-full min-w-[38rem] text-xs text-slate-700 dark:text-slate-200">
        <thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Ventas</th><th class="px-2 py-2 text-right">Compras</th><th class="px-2 py-2 text-right">Cobranzas</th><th class="px-2 py-2 text-right">Pagos</th></tr></thead>
        <tbody>${seriesRows}</tbody></table></div></details>
    <details class="mt-3"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Comparar período anterior</summary>
      <div class="mt-2 max-h-80 overflow-auto"><table class="w-full min-w-[34rem] text-xs text-slate-700 dark:text-slate-200">
        <thead><tr><th class="px-2 py-2 text-left">Indicador</th><th class="px-2 py-2 text-right">Actual</th><th class="px-2 py-2 text-right">Anterior</th><th class="px-2 py-2 text-right">Variación</th></tr></thead>
        <tbody>${rows}</tbody></table></div></details>`;
  }

  function renderComercialV45Comparison(areaData) {
    const comparison = areaData?.comparacion;
    if (!comparison?.kpis) return "";
    const actual = areaData.kpis || {};
    const previous = comparison.kpis;
    const fields = [
      ["Ventas netas", "ventas_netas", "money"],
      ["Rentabilidad", "rentabilidad", "money"],
      ["Margen", "margen_porcentaje", "percent"],
      ["Ticket promedio", "ticket_promedio", "money"],
      ["Presupuestos", "presupuestos", "count"],
      ["Monto presupuestos", "monto_presupuestos", "money"],
      ["Pedidos", "pedidos", "count"],
      ["Monto pedidos", "monto_pedidos", "money"],
      ["Pedidos pendientes", "pedidos_pendientes", "count"],
      ["Monto pendiente", "monto_pendientes", "money"],
      ["En remito", "pedidos_en_remito", "count"],
      ["Facturados", "pedidos_facturados", "count"],
      ["Remitos", "remitos", "count"],
      ["Facturas", "facturas", "count"],
      ["Créditos/devoluciones", "creditos_devoluciones", "money"],
      ["Notas de débito", "notas_debito", "money"],
    ];
    const formatValue = (value, kind) => {
      if (value == null) return "Sin permiso";
      if (kind === "money") return fmtMoney.format(value);
      if (kind === "percent") return `${Number(value).toFixed(2)} %`;
      return fmtNum.format(value);
    };
    const rows = fields.map(([label, key, kind]) => {
      const delta = comparison.diferencias?.[key];
      return `<tr class="border-t border-slate-100 dark:border-slate-800">
        <th scope="row" class="px-2 py-1.5 text-left font-medium">${label}</th>
        <td class="px-2 py-1.5 text-right tabular-nums">${formatValue(actual[key], kind)}</td>
        <td class="px-2 py-1.5 text-right tabular-nums">${formatValue(previous[key], kind)}</td>
        <td class="px-2 py-1.5 text-right tabular-nums">${formatValue(delta, kind)}</td>
      </tr>`;
    }).join("");
    const currentSeries = areaData.series?.ventas_actual || [];
    const previousSeries = areaData.series?.ventas_anterior || [];
    const pointCount = Math.max(currentSeries.length, previousSeries.length, 2);
    const allValues = [...currentSeries, ...previousSeries].map((item) => Number(item.valor || 0));
    const minValue = Math.min(0, ...allValues);
    const maxValue = Math.max(1, ...allValues);
    const range = Math.max(1, maxValue - minValue);
    const points = (series) => series.map((item, index) => {
      const x = 8 + (index / (pointCount - 1)) * 304;
      const y = 103 - ((Number(item.valor || 0) - minValue) / range) * 88;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
    const graph = `<div class="mt-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
      <p class="mb-1 text-[11px] font-semibold text-slate-600 dark:text-slate-300">Evolución de ventas por ${areaData.series?.agrupacion === "mes" ? "mes" : "día"}</p>
      <svg viewBox="0 0 320 112" role="img" aria-label="Ventas diarias: período actual azul y anterior naranja" class="h-28 w-full">
        <line x1="8" y1="103" x2="312" y2="103" stroke="#94a3b8" />
        <polyline points="${points(previousSeries)}" fill="none" stroke="#f97316" stroke-width="2.5" />
        <polyline points="${points(currentSeries)}" fill="none" stroke="#0284c7" stroke-width="2.5" />
      </svg>
      <div class="flex gap-4 text-[10px] text-slate-500"><span>● Azul: actual</span><span>● Naranja: anterior</span></div>
    </div>`;
    return `${graph}<details class="mt-3"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Comparar los 16 indicadores</summary>
      <div class="mt-2 max-h-80 overflow-auto"><table class="w-full min-w-[34rem] text-xs text-slate-700 dark:text-slate-200">
        <thead class="sticky top-0 bg-slate-50 dark:bg-slate-900"><tr><th class="px-2 py-2 text-left">Indicador</th><th class="px-2 py-2 text-right">Actual</th><th class="px-2 py-2 text-right">Anterior</th><th class="px-2 py-2 text-right">Variación</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div></details>`;
  }

  function renderStockV45Charts(areaData) {
    const movement = areaData?.serie_movimientos || {};
    const rows = Array.isArray(movement.filas) ? movement.filas : [];
    const lastRows = rows.slice(-30);
    const previousRows = Array.isArray(areaData?.serie_movimientos_anterior?.filas)
      ? areaData.serie_movimientos_anterior.filas : [];
    const priorLast = previousRows.slice(-30);
    const plotRows = Math.max(lastRows.length, priorLast.length);
    const maxValue = Math.max(1, ...[...lastRows, ...priorLast].flatMap((row) => [Number(row.entradas || 0), Number(row.salidas || 0)]));
    const step = plotRows ? 304 / plotRows : 304;
    const bars = Array.from({ length: plotRows }, (_, index) => {
      const row = lastRows[index] || {};
      const prior = priorLast[index] || {};
      const inHeight = Math.max(0, Number(row.entradas || 0)) / maxValue * 84;
      const outHeight = Math.max(0, Number(row.salidas || 0)) / maxValue * 84;
      const priorInHeight = Math.max(0, Number(prior.entradas || 0)) / maxValue * 84;
      const priorOutHeight = Math.max(0, Number(prior.salidas || 0)) / maxValue * 84;
      const x = 8 + index * step;
      const width = Math.max(1, step / (previousRows.length ? 4 : 2) - 0.5);
      return `<rect x="${x.toFixed(1)}" y="${(98 - inHeight).toFixed(1)}" width="${width.toFixed(1)}" height="${inHeight.toFixed(1)}" fill="#059669" />
        <rect x="${(x + width).toFixed(1)}" y="${(98 - outHeight).toFixed(1)}" width="${width.toFixed(1)}" height="${outHeight.toFixed(1)}" fill="#f97316" />
        ${previousRows.length ? `<rect x="${(x + width * 2).toFixed(1)}" y="${(98 - priorInHeight).toFixed(1)}" width="${width.toFixed(1)}" height="${priorInHeight.toFixed(1)}" fill="#86efac" />
        <rect x="${(x + width * 3).toFixed(1)}" y="${(98 - priorOutHeight).toFixed(1)}" width="${width.toFixed(1)}" height="${priorOutHeight.toFixed(1)}" fill="#fdba74" />` : ""}`;
    }).join("");
    const seriesTable = rows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800">
      <th class="py-1.5 text-left font-normal">${escHtml(row.fecha)}</th>
      <td class="py-1.5 text-right">${fmtNum.format(row.entradas)}</td>
      <td class="py-1.5 text-right">${fmtNum.format(row.salidas)}</td>
    </tr>`).join("");
    const graph = `<div class="mt-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
      <p class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Movimientos por ${movement.agrupacion || "período"} · ${escHtml(areaData.presentacion || "unidad")}</p>
      <svg viewBox="0 0 320 105" role="img" aria-label="Entradas en verde y salidas en naranja" class="h-28 w-full">
        <line x1="8" y1="98" x2="312" y2="98" stroke="#94a3b8" />${bars}
      </svg>
      <div class="flex flex-wrap gap-3 text-[10px] text-slate-500"><span>● Verde: entradas</span><span>● Naranja: salidas</span>${previousRows.length ? "<span>● Verde claro: entradas anteriores</span><span>● Naranja claro: salidas anteriores</span>" : ""}</div>
      <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa (${rows.length})</summary>
        <div class="max-h-60 overflow-auto"><table class="w-full text-xs"><thead><tr><th class="text-left">Fecha</th><th class="text-right">Entradas</th><th class="text-right">Salidas</th></tr></thead><tbody>${seriesTable}</tbody></table></div>
      </details>
      ${previousRows.length ? `<details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie anterior (${previousRows.length})</summary>
        <div class="max-h-60 overflow-auto"><table class="w-full text-xs"><thead><tr><th class="text-left">Fecha</th><th class="text-right">Entradas</th><th class="text-right">Salidas</th></tr></thead><tbody>${previousRows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800"><th class="py-1.5 text-left font-normal">${escHtml(row.fecha)}</th><td class="py-1.5 text-right">${fmtNum.format(row.entradas)}</td><td class="py-1.5 text-right">${fmtNum.format(row.salidas)}</td></tr>`).join("")}</tbody></table></div>
      </details>` : ""}
    </div>`;
    const deposits = Array.isArray(areaData?.series_depositos) ? areaData.series_depositos : [];
    const maxDeposit = Math.max(1, ...deposits.map((dep) => Number(dep.valor || 0)));
    const depositChart = deposits.length ? `<div class="mt-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
      <p class="mb-2 text-[11px] font-semibold text-slate-600 dark:text-slate-300">Valorización por depósito</p>
      ${deposits.map((dep) => `<div class="mb-2 text-xs"><div class="flex justify-between gap-2"><span class="truncate">${escHtml(dep.nombre)}</span><strong class="tabular-nums">${fmtMoney.format(dep.valor)}</strong></div><div class="mt-1 h-2 rounded bg-slate-100 dark:bg-slate-700"><div class="h-2 rounded bg-emerald-600" style="width:${(Math.max(0, Number(dep.valor || 0)) / maxDeposit * 100).toFixed(1)}%"></div></div></div>`).join("")}
    </div>` : "";
    const compare = areaData?.comparacion;
    const flowFields = [
      ["Entradas", "entradas_periodo", "qty"], ["Salidas", "salidas_periodo", "qty"],
      ["Valor entradas", "valor_entradas", "money"], ["Valor salidas", "valor_salidas", "money"],
    ];
    const comparison = compare ? `<div class="mt-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
      <p class="mb-2 text-[11px] font-semibold text-slate-600 dark:text-slate-300">Comparación de movimientos</p>
      <div class="overflow-x-auto"><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="text-left">Indicador</th><th class="text-right">Actual</th><th class="text-right">Anterior</th><th class="text-right">Variación</th></tr></thead><tbody>
      ${flowFields.map(([label, key, kind]) => {
        const fmt = (value) => value == null ? "Sin permiso" : kind === "money" ? fmtMoney.format(value) : fmtNum.format(value);
        return `<tr class="border-t border-slate-100 dark:border-slate-800"><th class="py-1.5 text-left font-medium">${label}</th><td class="text-right">${fmt(areaData.kpis?.[key])}</td><td class="text-right">${fmt(compare.kpis?.[key])}</td><td class="text-right">${fmt(compare.diferencias?.[key])}</td></tr>`;
      }).join("")}
      </tbody></table></div><p class="mt-2 text-[11px] text-slate-500">Las existencias son una foto actual y no se comparan como período.</p>
    </div>` : "";
    return graph + depositChart + comparison;
  }

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
          ([k, val, kpi]) => `
        <div class="flex items-start justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0 dark:border-slate-800">
          <span class="min-w-0 shrink text-sm text-slate-500 dark:text-slate-400">${k}
            ${kpi && val !== "Sin permiso de costos" ? `<button type="button" class="cc-v45-kpi-detail ml-1 align-middle text-sky-600 dark:text-sky-300" data-area="${def.key}" data-kpi="${kpi}" data-title="${escHtml(k)}" aria-label="Ver detalle de ${escHtml(k)}"><span class="material-icons text-sm" aria-hidden="true">open_in_new</span></button>` : ""}
          </span>
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
    scope?.querySelectorAll(".cc-v45-kpi-detail").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.area === "inventario") openStockDetail(btn.dataset.kpi, btn.dataset.title);
        else openComercialDetail(btn.dataset.kpi, btn.dataset.title);
      });
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
        renderGlobalKpis(areasCache);
      });
    });
    await Promise.allSettled(tasks);
  }

  async function loadDashboardMonolith() {
    if (!cfg.dashboardUrl) return;
    const loadToken = dashboardLoadToken;
    setLoading(true);
    showError("");
    try {
      const q = buildQuery({ tablero: selectedAreaKey });
      const data = await fetchJson(`${cfg.dashboardUrl}?${q}`);
      if (loadToken !== dashboardLoadToken) return;
      updatePeriodoLabel(false);
      areasCache = data.areas || {};
      renderGlobalKpis(areasCache);
      renderAreas({ areas: areasCache });
    } catch (e) {
      if (loadToken !== dashboardLoadToken) return;
      showError(e.message || "No se pudo cargar el Command Center.");
    } finally {
      if (loadToken === dashboardLoadToken) setLoading(false);
    }
  }

  async function loadDashboard() {
    selectedAreaKey = el("cc-tablero-select")?.value || "";
    document.querySelectorAll(".cc-sales-filter").forEach((node) => {
      node.classList.toggle("hidden", selectedAreaKey === "inventario");
    });
    document.querySelectorAll(".cc-pv-filter").forEach((node) => {
      node.classList.toggle("hidden", ["compras", "inventario", "gestion_contable"].includes(selectedAreaKey));
    });
    document.querySelectorAll(".cc-account-filter").forEach((node) => {
      node.classList.toggle("hidden", selectedAreaKey !== "gestion_contable");
      node.classList.toggle("flex", selectedAreaKey === "gestion_contable");
    });
    el("cc-incluir-impuestos")?.closest("label")?.classList.toggle("hidden", ["preparacion_pedidos", "compras", "financiero", "gestion_contable"].includes(selectedAreaKey));
    el("cc-comparar-anterior")?.closest("label")?.classList.toggle("hidden", ["resumen_general", "preparacion_pedidos", "compras", "financiero", "gestion_contable"].includes(selectedAreaKey));
    document.querySelectorAll(".cc-stock-filter").forEach((node) => {
      node.classList.toggle("hidden", selectedAreaKey !== "inventario");
      node.classList.toggle("flex", selectedAreaKey === "inventario");
    });
    dashboardLoadToken += 1;
    areasCache = {};
    if (!selectedAreaKey || cfg.areasVisible?.[selectedAreaKey] !== true) {
      el("cc-welcome")?.classList.remove("hidden");
      el("cc-global-kpis")?.classList.add("hidden");
      if (el("cc-areas-grid")) el("cc-areas-grid").innerHTML = "";
      if (el("cc-periodo-label")) el("cc-periodo-label").textContent = "";
      return;
    }
    el("cc-welcome")?.classList.add("hidden");
    el("cc-global-kpis")?.classList.remove("hidden");
    const areaUrls = cfg.areaUrls || {};
    const hasParallel = Object.keys(areaUrls).length > 0;
    if (!hasParallel && !cfg.dashboardUrl) return;

    rememberFilters();

    if (!hasParallel) {
      await loadDashboardMonolith();
      return;
    }

    const loadToken = dashboardLoadToken;
    showError("");
    setRefreshDisabled(true);
    updatePeriodoLabel(true);
    renderGlobalKpisLoading();
    renderAreasSkeleton();


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

  const V45_DOC_COLUMNS = [
    { key: "fecha", label: "Fecha" }, { key: "tipo_comprobante", label: "Tipo" },
    { key: "numero", label: "Número" }, { key: "cliente", label: "Cliente" },
    { key: "codigo_cliente", label: "Cód. cliente" }, { key: "importe", label: "Importe" },
  ];
  const V45_PROFIT_COLUMNS = [
    { key: "fecha", label: "Fecha" }, { key: "tipo_comprobante", label: "Movimiento" },
    { key: "codigo_articulo", label: "Código" }, { key: "articulo", label: "Artículo" },
    { key: "cantidad", label: "Cantidad" }, { key: "venta", label: "Venta" },
    { key: "costo", label: "Costo" }, { key: "rentabilidad", label: "Rentabilidad" },
  ];

  function comercialCardHtml(row) {
    const title = escHtml(row.cliente || row.articulo || "Sin descripción");
    const code = escHtml(row.numero || row.codigo_articulo || "");
    const amount = row.importe ?? row.rentabilidad;
    return `<article class="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
      <div class="flex justify-between gap-2"><strong class="min-w-0 break-words text-sm">${title}</strong><span class="shrink-0 text-sm font-semibold tabular-nums">${formatTabularCell("importe", amount)}</span></div>
      <p class="mt-1 text-xs text-slate-500">${escHtml(row.fecha)} · ${escHtml(row.tipo_comprobante)} · ${code}</p>
    </article>`;
  }

  const STOCK_COST_KEYS = new Set(["stock_valorizado", "valor_entradas", "valor_salidas"]);
  const STOCK_MOVEMENT_KEYS = new Set(["entradas_periodo", "salidas_periodo", "valor_entradas", "valor_salidas"]);
  const STOCK_LIMIT_KEYS = new Set(["bajo_minimo", "punto_pedido", "sobre_maximo"]);

  function stockColumns(kpi) {
    const value = { key: STOCK_COST_KEYS.has(kpi) ? "importe" : "cantidad", label: STOCK_COST_KEYS.has(kpi) ? "Importe" : "Cantidad" };
    if (STOCK_MOVEMENT_KEYS.has(kpi)) return [
      { key: "fecha", label: "Fecha" }, { key: "documento", label: "Comprobante" },
      { key: "articulo", label: "Artículo" }, { key: "codigo_manual", label: "Código" },
      { key: "deposito", label: "Depósito" }, value,
    ];
    const columns = [
      { key: "articulo", label: "Artículo" }, { key: "codigo_manual", label: "Código" },
      { key: "deposito", label: "Depósito" }, { key: "stock_actual", label: "Stock actual" },
    ];
    if (STOCK_LIMIT_KEYS.has(kpi)) columns.push(
      { key: "stock_minimo", label: "Mínimo" }, { key: "punto_pedido", label: "Punto pedido" },
      { key: "stock_maximo", label: "Máximo" },
    );
    columns.push(value);
    return columns;
  }

  function stockCardHtml(row) {
    const cost = STOCK_COST_KEYS.has(stockDetail?.kpi);
    const metric = cost ? fmtMoney.format(row.importe) : fmtNum.format(row.importe);
    const context = STOCK_MOVEMENT_KEYS.has(stockDetail?.kpi)
      ? `${escHtml(row.fecha || "")} · ${escHtml(row.documento || "")}`
      : `Stock ${fmtNum.format(row.stock_actual || 0)}`;
    return `<article class="rounded-xl border border-slate-200 bg-slate-50 p-3 dark:border-slate-700 dark:bg-slate-800/50">
      <div class="flex justify-between gap-2"><strong class="min-w-0 break-words text-sm">${escHtml(row.articulo || "Sin artículo")}</strong><span class="shrink-0 text-sm font-semibold tabular-nums">${metric}</span></div>
      <p class="mt-1 text-xs text-slate-500">${context} · ${escHtml(row.deposito || "")} · ${escHtml(row.codigo_manual || "")}</p>
    </article>`;
  }

  async function loadStockDetail() {
    if (!stockDetail) return;
    const base = (cfg.detailUrls || {}).stock_v45;
    if (!base) return;
    const term = (el("cc-v45-search")?.value || "").trim();
    const extra = {
      kpi: stockDetail.kpi, limit: "100", offset: String(stockDetail.offset),
      orden: el("cc-v45-order")?.value || "fecha_desc",
    };
    if (term.length >= 2) extra.busqueda = term;
    el("cc-detail-summary").textContent = "Cargando detalle…";
    el("cc-detail-error")?.classList.add("hidden");
    try {
      const data = await fetchJson(`${base}?${buildQuery(extra)}`);
      if (!stockDetail || stockDetail.kpi !== extra.kpi || stockDetail.offset !== Number(extra.offset)) return;
      stockDetailData = data;
      const cost = STOCK_COST_KEYS.has(stockDetail.kpi);
      const shown = cost ? data : { ...data, filas: data.filas.map((row) => ({ ...row, cantidad: row.importe })) };
      renderTabularDetail(shown, stockColumns(stockDetail.kpi), stockCardHtml, cost ? fmtMoney.format.bind(fmtMoney) : fmtNum.format.bind(fmtNum));
      const pagination = el("cc-v45-pagination");
      pagination?.classList.remove("hidden");
      pagination?.classList.add("flex");
      el("cc-v45-prev").disabled = data.offset <= 0;
      el("cc-v45-next").disabled = data.offset + data.filas.length >= data.total_registros;
      const start = data.total_registros ? data.offset + 1 : 0;
      el("cc-v45-page-label").textContent = `${start}–${data.offset + data.filas.length} de ${data.total_registros}`;
    } catch (e) {
      const err = el("cc-detail-error");
      err.textContent = e.message || "Error al cargar detalle de Stock.";
      err.classList.remove("hidden");
    }
  }

  function openStockDetail(kpi, title) {
    if (!kpi || !(cfg.detailUrls || {}).stock_v45) return;
    openModal(true);
    clearDetailContent();
    stockDetail = { kpi, offset: 0 };
    el("cc-detail-title").textContent = `Stock · ${title || kpi}`;
    const controls = el("cc-v45-detail-controls");
    controls?.classList.remove("hidden");
    controls?.classList.add("flex");
    if (el("cc-v45-search")) el("cc-v45-search").value = "";
    if (el("cc-v45-order")) el("cc-v45-order").value = "fecha_desc";
    void loadStockDetail();
  }

  async function loadComercialDetail() {
    if (!comercialDetail) return;
    const base = (cfg.detailUrls || {}).comercial_v45;
    if (!base) return;
    const term = (el("cc-v45-search")?.value || "").trim();
    const extra = {
      kpi: comercialDetail.kpi, limit: "100", offset: String(comercialDetail.offset),
      orden: el("cc-v45-order")?.value || "fecha_desc",
    };
    if (term.length >= 2) extra.busqueda = term;
    el("cc-detail-summary").textContent = "Cargando detalle…";
    el("cc-detail-error")?.classList.add("hidden");
    try {
      const data = await fetchJson(`${base}?${buildQuery(extra)}`);
      if (!comercialDetail || comercialDetail.kpi !== extra.kpi || comercialDetail.offset !== Number(extra.offset)) return;
      comercialDetailData = data;
      const cols = (extra.kpi === "rentabilidad" || extra.kpi === "margen_porcentaje")
        ? V45_PROFIT_COLUMNS : V45_DOC_COLUMNS;
      renderTabularDetail(data, cols, comercialCardHtml);
      const pagination = el("cc-v45-pagination");
      pagination?.classList.remove("hidden");
      pagination?.classList.add("flex");
      el("cc-v45-prev").disabled = data.offset <= 0;
      el("cc-v45-next").disabled = data.offset + data.filas.length >= data.total_registros;
      const start = data.total_registros ? data.offset + 1 : 0;
      el("cc-v45-page-label").textContent = `${start}–${data.offset + data.filas.length} de ${data.total_registros}`;
    } catch (e) {
      const err = el("cc-detail-error");
      err.textContent = e.message || "Error al cargar detalle.";
      err.classList.remove("hidden");
    }
  }

  function openComercialDetail(kpi, title) {
    if (!kpi || !(cfg.detailUrls || {}).comercial_v45) return;
    openModal(true);
    clearDetailContent();
    comercialDetail = { kpi, offset: 0 };
    el("cc-detail-title").textContent = `Ventas · ${title || kpi}`;
    el("cc-detail-error")?.classList.add("hidden");
    const controls = el("cc-v45-detail-controls");
    controls?.classList.remove("hidden");
    controls?.classList.add("flex");
    if (el("cc-v45-search")) el("cc-v45-search").value = "";
    if (el("cc-v45-order")) el("cc-v45-order").value = "fecha_desc";
    void loadComercialDetail();
  }

  function exportComercialCurrentPage() {
    if (!comercialDetailData?.filas?.length || !comercialDetail) return;
    const columns = (comercialDetail.kpi === "rentabilidad" || comercialDetail.kpi === "margen_porcentaje")
      ? V45_PROFIT_COLUMNS : V45_DOC_COLUMNS;
    const csvCell = (value) => {
      let cell = String(value ?? "");
      if (/^[=+\-@]/.test(cell)) cell = `'${cell}`;
      return `"${cell.replace(/"/g, '""')}"`;
    };
    const lines = [columns.map((col) => csvCell(col.label)).join(";")];
    comercialDetailData.filas.forEach((row) => {
      lines.push(columns.map((col) => csvCell(row[col.key])).join(";"));
    });
    const blob = new Blob(["\uFEFF", lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `ventas-v45-${comercialDetail.kpi}-${readFilters().fecha_inicio}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportStockCurrentPage() {
    if (!stockDetailData?.filas?.length || !stockDetail) return;
    const cols = stockColumns(stockDetail.kpi);
    const csvCell = (value) => {
      let cell = String(value ?? "");
      if (/^[=+\-@]/.test(cell)) cell = `'${cell}`;
      return `"${cell.replace(/"/g, '""')}"`;
    };
    const lines = [cols.map((col) => csvCell(col.label)).join(";")];
    stockDetailData.filas.forEach((row) => {
      lines.push(cols.map((col) => csvCell(col.key === "cantidad" ? row.importe : row[col.key])).join(";"));
    });
    const blob = new Blob(["\uFEFF", lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `stock-v45-${stockDetail.kpi}-${readFilters().fecha_inicio}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

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
    } else if (saved && (saved.sucursales?.length || saved.puntos_venta?.length || saved.depositos?.length)) {
      if (!window.__ccPendingFilterIds) {
        window.__ccPendingFilterIds = {
          sucursales: saved.sucursales || [],
          puntos_venta: saved.puntos_venta || [],
          depositos: saved.depositos || [],
        };
      }
    }
    const t = todayIso();
    const fi = el("cc-fecha-inicio");
    const ff = el("cc-fecha-fin");
    if (fi && !fi.value) fi.value = `${t.slice(0, 7)}-01`;
    if (ff && !ff.value) ff.value = t;
    const onFilterChange = () => {
      dashboardLoadToken += 1;
      setLoading(false);
      setRefreshDisabled(false);
      areasCache = {};
      if (selectedAreaKey) {
        if (el("cc-areas-grid")) el("cc-areas-grid").innerHTML = "";
        if (el("cc-global-kpis")) el("cc-global-kpis").innerHTML = "";
        const welcome = el("cc-welcome");
        if (welcome) {
          welcome.textContent = "Filtros modificados. Pulsá Actualizar para consultar el tablero con el nuevo período y alcance.";
          welcome.classList.remove("hidden");
        }
      }
      rememberFilters();
      syncReportLinks();
      updatePeriodoLabel(false);
    };
    fi?.addEventListener("change", onFilterChange);
    ff?.addEventListener("change", onFilterChange);
    el("sucursales")?.addEventListener("change", onFilterChange);
    el("punto_venta")?.addEventListener("change", onFilterChange);
    el("depositos")?.addEventListener("change", onFilterChange);
    el("cc-incluir-impuestos")?.addEventListener("change", onFilterChange);
    el("cc-comparar-anterior")?.addEventListener("change", onFilterChange);
    el("cc-stock-presentacion")?.addEventListener("change", onFilterChange);
    el("cc-stock-comparar")?.addEventListener("change", onFilterChange);
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
    el("cc-tablero-select")?.addEventListener("change", loadDashboard);
    el("cc-detail-close")?.addEventListener("click", () => openModal(false));
    el("cc-v45-search")?.addEventListener("input", () => {
      if (comercialSearchTimer) clearTimeout(comercialSearchTimer);
      if (!comercialDetail && !stockDetail) return;
      if (comercialDetail) comercialDetail.offset = 0;
      if (stockDetail) stockDetail.offset = 0;
      comercialSearchTimer = setTimeout(() => void (stockDetail ? loadStockDetail() : loadComercialDetail()), 300);
    });
    el("cc-v45-order")?.addEventListener("change", () => {
      if (!comercialDetail && !stockDetail) return;
      if (comercialDetail) comercialDetail.offset = 0;
      if (stockDetail) stockDetail.offset = 0;
      void (stockDetail ? loadStockDetail() : loadComercialDetail());
    });
    el("cc-v45-prev")?.addEventListener("click", () => {
      const state = stockDetail || comercialDetail;
      if (!state) return;
      state.offset = Math.max(0, state.offset - 100);
      void (stockDetail ? loadStockDetail() : loadComercialDetail());
    });
    el("cc-v45-next")?.addEventListener("click", () => {
      const state = stockDetail || comercialDetail;
      if (!state) return;
      state.offset += 100;
      void (stockDetail ? loadStockDetail() : loadComercialDetail());
    });
    el("cc-v45-export")?.addEventListener("click", () => {
      if (stockDetail) exportStockCurrentPage();
      else exportComercialCurrentPage();
    });
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
  });
})();
