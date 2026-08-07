/**
 * Informe Ventas por marca y SuperArt (jerarquía Marca → SuperArt → Artículo).
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "ventas-marca-superart") {
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
      if (!raw) return { expandedMarcas: {}, expandedNodes: {} };
      const parsed = JSON.parse(raw);
      return {
        expandedMarcas:
          parsed.expandedMarcas && typeof parsed.expandedMarcas === "object"
            ? parsed.expandedMarcas
            : {},
        expandedNodes:
          parsed.expandedNodes && typeof parsed.expandedNodes === "object"
            ? parsed.expandedNodes
            : {},
      };
    } catch (e) {
      return { expandedMarcas: {}, expandedNodes: {} };
    }
  }

  function saveViewState(state) {
    try {
      window.localStorage.setItem(
        VIEW_STATE_KEY,
        JSON.stringify({
          expandedMarcas: state.expandedMarcas || {},
          expandedNodes: state.expandedNodes || {},
        })
      );
    } catch (e) {
      /* sin localStorage */
    }
  }

  function isMarcaExpanded(st, key) {
    return Boolean(st?.expandedMarcas?.[String(key || "")]);
  }

  function isExpanded(st, key) {
    return Boolean(st?.expandedNodes?.[key]);
  }

  function metricKeyFromSort(ordenarPor) {
    const v = String(ordenarPor || "").trim();
    if (v === "packs") return "packs";
    if (v === "docenas") return "docenas";
    return "facturacion";
  }

  function getCurrentSortConfig() {
    const ordenarPor = document.getElementById("ordenar_por");
    const ordenForma = document.getElementById("orden_forma");
    const metricKey = metricKeyFromSort(ordenarPor?.value);
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
    jerarquia.forEach((marca) => {
      (marca.children || []).forEach((sa) => {
        (sa.children || []).sort((a, b) => {
          const d = compareMetric(a, b, metricKey, direction);
          if (d) return d;
          return String(a?.nombre_articulo || "")
            .toUpperCase()
            .localeCompare(String(b?.nombre_articulo || "").toUpperCase());
        });
      });
      marca.children = (marca.children || []).sort((a, b) => {
        const d = compareMetric(a, b, metricKey, direction);
        if (d) return d;
        return String(a?.nombre_superart || "")
          .toUpperCase()
          .localeCompare(String(b?.nombre_superart || "").toUpperCase());
      });
    });
    jerarquia.sort((a, b) => {
      const d = compareMetric(a, b, metricKey, direction);
      if (d) return d;
      return String(a?.nombre_marca || "")
        .toUpperCase()
        .localeCompare(String(b?.nombre_marca || "").toUpperCase());
    });
  }

  function buildThead() {
    return (
      "<thead class=\"sticky top-0 z-10 bg-slate-100 dark:bg-slate-800\">" +
      "<tr>" +
      '<th class="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Nombre</th>' +
      '<th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Packs</th>' +
      '<th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Docenas</th>' +
      '<th class="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300">Facturación</th>' +
      "</tr></thead>"
    );
  }

  function metricCells(row) {
    return (
      `<td class="px-3 py-1.5 text-right tabular-nums text-slate-800 dark:text-slate-100">${fmtNum(row.packs)}</td>` +
      `<td class="px-3 py-1.5 text-right tabular-nums text-slate-800 dark:text-slate-100">${fmtNum(row.docenas)}</td>` +
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
      `data-vmsa-chev="${escHtml(key)}" aria-expanded="${open ? "true" : "false"}">${open ? CHV.expandido : CHV.colapsado}</button>`
    );
  }

  function searchAttr(text) {
    const t = String(text || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
    return ` data-vmsa-search="${escHtml(t)}"`;
  }

  function marcaKey(marca) {
    return "m-" + String(marca.codigo_marca ?? 0);
  }

  function superartKey(mk, sa) {
    return mk + "-sa-" + String(sa.id_manual ?? "").replace(/[^a-zA-Z0-9_-]/g, "_");
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

    jerarquia.forEach((marca) => {
      const mk = marcaKey(marca);
      const marcaOpen = isMarcaExpanded(st, mk);
      const marcaSearch = [marca.nombre_marca, marca.codigo_marca].join(" ").toLowerCase();
      parts.push(`<tbody class="${tbClass}">`);
      parts.push(
        `<tr class="bg-slate-100 dark:bg-slate-800/90 cursor-pointer select-none"${searchAttr(marcaSearch)} data-vmsa-marca-toggle="${escHtml(mk)}" data-vmsa-marca="${escHtml(mk)}" role="button" tabindex="0" aria-expanded="${marcaOpen ? "true" : "false"}">` +
          nombreCell(12, toggleHtml(mk, marcaOpen), `<span class="text-xs font-bold uppercase">${escHtml(marca.nombre_marca || "Marca")}</span>`) +
          metricCells(marca) +
          "</tr></tbody>"
      );
      parts.push(`<tbody class="${tbClass}" data-vmsa-marca-details="${escHtml(mk)}"${marcaOpen ? "" : ' hidden="hidden"'}`);

      (marca.children || []).forEach((sa) => {
        const sk = superartKey(mk, sa);
        const saOpen = isExpanded(st, sk);
        const saSearch = [marca.nombre_marca, sa.nombre_superart, sa.id_manual].join(" ").toLowerCase();
        const saHidden = !marcaOpen;
        parts.push(
          `<tr class="vo-child-row bg-slate-50 dark:bg-slate-900/30 ${saHidden ? "hidden" : ""}"${searchAttr(saSearch)} data-parent="${escHtml(mk)}" data-vmsa-sa-key="${escHtml(sk)}">` +
            nombreCell(28, toggleHtml(sk, saOpen), `<span class="text-xs uppercase text-slate-700 dark:text-slate-200">SuperArt: ${escHtml(sa.nombre_superart || "—")}</span>`) +
            metricCells(sa) +
            "</tr>"
        );
        (sa.children || []).forEach((art) => {
          const artSearch = [marca.nombre_marca, sa.nombre_superart, art.nombre_articulo, art.id_art]
            .join(" ")
            .toLowerCase();
          const hideArt = saHidden || !saOpen;
          parts.push(
            `<tr class="vo-child-row hover:bg-slate-50 dark:hover:bg-slate-700/40 ${hideArt ? "hidden" : ""}"${searchAttr(artSearch)} data-parent="${escHtml(sk)}">` +
              nombreCell(44, '<span class="inline-block w-5"></span>', `<span class="text-xs text-slate-800 dark:text-slate-200">Artículo: ${escHtml(art.nombre_articulo || "—")}</span>`) +
              metricCells(art) +
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

    const tableHtml =
      '<table class="vo-jerarquia-table min-w-full text-xs">' +
      buildThead() +
      parts.join("") +
      "</table>";

    if (window.SynapReportsResponsive) {
      window.SynapReportsResponsive.wrapJerarquiaDual(container, tableHtml, {
        variant: "ventas-marca-superart",
        rows: jerarquia,
      });
    } else {
      container.innerHTML = tableHtml;
    }

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
      if (r.getAttribute("data-vmsa-marca-toggle")) {
        r.classList.remove("vo-bo-search-hide");
        return;
      }
      const hay = (r.getAttribute("data-vmsa-search") || "").toLowerCase();
      r.classList.toggle("vo-bo-search-hide", hay.indexOf(needle) < 0);
    });
  }

  function toggleMarcaExpanded(mk) {
    const st = loadViewState();
    const key = String(mk || "");
    st.expandedMarcas[key] = !isMarcaExpanded(st, key);
    saveViewState(st);
    if (_lastJerarquia) renderTable(_lastJerarquia, _lastTotals);
  }

  function toggleSuperartExpanded(container, saKey) {
    const st = loadViewState();
    const open = !isExpanded(st, saKey);
    st.expandedNodes[saKey] = open;
    saveViewState(st);
    container.querySelectorAll(`tr[data-parent="${escSel(saKey)}"]`).forEach((r) => {
      r.classList.toggle("hidden", !open);
    });
    const chev = container.querySelector(`[data-vmsa-chev="${escSel(saKey)}"]`);
    if (chev) {
      chev.textContent = open ? CHV.expandido : CHV.colapsado;
      chev.setAttribute("aria-expanded", open ? "true" : "false");
    }
  }

  function wireInteractions(container) {
    if (!container.dataset.vmsaDelegationWired) {
      container.dataset.vmsaDelegationWired = "1";
      container.addEventListener("click", function (e) {
        const t = e.target;
        if (!t || typeof t.closest !== "function") return;

        const chev = t.closest("[data-vmsa-chev]");
        if (chev && container.contains(chev)) {
          const chevKey = chev.getAttribute("data-vmsa-chev") || "";
          if (chevKey.indexOf("-sa-") >= 0) {
            e.preventDefault();
            e.stopPropagation();
            toggleSuperartExpanded(container, chevKey);
            return;
          }
        }

        const tr = t.closest("tr[data-vmsa-marca-toggle]");
        if (!tr || !container.contains(tr)) return;
        if (chev && chev.closest("tr[data-vmsa-marca-toggle]") !== tr) return;
        e.preventDefault();
        toggleMarcaExpanded(tr.getAttribute("data-vmsa-marca"));
      });

      container.addEventListener("keydown", function (e) {
        if (e.key !== "Enter" && e.key !== " ") return;
        const t = e.target;
        if (!t || typeof t.closest !== "function") return;
        const tr = t.closest("tr[data-vmsa-marca-toggle]");
        if (!tr || !container.contains(tr) || document.activeElement !== tr) return;
        e.preventDefault();
        toggleMarcaExpanded(tr.getAttribute("data-vmsa-marca"));
      });
    }

    const searchInput = document.getElementById("vo-bo-buscar-jerarquia");
    if (searchInput && !searchInput.dataset.vmsaSearchWired) {
      searchInput.dataset.vmsaSearchWired = "1";
      searchInput.placeholder = "Buscar marca, SuperArt o artículo… (mín. 2 caracteres)";
      searchInput.addEventListener("input", function () {
        applySearchFromInput();
      });
    }

    const btnExpand = document.getElementById("vo-bo-btn-expandir-todos");
    const btnCollapse = document.getElementById("vo-bo-btn-contraer-todos");
    if (btnExpand && !btnExpand.dataset.vmsaWired) {
      btnExpand.dataset.vmsaWired = "1";
      btnExpand.addEventListener("click", function () {
        const st = { expandedMarcas: {}, expandedNodes: {} };
        container.querySelectorAll("tr[data-vmsa-marca]").forEach((tr) => {
          st.expandedMarcas[tr.getAttribute("data-vmsa-marca")] = true;
        });
        container.querySelectorAll("[data-vmsa-sa-key]").forEach((tr) => {
          st.expandedNodes[tr.getAttribute("data-vmsa-sa-key")] = true;
        });
        saveViewState(st);
        if (_lastJerarquia) renderTable(_lastJerarquia, _lastTotals);
      });
    }
    if (btnCollapse && !btnCollapse.dataset.vmsaWired) {
      btnCollapse.dataset.vmsaWired = "1";
      btnCollapse.addEventListener("click", function () {
        saveViewState({ expandedMarcas: {}, expandedNodes: {} });
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
    if (ordenarPor && !ordenarPor.dataset.vmsaWired) {
      ordenarPor.dataset.vmsaWired = "1";
      ordenarPor.addEventListener("change", onSortChange);
    }
    if (ordenForma && !ordenForma.dataset.vmsaWired) {
      ordenForma.dataset.vmsaWired = "1";
      ordenForma.addEventListener("change", onSortChange);
    }
  }

  function processData(payload) {
    const totals = payload.totals || {};
    const meta = payload.meta || {};
    const extra = meta.extra || {};
    const tabs = extra.tabs || {};
    let jerarquia = Array.isArray(tabs.marca_superart_jerarquia) ? tabs.marca_superart_jerarquia : [];
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

  window.ventasMarcaSuperartHandler = { processData: processData };
})();
