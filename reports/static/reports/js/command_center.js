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
  let existenciasAbort = null;
  let existenciasDebounce = null;
  let existenciasSearchBound = false;

  function clearDetailContent() {
    const summaryEl = el("cc-detail-summary");
    if (summaryEl) summaryEl.textContent = "";
    const thead = el("cc-detail-thead");
    const tbody = el("cc-detail-tbody");
    if (thead) thead.innerHTML = "";
    if (tbody) tbody.innerHTML = "";
    const cards = el("cc-detail-cards");
    const tableWrap = el("cc-detail-table-wrap");
    if (cards) {
      cards.innerHTML = "";
      cards.classList.add("hidden");
    }
    if (tableWrap) tableWrap.classList.remove("hidden");
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
    const total = data.total_registros ?? 0;
    let sumTxt = `${total} registro(s)`;
    if (data.total_monto != null) sumTxt += ` · Total ${fmtMoney.format(data.total_monto)}`;
    const summaryEl = el("cc-detail-summary");
    if (summaryEl) {
      summaryEl.textContent = sumTxt;
      if (total > 0 && window.matchMedia("(max-width: 640px)").matches) {
        summaryEl.textContent += " · Deslizá horizontalmente para ver todas las columnas.";
      }
    }

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
      "<tr>" + keys.map((k) => `<th class="px-2 py-2">${k.replace(/_/g, " ")}</th>`).join("") + "</tr>";
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
              return `<td class="px-2 py-1.5 whitespace-nowrap">${v ?? ""}</td>`;
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

  function firstDayOfMonth(iso) {
    const p = String(iso).slice(0, 10).split("-");
    return `${p[0]}-${p[1]}-01`;
  }

  function readFilters() {
    const fecha = el("cc-fecha")?.value || todayIso();
    let fi = el("cc-fecha-inicio")?.value || firstDayOfMonth(fecha);
    let ff = el("cc-fecha-fin")?.value || fecha;
    const suc = el("cc-sucursal")?.value || "";
    return { fecha, fecha_inicio: fi, fecha_fin: ff, sucursal: suc };
  }

  function buildQuery(extra) {
    const f = readFilters();
    const q = new URLSearchParams({
      fecha: f.fecha,
      fecha_inicio: f.fecha_inicio,
      fecha_fin: f.fecha_fin,
      ...(extra || {}),
    });
    if (f.sucursal) q.set("sucursal", f.sucursal);
    return q.toString();
  }

  let waitModalLocks = 0;

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

  function showWaitModal(kind) {
    const modal = el("cc-wait-modal");
    if (!modal) return;
    waitModalLocks += 1;
    const labels = WAIT_LABELS[kind] || WAIT_LABELS.dashboard;
    const titleEl = el("cc-wait-title");
    const subEl = el("cc-wait-subtitle");
    if (titleEl) titleEl.textContent = labels.title;
    if (subEl) subEl.textContent = labels.subtitle;
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

  function fillSucursales(list, selected) {
    const sel = el("cc-sucursal");
    if (!sel) return;
    const cur = selected != null && selected !== "" ? String(selected) : sel.value;
    sel.innerHTML = '<option value="">Todas</option>';
    (list || []).forEach((s) => {
      const opt = document.createElement("option");
      opt.value = String(s.id_sucursal);
      opt.textContent = s.nombre_sucursal || `Sucursal ${s.id_sucursal}`;
      sel.appendChild(opt);
    });
    if (cur) sel.value = cur;
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

  function renderGlobalKpis(data, ventasDia) {
    const grid = el("cc-global-kpis");
    if (!grid) return;
    const a = data.areas || {};
    const v = a.ventas || {};
    const inv = a.inventario || {};
    const comp = a.compras || {};
    const mfg = a.manufactura || {};
    const cruz = a.cruzados || {};
    const vd = ventasDia?.kpis || {};

    const cards = [
      kpiCard("Ventas netas (día)", fmtMoney.format(vd.ventas_netas_dia || 0), "sky"),
      kpiCard("Total operativo (período)", fmtMoney.format(v.total_operativo || 0), "indigo"),
      kpiCard("Valor stock", fmtMoney.format(inv.valor_stock || 0), "emerald"),
      kpiCard("OC pendientes", fmtNum.format(comp.oc_pendientes_cantidad || 0), "amber"),
      kpiCard("OPT atrasadas", fmtNum.format(mfg.opt_atrasadas || 0), "purple"),
      kpiCard("Backorder", fmtMoney.format(cruz.backorder_importe || 0), "rose"),
    ];
    grid.innerHTML = cards.join("");
    Array.from(grid.querySelectorAll(".cc-card-animate")).forEach((node, i) => {
      node.style.animationDelay = `${i * 0.05}s`;
    });
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
        const notaBanco =
          a.banco_disponible === false
            ? [["Nota", "Sin datos bancarios (P1)"]]
            : [];
        return [
          ["Saldo inicial", fmtMoney.format(a.saldo_inicial || 0)],
          ["Saldo final", fmtMoney.format(a.saldo_final || 0)],
          ["Variación neta", fmtMoney.format(a.variacion_neta || 0)],
          ["Ingresos ventas", fmtMoney.format(a.ingresos_ventas || 0)],
          ["Ingresos cobranzas", fmtMoney.format(a.ingresos_cobranzas || 0)],
          ["Egresos proveedores", fmtMoney.format(a.egresos_proveedores || 0)],
          ...notaBanco,
        ];
      },
      details: [],
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
      details: [],
    },
  ];

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
      const rows = def.metrics(areaData || {})
        .map(
          ([k, val]) => `
        <div class="flex items-start justify-between gap-3 border-b border-slate-100 py-2.5 last:border-0 dark:border-slate-800">
          <span class="min-w-0 shrink text-sm text-slate-500 dark:text-slate-400">${k}</span>
          <span class="shrink-0 text-right text-sm font-semibold tabular-nums text-slate-900 dark:text-white">${val}</span>
        </div>`
        )
        .join("");
      body = `<div class="space-y-0">${rows}</div>`;
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

    const mprBtn = def.linkMpr && cfg.mprTableroUrl
      ? `<a href="${cfg.mprTableroUrl}" class="inline-flex min-h-10 w-full items-center justify-center rounded-lg border border-purple-300 bg-purple-50 px-2.5 py-2 text-[11px] font-medium text-purple-800 hover:bg-purple-100 dark:border-purple-700 dark:bg-purple-950/50 dark:text-purple-200 sm:w-auto sm:py-1">Tablero MPR</a>`
      : "";

    return `
      <article class="cc-card-animate flex min-w-0 flex-col overflow-hidden rounded-2xl border ${borderColor} bg-white shadow-md dark:bg-slate-900" style="animation-delay:${delayIdx * 0.06}s">
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
          ${def.key === "ventas" ? `<a href="${cfg.executiveSalesPageUrl || "#"}" class="inline-flex min-h-10 w-full items-center justify-center rounded-lg bg-sky-600 px-2.5 py-2 text-[11px] font-medium text-white hover:bg-sky-500 sm:w-auto sm:py-1">Panel del día</a>` : ""}
          ${mprBtn}
        </footer>
      </article>`;
  }

  function renderAreas(data) {
    const grid = el("cc-areas-grid");
    if (!grid) return;
    const areas = data.areas || {};
    grid.innerHTML = AREA_DEFS.map((def, i) => areaCard(def, areas[def.key], i)).join("");
    grid.querySelectorAll(".cc-detail-btn").forEach((btn) => {
      btn.addEventListener("click", () => openDetail(btn.dataset.urlKey, btn.dataset.title));
    });
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

  async function loadDashboard() {
    if (!cfg.dashboardUrl) return;
    setLoading(true);
    showError("");
    try {
      const q = buildQuery();
      const data = await fetchJson(`${cfg.dashboardUrl}?${q}`);
      fillSucursales(data.sucursales_disponibles, data.meta?.cod_sucursal_filtro);
      const periodo = data.periodo || {};
      const lbl = el("cc-periodo-label");
      if (lbl) {
        lbl.textContent = `Período: ${isoToDisplay(periodo.inicio)} — ${isoToDisplay(periodo.fin)}`;
      }
      let ventasDia = null;
      if (cfg.executiveSummaryUrl) {
        try {
          ventasDia = await fetchJson(`${cfg.executiveSummaryUrl}?fecha=${readFilters().fecha}`);
        } catch (e) {
          console.warn("Resumen ventas del día:", e);
        }
      }
      renderGlobalKpis(data, ventasDia);
      renderAreas(data);
    } catch (e) {
      showError(e.message || "No se pudo cargar el Command Center.");
    } finally {
      setLoading(false);
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

  async function openDetail(urlKey, title) {
    const base = (cfg.detailUrls || {})[urlKey];
    if (!base) return;
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
        renderGenericDetailTable(data);
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
    const t = todayIso();
    const fi = el("cc-fecha-inicio");
    const ff = el("cc-fecha-fin");
    const f = el("cc-fecha");
    if (f && !f.value) f.value = t;
    if (fi && !fi.value) fi.value = firstDayOfMonth(t);
    if (ff && !ff.value) ff.value = t;
    if (f) {
      f.addEventListener("change", () => {
        if (!fi || !ff) return;
        if (!fi.dataset.touched) fi.value = firstDayOfMonth(f.value);
        if (!ff.dataset.touched) ff.value = f.value;
      });
    }
    if (fi) fi.addEventListener("change", () => { fi.dataset.touched = "1"; });
    if (ff) ff.addEventListener("change", () => { ff.dataset.touched = "1"; });
  }

  function bind() {
    el("cc-refresh")?.addEventListener("click", loadDashboard);
    el("cc-detail-close")?.addEventListener("click", () => openModal(false));
    el("cc-detail-modal")?.addEventListener("click", (ev) => {
      if (ev.target === el("cc-detail-modal")) openModal(false);
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") openModal(false);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initDates();
    bind();
    loadDashboard();
  });
})();
