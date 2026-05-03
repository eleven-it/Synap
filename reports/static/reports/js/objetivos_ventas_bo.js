/**
 * Informe Objetivos de venta vs facturación, remitos y BO (jerarquía vendedor → cliente → rubro → subrubro → artículo).
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";

  if (reportSlug !== "ventas-objetivos-vs-bo") {
    return;
  }

  /** Último dataset para expandir/contraer todo sin nueva petición. */
  let _lastJerarquia = null;
  let _lastTotals = null;
  let _searchDebounceTimer = null;

  const ARS = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const NUM = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

  const VIEW_STATE_KEY = `synap:report-view:${reportSlug}:jerarquia`;

  function loadViewState() {
    try {
      const raw = window.localStorage.getItem(VIEW_STATE_KEY);
      if (!raw) return { expandedVendors: {}, expandedNodes: {} };
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed !== "object") return { expandedVendors: {}, expandedNodes: {} };
      return {
        expandedVendors:
          parsed.expandedVendors && typeof parsed.expandedVendors === "object"
            ? parsed.expandedVendors
            : {},
        expandedNodes:
          parsed.expandedNodes && typeof parsed.expandedNodes === "object" ? parsed.expandedNodes : {},
      };
    } catch (e) {
      return { expandedVendors: {}, expandedNodes: {} };
    }
  }

  function saveViewState(state) {
    try {
      window.localStorage.setItem(
        VIEW_STATE_KEY,
        JSON.stringify({
          expandedVendors: state.expandedVendors || {},
          expandedNodes: state.expandedNodes || {},
        })
      );
    } catch (e) {
      // sin localStorage
    }
  }

  function isExpanded(viewState, key) {
    return Boolean(viewState?.expandedNodes?.[key]);
  }

  function isVendorExpanded(viewState, codViajante) {
    return Boolean(viewState?.expandedVendors?.[String(codViajante || "")]);
  }

  /**
   * Con compra / Sin compra bajo un vendedor: por defecto colapsados la primera vez (sin clave en localStorage);
   * si el usuario ya abrió o cerró el bloque, respeta `expandedNodes[estadoKey]`.
   */
  function isEstadoCompraExpanded(viewState, estadoKey) {
    const raw = viewState?.expandedNodes?.[estadoKey];
    if (raw === undefined) return false;
    return Boolean(raw);
  }

  /**
   * Tras expandir un vendedor, reaplica visibilidad de filas bajo Con compra / Sin compra.
   */
  function refreshEstadoChildrenVisibility(container, vendorGroupEsc) {
    const st = loadViewState();
    container.querySelectorAll(`tr[data-vo-estado-head="1"][data-vo-vendor-group="${vendorGroupEsc}"]`).forEach(function (estRow) {
      const ek = estRow.getAttribute("data-vo-estado-key");
      if (!ek) return;
      const open = isEstadoCompraExpanded(st, ek);
      container.querySelectorAll(`tr[data-parent="${escSel(ek)}"]`).forEach(function (childRow) {
        childRow.classList.toggle("hidden", !open);
        const cid = childRow.getAttribute("data-vo-client");
        if (!open && cid) {
          container.querySelectorAll(`tr[data-vo-under-client="${escSel(cid)}"]`).forEach(function (sub) {
            sub.classList.add("hidden");
          });
        }
        if (open && cid) {
          applyClientDetalleVisibility(container, cid, isExpanded(st, "c-" + cid), st);
        }
      });
      const chev = estRow.querySelector(`[data-vo-chev="${escSel(ek)}"]`);
      if (chev) {
        chev.textContent = open ? CHV.expandido : CHV.colapsado;
        chev.setAttribute("aria-expanded", open ? "true" : "false");
      }
    });
  }

  function escSel(s) {
    const g = String(s || "");
    if (typeof CSS !== "undefined" && CSS.escape) return CSS.escape(g);
    return g.replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  function escHtml(s) {
    if (s == null || s === undefined) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Nombre visible + contador (n) entre paréntesis: el número va en gris y tipografía ligeramente menor
   * para diferenciarlo del nombre; contraste usable en modo claro y oscuro (WCAG orientativo).
   */
  function nombreJerarquiaConContadorHtml(nombreBase, count) {
    const n = fmtNum(count != null && count !== "" ? count : 0);
    const base = escHtml(String(nombreBase || "").trim() || "—");
    return (
      base +
      '<span class="vo-jerarquia-contador ms-0.5 inline-block align-baseline text-[0.8125rem] leading-tight font-normal tabular-nums text-slate-600 dark:text-slate-400" translate="no">(' +
      escHtml(n) +
      ")</span>"
    );
  }

  function fmtMoney(v) {
    const n = Number(v);
    if (v == null || v === "" || Number.isNaN(n)) return ARS.format(0);
    return ARS.format(n);
  }

  function fmtNum(v) {
    const n = Number(v);
    if (v == null || v === "" || Number.isNaN(n)) return "0";
    return NUM.format(n);
  }

  /** Negativos en rojo legible; `!` evita que `text-slate-700` de `tdNum` pise el color en el bundle CSS. */
  const tdNeg = "!text-red-600 dark:!text-red-400 font-semibold";

  /** Valor crudo del backend: objetivo − facturación − remitos − pedidos en armado. */
  function faltaValorVisual(faltaRaw) {
    const n = Number(faltaRaw);
    if (!Number.isFinite(n)) return NaN;
    const inverted = -n;
    /** `-0` formatea como moneda negativa; unificar a +0 cuando la magnitud es cero. */
    return inverted === 0 ? 0 : inverted;
  }

  /** Colores según el valor mostrado: negativo = aún falta cumplir; positivo = superado el objetivo. */
  function faltaClassVisual(faltaMostrada) {
    const n = Number(faltaMostrada);
    if (!Number.isNaN(n) && n < 0) return " " + tdNeg;
    if (!Number.isNaN(n) && n > 0)
      return " !text-emerald-700 dark:!text-emerald-300 font-semibold";
    return "";
  }

  /** Tarjeta KPI «brecha»: borde y fondo según pendiente (rojo) vs alcanzado/superado (verde). */
  const kpiFaltaCardNeutral =
    "rounded-2xl border border-slate-100 bg-white p-6 text-left shadow-lg shadow-slate-900/5 transition-colors dark:border-slate-800 dark:bg-slate-950 dark:shadow-black/20";
  const kpiFaltaCardPendiente =
    "rounded-2xl border border-red-200 bg-red-50/80 p-6 text-left shadow-lg shadow-red-900/10 transition-colors dark:border-red-900/55 dark:bg-red-950/35 dark:shadow-black/20";
  const kpiFaltaCardOk =
    "rounded-2xl border border-emerald-200 bg-emerald-50/70 p-6 text-left shadow-lg shadow-emerald-900/10 transition-colors dark:border-emerald-900/45 dark:bg-emerald-950/35 dark:shadow-black/20";

  /** Cabeceras / celdas: Objetivo verde suave, Falta rojo suave; grupo ventas+remitos+total; BO con total al final más oscuro. */
  const thObj = "bg-emerald-100 text-emerald-950 dark:bg-emerald-950/50 dark:text-emerald-100";
  const thFaltaHdr = "bg-rose-100 text-rose-950 dark:bg-rose-950/50 dark:text-rose-100";
  const thGrpVentas = "border-b border-l border-violet-200 bg-violet-100 text-violet-950 dark:border-violet-800 dark:bg-violet-950/40 dark:text-violet-100";
  const thGrpVentasSub =
    "border-b border-violet-200 bg-violet-50 text-violet-900 dark:border-violet-800 dark:bg-violet-950/30 dark:text-violet-100";
  const thTot = "border-b border-l border-violet-200 bg-violet-200/90 text-violet-950 dark:border-violet-800 dark:bg-violet-900/50 dark:text-violet-50";
  const thBoGrp = "border-b border-l border-sky-200 bg-sky-100 text-sky-950 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-100";
  const thSubBo = "border-b border-l border-sky-200 bg-sky-50 px-2 py-1.5 text-right text-[10px] font-bold uppercase tracking-wide text-sky-950 dark:border-sky-800 dark:bg-sky-900/40 dark:text-sky-100 align-bottom";
  const thSubBoPlain =
    "border-b border-sky-200 bg-sky-50 px-2 py-1.5 text-right text-[10px] font-bold uppercase tracking-wide text-sky-950 dark:bg-sky-900/40 dark:text-sky-100 align-bottom";
  const thSubBoTotal =
    "border-b border-sky-200 bg-sky-200/90 px-2 py-1.5 text-right text-[10px] font-bold uppercase tracking-wide text-sky-950 dark:bg-sky-950 dark:text-sky-50 align-bottom";

  const tdObj = "bg-emerald-50/90 dark:bg-emerald-950/25";
  const tdFaltaBody = "bg-rose-50/90 dark:bg-rose-950/25";
  const tdGrpV = "border-l border-violet-200 bg-violet-50/75 dark:border-violet-800/50 dark:bg-violet-950/20";
  const tdGrpVStrong = "border-l border-violet-200 bg-violet-100/80 dark:border-violet-800 dark:bg-violet-950/35";
  const tdBo = "border-l border-sky-200 bg-sky-50 dark:border-sky-800 dark:bg-sky-950/45";
  const tdBoPlain = "bg-sky-50 dark:bg-sky-950/45";
  const tdBoTotal = "bg-sky-100/90 dark:bg-sky-950/65";

  /** ▸ colapsado, ▾ expandido (mismo criterio que tree / categoría en referencia de diseño). */
  const CHV = { colapsado: "▸", expandido: "▾" };

  /** Tabulación: la flecha se desplaza a la derecha en cada nivel (px desde el borde izquierdo de la celda). */
  const TREE_INDENT_BASE = 6;
  const TREE_INDENT_STEP = 15;
  function treeIndentPx(nivel) {
    return TREE_INDENT_BASE + nivel * TREE_INDENT_STEP;
  }

  /**
   * Una sola columna de jerarquía: indentación + chevron pegado al nombre (sin columna ancha vacía).
   * chevHtml === null: sin hueco de icono (fila Totales).
   */
  function treeNombreCell(indentPx, chevHtml, tdClass, nameHtml) {
    const leftSlot =
      chevHtml === null
        ? ""
        : `<span class="flex shrink-0 items-center justify-start leading-none">${chevHtml || '<span class="inline-block w-4 shrink-0" aria-hidden="true"></span>'}</span>`;
    const gapClass = chevHtml === null ? "gap-0" : "gap-1";
    return (
      `<td class="vo-tree-nombre py-2 pr-2 align-middle ${tdClass}" style="padding-left:${indentPx}px">` +
      `<div class="flex min-w-0 items-center ${gapClass}">${leftSlot}<span class="min-w-0 flex-1 text-left">${nameHtml}</span></div></td>`
    );
  }

  /** Solo rubro/subrubro: vendedor, cliente y artículo se leen por indentación y chevron. */
  function etiquetaJerarquia(nivel) {
    const labels = { 2: "Rubro", 3: "Subrubro" };
    const t = labels[nivel];
    if (!t) return "";
    return `<span class="text-[10px] text-slate-400 dark:text-slate-500 font-normal uppercase tracking-tight mr-1.5 whitespace-nowrap">${t}</span>`;
  }

  /** Sin estilo de “botón” del SO al enfocar (▸/▾ solo texto). */
  const CLS_CHEV_BTN =
    "vo-chev inline-flex w-4 shrink-0 cursor-pointer select-none items-center justify-center border-0 bg-transparent p-0 text-sm leading-none text-slate-600 shadow-none [appearance:none] outline-none focus-visible:ring-2 focus-visible:ring-slate-500/35 focus-visible:ring-offset-1 dark:text-slate-400 dark:focus-visible:ring-slate-400/35 rounded-sm";
  const CLS_CHEV_VEND =
    "vo-vend-chev inline-flex w-4 shrink-0 select-none items-center justify-center border-0 bg-transparent p-0 text-sm leading-none text-slate-600 shadow-none [appearance:none] outline-none rounded-sm dark:text-slate-400";

  function treeToggleHtml(gid, expanded) {
    return (
      `<span class="${CLS_CHEV_BTN}" data-vo-chev="${escHtml(gid)}" role="button" tabindex="0" aria-expanded="${expanded ? "true" : "false"}">${expanded ? CHV.expandido : CHV.colapsado}</span>`
    );
  }

  function treeToggleVendorHtml(gid, expanded) {
    return (
      `<span class="${CLS_CHEV_VEND}" data-chev="${escHtml(gid)}" aria-hidden="true">${expanded ? CHV.expandido : CHV.colapsado}</span>`
    );
  }

  function treeSpacerHtml() {
    return '<span class="inline-flex w-4 shrink-0" aria-hidden="true"></span>';
  }

  function dashCell(extraCls) {
    const x = extraCls ? " " + extraCls : "";
    return `<td class="px-2 py-2 text-right text-xs text-slate-400 dark:text-slate-600${x}">—</td>`;
  }

  const tdNum = "px-2 py-2 text-right text-xs tabular-nums whitespace-nowrap text-slate-700 dark:text-slate-300";

  function negMoneyClass(v) {
    const n = Number(v);
    return Number.isFinite(n) && n < 0 ? " " + tdNeg : "";
  }

  function negNumClass(v) {
    const n = Number(v);
    return Number.isFinite(n) && n < 0 ? " " + tdNeg : "";
  }

  /** Fila con todas las métricas (vendedor / cliente / totales). Orden: … Remitos, Pedidos en armado, Total consolidado, BO … */
  function metricCellsFull(row) {
    return (
      `<td class="${tdNum} vo-td-obj ${tdObj}${negMoneyClass(row.objetivo)}">${fmtMoney(row.objetivo)}</td>` +
      `<td class="${tdNum} vo-td-falta ${tdFaltaBody}${faltaClassVisual(faltaValorVisual(row.falta))}">${fmtMoney(faltaValorVisual(row.falta))}</td>` +
      `<td class="${tdNum} ${tdGrpV}${negNumClass(row.cantidades_vendidas)}">${fmtNum(row.cantidades_vendidas)}</td>` +
      `<td class="${tdNum} ${tdGrpV}${negMoneyClass(row.facturacion)}">${fmtMoney(row.facturacion)}</td>` +
      `<td class="${tdNum} ${tdGrpV}${negMoneyClass(row.remitos)}">${fmtMoney(row.remitos)}</td>` +
      `<td class="${tdNum} ${tdGrpV}${negMoneyClass(row.pedidos_en_armado)}">${fmtMoney(row.pedidos_en_armado)}</td>` +
      `<td class="${tdNum} ${tdGrpVStrong}${negMoneyClass(row.total)}">${fmtMoney(row.total)}</td>` +
      `<td class="${tdNum} ${tdBo}${negMoneyClass(row.bo_con_stock)}">${fmtMoney(row.bo_con_stock)}</td>` +
      `<td class="${tdNum} ${tdBoPlain}${negMoneyClass(row.bo_con_ingreso)}">${fmtMoney(row.bo_con_ingreso)}</td>` +
      `<td class="${tdNum} ${tdBoPlain}${negMoneyClass(row.bo_sin_stock)}">${fmtMoney(row.bo_sin_stock)}</td>` +
      `<td class="${tdNum} ${tdBoTotal}${negMoneyClass(row.backorder_total)}">${fmtMoney(row.backorder_total)}</td>`
    );
  }

  /** Solo venta: unidades + facturación; resto en — */
  function metricCellsVentaSolo(row) {
    return (
      dashCell(tdObj) +
      dashCell(tdFaltaBody) +
      `<td class="${tdNum} ${tdGrpV}${negNumClass(row.cantidades_vendidas)}">${fmtNum(row.cantidades_vendidas)}</td>` +
      `<td class="${tdNum} ${tdGrpV}${negMoneyClass(row.facturacion)}">${fmtMoney(row.facturacion)}</td>` +
      dashCell(tdGrpV) +
      dashCell(tdGrpV) +
      dashCell(tdGrpVStrong) +
      dashCell(tdBo) +
      dashCell(tdBoPlain) +
      dashCell(tdBoPlain) +
      dashCell(tdBoTotal)
    );
  }

  /**
   * Rubro / subrubro / artículo: unidades, facturación y BO agregados.
   * Remitos y pedidos en armado por línea (remitos_lineas / pedidos_armado_lineas) si el backend los envía; si no, —.
   * Total consolidado sigue solo a nivel cliente.
   */
  function metricCellsVentaJerarquiaSinRemitosCabecera(row) {
    const bt = Number(row.backorder_total);
    const bs = Number(row.bo_con_stock);
    const bi = Number(row.bo_con_ingreso);
    const bn = Number(row.bo_sin_stock);
    const remL = Number(row.remitos_lineas);
    const pedL = Number(row.pedidos_armado_lineas);
    const remCell =
      Number.isFinite(remL) && Math.abs(remL) > 1e-9
        ? `<td class="${tdNum} ${tdGrpV}${negMoneyClass(remL)}">${fmtMoney(remL)}</td>`
        : dashCell(tdGrpV);
    const pedCell =
      Number.isFinite(pedL) && Math.abs(pedL) > 1e-9
        ? `<td class="${tdNum} ${tdGrpV}${negMoneyClass(pedL)}">${fmtMoney(pedL)}</td>`
        : dashCell(tdGrpV);
    return (
      dashCell(tdObj) +
      dashCell(tdFaltaBody) +
      `<td class="${tdNum} ${tdGrpV}${negNumClass(row.cantidades_vendidas)}">${fmtNum(row.cantidades_vendidas)}</td>` +
      `<td class="${tdNum} ${tdGrpV}${negMoneyClass(row.facturacion)}">${fmtMoney(row.facturacion)}</td>` +
      remCell +
      pedCell +
      dashCell(tdGrpVStrong) +
      `<td class="${tdNum} ${tdBo}${negMoneyClass(bs)}">${fmtMoney(bs)}</td>` +
      `<td class="${tdNum} ${tdBoPlain}${negMoneyClass(bi)}">${fmtMoney(bi)}</td>` +
      `<td class="${tdNum} ${tdBoPlain}${negMoneyClass(bn)}">${fmtMoney(bn)}</td>` +
      `<td class="${tdNum} ${tdBoTotal}${negMoneyClass(bt)}">${fmtMoney(bt)}</td>`
    );
  }

  /** En `<svg>`, `className` es de solo lectura (SVGAnimatedString); Tailwind debe ir en `class`. */
  function setSvgOrElementClass(el, cls) {
    if (!el) return;
    if (el.namespaceURI === "http://www.w3.org/2000/svg") {
      el.setAttribute("class", cls);
    } else {
      el.className = cls;
    }
  }

  function renderKpis(totals) {
    const elObj = document.getElementById("vo-kpi-total-objetivo");
    const elFalta = document.getElementById("vo-kpi-total-falta");
    const elFaltaEstado = document.getElementById("vo-kpi-total-falta-estado");
    const elFaltaCard = document.getElementById("vo-kpi-card-falta");
    const elFaltaIcon = document.getElementById("vo-kpi-falta-icon");
    if (!elObj || !elFalta || !elFaltaEstado || !elFaltaCard) return;

    const t = totals && typeof totals === "object" ? totals : {};
    const obj = Number(t.objetivo);
    const fal = Number(t.falta);
    const objN = Number.isFinite(obj) ? obj : 0;
    const falN = Number.isFinite(fal) ? fal : NaN;

    elObj.textContent = fmtMoney(objN);
    elObj.className =
      "text-2xl md:text-3xl font-bold tabular-nums " +
      (Number.isFinite(objN) && objN < 0 ? "text-red-600 dark:text-red-400" : "text-slate-900 dark:text-white");

    const valorClsBase = "text-2xl md:text-3xl font-bold tabular-nums ";
    const estadoBase = "mt-2 text-sm font-semibold leading-snug ";

    if (!Number.isFinite(falN)) {
      elFalta.textContent = "—";
      elFalta.className = valorClsBase + "text-slate-500 dark:text-slate-400";
      elFaltaEstado.textContent = "Estado: sin dato de brecha para el período actual.";
      elFaltaEstado.className = estadoBase + "text-slate-600 dark:text-slate-400";
      elFaltaEstado.classList.remove("hidden");
      elFaltaCard.className = kpiFaltaCardNeutral;
      setSvgOrElementClass(elFaltaIcon, "w-5 h-5 text-slate-400 opacity-80");
      return;
    }

    const falVis = faltaValorVisual(falN);
    elFalta.textContent = fmtMoney(falVis);
    elFaltaEstado.classList.remove("hidden");

    if (falN > 0) {
      elFalta.className = valorClsBase + "text-red-600 dark:text-red-400";
      elFaltaEstado.textContent =
        "Estado: pendiente. La suma de objetivos aún supera a facturación, remitos y pedidos en armado; en la columna FALTA se muestra la brecha en negativo (importe por cubrir).";
      elFaltaEstado.className = estadoBase + "text-red-800 dark:text-red-200";
      elFaltaCard.className = kpiFaltaCardPendiente;
      setSvgOrElementClass(elFaltaIcon, "w-5 h-5 text-red-600 opacity-90 dark:text-red-400");
    } else {
      elFalta.className = valorClsBase + "text-emerald-700 dark:text-emerald-300";
      if (falN < 0) {
        elFaltaEstado.textContent =
          "Estado: objetivo superado. Facturación, remitos y pedidos en armado superan la suma de objetivos; en la columna FALTA se muestra el margen en positivo.";
      } else {
        elFaltaEstado.textContent =
          "Estado: objetivo alcanzado. Facturación, remitos y pedidos en armado igualan la suma de objetivos (FALTA $ 0).";
      }
      elFaltaEstado.className = estadoBase + "text-emerald-800 dark:text-emerald-200";
      elFaltaCard.className = kpiFaltaCardOk;
      setSvgOrElementClass(elFaltaIcon, "w-5 h-5 text-emerald-600 opacity-90 dark:text-emerald-400");
    }
  }

  function voSearchDataAttr(lowerHaystack) {
    const t = String(lowerHaystack || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
    return ` data-vo-search="${escHtml(t)}"`;
  }

  function applySearchFilter(container, rawQ) {
    const table = container && container.querySelector && container.querySelector(".vo-jerarquia-table");
    if (!table) return;
    const needle = String(rawQ || "")
      .trim()
      .toLowerCase();
    const rows = table.querySelectorAll("tbody tr");
    if (needle.length < 2) {
      const hiddenBySearch = table.querySelectorAll("tbody tr.vo-bo-search-hide");
      hiddenBySearch.forEach(function (r) {
        r.classList.remove("vo-bo-search-hide");
      });
      return;
    }
    rows.forEach(function (r) {
      if (r.getAttribute("data-vo-totales") === "1") {
        r.classList.remove("vo-bo-search-hide");
        return;
      }
      const hay = (r.getAttribute("data-vo-search") || "").toLowerCase();
      r.classList.toggle("vo-bo-search-hide", hay.indexOf(needle) === -1);
    });
    container.querySelectorAll("tr[data-vo-toggle]").forEach(function (vTr) {
      const gid = vTr.getAttribute("data-vo-toggle");
      const selfHay = (vTr.getAttribute("data-vo-search") || "").toLowerCase();
      const selfMatch = selfHay.indexOf(needle) !== -1;
      let anyChild = false;
      if (gid) {
        const gEsc = escSel(gid);
        container.querySelectorAll(`tr[data-vo-vendor-group="${gEsc}"]`).forEach(function (ch) {
          if (!ch.classList.contains("vo-bo-search-hide")) anyChild = true;
        });
      }
      vTr.classList.toggle("vo-bo-search-hide", !selfMatch && !anyChild);
    });
  }

  function applySearchFilterFromInput() {
    const container = document.getElementById("vo-jerarquia-container");
    const inp = document.getElementById("vo-bo-buscar-jerarquia");
    if (!container) return;
    applySearchFilter(container, inp ? inp.value : "");
  }

  /**
   * Tras expandir/colapsar jerarquía: si no hay búsqueda activa (menos de 2 caracteres) y ninguna fila
   * está oculta por búsqueda, no recorrer la tabla (antes se tocaban todas las filas en cada clic).
   * Con búsqueda activa, recalcular cabeceras de vendedor según hijos visibles.
   */
  function applySearchFilterAfterHierarchyToggle(container) {
    if (!container) return;
    const inp = document.getElementById("vo-bo-buscar-jerarquia");
    const needle = String(inp ? inp.value : "")
      .trim()
      .toLowerCase();
    const table = container.querySelector(".vo-jerarquia-table");
    if (!table) return;
    if (needle.length >= 2) {
      applySearchFilter(container, inp ? inp.value : "");
      return;
    }
    if (!table.querySelector("tbody tr.vo-bo-search-hide")) return;
    applySearchFilter(container, inp ? inp.value : "");
  }

  function scheduleSearchFilter() {
    if (_searchDebounceTimer) window.clearTimeout(_searchDebounceTimer);
    _searchDebounceTimer = window.setTimeout(function () {
      _searchDebounceTimer = null;
      applySearchFilterFromInput();
    }, 200);
  }

  function expandAllBo() {
    if (!_lastJerarquia || !_lastJerarquia.length) return;
    const st = { expandedVendors: {}, expandedNodes: {} };
    _lastJerarquia.forEach(function (vend) {
      if (!vend || typeof vend !== "object") return;
      const cv = String(vend.cod_viajante || "");
      st.expandedVendors[cv] = true;
      (vend.children || [])
        .filter(function (estado) {
          return estado != null && typeof estado === "object";
        })
        .forEach(function (estado) {
          const ek = "ec-" + cv + "-" + String(estado.estado_compra || "sin_compra");
          st.expandedNodes[ek] = true;
          (estado.children || [])
            .filter(function (cli) {
              return cli != null && typeof cli === "object";
            })
            .forEach(function (cli) {
              const cid = String(cli.codigo_cliente || "");
              st.expandedNodes["c-" + cid] = true;
              (cli.venta_detalle || []).forEach(function (rub) {
                if (!rub || typeof rub !== "object") return;
                st.expandedNodes["r-" + cid + "-" + String(rub.codigo_rubro)] = true;
                (rub.children || [])
                  .filter(function (sub) {
                    return sub != null && typeof sub === "object";
                  })
                  .forEach(function (sub) {
                    st.expandedNodes["s-" + cid + "-" + String(rub.codigo_rubro) + "-" + String(sub.id_subrubro)] = true;
                  });
              });
          });
        });
    });
    saveViewState(st);
    renderTable(_lastJerarquia, _lastTotals);
  }

  function collapseAllBo() {
    if (!_lastJerarquia || !_lastJerarquia.length) return;
    saveViewState({ expandedVendors: {}, expandedNodes: {} });
    renderTable(_lastJerarquia, _lastTotals);
  }

  function wireBoToolbarOnce() {
    const btnExp = document.getElementById("vo-bo-btn-expandir-todos");
    const btnCont = document.getElementById("vo-bo-btn-contraer-todos");
    const inp = document.getElementById("vo-bo-buscar-jerarquia");
    if (btnExp && !btnExp.dataset.voBoWired) {
      btnExp.dataset.voBoWired = "1";
      btnExp.addEventListener("click", expandAllBo);
    }
    if (btnCont && !btnCont.dataset.voBoWired) {
      btnCont.dataset.voBoWired = "1";
      btnCont.addEventListener("click", collapseAllBo);
    }
    if (inp && !inp.dataset.voBoWired) {
      inp.dataset.voBoWired = "1";
      inp.addEventListener("input", scheduleSearchFilter);
    }
  }

  function buildThead() {
    const thTree =
      "min-w-[14rem] border-b border-slate-200 px-2 py-2 text-left text-[10px] font-bold uppercase tracking-wide text-slate-600 align-middle dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300";
    const thRs2Base =
      "border-b border-slate-200 px-2 py-2 text-[10px] font-bold uppercase tracking-wide align-middle dark:border-slate-600";
    return (
      '<thead class="sticky top-0 z-10 bg-slate-50 shadow-sm dark:bg-slate-800">' +
      '<tr class="align-bottom">' +
      `<th rowspan="2" scope="col" class="${thTree}">VENDEDOR / CLIENTE / RUBRO</th>` +
      `<th colspan="2" class="${thGrpVentas} px-2 py-1.5 text-center align-bottom">OBJETIVO</th>` +
      `<th colspan="5" class="${thGrpVentas} px-2 py-1.5 text-center align-bottom">VENTAS PERÍODO</th>` +
      `<th colspan="4" class="${thBoGrp} px-2 py-1.5 text-center align-bottom">BACKORDER</th>` +
      "</tr>" +
      "<tr>" +
      `<th class="${thObj} border-l border-emerald-200 px-2 py-1.5 text-right align-bottom">META</th>` +
      `<th class="${thFaltaHdr} px-2 py-1.5 text-right align-bottom">FALTA</th>` +
      `<th class="${thGrpVentasSub} border-l border-violet-200 px-2 py-1.5 text-right align-bottom">UNIDADES</th>` +
      `<th class="${thGrpVentasSub} px-2 py-1.5 text-right align-bottom">FACTURACIÓN</th>` +
      `<th class="${thGrpVentasSub} px-2 py-1.5 text-right align-bottom">REMITOS</th>` +
      `<th class="${thGrpVentasSub} px-2 py-1.5 text-right align-bottom">PEDIDOS EN ARMADO</th>` +
      `<th class="${thTot} px-2 py-1.5 text-right align-bottom">TOTAL</th>` +
      `<th class="${thSubBo}">BO C/STOCK</th>` +
      `<th class="${thSubBoPlain}">BO C/INGRESO</th>` +
      `<th class="${thSubBoPlain}">BO S/STOCK</th>` +
      `<th class="${thSubBoTotal}">BO TOTAL</th>` +
      "</tr>" +
      "</thead>"
    );
  }

  /**
   * Visibilidad de rubro/subrubro/artículo bajo un cliente según localStorage.
   * @param {object} [viewStateOpt] — estado ya cargado (evita JSON.parse repetido en bucles).
   */
  function applyClientDetalleVisibility(container, clientId, clientExpanded, viewStateOpt) {
    const cid = String(clientId);
    const cg = "c-" + cid;
    const st = viewStateOpt || loadViewState();
    if (!clientExpanded) {
      container.querySelectorAll(`tr[data-vo-under-client="${escSel(cid)}"]`).forEach(function (r) {
        r.classList.add("hidden");
      });
      return;
    }
    container.querySelectorAll(`tr[data-parent="${escSel(cg)}"]`).forEach(function (r) {
      r.classList.remove("hidden");
    });
    container.querySelectorAll(`tr[data-vo-under-client="${escSel(cid)}"][data-vo-under-rubro]`).forEach(function (r) {
      const rk = r.getAttribute("data-vo-under-rubro");
      if (!rk) return;
      if (!isExpanded(st, rk)) {
        r.classList.add("hidden");
        return;
      }
      const sk = r.getAttribute("data-vo-sub-key");
      if (sk) {
        r.classList.toggle("hidden", !isExpanded(st, sk));
        return;
      }
      const par = r.getAttribute("data-parent");
      if (par && String(par).indexOf("s-") === 0) {
        r.classList.toggle("hidden", !isExpanded(st, par));
      }
    });
  }

  /** Evita forEach sobre string JSON u otro tipo; intenta parsear si viene serializado. */
  function normalizeJerarquiaArray(raw) {
    if (raw == null) return [];
    if (Array.isArray(raw)) return raw;
    if (typeof raw === "string") {
      try {
        const p = JSON.parse(raw);
        return Array.isArray(p) ? p : [];
      } catch (e) {
        return [];
      }
    }
    return [];
  }

  const _METRIC_KEYS_JER = [
    "objetivo",
    "facturacion",
    "remitos",
    "pedidos_en_armado",
    "total",
    "falta",
    "cantidades_vendidas",
    "backorder_total",
    "bo_con_stock",
    "bo_con_ingreso",
    "bo_sin_stock",
  ];

  /** Si `meta.extra.tabs` no trae árbol, reagrupa por vendedor desde `data` plano (sin detalle rubro/subrubro). */
  function buildJerarquiaDesdeFilas(filas) {
    if (!filas || !filas.length) return [];
    const map = new Map();
    for (let i = 0; i < filas.length; i++) {
      const row = filas[i];
      if (!row || typeof row !== "object") continue;
      const cv = Number(row.cod_viajante);
      if (!Number.isFinite(cv) || cv <= 0) continue;
      let g = map.get(cv);
      if (!g) {
        g = {
          cod_viajante: cv,
          nombre_vendedor: row.nombre_vendedor || "Vendedor " + cv,
          children: [],
          objetivo: 0,
          facturacion: 0,
          remitos: 0,
          pedidos_en_armado: 0,
          total: 0,
          falta: 0,
          cantidades_vendidas: 0,
          backorder_total: 0,
          bo_con_stock: 0,
          bo_con_ingreso: 0,
          bo_sin_stock: 0,
        };
        map.set(cv, g);
      }
      const child = Object.assign({}, row, { tipo: "cliente", venta_detalle: row.venta_detalle || [] });
      const estadoKey = Number(row.total || 0) > 0 ? "con_compra" : "sin_compra";
      let estadoNode = (g.children || []).find((n) => n && n.tipo === "estado_compra" && n.estado_compra === estadoKey);
      if (!estadoNode) {
        estadoNode = {
          tipo: "estado_compra",
          estado_compra: estadoKey,
          nombre: estadoKey === "con_compra" ? "Con compra" : "Sin compra",
          children: [],
          objetivo: 0,
          facturacion: 0,
          remitos: 0,
          pedidos_en_armado: 0,
          total: 0,
          falta: 0,
          cantidades_vendidas: 0,
          backorder_total: 0,
          bo_con_stock: 0,
          bo_con_ingreso: 0,
          bo_sin_stock: 0,
          total_clientes: 0,
        };
        g.children.push(estadoNode);
      }
      estadoNode.children.push(child);
      estadoNode.total_clientes += 1;
      for (let k = 0; k < _METRIC_KEYS_JER.length; k++) {
        const key = _METRIC_KEYS_JER[k];
        g[key] = (Number(g[key]) || 0) + Number(row[key] || 0);
        estadoNode[key] = (Number(estadoNode[key]) || 0) + Number(row[key] || 0);
      }
    }
    map.forEach(function (g) {
      g.total_clientes = 0;
      (g.children || []).forEach(function (estado) {
        estado.children.sort(function (a, b) {
          const na = (a.nombre_cliente || "").toString().toUpperCase();
          const nb = (b.nombre_cliente || "").toString().toUpperCase();
          if (na !== nb) return na.localeCompare(nb);
          return (Number(a.codigo_cliente) || 0) - (Number(b.codigo_cliente) || 0);
        });
        g.total_clientes += Number(estado.total_clientes || 0);
      });
    });
    return Array.from(map.values()).sort(function (a, b) {
      const oa = Number(a.objetivo) || 0;
      const ob = Number(b.objetivo) || 0;
      if (oa !== ob) return ob - oa;
      const sa = (a.nombre_vendedor || "").toString().toUpperCase();
      const sb = (b.nombre_vendedor || "").toString().toUpperCase();
      if (sa !== sb) return sa.localeCompare(sb);
      return (Number(a.cod_viajante) || 0) - (Number(b.cod_viajante) || 0);
    });
  }

  function appendVentaDetalle(parts, detalle, vendorGid, parentClientGid, clientId, viewState, vendorExpanded, clientExpanded, searchBase) {
    if (!detalle || !detalle.length) return;
    const cid = String(clientId);
    const vg = escHtml(vendorGid);
    const hideTree = !vendorExpanded || !clientExpanded;
    const rowHover = "vo-child-row hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors";
    const base = String(searchBase || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();

    detalle.forEach((rub) => {
      if (!rub || typeof rub !== "object") return;
      const rg = "r-" + clientId + "-" + String(rub.codigo_rubro);
      const expR = isExpanded(viewState, rg);
      const subHiddenBase = hideTree || !expR;
      const sr = (base + " " + String(rub.nombre_rubro || "")).trim().toLowerCase();
      parts.push(
        `<tr class="${rowHover} ${hideTree ? "hidden" : ""} bg-slate-50 dark:bg-slate-800/40 text-slate-800 dark:text-slate-200"${voSearchDataAttr(sr)} data-vo-vendor-group="${vg}" data-parent="${escHtml(parentClientGid)}" data-vo-under-client="${escHtml(cid)}" data-vo-rubro-key="${escHtml(rg)}">` +
          treeNombreCell(
            treeIndentPx(3),
            treeToggleHtml(rg, expR),
            "text-xs uppercase font-normal tracking-tight",
            `${etiquetaJerarquia(2)}${escHtml(rub.nombre_rubro)}`
          ) +
          metricCellsVentaJerarquiaSinRemitosCabecera(rub) +
          "</tr>"
      );
      (rub.children || [])
        .filter(function (sub) {
          return sub != null && typeof sub === "object";
        })
        .forEach((sub) => {
        const sg = "s-" + clientId + "-" + String(rub.codigo_rubro) + "-" + String(sub.id_subrubro);
        const expS = isExpanded(viewState, sg);
        const hideSub = subHiddenBase || !expS;
        const ss = (sr + " " + String(sub.nombre_subrubro || "")).trim().toLowerCase();
        parts.push(
          `<tr class="${rowHover} ${hideSub ? "hidden" : ""} bg-white dark:bg-slate-900/20"${voSearchDataAttr(ss)} data-vo-vendor-group="${vg}" data-parent="${escHtml(rg)}" data-vo-under-client="${escHtml(cid)}" data-vo-under-rubro="${escHtml(rg)}" data-vo-sub-key="${escHtml(sg)}">` +
            treeNombreCell(
              treeIndentPx(4),
              treeToggleHtml(sg, expS),
              "text-xs uppercase font-normal tracking-tight text-slate-800 dark:text-slate-200",
              `${etiquetaJerarquia(3)}${escHtml(sub.nombre_subrubro)}`
            ) +
            metricCellsVentaJerarquiaSinRemitosCabecera(sub) +
            "</tr>"
        );
        (sub.children || [])
          .filter(function (art) {
            return art != null && typeof art === "object";
          })
          .forEach((art) => {
          const hideArt = hideSub;
          const sa = (ss + " " + String(art.nombre_articulo || "")).trim().toLowerCase();
          parts.push(
            `<tr class="${rowHover} ${hideArt ? "hidden" : ""} bg-white dark:bg-slate-900/10"${voSearchDataAttr(sa)} data-vo-vendor-group="${vg}" data-parent="${escHtml(sg)}" data-vo-under-client="${escHtml(cid)}" data-vo-under-rubro="${escHtml(rg)}">` +
              treeNombreCell(
                treeIndentPx(5),
                treeSpacerHtml(),
                "text-xs font-normal text-slate-700 dark:text-slate-300",
                `${etiquetaJerarquia(4)}${escHtml(art.nombre_articulo)}`
              ) +
              metricCellsVentaJerarquiaSinRemitosCabecera(art) +
              "</tr>"
          );
        });
      });
    });
  }

  function wireNestedToggles(container) {
    container.querySelectorAll("[data-vo-chev]").forEach(function (chev) {
      const gid = chev.getAttribute("data-vo-chev");
      if (!gid) return;
      function toggleFromChev() {
        const st = loadViewState();
        st.expandedNodes = st.expandedNodes || {};
        const direct = container.querySelectorAll(`tr[data-parent="${escSel(gid)}"]`);
        if (!direct.length && String(gid).indexOf("c-") !== 0 && String(gid).indexOf("ec-") !== 0) return;

        if (String(gid).indexOf("ec-") === 0) {
          const wasOpen = isEstadoCompraExpanded(st, gid);
          const open = !wasOpen;
          st.expandedNodes[gid] = open;
          saveViewState(st);
          direct.forEach(function (r) {
            r.classList.toggle("hidden", !open);
            const cid = r.getAttribute("data-vo-client");
            if (!open && cid) {
              container.querySelectorAll(`tr[data-vo-under-client="${escSel(cid)}"]`).forEach(function (sub) {
                sub.classList.add("hidden");
              });
            }
            if (open && cid) {
              applyClientDetalleVisibility(container, cid, isExpanded(st, "c-" + cid), st);
            }
          });
          chev.textContent = open ? CHV.expandido : CHV.colapsado;
          chev.setAttribute("aria-expanded", open ? "true" : "false");
          applySearchFilterAfterHierarchyToggle(container);
          return;
        }

        if (String(gid).indexOf("c-") === 0) {
          const cid = gid.replace(/^c-/, "");
          const was = isExpanded(st, gid);
          st.expandedNodes[gid] = !was;
          saveViewState(st);
          const nowOpen = Boolean(st.expandedNodes[gid]);
          applyClientDetalleVisibility(container, cid, nowOpen, st);
          chev.textContent = nowOpen ? CHV.expandido : CHV.colapsado;
          chev.setAttribute("aria-expanded", nowOpen ? "true" : "false");
          applySearchFilterAfterHierarchyToggle(container);
          return;
        }

        if (String(gid).indexOf("r-") === 0) {
          const wasR = isExpanded(st, gid);
          st.expandedNodes[gid] = !wasR;
          saveViewState(st);
          const rubOpen = Boolean(st.expandedNodes[gid]);
          direct.forEach(function (r) {
            r.classList.toggle("hidden", !rubOpen);
          });
          if (!rubOpen) {
            direct.forEach(function (r) {
              const sk = r.getAttribute("data-vo-sub-key");
              if (!sk) return;
              container.querySelectorAll(`tr[data-parent="${escSel(sk)}"]`).forEach(function (a) {
                a.classList.add("hidden");
              });
            });
          } else {
            direct.forEach(function (r) {
              const sk = r.getAttribute("data-vo-sub-key");
              if (!sk) return;
              const expS = isExpanded(st, sk);
              container.querySelectorAll(`tr[data-parent="${escSel(sk)}"]`).forEach(function (a) {
                a.classList.toggle("hidden", !expS);
              });
            });
          }
          chev.textContent = rubOpen ? CHV.expandido : CHV.colapsado;
          chev.setAttribute("aria-expanded", rubOpen ? "true" : "false");
          applySearchFilterAfterHierarchyToggle(container);
          return;
        }

        if (String(gid).indexOf("s-") === 0) {
          const wasS = isExpanded(st, gid);
          st.expandedNodes[gid] = !wasS;
          saveViewState(st);
          const subOpen = Boolean(st.expandedNodes[gid]);
          direct.forEach(function (r) {
            r.classList.toggle("hidden", !subOpen);
          });
          chev.textContent = subOpen ? CHV.expandido : CHV.colapsado;
          chev.setAttribute("aria-expanded", subOpen ? "true" : "false");
          applySearchFilterAfterHierarchyToggle(container);
        }
      }
      chev.addEventListener("click", function (e) {
        e.stopPropagation();
        toggleFromChev();
      });
      chev.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          e.stopPropagation();
          toggleFromChev();
        }
      });
    });
  }

  function renderTable(jerarquia, totals) {
    const container = document.getElementById("vo-jerarquia-container");
    if (!container) return;
    const viewState = loadViewState();

    if (!jerarquia || !jerarquia.length) {
      container.innerHTML =
        '<p class="text-xs text-slate-500 dark:text-slate-400">No hay datos para el período y filtros seleccionados.</p>';
      return;
    }

    const parts = ['<tbody class="divide-y divide-slate-200 dark:divide-slate-700">'];
    jerarquia.forEach((vend) => {
      if (!vend || typeof vend !== "object") return;
      const codViajante = String(vend.cod_viajante || "");
      const gid = "vo-grp-v-" + codViajante;
      const expanded = isVendorExpanded(viewState, codViajante);
      const vendSearch = [vend.nombre_vendedor, codViajante]
        .filter(function (x) {
          return x != null && String(x).trim() !== "";
        })
        .join(" ")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
      parts.push(
        `<tr class="bg-slate-100 dark:bg-slate-800/90 cursor-pointer select-none hover:bg-slate-200/90 dark:hover:bg-slate-800"${voSearchDataAttr(vendSearch)} data-vo-toggle="${gid}" data-vo-vendor="${escHtml(codViajante)}" role="button" tabindex="0" aria-expanded="${expanded ? "true" : "false"}">` +
          treeNombreCell(
            treeIndentPx(0),
            treeToggleVendorHtml(gid, expanded),
            "text-xs font-bold uppercase tracking-tight text-slate-900 dark:text-white",
            nombreJerarquiaConContadorHtml(
              vend.nombre_vendedor || "Vendedor " + codViajante,
              vend.total_clientes || 0
            )
          ) +
          metricCellsFull(vend) +
          "</tr>"
      );

      (vend.children || [])
        .filter(function (estado) {
          return estado != null && typeof estado === "object";
        })
        .forEach((estado) => {
          const estadoKey = "ec-" + codViajante + "-" + String(estado.estado_compra || "sin_compra");
          const expEstado = isEstadoCompraExpanded(viewState, estadoKey);
          const estadoNombreHtml = nombreJerarquiaConContadorHtml(
            estado.nombre || "Estado",
            estado.total_clientes || 0
          );
          const estadoSearch = [vend.nombre_vendedor, estado.nombre]
            .filter(function (x) {
              return x != null && String(x).trim() !== "";
            })
            .join(" ")
            .toLowerCase()
            .replace(/\s+/g, " ")
            .trim();
          parts.push(
            `<tr class="vo-child-row ${expanded ? "" : "hidden"} bg-slate-50 dark:bg-slate-900/30"${voSearchDataAttr(estadoSearch)} data-parent="${escHtml(gid)}" data-vo-vendor-group="${escHtml(gid)}" data-vo-estado-head="1" data-vo-estado-key="${escHtml(estadoKey)}">` +
              treeNombreCell(
                treeIndentPx(1),
                treeToggleHtml(estadoKey, expEstado),
                "text-xs uppercase tracking-tight font-normal text-slate-800 dark:text-slate-200",
                estadoNombreHtml
              ) +
              metricCellsFull(estado) +
              "</tr>"
          );

          (estado.children || [])
            .filter(function (cli) {
              return cli != null && typeof cli === "object";
            })
            .forEach((cli) => {
              const cid = String(cli.codigo_cliente || "");
              const cg = "c-" + cid;
              const expC = isExpanded(viewState, cg);
              const hasDet = (cli.venta_detalle || []).length > 0;
              const chevC = hasDet ? treeToggleHtml(cg, expC) : treeSpacerHtml();
              const cliSearch = [vend.nombre_vendedor, estado.nombre, cli.nombre_cliente, cid]
                .filter(function (x) {
                  return x != null && String(x).trim() !== "";
                })
                .join(" ")
                .toLowerCase()
                .replace(/\s+/g, " ")
                .trim();
              const cliHidden = !expanded || !expEstado;
              parts.push(
                `<tr class="vo-child-row hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors ${cliHidden ? "hidden" : ""} bg-white dark:bg-slate-900/30"${voSearchDataAttr(cliSearch)} data-parent="${escHtml(estadoKey)}" data-vo-vendor-group="${escHtml(gid)}" data-vo-client="${escHtml(cid)}">` +
                  treeNombreCell(
                    treeIndentPx(2),
                    chevC,
                    "text-xs font-normal uppercase tracking-tight text-slate-800 dark:text-slate-200",
                    `${etiquetaJerarquia(1)}${escHtml(cli.nombre_cliente)}`
                  ) +
                  metricCellsFull(cli) +
                  "</tr>"
              );
              if (hasDet) {
                appendVentaDetalle(parts, cli.venta_detalle, gid, cg, cid, viewState, expanded && expEstado, expC, cliSearch);
              }
            });
        });
    });

    if (totals && typeof totals === "object") {
      parts.push(
        '<tr data-vo-totales="1" class="border-t-[3px] border-violet-500 dark:border-violet-400 bg-gradient-to-r from-slate-200 via-slate-100 to-slate-200 dark:from-slate-700 dark:via-slate-800 dark:to-slate-700 font-bold text-slate-900 dark:text-white">' +
          treeNombreCell(treeIndentPx(0), null, "py-2.5 text-xs uppercase tracking-wide", "Totales") +
          metricCellsFull(totals) +
          "</tr>"
      );
    }

    parts.push("</tbody>");
    container.innerHTML =
      '<table class="vo-jerarquia-table min-w-full divide-y divide-slate-200 text-xs dark:divide-slate-700">' +
      buildThead() +
      parts.join("") +
      "</table>";

    container.querySelectorAll("tr[data-vo-toggle]").forEach(function (tr) {
      tr.addEventListener("click", function (e) {
        const t = e.target;
        if (t && typeof t.closest === "function" && t.closest("[data-vo-chev]")) return;
        toggleVendor(container, tr);
      });
      tr.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggleVendor(container, tr);
        }
      });
    });

    wireNestedToggles(container);
    wireBoToolbarOnce();
    applySearchFilterFromInput();
  }

  function toggleVendor(container, headerRow) {
    const gid = headerRow?.getAttribute("data-vo-toggle");
    if (!gid) return;
    const gEsc = escSel(gid);
    const codViajante = headerRow.getAttribute("data-vo-vendor");
    const rows = container.querySelectorAll(`tr[data-vo-vendor-group="${gEsc}"]`);
    const chev = headerRow.querySelector("[data-chev]");
    const st = loadViewState();
    st.expandedVendors = st.expandedVendors || {};
    const key = String(codViajante || "");
    const currentlyExpanded = Boolean(st.expandedVendors[key]);

    if (currentlyExpanded) {
      /** Colapsar: ocultar todas las filas del grupo (no usar toggle: filas ya hidden por rubro/sub se invertirían y quedarían visibles). */
      rows.forEach(function (r) {
        r.classList.add("hidden");
      });
      if (chev) chev.textContent = CHV.colapsado;
      headerRow.setAttribute("aria-expanded", "false");
      st.expandedVendors[key] = false;
      saveViewState(st);
      applySearchFilterAfterHierarchyToggle(container);
      return;
    }

    rows.forEach(function (r) {
      r.classList.remove("hidden");
    });
    st.expandedVendors[key] = true;
    saveViewState(st);
    if (chev) chev.textContent = CHV.expandido;
    headerRow.setAttribute("aria-expanded", "true");

    container.querySelectorAll(`tr[data-vo-vendor-group="${gEsc}"][data-vo-client]`).forEach(function (r) {
      const cid = r.getAttribute("data-vo-client");
      if (!cid) return;
      applyClientDetalleVisibility(container, cid, isExpanded(st, "c-" + cid), st);
    });
    refreshEstadoChildrenVisibility(container, gEsc);
    applySearchFilterAfterHierarchyToggle(container);
  }

  function processData(payload) {
    try {
      const totals = payload.totals || {};
      renderKpis(totals);

      const meta = payload.meta || {};
      const extra = meta.extra || {};
      const tabs = extra.tabs || {};
      let jerarquia = normalizeJerarquiaArray(tabs.objetivos_jerarquia);
      if (!jerarquia.length && Array.isArray(payload.data) && payload.data.length) {
        jerarquia = buildJerarquiaDesdeFilas(payload.data);
      }
      _lastJerarquia = jerarquia && jerarquia.length ? jerarquia : null;
      _lastTotals = totals && typeof totals === "object" ? totals : null;
      renderTable(jerarquia, totals);
    } catch (err) {
      console.error("[objetivos_ventas_bo] processData", err);
      const container = document.getElementById("vo-jerarquia-container");
      if (container) {
        const msg = err && err.message ? String(err.message) : "Error desconocido";
        container.innerHTML =
          '<div class="px-3 py-4 text-sm text-rose-600 dark:text-rose-400">' +
          "<strong>No se pudo mostrar la grilla.</strong> Revisá la consola del navegador (F12) para el detalle técnico. " +
          escHtml(msg) +
          "</div>";
      }
    }
  }

  wireBoToolbarOnce();

  window.objetivosVentasBoHandler = { processData: processData };
})();
