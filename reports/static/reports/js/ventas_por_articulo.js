/**
 * Informe Ventas por artículo (jerarquía artículo → proveedor → cliente).
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "ventas-por-articulo") {
    return;
  }

  let _lastJerarquia = null;
  let _lastTotals = null;

  const VIEW_STATE_KEY = `synap:report-view:${reportSlug}:jerarquia`;
  const CHV = { expandido: "▾", colapsado: "▸" };

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

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escSel(s) {
    return String(s ?? "").replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  function fmtMoney(v) {
    const n = Number(v);
    return Number.isFinite(n) ? ARS.format(n) : "—";
  }

  function fmtNum(v) {
    const n = Number(v);
    return Number.isFinite(n) ? NUM.format(n) : "—";
  }

  function loadViewState() {
    try {
      const raw = window.localStorage.getItem(VIEW_STATE_KEY);
      if (!raw) return { expandedArticles: {}, expandedNodes: {} };
      const parsed = JSON.parse(raw);
      return {
        expandedArticles:
          parsed.expandedArticles && typeof parsed.expandedArticles === "object"
            ? parsed.expandedArticles
            : {},
        expandedNodes:
          parsed.expandedNodes && typeof parsed.expandedNodes === "object"
            ? parsed.expandedNodes
            : {},
      };
    } catch (e) {
      return { expandedArticles: {}, expandedNodes: {} };
    }
  }

  function saveViewState(state) {
    try {
      window.localStorage.setItem(
        VIEW_STATE_KEY,
        JSON.stringify({
          expandedArticles: state.expandedArticles || {},
          expandedNodes: state.expandedNodes || {},
        })
      );
    } catch (e) {
      /* sin localStorage */
    }
  }

  function isArticleExpanded(st, idArt) {
    return Boolean(st?.expandedArticles?.[String(idArt || "")]);
  }

  function isExpanded(st, key) {
    return Boolean(st?.expandedNodes?.[key]);
  }

  function getCurrentSortConfig() {
    const ordenarPor = document.getElementById("ordenar_por");
    const ordenForma = document.getElementById("orden_forma");
    const metricKey =
      ordenarPor && ordenarPor.value === "unidades_periodo"
        ? "cantidades_vendidas"
        : "facturacion";
    const direction =
      ordenForma && String(ordenForma.value).toLowerCase() === "asc" ? "asc" : "desc";
    return { metricKey, direction };
  }

  function compareMetric(a, b, metricKey, direction) {
    const va = Number(a?.[metricKey]) || 0;
    const vb = Number(b?.[metricKey]) || 0;
    const diff = va - vb;
    if (Math.abs(diff) < 1e-9) return 0;
    return direction === "asc" ? diff : -diff;
  }

  function sortJerarquiaInPlace(jerarquia, metricKey, direction) {
    jerarquia.forEach((art) => {
      (art.children || []).forEach((prov) => {
        (prov.children || []).sort((a, b) => {
          const d = compareMetric(a, b, metricKey, direction);
          if (d) return d;
          return String(a?.nombre_cliente || "")
            .toUpperCase()
            .localeCompare(String(b?.nombre_cliente || "").toUpperCase());
        });
      });
      art.children = (art.children || []).sort((a, b) => {
        const d = compareMetric(a, b, metricKey, direction);
        if (d) return d;
        return String(a?.nombre_proveedor || "")
          .toUpperCase()
          .localeCompare(String(b?.nombre_proveedor || "").toUpperCase());
      });
    });
    jerarquia.sort((a, b) => {
      const d = compareMetric(a, b, metricKey, direction);
      if (d) return d;
      return String(a?.nombre_articulo || "")
        .toUpperCase()
        .localeCompare(String(b?.nombre_articulo || "").toUpperCase());
    });
  }

  function buildThead() {
    return (
      "<thead class=\"sticky top-0 z-10 bg-slate-100 dark:bg-slate-800\">" +
      "<tr>" +
      '<th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Nombre</th>' +
      '<th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Unidades</th>' +
      '<th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Facturación</th>' +
      "</tr></thead>"
    );
  }

  function metricCells(row) {
    return (
      `<td class="px-3 py-1.5 text-right tabular-nums text-slate-800 dark:text-slate-100">${fmtNum(row.cantidades_vendidas)}</td>` +
      `<td class="px-3 py-1.5 text-right tabular-nums text-slate-800 dark:text-slate-100">${fmtMoney(row.facturacion)}</td>`
    );
  }

  function nombreCell(indentPx, toggleHtml, labelHtml) {
    return (
      `<td class="px-3 py-1.5 text-left align-middle" style="padding-left:${indentPx}px">` +
      (toggleHtml || "") +
      `<span class="inline align-middle">${labelHtml}</span></td>`
    );
  }

  function toggleHtml(key, open) {
    return (
      `<button type="button" class="vo-chev inline-flex min-w-[1.25rem] items-center justify-center text-slate-600 dark:text-slate-300" ` +
      `data-vpa-chev="${escHtml(key)}" aria-expanded="${open ? "true" : "false"}">${open ? CHV.expandido : CHV.colapsado}</button>`
    );
  }

  function searchAttr(text) {
    const t = String(text || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
    return ` data-vpa-search="${escHtml(t)}"`;
  }

  function renderTable(jerarquia, totals) {
    const container = document.getElementById("vo-jerarquia-container");
    if (!container) return;
    const st = loadViewState();

    if (!jerarquia || !jerarquia.length) {
      container.innerHTML =
        '<p class="px-3 py-4 text-xs text-slate-500 dark:text-slate-400">No hay datos para el período y filtros seleccionados.</p>';
      return;
    }

    const tbClass = "divide-y divide-slate-200 dark:divide-slate-700";
    const parts = [];

    jerarquia.forEach((art) => {
      const idArt = String(art.id_art || "");
      const ag = "a-" + idArt;
      const artOpen = isArticleExpanded(st, idArt);
      const artSearch = [art.nombre_articulo, idArt].join(" ").toLowerCase();
      parts.push(`<tbody class="${tbClass}">`);
      parts.push(
        `<tr class="bg-slate-100 dark:bg-slate-800/90 cursor-pointer select-none"${searchAttr(artSearch)} data-vpa-art-toggle="${escHtml(ag)}" data-vpa-art="${escHtml(idArt)}" role="button" tabindex="0" aria-expanded="${artOpen ? "true" : "false"}">` +
          nombreCell(12, toggleHtml(ag, artOpen), `<span class="text-xs font-bold uppercase">${escHtml(art.nombre_articulo || "Artículo")}</span>`) +
          metricCells(art) +
          "</tr></tbody>"
      );
      parts.push(`<tbody class="${tbClass}" data-vpa-art-details="${escHtml(ag)}"${artOpen ? "" : ' hidden="hidden"'}`);

      (art.children || []).forEach((prov) => {
        const pk = ag + "-p-" + String(prov.codigo_proveedor ?? 0);
        const provOpen = isExpanded(st, pk);
        const provSearch = [art.nombre_articulo, prov.nombre_proveedor].join(" ").toLowerCase();
        const provHidden = !artOpen;
        parts.push(
          `<tr class="vo-child-row bg-slate-50 dark:bg-slate-900/30 ${provHidden ? "hidden" : ""}"${searchAttr(provSearch)} data-parent="${escHtml(ag)}" data-vpa-prov-key="${escHtml(pk)}">` +
            nombreCell(28, toggleHtml(pk, provOpen), `<span class="text-xs uppercase text-slate-700 dark:text-slate-200">Proveedor: ${escHtml(prov.nombre_proveedor || "—")}</span>`) +
            metricCells(prov) +
            "</tr>"
        );
        (prov.children || []).forEach((cli) => {
          const cliSearch = [art.nombre_articulo, prov.nombre_proveedor, cli.nombre_cliente]
            .join(" ")
            .toLowerCase();
          const hideCli = provHidden || !provOpen;
          parts.push(
            `<tr class="vo-child-row hover:bg-slate-50 dark:hover:bg-slate-700/40 ${hideCli ? "hidden" : ""}"${searchAttr(cliSearch)} data-parent="${escHtml(pk)}">` +
              nombreCell(44, '<span class="inline-block w-5"></span>', `<span class="text-xs text-slate-800 dark:text-slate-200">Cliente: ${escHtml(cli.nombre_cliente || "—")}</span>`) +
              metricCells(cli) +
              "</tr>"
          );
        });
      });
      parts.push("</tbody>");
    });

    if (totals && typeof totals === "object") {
      parts.push(`<tbody class="${tbClass}"><tr class="font-bold bg-slate-200 dark:bg-slate-700">` +
        nombreCell(12, "", "<span>Totales</span>") +
        metricCells(totals) +
        "</tr></tbody>");
    }

    container.innerHTML =
      '<table class="vo-jerarquia-table min-w-full text-xs">' +
      buildThead() +
      parts.join("") +
      "</table>";

    wireInteractions(container);
    applySearchFromInput();
  }

  function applySearchFromInput() {
    const input = document.getElementById("vo-bo-buscar-jerarquia");
    const container = document.getElementById("vo-jerarquia-container");
    if (!input || !container) return;
    const needle = String(input.value || "")
      .trim()
      .toLowerCase();
    const rows = container.querySelectorAll("tbody tr");
    if (needle.length < 2) {
      rows.forEach((r) => r.classList.remove("vo-bo-search-hide"));
      return;
    }
    rows.forEach((r) => {
      if (r.getAttribute("data-vpa-art-toggle")) {
        r.classList.remove("vo-bo-search-hide");
        return;
      }
      const hay = (r.getAttribute("data-vpa-search") || "").toLowerCase();
      r.classList.toggle("vo-bo-search-hide", hay.indexOf(needle) < 0);
    });
  }

  function toggleArticleExpanded(idArt) {
    const st = loadViewState();
    const key = String(idArt || "");
    st.expandedArticles[key] = !isArticleExpanded(st, key);
    saveViewState(st);
    if (_lastJerarquia) renderTable(_lastJerarquia, _lastTotals);
  }

  function toggleProveedorExpanded(container, provKey) {
    const st = loadViewState();
    const open = !isExpanded(st, provKey);
    st.expandedNodes[provKey] = open;
    saveViewState(st);
    container.querySelectorAll(`tr[data-parent="${escSel(provKey)}"]`).forEach((r) => {
      r.classList.toggle("hidden", !open);
    });
    const chev = container.querySelector(`[data-vpa-chev="${escSel(provKey)}"]`);
    if (chev) {
      chev.textContent = open ? CHV.expandido : CHV.colapsado;
      chev.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  function wireInteractions(container) {
    if (!container.dataset.vpaDelegationWired) {
      container.dataset.vpaDelegationWired = "1";
      container.addEventListener("click", function (e) {
        const t = e.target;
        if (!t || typeof t.closest !== "function") return;

        const chev = t.closest("[data-vpa-chev]");
        if (chev && container.contains(chev)) {
          const chevKey = chev.getAttribute("data-vpa-chev") || "";
          if (chevKey.indexOf("-p-") >= 0) {
            e.preventDefault();
            e.stopPropagation();
            toggleProveedorExpanded(container, chevKey);
            return;
          }
        }

        const tr = t.closest("tr[data-vpa-art-toggle]");
        if (!tr || !container.contains(tr)) return;
        if (chev && chev.closest("tr[data-vpa-art-toggle]") !== tr) return;
        e.preventDefault();
        toggleArticleExpanded(tr.getAttribute("data-vpa-art"));
      });

      container.addEventListener("keydown", function (e) {
        if (e.key !== "Enter" && e.key !== " ") return;
        const t = e.target;
        if (!t || typeof t.closest !== "function") return;
        const tr = t.closest("tr[data-vpa-art-toggle]");
        if (!tr || !container.contains(tr) || document.activeElement !== tr) return;
        e.preventDefault();
        toggleArticleExpanded(tr.getAttribute("data-vpa-art"));
      });
    }

    const searchInput = document.getElementById("vo-bo-buscar-jerarquia");
    if (searchInput && !searchInput.dataset.vpaSearchWired) {
      searchInput.dataset.vpaSearchWired = "1";
      searchInput.placeholder = "Buscar artículo, proveedor o cliente… (mín. 2 caracteres)";
      searchInput.addEventListener("input", function () {
        applySearchFromInput();
      });
    }

    const btnExpand = document.getElementById("vo-bo-btn-expandir-todos");
    const btnCollapse = document.getElementById("vo-bo-btn-contraer-todos");
    if (btnExpand && !btnExpand.dataset.vpaWired) {
      btnExpand.dataset.vpaWired = "1";
      btnExpand.addEventListener("click", function () {
        const st = { expandedArticles: {}, expandedNodes: {} };
        container.querySelectorAll("tr[data-vpa-art]").forEach((tr) => {
          st.expandedArticles[tr.getAttribute("data-vpa-art")] = true;
        });
        container.querySelectorAll("[data-vpa-prov-key]").forEach((tr) => {
          st.expandedNodes[tr.getAttribute("data-vpa-prov-key")] = true;
        });
        saveViewState(st);
        if (_lastJerarquia) renderTable(_lastJerarquia, _lastTotals);
      });
    }
    if (btnCollapse && !btnCollapse.dataset.vpaWired) {
      btnCollapse.dataset.vpaWired = "1";
      btnCollapse.addEventListener("click", function () {
        saveViewState({ expandedArticles: {}, expandedNodes: {} });
        if (_lastJerarquia) renderTable(_lastJerarquia, _lastTotals);
      });
    }

    const ordenarPor = document.getElementById("ordenar_por");
    const ordenForma = document.getElementById("orden_forma");
    function onSortChange() {
      if (!_lastJerarquia || !_lastJerarquia.length) return;
      const cfg = getCurrentSortConfig();
      const copy = JSON.parse(JSON.stringify(_lastJerarquia));
      sortJerarquiaInPlace(copy, cfg.metricKey, cfg.direction);
      renderTable(copy, _lastTotals);
    }
    if (ordenarPor && !ordenarPor.dataset.vpaWired) {
      ordenarPor.dataset.vpaWired = "1";
      ordenarPor.addEventListener("change", onSortChange);
    }
    if (ordenForma && !ordenForma.dataset.vpaWired) {
      ordenForma.dataset.vpaWired = "1";
      ordenForma.addEventListener("change", onSortChange);
    }
  }

  function processData(payload) {
    const totals = payload.totals || {};
    const meta = payload.meta || {};
    const extra = meta.extra || {};
    const tabs = extra.tabs || {};
    let jerarquia = Array.isArray(tabs.objetivos_jerarquia) ? tabs.objetivos_jerarquia : [];
    if (!jerarquia.length && Array.isArray(payload.data)) {
      jerarquia = [];
    }
    if (jerarquia.length) {
      const cfg = getCurrentSortConfig();
      sortJerarquiaInPlace(jerarquia, cfg.metricKey, cfg.direction);
    }
    _lastJerarquia = jerarquia.length ? jerarquia : null;
    _lastTotals = totals;
    renderTable(jerarquia, totals);

    const periodEl = document.getElementById("vo-summary-period");
    const fa = meta.filters_applied || {};
    if (periodEl && fa.fecha_inicio_facturacion && fa.fecha_fin_facturacion) {
      periodEl.textContent =
        "Período facturación: " + fa.fecha_inicio_facturacion + " — " + fa.fecha_fin_facturacion;
    }
  }

  window.ventasPorArticuloHandler = { processData: processData };
})();
