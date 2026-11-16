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
  const CUSTOM_COMPARE_AREAS = new Set([
    "resumen_general", "ventas", "preparacion_pedidos", "inventario",
    "compras", "financiero", "gestion_contable", "impositivo",
    "libros_contables", "logistica", "gastos",
  ]);
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
  let genericV45Detail = null;
  let genericV45DetailData = null;
  let comercialSearchTimer = null;
  const RESUMEN_COUNT_KPIS = new Set(["presupuestos", "pedidos", "facturas", "remitos"]);
  const RESUMEN_GLOBAL_KPIS = new Set(["vencimiento_cobrar", "vencimiento_pagar", "efectivo_actual", "tarjetas_actual", "cheques_actual", "bancos_actual"]);

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
    genericV45Detail = null;
    genericV45DetailData = null;
    el("cc-v45-order")?.classList.remove("hidden");
    for (const id of ["cc-v45-view", "cc-v45-group", "cc-v45-chart-mode", "cc-v45-visual"]) {
      el(id)?.classList.add("hidden");
    }
    if (el("cc-v45-visual")) el("cc-v45-visual").innerHTML = "";
    el("cc-detail-table-wrap")?.classList.remove("hidden");
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
    const tableWrap = el("cc-detail-table-wrap");
    const cards = el("cc-detail-cards");
    if (tableWrap) tableWrap.className = DETAIL_TABLE_WRAP_DESKTOP_CLASS;
    if (cards) cards.className = DETAIL_CARDS_MOBILE_CLASS;
    const total = data.total_registros ?? 0;
    let sumTxt = `${total} registro(s)`;
    if (data.total_monto != null) sumTxt += ` · Total ${fmtMoney.format(data.total_monto)}`;
    if (data.meta?.alcance) sumTxt += ` · ${data.meta.alcance}`;
    if (data.meta?.notas_semanticas?.length) sumTxt += ` · ${data.meta.notas_semanticas.join(" ")}`;
    const summaryEl = el("cc-detail-summary");
    if (summaryEl) summaryEl.textContent = sumTxt;

    const filas = data.filas || [];
    const tbody = el("cc-detail-tbody");
    const thead = el("cc-detail-thead");
    if (!tbody || !thead) return;

    if (!filas.length) {
      if (cards) cards.innerHTML = '<p class="py-4 text-sm text-slate-500">Sin registros en el período.</p>';
      thead.innerHTML = "";
      tbody.innerHTML =
        '<tr><td class="py-4 text-slate-500" colspan="99">Sin registros en el período.</td></tr>';
      return;
    }
    const keys = Object.keys(filas[0]);
    const cellText = (key, value) => {
      if (value == null || value === "") return "—";
      if (typeof value === "number" && (key.includes("monto") || key.includes("importe") || key === "subtotal_desc")) {
        return fmtMoney.format(value);
      }
      return String(value);
    };
    if (cards) {
      cards.innerHTML = filas.map((row) => `
        <article class="rounded-xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-800" role="listitem">
          <dl class="grid grid-cols-2 gap-x-3 gap-y-2">
            ${keys.map((key) => `
              <div class="min-w-0 ${/nombre|descripcion|articulo|cliente/i.test(key) ? "col-span-2" : ""}">
                <dt class="text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">${escHtml(key.replace(/_/g, " "))}</dt>
                <dd class="break-words text-sm font-medium tabular-nums text-slate-800 dark:text-slate-100">${escHtml(cellText(key, row[key]))}</dd>
              </div>`).join("")}
          </dl>
        </article>`).join("");
    }
    thead.innerHTML =
      "<tr>" +
      keys
        .map(
          (k) =>
            `<th scope="col" class="px-2 py-2 text-[10px] font-semibold uppercase tracking-wide">${escHtml(k.replace(/_/g, " "))}</th>`,
        )
        .join("") +
      "</tr>";
    tbody.innerHTML = filas
      .map((row) => {
        return (
          '<tr class="border-b border-slate-100 dark:border-slate-800">' +
          keys
            .map((k) => {
              const v = cellText(k, row[k]);
              const wrap = /nombre|descripcion|articulo|cliente/i.test(k);
              const cls = wrap
                ? "max-w-[12rem] break-words px-2 py-1.5 text-sm"
                : "whitespace-nowrap px-2 py-1.5 text-sm tabular-nums";
              return `<td class="${cls}">${escHtml(v)}</td>`;
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
    const fi = el("cc-fecha-inicio")?.value || `${t.slice(0, 7)}-01`;
    const ff = el("cc-fecha-fin")?.value || t;
    return {
      fecha_inicio: fi,
      fecha_fin: ff,
      comparacion_inicio: el("cc-comparacion-inicio")?.value || "",
      comparacion_fin: el("cc-comparacion-fin")?.value || "",
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
              comparacion_inicio: "",
              comparacion_fin: "",
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
      const ci = String(parsed.comparacion_inicio || "").trim();
      const cf = String(parsed.comparacion_fin || "").trim();
      if (fi && !ISO_DATE.test(fi)) return null;
      if (ff && !ISO_DATE.test(ff)) return null;
      if (ci && !ISO_DATE.test(ci)) return null;
      if (cf && !ISO_DATE.test(cf)) return null;
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
        comparacion_inicio: ci || "",
        comparacion_fin: cf || "",
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
          comparacion_inicio: f.comparacion_inicio || "",
          comparacion_fin: f.comparacion_fin || "",
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
      url.searchParams.delete("comparacion_inicio");
      url.searchParams.delete("comparacion_fin");
      if (f.comparacion_inicio) url.searchParams.set("comparacion_inicio", f.comparacion_inicio);
      if (f.comparacion_fin) url.searchParams.set("comparacion_fin", f.comparacion_fin);
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
    if (CUSTOM_COMPARE_AREAS.has(selectedAreaKey)) {
      if (f.comparacion_inicio) q.set("comparacion_inicio", f.comparacion_inicio);
      if (f.comparacion_fin) q.set("comparacion_fin", f.comparacion_fin);
    }
    if (selectedAreaKey === "ventas" || selectedAreaKey === "resumen_general") {
      if (el("cc-incluir-impuestos")?.checked) q.set("incluir_impuestos", "1");
      if (el("cc-comparar-anterior")?.checked) q.set("comparar", "anterior");
    } else if (selectedAreaKey === "inventario") {
      q.set("presentacion", el("cc-stock-presentacion")?.value || "unidad");
      if (el("cc-stock-comparar")?.checked) q.set("comparar", "anterior");
    }
    if (["gestion_contable", "libros_contables"].includes(selectedAreaKey) && el("cc-grupo-contable")?.value) {
      q.set("grupo_contable", el("cc-grupo-contable").value);
    }
    if (selectedAreaKey === "gastos") {
      q.set("fuente", el("cc-gastos-fuente")?.value || "0");
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
    const ci = (params.get("comparacion_inicio") || "").trim();
    const cf = (params.get("comparacion_fin") || "").trim();
    if (ci && ISO_DATE.test(ci) && el("cc-comparacion-inicio")) el("cc-comparacion-inicio").value = ci;
    if (cf && ISO_DATE.test(cf) && el("cc-comparacion-fin")) el("cc-comparacion-fin").value = cf;
    if (ci || cf) el("cc-custom-comparison")?.setAttribute("open", "");
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

  function applyScopeFromStorage() {
    const saved = loadPersistedFilters();
    if (!saved) return;
    // La selección territorial se conserva; cada visita nueva empieza en el mes actual.
    if (saved.sucursales?.length || saved.puntos_venta?.length || saved.depositos?.length) {
      window.__ccPendingFilterIds = {
        sucursales: saved.sucursales || [],
        puntos_venta: saved.puntos_venta || [],
        depositos: saved.depositos || [],
      };
    }
  }

  let waitModalLocks = 0;
  let areasCache = {};
  let dashboardLoadToken = 0;
  let selectedAreaKey = "";
  let autoRefreshTimer = null;

  function scheduleAutoRefresh() {
    if (autoRefreshTimer) clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
    const minutes = Number(el("cc-refresh-interval")?.value || 0);
    if (![1, 5, 10, 15].includes(minutes)) return;
    autoRefreshTimer = setInterval(() => {
      if (!selectedAreaKey || document.visibilityState === "hidden") return;
      const detail = el("cc-detail-modal");
      if (el("cc-refresh")?.disabled || (detail && !detail.classList.contains("hidden"))) return;
      void loadDashboard();
    }, minutes * 60 * 1000);
  }

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
      impositivo: "impuestos y posiciones fiscales",
      libros_contables: "libros y estados contables",
      logistica: "logística y hojas de ruta",
      gastos: "análisis de gastos",
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

  function globalKpiValue(area, key, kind = "money", fallbackKey = "") {
    if (!area || area.disponible === false) return "No disponible";
    const value = area.kpis?.[key] ?? (fallbackKey ? area[fallbackKey] : null);
    if (value == null) return "No disponible";
    return kind === "count" ? fmtNum.format(value) : fmtMoney.format(value);
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
    if (CUSTOM_COMPARE_AREAS.has(selectedAreaKey)) {
      grid.innerHTML = "";
      grid.classList.add("hidden");
      return;
    }
    grid.classList.remove("hidden");
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
    const tax = a.impositivo || {};
    const books = a.libros_contables || {};
    const routes = a.logistica || {};
    const expenses = a.gastos || {};
    const mfg = a.manufactura || {};
    const cruz = a.cruzados || {};
    const ventasFirstLabel = singleDay ? "Ventas netas (día)" : "Ventas netas (período)";
    const ventasFirstVal = globalKpiValue(v, "ventas_netas", "money", "ventas_netas");

    const cards = [];
    if (isAreaVisible("resumen_general")) {
      cards.push(kpiCard("Ventas del período", globalKpiValue(resumen, "ventas"), "sky"));
      cards.push(kpiCard("Pedidos", globalKpiValue(resumen, "pedidos", "count"), "indigo"));
    }
    if (isAreaVisible("preparacion_pedidos")) {
      cards.push(kpiCard("Pedidos ingresados", globalKpiValue(preparacion, "pedidos_ingresados", "count"), "sky"));
      cards.push(kpiCard("Pedidos pendientes", globalKpiValue(preparacion, "pendientes", "count"), "amber"));
    }
    if (isAreaVisible("ventas")) {
      cards.push(kpiCard(ventasFirstLabel, ventasFirstVal, "sky"));
      cards.push(kpiCard("Facturas", globalKpiValue(v, "facturas", "count"), "indigo"));
    }
    if (isAreaVisible("inventario")) {
      cards.push(kpiCard("Valor stock", stockValueLabel(inv), "emerald"));
    }
    if (isAreaVisible("compras")) {
      cards.push(
        kpiCard("Compras netas", globalKpiValue(comp, "compras_netas"), "amber")
      );
    }
    if (isAreaVisible("financiero")) {
      cards.push(kpiCard("Flujo neto", globalKpiValue(fin, "flujo_neto"), "teal"));
      cards.push(kpiCard("Vencido a cobrar", globalKpiValue(fin, "vencido_cobrar"), "amber"));
    }
    if (isAreaVisible("gestion_contable")) {
      cards.push(kpiCard("Asientos", globalKpiValue(account, "asientos", "count"), "indigo"));
      cards.push(kpiCard("Diferencia Debe/Haber", globalKpiValue(account, "diferencia"), "emerald"));
    }
    if (isAreaVisible("impositivo")) {
      cards.push(kpiCard("Posición IVA", globalKpiValue(tax, "posicion_iva"), "amber"));
      cards.push(kpiCard("IVA débito", globalKpiValue(tax, "iva_debito"), "sky"));
    }
    if (isAreaVisible("libros_contables")) {
      cards.push(kpiCard("Asientos del Diario", globalKpiValue(books, "asientos", "count"), "indigo"));
      cards.push(kpiCard("Resultado del período", globalKpiValue(books, "resultado_periodo"), "purple"));
    }
    if (isAreaVisible("logistica")) {
      cards.push(kpiCard("Hojas de ruta", globalKpiValue(routes, "hojas_ruta", "count"), "sky"));
      cards.push(kpiCard("Facturación en rutas", globalKpiValue(routes, "facturacion_rutas"), "emerald"));
    }
    if (isAreaVisible("gastos")) {
      cards.push(kpiCard("Total de gastos", globalKpiValue(expenses, "total_gastos"), "rose"));
      cards.push(kpiCard("Documentos de gasto", globalKpiValue(expenses, "documentos", "count"), "indigo"));
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
    if (CUSTOM_COMPARE_AREAS.has(selectedAreaKey)) {
      grid.innerHTML = "";
      grid.classList.add("hidden");
      return;
    }
    grid.classList.remove("hidden");
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
    if (isAreaVisible("impositivo")) {
      loadingCards.push(kpiCardLoading("Posición IVA", "amber"));
      loadingCards.push(kpiCardLoading("IVA débito", "sky"));
    }
    if (isAreaVisible("libros_contables")) {
      loadingCards.push(kpiCardLoading("Asientos del Diario", "indigo"));
      loadingCards.push(kpiCardLoading("Resultado del período", "purple"));
    }
    if (isAreaVisible("logistica")) {
      loadingCards.push(kpiCardLoading("Hojas de ruta", "sky"));
      loadingCards.push(kpiCardLoading("Facturación en rutas", "emerald"));
    }
    if (isAreaVisible("gastos")) {
      loadingCards.push(kpiCardLoading("Total de gastos", "rose"));
      loadingCards.push(kpiCardLoading("Documentos de gasto", "indigo"));
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
        const rows = [
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
        const keys = [
          "ventas", "compras_netas", "cobranzas", "pagos", "presupuestos",
          "pedidos", "facturas", "remitos", "vencimiento_cobrar",
          "vencimiento_pagar", "efectivo_actual", "tarjetas_actual",
          "cheques_actual", "bancos_actual", "venta_cuenta_corriente",
          "compra_cuenta_corriente",
        ];
        return rows.map((row, index) => [...row, keys[index]]);
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
      details: [
        { label: "Todos los pedidos", urlKey: "preparacion_v45", vista: "pedidos" },
        { label: "Pendientes", urlKey: "preparacion_v45", vista: "pendientes" },
        { label: "En preparación", urlKey: "preparacion_v45", vista: "en_preparacion" },
        { label: "Preparados", urlKey: "preparacion_v45", vista: "preparados" },
        { label: "Backorder", urlKey: "preparacion_v45", vista: "backorder" },
        { label: "En remito", urlKey: "preparacion_v45", vista: "en_remito" },
        { label: "Facturados", urlKey: "preparacion_v45", vista: "facturados" },
        { label: "Cerrados", urlKey: "preparacion_v45", vista: "cerrados" },
        { label: "Anulados", urlKey: "preparacion_v45", vista: "anulados" },
      ],
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
      details: [
        { label: "Comprobantes", urlKey: "compras_v45", vista: "comprobantes" },
        { label: "Proveedores", urlKey: "compras_v45", vista: "proveedores" },
        { label: "Órdenes de compra", urlKey: "compras_v45", vista: "ordenes" },
        { label: "OC abiertas", urlKey: "compras_v45", vista: "ordenes_abiertas" },
        { label: "Remitos", urlKey: "compras_v45", vista: "remitos" },
      ],
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
      details: [
        { label: "Cobranzas", urlKey: "financiero_v45", vista: "cobranzas" },
        { label: "Pagos", urlKey: "financiero_v45", vista: "pagos" },
        { label: "Cartera a cobrar", urlKey: "financiero_v45", vista: "cartera_cobrar" },
        { label: "Cartera a pagar", urlKey: "financiero_v45", vista: "cartera_pagar" },
        { label: "Vencido a cobrar", urlKey: "financiero_v45", vista: "vencido_cobrar" },
        { label: "Vencido a pagar", urlKey: "financiero_v45", vista: "vencido_pagar" },
        { label: "Efectivo", urlKey: "financiero_v45", vista: "efectivo", exact: true },
        { label: "Tarjetas", urlKey: "financiero_v45", vista: "tarjetas", exact: true },
        { label: "Cheques en cartera", urlKey: "financiero_v45", vista: "cheques_cartera", exact: true },
        { label: "Cheques emitidos", urlKey: "financiero_v45", vista: "cheques_emitidos", exact: true },
        { label: "Cheques rechazados", urlKey: "financiero_v45", vista: "cheques_rechazados", exact: true },
        { label: "Bancos", urlKey: "financiero_v45", vista: "bancos", exact: true },
      ],
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
      details: [
        { label: "Renglones de asiento", urlKey: "contable_v45", vista: "asientos" },
        { label: "Determinaciones", urlKey: "contable_v45", vista: "impuestos" },
        { label: "Períodos", urlKey: "contable_v45", vista: "periodos" },
        { label: "Ejercicios", urlKey: "contable_v45", vista: "ejercicios" },
      ],
    },
    {
      key: "impositivo",
      title: "Impuestos · posiciones fiscales (V45)",
      icon: "receipt_long",
      color: "amber",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        const count = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        return [
          ["Posición IVA", money("posicion_iva")], ["IVA débito", money("iva_debito")],
          ["IVA crédito", money("iva_credito")], ["Percep. IVA ventas", money("percep_iva_ventas")],
          ["Percep. IVA compras", money("percep_iva_compras")], ["Retenciones IVA", money("retenciones_iva")],
          ["Libro IVA ventas", count("libro_ventas")], ["Libro IVA compras", count("libro_compras")],
          ["IIBB ventas", money("iibb_ventas")], ["Percep. IIBB ventas", money("percep_iibb_ventas")],
          ["Percep. IIBB compras", money("percep_iibb_compras")],
          ["Retenciones IIBB", money("retenciones_iibb")],
          ["Impuestos determinados", money("impuestos_determinados")],
          ["Impuestos pagados", money("impuestos_pagados")],
        ];
      },
      afterMetrics: (a) => renderImpositivoV45Chart(a),
      details: [
        { label: "Posición IVA", urlKey: "impositivo_v45", vista: "posicion_iva" },
        { label: "Libro IVA ventas", urlKey: "impositivo_v45", vista: "ventas" },
        { label: "Libro IVA compras", urlKey: "impositivo_v45", vista: "compras" },
        { label: "Percepciones", urlKey: "impositivo_v45", vista: "percepciones" },
        { label: "Retenciones", urlKey: "impositivo_v45", vista: "retenciones" },
        { label: "Determinaciones", urlKey: "impositivo_v45", vista: "determinados" },
        { label: "Pagos fiscales", urlKey: "impositivo_v45", vista: "pagados" },
      ],
    },
    {
      key: "libros_contables",
      title: "Contabilidad · libros y estados (V45)",
      icon: "menu_book",
      color: "indigo",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        const count = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        const audit = k.sin_clasificar_conflicto || {};
        return [
          ["Asientos · Diario", count("asientos")], ["Total Debe", money("total_debe")],
          ["Total Haber", money("total_haber")], ["Diferencia", money("diferencia")],
          ["Cuentas · Mayor", count("cuentas_movimiento")],
          ["Saldo neto · Mayor", money("saldo_neto_mayor")],
          ["Saldo deudor", money("saldo_deudor")], ["Saldo acreedor", money("saldo_acreedor")],
          ["Resultado del período", money("resultado_periodo")],
          ["Ingresos", money("ingresos")], ["Egresos", money("egresos")],
          ["Activo", money("activo")], ["Pasivo", money("pasivo")],
          ["Sin clasificar / conflicto", `${fmtNum.format(audit.sin_clasificar || 0)} / ${fmtNum.format(audit.conflictos || 0)}`],
        ];
      },
      afterMetrics: (a) => renderLibrosV45Charts(a),
      details: [
        { label: "Libro Diario", urlKey: "libros_v45", vista: "diario" },
        { label: "Libro Mayor", urlKey: "libros_v45", vista: "mayor" },
        { label: "Balance", urlKey: "libros_v45", vista: "balance" },
        { label: "Resultados", urlKey: "libros_v45", vista: "resultados" },
      ],
    },
    {
      key: "logistica",
      title: "Logística · hojas de ruta (V45)",
      icon: "local_shipping",
      color: "sky",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (key) => k[key] == null ? "No disponible" : fmtMoney.format(k[key]);
        const count = (key) => k[key] == null ? "No disponible" : fmtNum.format(k[key]);
        return [
          ["Hojas de ruta", count("hojas_ruta")], ["Rutas abiertas", count("rutas_abiertas")],
          ["Rutas cerradas", count("rutas_cerradas")], ["Rutas rendidas", count("rutas_rendidas")],
          ["Pendientes de rendir", count("pendientes_rendir")],
          ["Documentos valorizados", count("documentos_valorizados")],
          ["Facturas en ruta", count("facturas_ruta")], ["Notas de crédito", count("notas_credito")],
          ["Facturación en rutas", money("facturacion_rutas")],
          ["Promedio por ruta", money("promedio_ruta")],
          ["Promedio por factura", money("promedio_factura")],
          ["Choferes utilizados", count("choferes")], ["Unidades utilizadas", count("unidades")],
          ["Dif. de rendición", money("diferencia_rendicion")],
        ];
      },
      afterMetrics: (a) => renderLogisticaV45Comparison(a),
      details: [
        { label: "Hojas de ruta", urlKey: "logistica_v45", vista: "rutas" },
        { label: "Comprobantes", urlKey: "logistica_v45", vista: "documentos" },
        { label: "Facturación por ruta", urlKey: "logistica_v45", vista: "por_ruta" },
        { label: "Por chofer", urlKey: "logistica_v45", vista: "por_chofer" },
        { label: "Por unidad", urlKey: "logistica_v45", vista: "por_unidad" },
        { label: "Por zona", urlKey: "logistica_v45", vista: "por_zona" },
      ],
    },
    {
      key: "gastos",
      title: "Análisis de gastos (V45)",
      icon: "receipt",
      color: "rose",
      metrics: (a) => {
        const k = a.kpis || {};
        const money = (value) => value == null ? "No disponible" : fmtMoney.format(value);
        const named = (value) => value?.nombre ? `${escHtml(value.nombre)} · ${money(value.importe)}` : "No disponible";
        return [
          ["Total de gastos", money(k.total_gastos)],
          ["Operativos", money(k.operativos)], ["Bancarios", money(k.bancarios)],
          ["Impuestos pagados", money(k.impuestos_pagados)],
          ["NC / Ajustes", money(k.nc_ajustes)], ["Documentos", fmtNum.format(k.documentos || 0)],
          ["Promedio por documento", money(k.promedio_documento)],
          ["Promedio diario", money(k.promedio_diario)],
          ["Gastos sobre ventas", k.gastos_sobre_ventas == null ? "No disponible" : `${k.gastos_sobre_ventas} %`],
          ["Variación vs anterior", k.variacion?.importe == null ? "No disponible" : `${money(k.variacion.importe)} · ${k.variacion.porcentaje == null ? "Nuevo" : `${k.variacion.porcentaje} %`}`],
          ["Sin grupo", `${money(k.sin_grupo?.importe)} · ${fmtNum.format(k.sin_grupo?.documentos || 0)} docs`],
          ["Sin cuenta contable", `${money(k.sin_cuenta?.importe)} · ${fmtNum.format(k.sin_cuenta?.documentos || 0)} docs`],
          ["Grupo principal", named(k.grupo_principal)],
          ["Gasto principal", named(k.gasto_principal)],
          ["Sucursal principal", named(k.sucursal_principal)],
        ];
      },
      afterMetrics: (a) => renderGastosV45Composition(a),
      details: [
        { label: "Documentos", urlKey: "gastos_v45", vista: "documentos" },
        { label: "Por grupo", urlKey: "gastos_v45", vista: "grupo" },
        { label: "Por gasto", urlKey: "gastos_v45", vista: "gasto" },
        { label: "Por fuente", urlKey: "gastos_v45", vista: "fuente" },
        { label: "Por sucursal", urlKey: "gastos_v45", vista: "sucursal" },
        { label: "Por día", urlKey: "gastos_v45", vista: "dia" },
        { label: "Por mes", urlKey: "gastos_v45", vista: "mes" },
      ],
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

  // Las aperturas existentes por área se ofrecen desde la tarjeta del KPI.
  // Son datos relacionados cuando la API no expone una apertura exacta de ese cálculo.
  const V45_RELATED_VIEWS = {
    preparacion_pedidos: ["pedidos", "pedidos", "pendientes", "pendientes", "en_preparacion", "preparados", "backorder", "backorder", "en_remito", "facturados", "cerrados", "anulados", "pendientes", null, "facturados", "en_remito"],
    compras: ["comprobantes", "comprobantes", "comprobantes", "comprobantes", "ordenes", "ordenes", "ordenes_abiertas", "ordenes_abiertas", "ordenes_abiertas", "remitos", "remitos", "ordenes_abiertas", "proveedores", null],
    financiero: ["cobranzas", "pagos", null, "cartera_cobrar", "cartera_pagar", "vencido_cobrar", "vencido_pagar", "efectivo", "tarjetas", "cheques_cartera", "cheques_emitidos", "cheques_rechazados", "bancos", "vencido_cobrar", "vencido_pagar"],
    gestion_contable: ["asientos", "asientos", "asientos", "asientos", "asientos", "asientos", "asientos", "asientos", "impuestos", "impuestos", "impuestos", "impuestos", "periodos", "ejercicios"],
    impositivo: ["posicion_iva", "ventas", "compras", "percepciones", "percepciones", "retenciones", "ventas", "compras", "ventas", "percepciones", "percepciones", "retenciones", "determinados", "pagados"],
    libros_contables: ["diario", "diario", "diario", "diario", "mayor", "mayor", "balance", "balance", "resultados", "resultados", "resultados", "balance", "balance", "balance"],
    logistica: ["rutas", "rutas", "rutas", "rutas", "rutas", "documentos", "documentos", "documentos", "por_ruta", "por_ruta", "documentos", "por_chofer", "por_unidad", "rutas"],
    gastos: ["documentos", "fuente", "fuente", "documentos", "documentos", "documentos", "documentos", "dia", "documentos", "mes", "grupo", "documentos", "grupo", "gasto", "sucursal"],
  };

  function relatedMetricDetail(def, index) {
    const view = V45_RELATED_VIEWS[def.key]?.[index];
    return view ? (def.details || []).find((detail) => detail.vista === view) : null;
  }

  function metricDetailButton(def, index, label, value, kpi, compact = false) {
    if (["Sin permiso de costos", "No disponible", "N/D"].includes(value)) return "";
    const related = kpi ? null : relatedMetricDetail(def, index);
    if (!kpi && !related) return "";
    const attrs = related
      ? `data-url-key="${related.urlKey}" data-vista="${related.vista}" data-title="${escHtml(label)}${related.exact ? "" : " · datos relacionados"}"`
      : `data-kpi="${kpi}" data-title="${escHtml(label)}"`;
    const text = related && !related.exact ? "Ver datos ›" : "Ver detalle ›";
    return `<button type="button" class="cc-v45-kpi-detail ${compact ? "ml-1 align-middle" : ""} text-xs font-semibold text-blue-700 underline dark:text-blue-300" data-area="${def.key}" ${attrs}>${text}</button>`;
  }

  function comparisonPeriodLabel(areaData) {
    const period = areaData?.comparacion?.periodo;
    if (!period?.inicio || !period?.fin) return "período anterior";
    return `${isoToDisplay(period.inicio)} al ${isoToDisplay(period.fin)}`;
  }

  function renderV45ComparisonTable(areaData, fields) {
    const previous = areaData.comparacion?.kpis;
    if (!previous) return "";
    const current = areaData.kpis || {};
    const rows = fields.map(([label, key, kind = "money"]) => {
      const format = (value) => value == null ? "N/D" : kind === "count" ? fmtNum.format(value) : fmtMoney.format(value);
      return `<tr class="border-t border-slate-100 dark:border-slate-800"><th class="p-2 text-left font-medium">${escHtml(label)}</th><td class="p-2 text-right tabular-nums">${format(current[key])}</td><td class="p-2 text-right tabular-nums">${format(previous[key])}</td><td class="p-2 text-right tabular-nums">${format(areaData.comparacion?.diferencias?.[key])}</td></tr>`;
    }).join("");
    return `<div class="mt-3 overflow-x-auto rounded-lg border border-slate-200 p-2 dark:border-slate-700"><h3 class="text-xs font-semibold">Comparación · ${escHtml(comparisonPeriodLabel(areaData))}</h3><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="p-2 text-left">Indicador</th><th class="p-2 text-right">Actual</th><th class="p-2 text-right">Comparación</th><th class="p-2 text-right">Variación</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderV45GroupedChart(rows, first, second, firstLabel, secondLabel, unit = "money") {
    const items = (rows || []).slice(-30);
    const divisor = unit === "money" ? 1000000 : 1;
    const values = items.flatMap((row) => [Number(row[first] || 0), ...(second ? [Number(row[second] || 0)] : [])]).map((value) => value / divisor);
    const low = Math.min(0, ...values);
    const high = Math.max(unit === "money" ? 1 : 1, ...values);
    const range = high - low;
    const plot = { x: 52, y: 10, width: 420, height: 174 };
    const yFor = (value) => plot.y + (high - value) / range * plot.height;
    const zeroY = yFor(0);
    const number = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 1 });
    const grid = Array.from({ length: 5 }, (_, index) => {
      const value = high - index * range / 4;
      const y = plot.y + index * plot.height / 4;
      return `<line x1="${plot.x}" y1="${y}" x2="${plot.x + plot.width}" y2="${y}" class="cc-chart-grid" /><text x="${plot.x - 7}" y="${y + 3}" text-anchor="end" class="cc-chart-axis">${number.format(value)}</text>`;
    }).join("");
    const step = items.length ? plot.width / items.length : plot.width;
    const barWidth = Math.max(1, Math.min(15, step * (second ? .36 : .55)));
    const labelEvery = Math.max(1, Math.ceil(items.length / 9));
    const bars = items.map((row, index) => {
      const metrics = [[first, firstLabel, "#2563eb", 0], ...(second ? [[second, secondLabel, "#7c3aed", barWidth]] : [])];
      const x = plot.x + index * step + (step - metrics.length * barWidth) / 2;
      const category = String(row.fecha || row.estado || row.nombre || "");
      const day = category.match(/^(\d{4})-(\d{2})-(\d{2})$/);
      const month = category.match(/^(\d{4})-(\d{2})$/);
      const shown = day ? `${day[3]}/${day[2]}` : month ? `${month[2]}/${month[1]}` : category;
      const rects = metrics.map(([key, label, color, offset]) => {
        const value = Number(row[key] || 0) / divisor;
        const y = Math.min(yFor(value), zeroY);
        const height = Math.abs(yFor(value) - zeroY);
        const original = unit === "money" ? fmtMoney.format(row[key] || 0) : fmtNum.format(row[key] || 0);
        return `<rect x="${(x + offset).toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${height.toFixed(1)}" rx="2" fill="${color}"><title>${escHtml(category)} · ${escHtml(label)}: ${original}</title></rect>`;
      }).join("");
      return rects + (index % labelEvery === 0 || index === items.length - 1
        ? `<text x="${(plot.x + (index + .5) * step).toFixed(1)}" y="202" text-anchor="middle" class="cc-chart-axis">${escHtml(shown.length > 11 ? shown.slice(0, 10) + "…" : shown)}</text>` : "");
    }).join("");
    const legend = `<rect x="485" y="74" width="10" height="10" rx="2" fill="#2563eb" /><text x="499" y="83" class="cc-chart-axis">${escHtml(firstLabel)}</text>${second ? `<rect x="485" y="94" width="10" height="10" rx="2" fill="#7c3aed" /><text x="499" y="103" class="cc-chart-axis">${escHtml(secondLabel)}</text>` : ""}`;
    return `<svg viewBox="0 0 600 217" role="img" aria-label="${escHtml(firstLabel)}${second ? ` y ${escHtml(secondLabel)}` : ""} por ${unit === "money" ? "millones" : "cantidad"}" class="cc-v45-chart-svg">
      ${grid}<line x1="${plot.x}" y1="${zeroY.toFixed(1)}" x2="${plot.x + plot.width}" y2="${zeroY.toFixed(1)}" class="cc-chart-zero" />${bars}
      <text x="12" y="108" transform="rotate(-90 12 108)" text-anchor="middle" class="cc-chart-axis">${unit === "money" ? "Importe (millones)" : "Cantidad"}</text>${legend}
      ${items.length ? "" : '<text x="288" y="108" text-anchor="middle" class="cc-chart-axis">Sin datos</text>'}
    </svg>`;
  }

  function renderV45SeriesComparison(areaData, currentSeries, previousSeries, field, title) {
    const actual = (currentSeries?.filas || []).slice(-24);
    const prior = (previousSeries?.filas || []).slice(-24);
    if (!actual.length && !prior.length) return "";
    const count = Math.max(actual.length, prior.length);
    const rows = Array.from({ length: count }, (_, index) => ({
      fecha: actual[index]?.fecha || prior[index]?.fecha || String(index + 1),
      actual: actual[index]?.[field] || 0,
      anterior: prior[index]?.[field] || 0,
    }));
    return `<div class="cc-summary-chart mt-3"><h3 class="cc-summary-chart-title">${escHtml(title)} · comparación</h3>${renderV45GroupedChart(rows, "actual", "anterior", "Actual", comparisonPeriodLabel(areaData))}<p class="text-[11px] text-slate-500 dark:text-slate-300">Barras alineadas por posición en cada período.</p></div>`;
  }

  function renderGastosV45Composition(areaData) {
    const k = areaData.kpis || {};
    const sources = [
      ["Operativos", "operativos", "bg-rose-500"],
      ["Bancarios", "bancarios", "bg-indigo-500"],
      ["Impuestos pagados · separados", "impuestos_pagados", "bg-amber-500"],
    ];
    const max = Math.max(1, ...sources.map(([, key]) => Math.abs(Number(k[key] || 0))));
    const rows = sources.map(([label, key, color]) => `<div class="grid grid-cols-[9rem_1fr] items-center gap-2 py-1 text-xs"><span>${label}</span><div class="h-3 rounded bg-slate-100 dark:bg-slate-800"><div class="h-3 rounded ${color}" style="width:${Math.abs(Number(k[key] || 0)) / max * 100}%"></div></div><strong class="col-span-2 text-right tabular-nums">${k[key] == null ? "N/D" : fmtMoney.format(k[key])}</strong></div>`).join("");
    const previous = areaData.comparacion?.kpis?.total_gastos;
    const seriesRows = [
      ...(areaData.serie?.filas || []).map((row) => ({ ...row, periodo: "Actual" })),
      ...(areaData.serie_comparacion?.filas || []).map((row) => ({ ...row, periodo: "Comparación" })),
    ].map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800"><th scope="row" class="p-2 text-left">${escHtml(row.periodo)}</th><td class="p-2">${escHtml(row.fecha)}</td><td class="p-2 text-right tabular-nums">${fmtNum.format(row.documentos)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.importe)}</td></tr>`).join("");
    const actualSeries = areaData.serie?.filas || [];
    const priorSeries = areaData.serie_comparacion?.filas || [];
    const trendRows = Array.from({ length: Math.max(actualSeries.length, priorSeries.length) }, (_, index) => ({
      fecha: actualSeries[index]?.fecha || priorSeries[index]?.fecha || String(index + 1),
      actual: actualSeries[index]?.importe || 0,
      anterior: priorSeries[index]?.importe || 0,
    }));
    const sourceRows = sources.slice(0, 2).map(([label, key]) => ({ estado: label, importe: k[key] || 0 }));
    return `<div class="cc-summary-charts mt-3">
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Gastos · actual vs período anterior</h3>${renderV45GroupedChart(trendRows, "actual", "anterior", "Actual", "Anterior")}</section>
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Composición por fuente</h3>${renderV45GroupedChart(sourceRows, "importe", null, "Importe", "")}</section>
    </div><details class="mt-2"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Ver composición y comparación</summary><p class="text-[11px] text-slate-500">Los impuestos se muestran separados y no integran «Todos».</p>${rows}<p class="mt-2 text-xs">Gasto del ${escHtml(comparisonPeriodLabel(areaData))}: <strong class="tabular-nums">${previous == null ? "N/D" : fmtMoney.format(previous)}</strong></p></details>`
      + `<details class="mt-2 rounded-lg border border-slate-200 p-2 dark:border-slate-700"><summary class="cursor-pointer text-xs font-semibold">Ver serie de gastos</summary><div class="mt-2 max-h-64 overflow-auto"><table class="w-full min-w-[27rem] text-xs"><thead><tr><th class="p-2 text-left">Período</th><th class="p-2 text-left">Fecha</th><th class="p-2 text-right">Documentos</th><th class="p-2 text-right">Importe</th></tr></thead><tbody>${seriesRows || '<tr><td class="p-2" colspan="4">Sin gastos en los períodos.</td></tr>'}</tbody></table></div></details>`;
  }

  function renderLogisticaV45Comparison(areaData) {
    const k = areaData.kpis || {};
    const previous = areaData.comparacion || {};
    const pairs = [
      ["Hojas de ruta", "hojas_ruta"], ["Abiertas", "rutas_abiertas"],
      ["Cerradas", "rutas_cerradas"], ["Rendidas", "rutas_rendidas"],
      ["Pendientes", "pendientes_rendir"],
    ];
    const rows = pairs.map(([label, key]) => `<tr class="border-t border-slate-100 dark:border-slate-800"><th scope="row" class="p-2 text-left">${label}</th><td class="p-2 text-right tabular-nums">${fmtNum.format(k[key] || 0)}</td><td class="p-2 text-right tabular-nums">${fmtNum.format(previous[key] || 0)}</td></tr>`).join("");
    const states = pairs.map(([label, key]) => ({ estado: label, actual: k[key] || 0, anterior: previous[key] || 0 }));
    return `<div class="cc-summary-charts mt-3">
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Estado de rutas · actual vs anterior</h3>${renderV45GroupedChart(states, "actual", "anterior", "Actual", "Anterior", "count")}</section>
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Importe facturado por hoja de ruta</h3>${renderV45GroupedChart([], "importe", null, "Importe", "")}<p class="text-[11px] text-slate-500">Sin serie por hoja de ruta en este período; disponible en «Facturación por ruta».</p></section>
    </div><div class="mt-4 overflow-x-auto rounded-lg border border-slate-200 p-2 dark:border-slate-700"><h3 class="mb-2 text-xs font-semibold">Rutas · actual y ${escHtml(comparisonPeriodLabel(areaData))}</h3><table class="w-full min-w-[24rem] text-xs"><thead><tr><th class="p-2 text-left">Estado</th><th class="p-2 text-right">Actual</th><th class="p-2 text-right">Comparación</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function renderLibrosV45Charts(areaData) {
    const rows = (areaData.series?.filas || []).slice(-30);
    const panels = [
      ["Libro Diario · Debe vs Haber", "debe", "haber"],
      ["Resultados · Ingresos vs Egresos", "ingresos", "egresos"],
    ];
    const chart = ([title, first, second]) => {
      const table = rows.map((row) => `<tr><th scope="row" class="p-1 text-left">${escHtml(row.fecha)}</th><td class="p-1 text-right tabular-nums">${fmtMoney.format(row[first])}</td><td class="p-1 text-right tabular-nums">${fmtMoney.format(row[second])}</td></tr>`).join("");
      return `<div class="cc-summary-chart"><h3 class="cc-summary-chart-title">${title}</h3>${renderV45GroupedChart(rows, first, second, first, second)}<details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700">Ver serie completa</summary><div class="max-h-56 overflow-auto"><table class="w-full min-w-[25rem] text-xs"><thead><tr><th class="p-1 text-left">Fecha</th><th class="p-1 text-right">${first}</th><th class="p-1 text-right">${second}</th></tr></thead><tbody>${table}</tbody></table></div></details></div>`;
    };
    return `<div class="mt-4 grid gap-3 lg:grid-cols-2">${panels.map(chart).join("")}</div>`
      + renderV45SeriesComparison(areaData, areaData.series, areaData.series_comparacion, "debe", "Libro Diario · Debe")
      + renderV45SeriesComparison(areaData, areaData.series, areaData.series_comparacion, "ingresos", "Resultados · Ingresos")
      + renderV45ComparisonTable(areaData, [
        ["Asientos", "asientos", "count"], ["Total Debe", "total_debe"],
        ["Total Haber", "total_haber"], ["Resultado", "resultado_periodo"],
        ["Ingresos", "ingresos"], ["Egresos", "egresos"],
        ["Activo", "activo"], ["Pasivo", "pasivo"],
      ]);
  }

  function renderImpositivoV45Chart(areaData) {
    const k = areaData.kpis || {};
    const metrics = [
      ["IVA débito", "iva_debito", "bg-sky-500"],
      ["Percep. IVA ventas", "percep_iva_ventas", "bg-sky-400"],
      ["IVA crédito", "iva_credito", "bg-amber-500"],
      ["Percep. IVA compras", "percep_iva_compras", "bg-amber-400"],
      ["Retenciones IVA", "retenciones_iva", "bg-amber-300"],
    ];
    const max = Math.max(1, ...metrics.map(([, key]) => Math.abs(Number(k[key] || 0))));
    const bars = metrics.map(([label, key, color]) => `<div class="grid grid-cols-[8.5rem_1fr] items-center gap-2 py-1 text-xs"><span>${label}</span><div class="h-3 rounded bg-slate-100 dark:bg-slate-800"><div class="h-3 rounded ${color}" style="width:${Math.abs(Number(k[key] || 0)) / max * 100}%"></div></div><strong class="col-span-2 text-right tabular-nums">${fmtMoney.format(k[key] || 0)}</strong></div>`).join("");
    const fiscalRows = (areaData.serie_mensual?.filas || []).map((row) =>
      `<tr class="border-t border-slate-100 dark:border-slate-800"><th scope="row" class="p-2 text-left">${escHtml(row.fecha)}</th><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iva_debito)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iva_credito)}</td><td class="p-2 text-right font-semibold tabular-nums">${fmtMoney.format(row.iva_posicion)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iibb_debito)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iibb_credito)}</td></tr>`
    ).join("");
    const previousRows = (areaData.serie_mensual_comparacion?.filas || []).map((row) =>
      `<tr class="border-t border-slate-100 dark:border-slate-800"><th scope="row" class="p-2 text-left">${escHtml(row.fecha)}</th><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iva_debito)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iva_credito)}</td><td class="p-2 text-right font-semibold tabular-nums">${fmtMoney.format(row.iva_posicion)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iibb_debito)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(row.iibb_credito)}</td></tr>`
    ).join("");
    const fiscalTable = (title, rows) => `<section class="mt-3 overflow-x-auto rounded-lg border border-slate-200 p-2 dark:border-slate-700"><h3 class="text-xs font-semibold">${escHtml(title)}</h3><table class="w-full min-w-[42rem] text-xs"><thead><tr><th class="p-2 text-left">Mes</th><th class="p-2 text-right">IVA débito</th><th class="p-2 text-right">IVA crédito</th><th class="p-2 text-right">Posición IVA</th><th class="p-2 text-right">IIBB ventas</th><th class="p-2 text-right">IIBB crédito</th></tr></thead><tbody>${rows || '<tr><td class="p-2" colspan="6">Sin movimientos en el período.</td></tr>'}</tbody></table></section>`;
    return `<div class="cc-summary-charts mt-3">
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">IVA débito vs crédito por período</h3>${renderV45GroupedChart(areaData.serie_mensual?.filas, "iva_debito", "iva_credito", "Cargos IVA", "Créditos IVA")}</section>
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">IIBB en ventas vs pagos a cuenta</h3>${renderV45GroupedChart(areaData.serie_mensual?.filas, "iibb_debito", "iibb_credito", "IIBB ventas", "Pagos a cuenta")}</section>
    </div><details class="mt-2"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Ver composición de la posición IVA</summary><p class="mb-2 text-xs text-slate-500">Débito + percepciones de ventas − crédito − percepciones de compras − retenciones</p>${bars}</details>`
      + fiscalTable("Evolución fiscal mensual · período actual", fiscalRows)
      + fiscalTable(`Evolución fiscal mensual · ${comparisonPeriodLabel(areaData)}`, previousRows)
      + renderV45SeriesComparison(areaData, areaData.serie_mensual, areaData.serie_mensual_comparacion, "iva_debito", "IVA débito mensual")
      + renderV45SeriesComparison(areaData, areaData.serie_mensual, areaData.serie_mensual_comparacion, "iva_credito", "IVA crédito mensual")
      + renderV45SeriesComparison(areaData, areaData.serie_mensual, areaData.serie_mensual_comparacion, "iibb_debito", "IIBB ventas mensual")
      + renderV45SeriesComparison(areaData, areaData.serie_mensual, areaData.serie_mensual_comparacion, "iibb_credito", "IIBB crédito mensual")
      + renderV45ComparisonTable(areaData, [
        ["Posición IVA", "posicion_iva"], ["IVA débito", "iva_debito"],
        ["IVA crédito", "iva_credito"], ["Percep. IVA ventas", "percep_iva_ventas"],
        ["Percep. IVA compras", "percep_iva_compras"], ["Retenciones IVA", "retenciones_iva"],
        ["Libro IVA ventas", "libro_ventas", "count"], ["Libro IVA compras", "libro_compras", "count"],
        ["IIBB ventas", "iibb_ventas"], ["Impuestos determinados", "impuestos_determinados"],
        ["Impuestos pagados", "impuestos_pagados"],
      ]);
  }

  function renderContableV45Charts(areaData) {
    const rows = (areaData.serie_asientos?.filas || []).slice(-30);
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
      <div class="cc-summary-chart"><h3 class="cc-summary-chart-title">Libro Diario · Debe y Haber</h3>${renderV45GroupedChart(rows, "debe", "haber", "Debe", "Haber")}
        <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa</summary><div class="mt-2 max-h-60 overflow-auto"><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Debe</th><th class="px-2 py-2 text-right">Haber</th></tr></thead><tbody>${tableRows}</tbody></table></div></details>
      </div><div class="cc-summary-chart"><h3 class="cc-summary-chart-title">Impuestos · a pagar vs a favor</h3>${renderV45GroupedChart([{ estado: "A pagar", importe: k.impuestos_pagar || 0 }, { estado: "A favor", importe: k.impuestos_favor || 0 }], "importe", null, "Importe", "")}<details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver situación fiscal</summary>${taxRows}</details></div>
    </div><p class="mt-2 text-[11px] text-slate-500">Impuestos, períodos y ejercicios son generales para la empresa.</p>`
      + renderV45SeriesComparison(areaData, areaData.serie_asientos, areaData.serie_asientos_comparacion, "debe", "Libro Diario · Debe")
      + renderV45ComparisonTable(areaData, [
        ["Asientos", "asientos", "count"], ["Total Debe", "total_debe"],
        ["Total Haber", "total_haber"], ["Desbalanceados", "desbalanceados", "count"],
        ["Resultado contable", "resultado_contable"],
        ["Impuestos determinados", "impuestos_determinados"],
        ["Impuestos a pagar", "impuestos_pagar"],
      ]);
  }

  function renderFinancieroV45Charts(areaData) {
    const rows = (areaData.serie_flujo?.filas || []).slice(-30);
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
    const compared = areaData.comparacion?.kpis || {};
    const checks = [
      ["De terceros en cartera", "cheques_cartera", "bg-sky-500"],
      ["Propios emitidos", "cheques_emitidos", "bg-indigo-600"],
      ["Rechazados", "cheques_rechazados", "bg-rose-500"],
    ];
    const checkMax = Math.max(1, ...checks.map(([, key]) => Number(areaData.kpis?.[key] || 0)));
    const checkChart = checks.every(([, key]) => areaData.kpis?.[key] == null) ? "" : `<section class="cc-summary-chart lg:col-span-2"><h3 class="cc-summary-chart-title">Situación de cheques</h3><div class="space-y-3">${checks.map(([label, key, color]) => `<div class="grid grid-cols-[minmax(8rem,1fr)_minmax(0,2fr)_auto] items-center gap-3 text-xs"><span>${label}</span><div class="h-3 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800"><div class="h-full rounded-full ${color}" style="width:${Math.max(0, Number(areaData.kpis?.[key] || 0)) / checkMax * 100}%"></div></div><strong class="min-w-[6rem] text-right tabular-nums">${areaData.kpis?.[key] == null ? "N/D" : fmtMoney.format(areaData.kpis[key])}</strong></div>`).join("")}</div><p class="mt-3 text-[11px] text-slate-500 dark:text-slate-400">Un cheque rechazado puede figurar también en la cartera de terceros.</p></section>`;
    const comparisonRows = [["Cobranzas", "cobranzas"], ["Pagos", "pagos"], ["Flujo neto", "flujo_neto"]]
      .map(([label, key]) => `<tr class="border-t border-slate-100 dark:border-slate-800"><th class="p-2 text-left">${label}</th><td class="p-2 text-right tabular-nums">${fmtMoney.format(areaData.kpis?.[key] || 0)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(compared[key] || 0)}</td><td class="p-2 text-right tabular-nums">${fmtMoney.format(areaData.comparacion?.diferencias?.[key] || 0)}</td></tr>`).join("");
    return `<div class="mt-4 grid gap-3 lg:grid-cols-2">
      <div class="cc-summary-chart"><h3 class="cc-summary-chart-title">Cobranzas vs Pagos</h3>${renderV45GroupedChart(rows, "cobranzas", "pagos", "Cobranzas", "Pagos")}
        <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa</summary><div class="mt-2 max-h-60 overflow-auto"><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Cobranzas</th><th class="px-2 py-2 text-right">Pagos</th></tr></thead><tbody>${seriesRows}</tbody></table></div></details>
      </div>
      <div class="cc-summary-chart"><h3 class="cc-summary-chart-title">Antigüedad de saldos</h3>${renderV45GroupedChart(buckets.map(([name, key]) => ({ estado: name, cobrar: receivable[key] || 0, pagar: payable[key] || 0 })), "cobrar", "pagar", "A cobrar", "A pagar")}<details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver importes por tramo</summary>${agingRows}</details></div>${checkChart}
    </div><div class="mt-3 overflow-x-auto rounded-lg border border-slate-200 p-2 dark:border-slate-700"><h3 class="text-xs font-semibold">Flujo comparado con ${escHtml(comparisonPeriodLabel(areaData))}</h3><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="p-2 text-left">Indicador</th><th class="p-2 text-right">Actual</th><th class="p-2 text-right">Comparación</th><th class="p-2 text-right">Variación</th></tr></thead><tbody>${comparisonRows}</tbody></table></div>`;
  }

  function renderComprasV45Charts(areaData) {
    const rows = (areaData.serie_evolucion?.filas || []).slice(-30);
    const tableRows = rows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800">
      <th scope="row" class="px-2 py-1.5 text-left font-medium">${escHtml(row.fecha)}</th>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.compras)}</td>
      <td class="px-2 py-1.5 text-right tabular-nums">${fmtMoney.format(row.ordenes)}</td>
    </tr>`).join("");
    const previous = areaData.comparacion?.kpis?.compras_netas;
    const statusRows = [["OC pendientes", "oc_pendientes"], ["OC parciales", "oc_parciales"], ["Remitos recibidos", "remitos_recibidos"], ["OC vencidas", "oc_vencidas"]]
      .map(([estado, key]) => ({ estado, cantidad: areaData.kpis?.[key] || 0 }));
    return `<div class="cc-summary-charts mt-3"><section class="cc-summary-chart">
      <p class="text-xs font-semibold">Evolución de compras y OC · ${areaData.serie_evolucion?.agrupacion || "período"}</p>
      ${renderV45GroupedChart(rows, "compras", "ordenes", "Compras netas", "Órdenes de compra")}
      <p class="mt-2 text-xs">Compras del ${escHtml(comparisonPeriodLabel(areaData))}: <strong class="tabular-nums">${previous == null ? "No disponible" : fmtMoney.format(previous)}</strong></p>
      <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa</summary>
        <div class="mt-2 max-h-72 overflow-auto"><table class="w-full min-w-[30rem] text-xs"><thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Compras</th><th class="px-2 py-2 text-right">OC</th></tr></thead><tbody>${tableRows}</tbody></table></div>
      </details></section><section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Situación actual de órdenes de compra</h3>${renderV45GroupedChart(statusRows, "cantidad", null, "Órdenes", "", "count")}</section></div>`;
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
    return `<div class="cc-summary-charts mt-3">
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Estados · actual vs ${escHtml(comparisonPeriodLabel(areaData))}</h3>${renderV45GroupedChart(states, "actual", "anterior", "Actual", "Anterior", "count")}</section>
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Importe de pedidos por estado</h3>${renderV45GroupedChart(amounts, "importe", null, "Importe", "")}</section>
    </div><details class="mt-2"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Ver importes y estados</summary><div class="grid gap-3 lg:grid-cols-2"><section>${stateRows}</section><section>${amountRows}</section></div></details>`;
  }

  const RESUMEN_KPIS = [
    ["Ventas netas", "ventas", "money", "#1d4ed8", "Ventas netas del período"],
    ["Compras netas", "compras_netas", "money", "#1d4ed8", "Compras netas del período"],
    ["Cobranzas", "cobranzas", "money", "#0f766e", "Cobranzas registradas en el período"],
    ["Pagos", "pagos", "money", "#0f766e", "Pagos registrados en el período"],
    ["Presupuestos", "presupuestos", "count", "#6d28d9", "Presupuestos emitidos en el período"],
    ["Pedidos", "pedidos", "count", "#6d28d9", "Pedidos registrados en el período"],
    ["Facturas", "facturas", "count", "#6d28d9", "Comprobantes de venta emitidos"],
    ["Remitos", "remitos", "count", "#6d28d9", "Entregas de mercadería registradas"],
    ["Vencimiento a cobrar", "vencimiento_cobrar", "money", "#c2410c", "Vencimientos dentro del intervalo"],
    ["Vencimiento a pagar", "vencimiento_pagar", "money", "#c2410c", "Vencimientos dentro del intervalo"],
    ["Efectivo actual", "efectivo_actual", "money", "#475569", "Cajas finales de efectivo"],
    ["Tarjetas actual", "tarjetas_actual", "money", "#475569", "Saldos actuales de tarjetas en pesos"],
    ["Cheques actual", "cheques_actual", "money", "#475569", "Saldos actuales de cheques en pesos"],
    ["Bancos actual", "bancos_actual", "money", "#475569", "Saldo neto de cuentas bancarias en pesos"],
    ["Venta cuenta corriente", "venta_cuenta_corriente", "money", "#475569", "Venta financiada en el período"],
    ["Compra cuenta corriente", "compra_cuenta_corriente", "money", "#475569", "Compra neta financiada en el período"],
  ];

  function resumenTrend(key, current, previous) {
    if (current == null) return null;
    if (["efectivo_actual", "bancos_actual"].includes(key)) {
      return Number(current) < -0.0001
        ? { direction: "down", label: "Controlar", note: "Controlar saldo negativo" }
        : null;
    }
    if (!["ventas", "compras_netas", "cobranzas", "pagos"].includes(key)) return null;
    if (previous == null || Math.abs(Number(previous)) < 0.0001) {
      return { direction: "none", label: "", note: "Sin base en período anterior" };
    }
    const pct = (Number(current) / Number(previous) - 1) * 100;
    if (!Number.isFinite(pct)) return null;
    if (Math.abs(pct) < 0.05) {
      return { direction: "flat", label: "Sin cambio", note: "0,0 % vs período anterior" };
    }
    const magnitude = Math.abs(pct);
    const strength = magnitude < 10 ? "mínima" : magnitude < 25 ? "leve"
      : magnitude < 50 ? "media" : magnitude < 100 ? "fuerte" : "extrema";
    const direction = pct > 0 ? "up" : "down";
    const percent = new Intl.NumberFormat("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(pct);
    return {
      direction,
      label: `${pct > 0 ? "Suba" : "Baja"} ${strength}`,
      note: `${pct > 0 ? "+" : ""}${percent} % vs período anterior`,
    };
  }

  function trendForV45(areaKey, index, data) {
    const arrows = {
      preparacion_pedidos: { 1: "monto_pedidos" },
      compras: { 0: "compras_netas" },
      financiero: { 0: "cobranzas", 1: "pagos" },
      gastos: { 9: "total_gastos" },
    };
    const key = arrows[areaKey]?.[index];
    if (!key) return null;
    return resumenTrend("ventas", data.kpis?.[key], data.comparacion?.kpis?.[key]);
  }

  function renderResumenV45Kpis(areaData) {
    const current = areaData.kpis || {};
    const previous = areaData.comparacion?.kpis || {};
    const trendIcon = { up: "arrow_upward", down: "arrow_downward", flat: "remove" };
    return `<div class="cc-summary-kpis" aria-label="Indicadores del Resumen gerencial">${RESUMEN_KPIS.map(([label, key, kind, accent, description]) => {
      const value = current[key];
      const trend = resumenTrend(key, value, previous[key]);
      const quantityKey = `${key}_cantidad`;
      const note = trend?.note || (current[quantityKey] != null
        ? `${fmtNum.format(current[quantityKey])} vencimientos dentro del intervalo` : description);
      const trendHtml = trend && trend.direction !== "none"
        ? `<span class="cc-trend cc-trend-${trend.direction}" aria-label="${escHtml(trend.label)}"><span class="cc-trend-icon"><span class="material-icons" aria-hidden="true">${trendIcon[trend.direction]}</span></span><span>${escHtml(trend.label)}</span></span>`
        : "";
      const detail = value == null ? "" : `<button type="button" class="cc-v45-kpi-detail text-xs font-semibold text-blue-700 underline dark:text-blue-300" data-area="resumen_general" data-kpi="${key}" data-title="${escHtml(label)}">Ver detalle ›</button>`;
      return `<article class="cc-summary-kpi" style="--cc-kpi-accent:${accent}">
        <div class="cc-summary-kpi-head"><h3 class="cc-summary-kpi-title">${escHtml(label)}</h3>${detail}</div>
        <div class="cc-summary-kpi-middle"><strong class="cc-summary-kpi-value">${value == null ? "N/D" : kind === "count" ? fmtNum.format(value) : fmtMoney.format(value)}</strong>${trendHtml}</div>
        <p class="cc-summary-kpi-note ${trend?.direction === "down" ? "cc-trend-down" : trend?.direction === "up" ? "cc-trend-up" : ""}">${escHtml(value == null ? "Información no disponible para este alcance" : note)}</p>
      </article>`;
    }).join("")}</div>`;
  }

  function renderResumenV45Charts(areaData) {
    const series = (areaData.series?.filas || []).slice(-30);
    const chartDate = (date) => {
      const day = String(date || "").match(/^(\d{4})-(\d{2})-(\d{2})$/);
      if (day) return `${day[3]}/${day[2]}`;
      const month = String(date || "").match(/^(\d{4})-(\d{2})$/);
      return month ? `${month[2]}/${month[1]}` : String(date || "");
    };
    const chart = (title, left, right, leftLabel, rightLabel) => {
      if (!series.length) return `<section class="cc-summary-chart"><h3 class="cc-summary-chart-title">${escHtml(title)}</h3><p class="p-6 text-center text-sm text-slate-500 dark:text-slate-300">Sin movimientos en el período.</p></section>`;
      const values = series.flatMap((row) => [Number(row[left] || 0) / 1000000, Number(row[right] || 0) / 1000000]);
      const low = Math.min(0, ...values);
      const high = Math.max(1, ...values);
      const range = high - low;
      const plot = { x: 50, y: 10, width: 422, height: 174 };
      const yFor = (value) => plot.y + (high - value) / range * plot.height;
      const zeroY = yFor(0);
      const millions = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 1 });
      const grid = Array.from({ length: 5 }, (_, index) => {
        const value = high - index * range / 4;
        const y = plot.y + index * plot.height / 4;
        return `<line x1="${plot.x}" y1="${y}" x2="${plot.x + plot.width}" y2="${y}" class="cc-chart-grid" />
          <text x="${plot.x - 7}" y="${y + 3}" text-anchor="end" class="cc-chart-axis">${millions.format(value)}</text>`;
      }).join("");
      const step = series.length ? plot.width / series.length : plot.width;
      const barWidth = Math.max(1, Math.min(15, step * .36));
      const labelEvery = Math.max(1, Math.ceil(series.length / 10));
      const bars = series.map((row, index) => {
        const x = plot.x + index * step + (step - 2 * barWidth) / 2;
        const rectangles = [[left, "#2563eb", 0], [right, "#7c3aed", barWidth]].map(([key, color, offset]) => {
          const amount = Number(row[key] || 0) / 1000000;
          const y = Math.min(yFor(amount), zeroY);
          const height = Math.max(0, Math.abs(yFor(amount) - zeroY));
          return `<rect x="${(x + offset).toFixed(1)}" y="${y.toFixed(1)}" width="${barWidth.toFixed(1)}" height="${height.toFixed(1)}" rx="2" fill="${color}"><title>${escHtml(row.fecha)} · ${escHtml(key === left ? leftLabel : rightLabel)}: ${fmtMoney.format(row[key] || 0)}</title></rect>`;
        }).join("");
        const label = index % labelEvery === 0 || index === series.length - 1
          ? `<text x="${(plot.x + (index + .5) * step).toFixed(1)}" y="202" text-anchor="middle" class="cc-chart-axis">${escHtml(chartDate(row.fecha))}</text>` : "";
        return rectangles + label;
      }).join("");
      return `<section class="cc-summary-chart" aria-label="${escHtml(title)}">
        <h3 class="cc-summary-chart-title">${escHtml(title)}</h3>
        <svg viewBox="0 0 600 217" role="img" aria-label="${escHtml(title)}: importes en millones" class="cc-v45-chart-svg">
          ${grid}<line x1="${plot.x}" y1="${zeroY.toFixed(1)}" x2="${plot.x + plot.width}" y2="${zeroY.toFixed(1)}" class="cc-chart-zero" />${bars}
          <text x="12" y="108" transform="rotate(-90 12 108)" text-anchor="middle" class="cc-chart-axis">Importe (millones)</text>
          <rect x="485" y="74" width="10" height="10" rx="2" fill="#2563eb" /><text x="499" y="83" class="cc-chart-axis">${escHtml(leftLabel)}</text>
          <rect x="485" y="94" width="10" height="10" rx="2" fill="#7c3aed" /><text x="499" y="103" class="cc-chart-axis">${escHtml(rightLabel)}</text>
        </svg>
      </section>`;
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
    const readout = (label, value) => `<span>${escHtml(label)}: <strong>${value == null ? "N/D" : fmtMoney.format(value)}</strong></span>`;
    const flow = current.cobranzas == null || current.pagos == null ? null : current.cobranzas - current.pagos;
    const margin = current.ventas == null || current.compras_netas == null ? null : current.ventas - current.compras_netas;
    const ordersBudget = current.pedidos == null || current.presupuestos == null || !Number(current.presupuestos)
      ? "N/D" : `${new Intl.NumberFormat("es-AR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(current.pedidos / current.presupuestos * 100)} %`;
    return `<div class="cc-summary-charts">
      ${chart("Gestión comercial · Ventas vs Compras", "ventas", "compras", "Venta neta", "Compras netas")}
      ${chart("Tesorería · Cobranzas vs Pagos", "cobranzas", "pagos", "Cobranzas", "Pagos")}
    </div><div class="cc-summary-readout">${readout("Flujo del período", flow)}<span aria-hidden="true">|</span>${readout("Ventas - Compras", margin)}<span aria-hidden="true">|</span><span>Pedidos / Presupuestos: <strong>${ordersBudget}</strong></span></div><details class="mt-3"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Ver serie completa (${areaData.series?.agrupacion || "período"})</summary>
      <div class="mt-2 max-h-80 overflow-auto"><table class="w-full min-w-[38rem] text-xs text-slate-700 dark:text-slate-200">
        <thead><tr><th class="px-2 py-2 text-left">Fecha</th><th class="px-2 py-2 text-right">Ventas</th><th class="px-2 py-2 text-right">Compras</th><th class="px-2 py-2 text-right">Cobranzas</th><th class="px-2 py-2 text-right">Pagos</th></tr></thead>
        <tbody>${seriesRows}</tbody></table></div></details>
    <details class="mt-3"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Comparar con ${escHtml(comparisonPeriodLabel(areaData))}</summary>
      <div class="mt-2 max-h-80 overflow-auto"><table class="w-full min-w-[34rem] text-xs text-slate-700 dark:text-slate-200">
        <thead><tr><th class="px-2 py-2 text-left">Indicador</th><th class="px-2 py-2 text-right">Actual</th><th class="px-2 py-2 text-right">Comparación</th><th class="px-2 py-2 text-right">Variación</th></tr></thead>
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
    const salesSeries = Array.from({ length: Math.max(currentSeries.length, previousSeries.length) }, (_, index) => ({
      fecha: currentSeries[index]?.fecha || previousSeries[index]?.fecha || String(index + 1),
      actual: currentSeries[index]?.valor || 0,
      anterior: previousSeries[index]?.valor || 0,
    }));
    const documents = [["Presupuestos", "presupuestos"], ["Pedidos", "pedidos"], ["Remitos", "remitos"], ["Facturas", "facturas"]]
      .map(([estado, key]) => ({ estado, actual: actual[key] || 0, anterior: previous[key] || 0 }));
    const graph = `<div class="cc-summary-charts mt-3">
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Ventas netas · actual vs anterior</h3>${renderV45GroupedChart(salesSeries, "actual", "anterior", "Actual", "Anterior")}</section>
      <section class="cc-summary-chart"><h3 class="cc-summary-chart-title">Documentos · actual vs período anterior</h3>${renderV45GroupedChart(documents, "actual", "anterior", "Actual", "Anterior", "count")}</section>
    </div>`;
    return `${graph}<details class="mt-3"><summary class="cursor-pointer text-xs font-semibold text-sky-700 dark:text-sky-300">Comparar los 16 indicadores</summary>
      <div class="mt-2 max-h-80 overflow-auto"><table class="w-full min-w-[34rem] text-xs text-slate-700 dark:text-slate-200">
        <thead class="sticky top-0 bg-slate-50 dark:bg-slate-900"><tr><th class="px-2 py-2 text-left">Indicador</th><th class="px-2 py-2 text-right">Actual</th><th class="px-2 py-2 text-right">Comparación</th><th class="px-2 py-2 text-right">Variación</th></tr></thead>
        <tbody>${rows}</tbody>
      </table></div></details>`;
  }

  function renderStockV45Charts(areaData) {
    const movement = areaData?.serie_movimientos || {};
    const rows = Array.isArray(movement.filas) ? movement.filas : [];
    const previousRows = Array.isArray(areaData?.serie_movimientos_anterior?.filas)
      ? areaData.serie_movimientos_anterior.filas : [];
    const seriesTable = rows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800">
      <th class="py-1.5 text-left font-normal">${escHtml(row.fecha)}</th>
      <td class="py-1.5 text-right">${fmtNum.format(row.entradas)}</td>
      <td class="py-1.5 text-right">${fmtNum.format(row.salidas)}</td>
    </tr>`).join("");
    const graph = `<div class="mt-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
      <p class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">Movimientos por ${movement.agrupacion || "período"} · ${escHtml(areaData.presentacion || "unidad")}</p>
      ${renderV45GroupedChart(rows, "entradas", "salidas", "Entradas", "Salidas", "count")}
      <details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie completa (${rows.length})</summary>
        <div class="max-h-60 overflow-auto"><table class="w-full text-xs"><thead><tr><th class="text-left">Fecha</th><th class="text-right">Entradas</th><th class="text-right">Salidas</th></tr></thead><tbody>${seriesTable}</tbody></table></div>
      </details>
      ${previousRows.length ? `<details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver serie comparada (${previousRows.length})</summary>
        <div class="max-h-60 overflow-auto"><table class="w-full text-xs"><thead><tr><th class="text-left">Fecha</th><th class="text-right">Entradas</th><th class="text-right">Salidas</th></tr></thead><tbody>${previousRows.map((row) => `<tr class="border-t border-slate-100 dark:border-slate-800"><th class="py-1.5 text-left font-normal">${escHtml(row.fecha)}</th><td class="py-1.5 text-right">${fmtNum.format(row.entradas)}</td><td class="py-1.5 text-right">${fmtNum.format(row.salidas)}</td></tr>`).join("")}</tbody></table></div>
      </details>` : ""}
    </div>`;
    const deposits = Array.isArray(areaData?.series_depositos) ? areaData.series_depositos : [];
    const maxDeposit = Math.max(1, ...deposits.map((dep) => Number(dep.valor || 0)));
    const depositChart = `<div class="cc-summary-chart mt-3">
      <h3 class="cc-summary-chart-title">Valorización por depósito</h3>
      ${renderV45GroupedChart(deposits, "valor", null, "Stock valorizado", "")}
      ${deposits.length ? `<details class="mt-2"><summary class="cursor-pointer text-xs text-sky-700 dark:text-sky-300">Ver depósitos</summary>${deposits.map((dep) => `<div class="mb-2 text-xs"><div class="flex justify-between gap-2"><span class="truncate">${escHtml(dep.nombre)}</span><strong class="tabular-nums">${fmtMoney.format(dep.valor)}</strong></div><div class="mt-1 h-2 rounded bg-slate-100 dark:bg-slate-700"><div class="h-2 rounded bg-emerald-600" style="width:${(Math.max(0, Number(dep.valor || 0)) / maxDeposit * 100).toFixed(1)}%"></div></div></div>`).join("")}</details>` : ""}
    </div>`;
    const compare = areaData?.comparacion;
    const flowFields = [
      ["Entradas", "entradas_periodo", "qty"], ["Salidas", "salidas_periodo", "qty"],
      ["Valor entradas", "valor_entradas", "money"], ["Valor salidas", "valor_salidas", "money"],
    ];
    const comparison = compare ? `<div class="mt-3 rounded-lg border border-slate-200 p-2 dark:border-slate-700">
      <p class="mb-2 text-[11px] font-semibold text-slate-600 dark:text-slate-300">Comparación de movimientos · ${escHtml(comparisonPeriodLabel(areaData))}</p>
      <div class="overflow-x-auto"><table class="w-full min-w-[28rem] text-xs"><thead><tr><th class="text-left">Indicador</th><th class="text-right">Actual</th><th class="text-right">Comparación</th><th class="text-right">Variación</th></tr></thead><tbody>
      ${flowFields.map(([label, key, kind]) => {
        const fmt = (value) => value == null ? "Sin permiso" : kind === "money" ? fmtMoney.format(value) : fmtNum.format(value);
        return `<tr class="border-t border-slate-100 dark:border-slate-800"><th class="py-1.5 text-left font-medium">${label}</th><td class="text-right">${fmt(areaData.kpis?.[key])}</td><td class="text-right">${fmt(compare.kpis?.[key])}</td><td class="text-right">${fmt(compare.diferencias?.[key])}</td></tr>`;
      }).join("")}
      </tbody></table></div><p class="mt-2 text-[11px] text-slate-500">Las existencias son una foto actual y no se comparan como período.</p>
    </div>` : "";
    return `<div class="cc-summary-charts">${depositChart}${graph}</div>${comparison}`;
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

    if (def.key === "resumen_general" && !unavailable) {
      const data = areaData || {};
      return `<article data-area-key="${def.key}" class="cc-card-animate min-w-0 rounded-xl border ${borderColor} bg-white p-2 shadow-sm dark:bg-slate-900" style="animation-delay:${delayIdx * 0.06}s">
        <h2 class="sr-only">${def.title}</h2>
        ${renderResumenV45Kpis(data)}
        <p class="cc-summary-legend">Lectura: Suba/Baja = dirección | Fuerza: Mínima &lt;10 % | Leve 10-24,9 % | Media 25-49,9 % | Fuerte 50-99,9 % | Extrema ≥100 % | Verde = suba | Rojo = baja | Caja/Banco negativo: Controlar</p>
        ${renderResumenV45Charts(data)}
      </article>`;
    }

    let body = "";
    if (unavailable) {
      body = `<p class="text-sm text-amber-700 dark:text-amber-300">${areaData.error?.mensaje || "Datos no disponibles"}</p>`;
    } else {
      const a = areaData || {};
      const metrics = def.metrics(a);
      const useV45Layout = CUSTOM_COMPARE_AREAS.has(def.key);
      const rows = metrics
        .map(
          ([k, val, kpi], index) => useV45Layout ? `<article class="cc-summary-kpi" style="--cc-kpi-accent:${["#1d4ed8", "#1d4ed8", "#0f766e", "#0f766e", "#6d28d9", "#6d28d9", "#6d28d9", "#6d28d9", "#c2410c", "#c2410c", "#475569", "#475569", "#475569", "#475569", "#475569", "#475569"][index] || "#475569"}">
            <div class="cc-summary-kpi-head"><h3 class="cc-summary-kpi-title">${escHtml(k)}</h3>
              ${metricDetailButton(def, index, k, val, kpi)}
            </div><div class="cc-summary-kpi-middle"><strong class="cc-summary-kpi-value">${val}</strong>${(() => { const trend = trendForV45(def.key, index, a); return trend && trend.direction !== "none" ? `<span class="cc-trend cc-trend-${trend.direction}"><span class="cc-trend-icon"><span class="material-icons" aria-hidden="true">${trend.direction === "up" ? "arrow_upward" : trend.direction === "down" ? "arrow_downward" : "remove"}</span></span>${escHtml(trend.label)}</span>` : ""; })()}</div>
            ${(() => { const trend = trendForV45(def.key, index, a); return trend ? `<p class="cc-summary-kpi-note cc-trend-${trend.direction}">${escHtml(trend.note)}</p>` : ""; })()}
          </article>` : `
        <div class="flex items-start justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0 dark:border-slate-800">
          <span class="min-w-0 shrink text-sm text-slate-500 dark:text-slate-400">${k}
            ${metricDetailButton(def, index, k, val, kpi, true)}
          </span>
          <span class="shrink-0 text-right text-sm font-semibold tabular-nums text-slate-900 dark:text-white">${val}</span>
        </div>`
        )
        .join("");
      const extra = typeof def.afterMetrics === "function" ? def.afterMetrics(a) : "";
      body = `<div class="${useV45Layout ? "cc-summary-kpis" : "space-y-0"}">${rows}</div>${extra || ""}`;
    }

    const detailBtns = (def.details || [])
      .map(
        (d) => `
      <button type="button" class="cc-detail-btn inline-flex min-h-10 w-full items-center justify-center rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-[11px] font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700 sm:w-auto sm:justify-start sm:py-1"
        data-url-key="${d.urlKey}" data-vista="${d.vista || ""}" data-title="${def.title}: ${d.label}">
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
        ${detailBtns || cashFlowBtn || mprBtn ? `<footer class="flex flex-col gap-2 border-t border-slate-100 px-4 py-3 sm:flex-row sm:flex-wrap dark:border-slate-700">
          ${detailBtns}${cashFlowBtn}${mprBtn}
        </footer>` : ""}
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
      btn.addEventListener("click", () => openDetail(btn.dataset.urlKey, btn.dataset.title, btn.dataset.vista));
    });
    scope?.querySelectorAll(".cc-v45-kpi-detail").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.urlKey) openDetail(btn.dataset.urlKey, btn.dataset.title, btn.dataset.vista);
        else if (btn.dataset.area === "resumen_general" || (btn.dataset.area === "ventas" && btn.dataset.kpi === "ventas_netas")) {
          openDetail("resumen_v45", btn.dataset.title, "ventas_netas" === btn.dataset.kpi ? "ventas" : btn.dataset.kpi);
        }
        else if (btn.dataset.area === "inventario") openStockDetail(btn.dataset.kpi, btn.dataset.title);
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
      node.classList.toggle("hidden", ["compras", "inventario", "gestion_contable", "libros_contables"].includes(selectedAreaKey));
    });
    document.querySelectorAll(".cc-account-filter").forEach((node) => {
      node.classList.toggle("hidden", !["gestion_contable", "libros_contables"].includes(selectedAreaKey));
      node.classList.toggle("flex", ["gestion_contable", "libros_contables"].includes(selectedAreaKey));
    });
    document.querySelectorAll(".cc-expense-filter").forEach((node) => {
      node.classList.toggle("hidden", selectedAreaKey !== "gastos");
      node.classList.toggle("flex", selectedAreaKey === "gastos");
    });
    el("cc-custom-comparison")?.classList.toggle("hidden", !CUSTOM_COMPARE_AREAS.has(selectedAreaKey));
    el("cc-incluir-impuestos")?.closest("label")?.classList.toggle("hidden", ["preparacion_pedidos", "compras", "financiero", "gestion_contable", "impositivo", "libros_contables", "logistica", "gastos"].includes(selectedAreaKey));
    el("cc-comparar-anterior")?.closest("label")?.classList.toggle("hidden", ["resumen_general", "preparacion_pedidos", "compras", "financiero", "gestion_contable", "impositivo", "libros_contables", "logistica", "gastos"].includes(selectedAreaKey));
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
    const currentFilters = readFilters();
    if (CUSTOM_COMPARE_AREAS.has(selectedAreaKey) &&
        !!currentFilters.comparacion_inicio !== !!currentFilters.comparacion_fin) {
      showError("Ingresá ambas fechas del período de comparación o dejá las dos vacías.");
      return;
    }
    if (CUSTOM_COMPARE_AREAS.has(selectedAreaKey) && currentFilters.comparacion_inicio &&
        currentFilters.comparacion_inicio > currentFilters.comparacion_fin) {
      showError("La fecha inicial de comparación no puede ser posterior a la final.");
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

  function renderResumenRanking(data, state) {
    const visual = el("cc-v45-visual");
    if (!visual) return;
    const rows = data.filas || [];
    const compare = state.mode === "comparacion";
    const count = RESUMEN_COUNT_KPIS.has(state.vista);
    const format = (value) => count ? fmtNum.format(Number(value || 0)) : fmtMoney.format(Number(value || 0));
    const total = Number(data.total_importe || 0);
    const previous = Number(data.total_anterior || 0);
    const pct = (value) => total ? `${fmtNum.format(Number(value || 0) / total * 100)} %` : "—";
    const mode = el("cc-v45-chart-mode")?.value || "auto";
    const chartMode = compare ? "barras" : mode === "auto"
      ? (rows.filter((row) => Number(row.importe) > 0).length <= 7 ? "torta" : "barras") : mode;
    const top = rows.filter((row) => Number(row.importe) > 0).slice(0, 7);
    const chartCandidates = compare ? rows.filter((row) => Number(row.importe) !== 0 || Number(row.anterior) !== 0) : top;
    const colors = ["#2563eb", "#14b8a6", "#f97316", "#8b5cf6", "#eab308", "#ec4899", "#0ea5e9", "#64748b"];
    let chart = '<p class="text-sm text-slate-500 dark:text-slate-300">Sin valores positivos para graficar.</p>';
    if (top.length && chartMode === "torta") {
      const chartTotal = rows.reduce((sum, row) => sum + Math.max(0, Number(row.importe || 0)), 0);
      const slices = top.map((row) => Number(row.importe || 0));
      const others = Math.max(0, chartTotal - slices.reduce((sum, value) => sum + value, 0));
      if (others) slices.push(others);
      let position = 0;
      const stops = slices.map((value, index) => {
        const start = position;
        position += value / chartTotal * 100;
        return `${colors[index]} ${start.toFixed(2)}% ${position.toFixed(2)}%`;
      });
      chart = `<div class="flex flex-col items-center gap-5 sm:flex-row">
        <div class="aspect-square w-48 shrink-0 rounded-full shadow-inner sm:w-60" role="img" aria-label="Participación de los importes positivos" style="background:conic-gradient(${stops.join(",")})"></div>
        <ul class="min-w-0 space-y-1 text-xs">${top.map((row, index) => `<li class="flex items-center gap-2"><span class="h-3 w-3 shrink-0 rounded-sm" style="background:${colors[index]}"></span><span class="truncate">${escHtml(row.etiqueta)}</span><strong class="tabular-nums">${fmtNum.format(Number(row.importe) / chartTotal * 100)} %</strong></li>`).join("")}${others ? `<li class="flex items-center gap-2"><span class="h-3 w-3 shrink-0 rounded-sm" style="background:${colors[7]}"></span>Otros</li>` : ""}</ul>
      </div>`;
    } else if (chartCandidates.length && ["linea", "area"].includes(chartMode)) {
      const chartRows = chartCandidates.slice(0, 12);
      const amounts = chartRows.map((row) => Number(row.importe || 0));
      const min = Math.min(0, ...amounts);
      const max = Math.max(1, ...amounts);
      const xFor = (index) => 40 + index * 520 / Math.max(1, chartRows.length - 1);
      const yFor = (value) => 170 - (value - min) * 135 / (max - min);
      const points = amounts.map((value, index) => `${xFor(index).toFixed(1)},${yFor(value).toFixed(1)}`).join(" ");
      const baseline = yFor(0).toFixed(1);
      const area = chartMode === "area" ? `<polygon points="40,${baseline} ${points} ${xFor(chartRows.length - 1).toFixed(1)},${baseline}" fill="#2563eb" fill-opacity=".17" />` : "";
      const marks = chartRows.map((row, index) => `<circle cx="${xFor(index).toFixed(1)}" cy="${yFor(amounts[index]).toFixed(1)}" r="3.5" fill="#2563eb"><title>${escHtml(row.etiqueta)}: ${escHtml(format(row.importe))}</title></circle>${index % Math.max(1, Math.ceil(chartRows.length / 5)) === 0 ? `<text x="${xFor(index).toFixed(1)}" y="205" text-anchor="middle" class="cc-chart-axis">${escHtml(String(row.etiqueta).slice(0, 11))}</text>` : ""}`).join("");
      chart = `<svg viewBox="0 0 600 220" role="img" aria-label="${chartMode === "area" ? "Área" : "Línea"} de importes por agrupación" class="w-full">${area}<line x1="40" y1="${baseline}" x2="560" y2="${baseline}" class="cc-chart-zero" /><polyline points="${points}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linejoin="round" />${marks}</svg>`;
    } else if (chartCandidates.length) {
      const chartRows = chartCandidates.slice(0, compare ? 12 : 7);
      const max = Math.max(1, ...chartRows.flatMap((row) => [Math.abs(Number(row.importe || 0)), compare ? Math.abs(Number(row.anterior || 0)) : 0]));
      chart = `<div class="space-y-3">${chartRows.map((row) => `<div class="grid grid-cols-[minmax(5rem,8rem)_1fr] items-center gap-2 text-xs"><span class="truncate" title="${escHtml(row.etiqueta)}">${escHtml(row.etiqueta)}</span><div class="space-y-1"><div class="h-4 rounded-sm bg-blue-600" style="width:${Math.max(1, Math.abs(Number(row.importe || 0)) / max * 100).toFixed(1)}%" title="Actual: ${escHtml(format(row.importe))}"></div>${compare ? `<div class="h-4 rounded-sm bg-violet-600" style="width:${Math.max(1, Math.abs(Number(row.anterior || 0)) / max * 100).toFixed(1)}%" title="Comparación: ${escHtml(format(row.anterior))}"></div>` : ""}</div></div>`).join("")}</div>${compare ? '<p class="mt-3 text-xs text-slate-500"><span class="text-blue-600">■</span> Período 1 &nbsp; <span class="text-violet-600">■</span> Período 2</p>' : ""}`;
    }
    const period = data.periodo ? `${data.periodo.inicio} a ${data.periodo.fin}` : "";
    const compPeriod = data.comparacion ? `${data.comparacion.inicio} a ${data.comparacion.fin}` : "";
    const head = compare
      ? "<th>Descripción</th><th>Período 1</th><th>Período 2</th><th>Variación</th><th>Variación %</th><th>Indicador</th>"
      : "<th>Pos.</th><th>Descripción</th><th>Importe</th><th>% part.</th><th>Cantidad</th>";
    const body = rows.map((row, index) => {
      const direction = Number(row.variacion || 0) > 0 ? "↑ Sube" : Number(row.variacion || 0) < 0 ? "↓ Baja" : "— Estable";
      const color = Number(row.variacion || 0) > 0 ? "text-green-700 dark:text-green-400" : Number(row.variacion || 0) < 0 ? "text-red-700 dark:text-red-400" : "text-slate-500";
      return `<tr class="border-b border-slate-100 dark:border-slate-800">${compare
        ? `<td>${escHtml(row.etiqueta)}</td><td>${format(row.importe)}</td><td>${format(row.anterior)}</td><td>${format(row.variacion)}</td><td>${row.variacion_pct == null ? "Nuevo" : `${fmtNum.format(row.variacion_pct)} %`}</td><td class="${color}">${direction}</td>`
        : `<td>${index + 1}</td><td>${escHtml(row.etiqueta)}</td><td>${format(row.importe)}</td><td>${pct(row.importe)}</td><td>${fmtNum.format(Number(row.cantidad || 0))}</td>`}</tr>`;
    }).join("");
    const totalRow = compare
      ? `<td>Total</td><td>${format(total)}</td><td>${format(previous)}</td><td>${format(total - previous)}</td><td>${previous ? `${fmtNum.format((total - previous) / Math.abs(previous) * 100)} %` : "Nuevo"}</td><td></td>`
      : `<td></td><td>Total general</td><td>${format(total)}</td><td>${total ? "100 %" : "—"}</td><td>${fmtNum.format(Number(data.total_cantidad || 0))}</td>`;
    visual.innerHTML = `<div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
      <section class="min-w-0 rounded-lg border border-slate-200 p-3 dark:border-slate-700"><h3 class="mb-3 text-sm font-semibold">${compare ? "Análisis por períodos" : "Ranking"}</h3>${chart}</section>
      <section class="min-w-0 overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700"><table class="w-full min-w-[34rem] text-xs [&_td]:px-2 [&_td]:py-1.5 [&_th]:px-2 [&_th]:py-2 [&_th]:text-left"><thead class="bg-slate-100 dark:bg-slate-800"><tr>${head}</tr></thead><tbody>${body || '<tr><td colspan="6">Sin datos.</td></tr>'}<tr class="font-bold text-amber-800 dark:text-amber-300">${totalRow}</tr></tbody></table></section>
    </div><p class="mt-3 text-xs text-slate-500 dark:text-slate-300">${escHtml(data.nota || "")}${data.truncado ? " Se muestran hasta 500 posiciones." : ""} Los importes cero o negativos permanecen en la tabla; el gráfico de torta usa sólo valores positivos.</p>`;
    visual.classList.remove("hidden");
    el("cc-detail-table-wrap")?.classList.add("hidden");
    el("cc-detail-cards")?.classList.add("hidden");
    el("cc-v45-pagination")?.classList.add("hidden");
    el("cc-detail-summary").textContent = compare
      ? `Período 1: ${period} · Período 2: ${compPeriod} · Total: ${format(total)}`
      : `${rows.length} posición(es) · Total: ${format(total)}`;
  }

  async function loadGenericV45Detail() {
    const state = genericV45Detail;
    if (!state) return;
    const term = (el("cc-v45-search")?.value || "").trim();
    if (term.length === 1) {
      el("cc-detail-summary").textContent = "Escribí al menos 2 caracteres para buscar.";
      return;
    }
    const extra = { vista: state.vista, limit: "100", offset: String(state.offset) };
    if (state.resumen || state.financeChecks) {
      extra.modo = state.mode;
      if (state.mode !== "documentos") extra.agrupar_por = el("cc-v45-group")?.value || "entidad";
    }
    if (term.length >= 2) extra.busqueda = term;
    const requestId = (state.requestId || 0) + 1;
    state.requestId = requestId;
    el("cc-detail-summary").textContent = "Cargando detalle…";
    el("cc-detail-error")?.classList.add("hidden");
    try {
      const data = await fetchJson(`${state.base}?${buildQuery(extra)}`);
      if (genericV45Detail !== state || state.offset !== Number(extra.offset) || state.requestId !== requestId) return;
      if (data.disponible === false) {
        el("cc-v45-visual")?.classList.add("hidden");
        el("cc-detail-table-wrap")?.classList.remove("hidden");
        renderGenericDetailTable({ filas: [], total_registros: 0 });
        el("cc-detail-summary").textContent = data.motivo === "sin_alcance_territorial"
          ? "Este origen fiscal no tiene sucursal ni punto de venta. Quitá el filtro para consultar sus documentos generales."
          : data.motivo === "saldo_sin_periodo" ? "Este saldo es una foto actual y no tiene comparación entre períodos."
          : "Detalle no disponible para esta empresa.";
        return;
      }
      genericV45DetailData = data;
      if ((state.resumen || state.financeChecks) && state.mode !== "documentos") {
        renderResumenRanking(data, state);
        return;
      }
      el("cc-v45-visual")?.classList.add("hidden");
      el("cc-detail-table-wrap")?.classList.remove("hidden");
      renderGenericDetailTable(data);
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

  function exportGenericV45CurrentPage() {
    if (!genericV45DetailData?.filas?.length || !genericV45Detail) return;
    const rows = genericV45DetailData.filas;
    const keys = Object.keys(rows[0]);
    const csvCell = (value) => {
      let cell = String(value ?? "");
      if (/^[=+\-@]/.test(cell)) cell = `'${cell}`;
      return `"${cell.replace(/"/g, '""')}"`;
    };
    const lines = [keys.map(csvCell).join(";")];
    rows.forEach((row) => lines.push(keys.map((key) => csvCell(row[key])).join(";")));
    const blob = new Blob(["\uFEFF", lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${genericV45Detail.vista}-${readFilters().fecha_inicio}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  async function openDetail(urlKey, title, vista = "") {
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
    if (["resumen_v45", "libros_v45", "gastos_v45", "contable_v45", "impositivo_v45", "logistica_v45", "compras_v45", "preparacion_v45", "financiero_v45"].includes(urlKey) && vista) {
      const resumen = urlKey === "resumen_v45";
      const financeChecks = urlKey === "financiero_v45" && ["cheques_cartera", "cheques_emitidos", "cheques_rechazados"].includes(vista);
      const ranked = resumen || financeChecks;
      genericV45Detail = { base, vista, offset: 0, resumen, financeChecks, mode: ranked ? "ranking" : "documentos" };
      const controls = el("cc-v45-detail-controls");
      controls?.classList.remove("hidden");
      controls?.classList.add("flex");
      if (el("cc-v45-search")) el("cc-v45-search").value = "";
      el("cc-v45-order")?.classList.add("hidden");
      for (const id of ["cc-v45-view", "cc-v45-group", "cc-v45-chart-mode"]) {
        el(id)?.classList.toggle("hidden", !ranked);
      }
      if (ranked) {
        el("cc-v45-view").value = "ranking";
        const group = el("cc-v45-group");
        const scopeDimensions = ["ventas", "cobranzas", "facturas", "compras_netas", "pagos", "presupuestos", "pedidos", "remitos"].includes(vista);
        const globalDimensions = RESUMEN_GLOBAL_KPIS.has(vista);
        const salesGroups = vista === "ventas" ? `<optgroup label="Comercial"><option value="vendedor">Vendedor</option><option value="condicion_venta">Condición de venta</option><option value="usuario">Usuario</option><option value="medio_cobro">Medio de cobro</option><option value="tipo_entrega">Tipo de entrega</option></optgroup><optgroup label="Producto"><option value="marca">Marca</option><option value="articulo">Artículo</option><option value="proveedor_habitual">Proveedor habitual</option><option value="rubro">Rubro</option><option value="subrubro">Subrubro</option><option value="categoria">Categoría</option><option value="actividad_iibb">Actividad IIBB (RPT)</option></optgroup><optgroup label="Territorio"><option value="zona">Zona</option><option value="provincia">Provincia</option><option value="departamento">Departamento</option><option value="distrito">Distrito</option><option value="jurisdiccion_iibb">Jurisdicción IIBB</option></optgroup>` : "";
        const purchaseGroups = vista === "compras_netas" ? '<optgroup label="Producto"><option value="articulo">Artículo</option><option value="marca">Marca</option><option value="rubro">Rubro</option><option value="subrubro">Subrubro</option><option value="categoria">Categoría</option></optgroup>' : "";
        group.innerHTML = financeChecks
          ? `<option value="entidad">${vista === "cheques_emitidos" ? "Proveedor" : "Cliente / librador"}</option><option value="banco">Banco</option><option value="fecha">Fecha de cobro o pago</option><option value="vencimiento">Rango de vencimiento</option>${vista === "cheques_rechazados" ? '<option value="tipo">Tercero / propio</option>' : ""}`
          : `<option value="entidad">${["compras_netas", "pagos", "compra_cuenta_corriente", "vencimiento_pagar"].includes(vista) ? "Proveedor" : "Cliente / entidad"}</option>${salesGroups}${purchaseGroups}${globalDimensions ? "" : '<option value="fecha">Fecha</option>'}<option value="tipo">Tipo de comprobante</option>${scopeDimensions ? '<option value="sucursal">Sucursal</option><option value="punto_venta">Punto de venta</option>' : ""}`;
        group.value = resumen && vista === "ventas" ? "vendedor" : vista === "cheques_rechazados" ? "tipo" : "entidad";
        el("cc-v45-chart-mode").value = "auto";
        el("cc-v45-view").querySelector('option[value="comparacion"]').hidden = financeChecks || RESUMEN_GLOBAL_KPIS.has(vista);
      }
      void loadGenericV45Detail();
      return;
    }
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
      applyScopeFromStorage();
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
    el("cc-grupo-contable")?.addEventListener("change", onFilterChange);
    el("cc-gastos-fuente")?.addEventListener("change", onFilterChange);
    el("cc-comparacion-inicio")?.addEventListener("change", onFilterChange);
    el("cc-comparacion-fin")?.addEventListener("change", onFilterChange);
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
    el("cc-refresh-interval")?.addEventListener("change", scheduleAutoRefresh);
    scheduleAutoRefresh();
    el("cc-detail-close")?.addEventListener("click", () => openModal(false));
    el("cc-v45-search")?.addEventListener("input", () => {
      if (comercialSearchTimer) clearTimeout(comercialSearchTimer);
      if (!comercialDetail && !stockDetail && !genericV45Detail) return;
      if (comercialDetail) comercialDetail.offset = 0;
      if (stockDetail) stockDetail.offset = 0;
      if (genericV45Detail) genericV45Detail.offset = 0;
      comercialSearchTimer = setTimeout(() => void (genericV45Detail ? loadGenericV45Detail() : stockDetail ? loadStockDetail() : loadComercialDetail()), 300);
    });
    el("cc-v45-view")?.addEventListener("change", () => {
      if (!genericV45Detail?.resumen && !genericV45Detail?.financeChecks) return;
      genericV45Detail.mode = el("cc-v45-view").value;
      genericV45Detail.offset = 0;
      const ranking = genericV45Detail.mode !== "documentos";
      el("cc-v45-group")?.classList.toggle("hidden", !ranking);
      el("cc-v45-chart-mode")?.classList.toggle("hidden", !ranking);
      void loadGenericV45Detail();
    });
    el("cc-v45-group")?.addEventListener("change", () => {
      if ((genericV45Detail?.resumen || genericV45Detail?.financeChecks) && genericV45Detail.mode !== "documentos") void loadGenericV45Detail();
    });
    el("cc-v45-chart-mode")?.addEventListener("change", () => {
      if ((genericV45Detail?.resumen || genericV45Detail?.financeChecks) && genericV45Detail.mode !== "documentos" && genericV45DetailData) {
        renderResumenRanking(genericV45DetailData, genericV45Detail);
      }
    });
    el("cc-v45-order")?.addEventListener("change", () => {
      if (!comercialDetail && !stockDetail) return;
      if (comercialDetail) comercialDetail.offset = 0;
      if (stockDetail) stockDetail.offset = 0;
      void (stockDetail ? loadStockDetail() : loadComercialDetail());
    });
    el("cc-v45-prev")?.addEventListener("click", () => {
      const state = stockDetail || comercialDetail || genericV45Detail;
      if (!state) return;
      state.offset = Math.max(0, state.offset - 100);
      void (genericV45Detail ? loadGenericV45Detail() : stockDetail ? loadStockDetail() : loadComercialDetail());
    });
    el("cc-v45-next")?.addEventListener("click", () => {
      const state = stockDetail || comercialDetail || genericV45Detail;
      if (!state) return;
      state.offset += 100;
      void (genericV45Detail ? loadGenericV45Detail() : stockDetail ? loadStockDetail() : loadComercialDetail());
    });
    el("cc-v45-export")?.addEventListener("click", () => {
      if (stockDetail) exportStockCurrentPage();
      else if (genericV45Detail) exportGenericV45CurrentPage();
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
