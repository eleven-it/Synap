/**
 * Bottom sheet de filtros en viewport < lg (1024px).
 * Opt-in: data-filters-sheet en [data-filters-wrapper].
 * Reutiliza el mismo DOM del formulario (#report-filters); sin diálogos nativos.
 */
(function () {
  "use strict";

  const NARROW_MQ = "(max-width: 1023px)";
  const mq = window.matchMedia(NARROW_MQ);

  const wrapper = document.querySelector("[data-filters-wrapper][data-filters-sheet]");
  const filtersContainer = document.querySelector("[data-filters-container]");
  const toggleBtn = document.querySelector("[data-filters-toggle]");

  if (!wrapper || !filtersContainer) {
    return;
  }

  let overlay = null;
  let sheetHeader = null;
  let chipsBar = null;
  let stickyFooter = null;
  let isOpen = false;
  let lastFocus = null;

  const FOCUSABLE =
    'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function isMobile() {
    return mq.matches;
  }

  function ensureSheetChrome() {
    if (wrapper.querySelector("[data-filters-sheet-header]")) {
      return;
    }

    sheetHeader = document.createElement("div");
    sheetHeader.setAttribute("data-filters-sheet-header", "");
    sheetHeader.className =
      "lg:hidden flex items-center justify-between gap-3 px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shrink-0";
    sheetHeader.innerHTML =
      '<h2 class="text-sm font-semibold text-slate-800 dark:text-slate-100 m-0">Filtros</h2>' +
      '<button type="button" data-filters-sheet-close aria-label="Cerrar filtros" ' +
      'class="inline-flex items-center justify-center min-h-[44px] min-w-[44px] rounded-full text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">' +
      '<span class="material-icons text-xl" aria-hidden="true">close</span></button>';

    chipsBar = document.createElement("div");
    chipsBar.setAttribute("data-filters-sheet-chips", "");
    chipsBar.className =
      "lg:hidden flex flex-wrap gap-2 px-4 py-2 border-b border-slate-100 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/60 min-h-[44px] items-center shrink-0";
    chipsBar.setAttribute("aria-live", "polite");

    stickyFooter = document.createElement("div");
    stickyFooter.setAttribute("data-filters-sheet-footer", "");
    stickyFooter.className =
      "lg:hidden sticky bottom-0 z-10 px-4 py-3 border-t border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-[0_-4px_16px_rgba(15,23,42,0.08)] shrink-0";
    stickyFooter.innerHTML =
      '<button type="button" data-filters-sheet-apply ' +
      'class="w-full inline-flex items-center justify-center gap-2 min-h-[44px] px-4 py-3 text-sm font-semibold text-white bg-sky-600 hover:bg-sky-700 dark:bg-sky-500 dark:hover:bg-sky-600 rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400">' +
      '<span class="material-icons text-lg" aria-hidden="true">refresh</span>' +
      "<span>Actualizar</span></button>";

    wrapper.insertBefore(sheetHeader, filtersContainer);
    wrapper.insertBefore(chipsBar, filtersContainer);
    wrapper.appendChild(stickyFooter);

    overlay = document.createElement("div");
    overlay.setAttribute("data-filters-sheet-overlay", "");
    overlay.className =
      "lg:hidden fixed inset-0 z-[45] bg-black/50 backdrop-blur-sm opacity-0 pointer-events-none transition-opacity duration-300";
    overlay.setAttribute("aria-hidden", "true");
    document.body.appendChild(overlay);

    sheetHeader.querySelector("[data-filters-sheet-close]").addEventListener("click", closeSheet);
    overlay.addEventListener("click", closeSheet);
    stickyFooter.querySelector("[data-filters-sheet-apply]").addEventListener("click", applyAndClose);

    filtersContainer.addEventListener("change", () => {
      if (isOpen) updateChips();
    });
    filtersContainer.addEventListener("input", () => {
      if (isOpen) updateChips();
    });
  }

  function chipHtml(label) {
    return (
      '<span class="inline-flex items-center min-h-[32px] px-2.5 py-1 rounded-full text-[11px] font-medium ' +
      "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200 border border-sky-200 dark:border-sky-700\">" +
      label +
      "</span>"
    );
  }

  function selectedCount(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return 0;
    return Array.from(sel.selectedOptions).filter((o) => o.value).length;
  }

  function hasPeriodoFacturacion() {
    const fi = document.getElementById("fecha_inicio_facturacion")?.value;
    const ff = document.getElementById("fecha_fin_facturacion")?.value;
    return Boolean(fi && ff);
  }

  function fmtDateIso(iso) {
    if (!iso) return "";
    const p = String(iso).split("-");
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : iso;
  }

  function updateChips() {
    if (!chipsBar) return;
    const chips = [];

    if (hasPeriodoFacturacion()) {
      const fi = document.getElementById("fecha_inicio_facturacion")?.value;
      const ff = document.getElementById("fecha_fin_facturacion")?.value;
      chips.push(chipHtml(`Período: ${fmtDateIso(fi)} – ${fmtDateIso(ff)}`));
    }

    const marcasN = selectedCount("vmm_marcas_incluidos");
    if (marcasN) chips.push(chipHtml(`Marcas (${marcasN})`));

    const saN = selectedCount("vmm_superarts_incluidos");
    if (saN) chips.push(chipHtml(`SuperArt (${saN})`));

    const pvN = selectedCount("punto_venta");
    if (pvN) chips.push(chipHtml(`PV (${pvN})`));

    const sucN = selectedCount("sucursales");
    if (sucN) chips.push(chipHtml(`Sucursales (${sucN})`));

    const cliInc = selectedCount("clientes_incluir");
    if (cliInc) chips.push(chipHtml(`Clientes incl. (${cliInc})`));

    const cliExc = selectedCount("clientes_excluidos");
    if (cliExc) chips.push(chipHtml(`Clientes excl. (${cliExc})`));

    const proy = document.getElementById("vmm_incluir_proyeccion")?.value;
    if (proy === "1") chips.push(chipHtml("Proyección activa"));

    try {
      const slug = document.querySelector("#dashboard-root")?.dataset?.reportSlug || "";
      const presetKey = `synap:vmm:preset-hombre-applied:${slug}`;
      if (window.localStorage.getItem(presetKey) === "1") {
        chips.push(chipHtml("Preset Hombre"));
      }
    } catch (_e) {
      /* sin localStorage */
    }

    if (!chips.length) {
      chipsBar.innerHTML =
        '<span class="text-[11px] text-slate-500 dark:text-slate-400">Sin filtros restrictivos activos</span>';
    } else {
      chipsBar.innerHTML = chips.join("");
    }

    updateFiltersBadge(chips.length);
  }

  function updateFiltersBadge(count) {
    const badge = document.getElementById("filters-count-badge");
    const num = document.getElementById("filters-count-number");
    if (!badge || !num) return;
    if (count > 0) {
      num.textContent = String(count);
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  function applySheetLayoutClasses() {
    wrapper.classList.add(
      "reports-filters-sheet",
      "lg:!relative",
      "lg:!inset-auto",
      "lg:!transform-none",
      "lg:!max-h-none",
      "lg:!rounded-none",
      "lg:!shadow-none",
      "lg:!flex-none",
      "lg:!overflow-visible",
      "lg:!z-auto"
    );
    filtersContainer.classList.add("reports-filters-sheet-body", "overflow-y-auto", "flex-1", "max-h-[50vh]", "lg:max-h-none", "lg:overflow-visible");
  }

  function openSheet() {
    if (!isMobile()) return;
    ensureSheetChrome();
    applySheetLayoutClasses();
    lastFocus = document.activeElement;
    isOpen = true;

    wrapper.classList.remove("hidden");
    filtersContainer.classList.remove("hidden");
    wrapper.classList.add(
      "fixed",
      "inset-x-0",
      "bottom-0",
      "z-[50]",
      "flex",
      "flex-col",
      "max-h-[92vh]",
      "rounded-t-2xl",
      "shadow-2xl",
      "bg-white",
      "dark:bg-slate-900",
      "border-t",
      "border-slate-200",
      "dark:border-slate-700",
      "translate-y-0",
      "transition-transform",
      "duration-300"
    );

    if (overlay) {
      overlay.classList.remove("opacity-0", "pointer-events-none");
      overlay.setAttribute("aria-hidden", "false");
    }

    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", "true");
      const label = toggleBtn.querySelector("[data-toggle-label]");
      if (label) {
        label.textContent = toggleBtn.dataset.labelHide || "Ocultar filtros";
      }
    }

    updateChips();
    document.addEventListener("keydown", onKeyDown);
    const first = wrapper.querySelector(FOCUSABLE);
    if (first) first.focus();
  }

  function closeSheet() {
    if (!isMobile()) return;
    isOpen = false;
    document.removeEventListener("keydown", onKeyDown);

    wrapper.classList.remove(
      "fixed",
      "inset-x-0",
      "bottom-0",
      "z-[50]",
      "flex",
      "flex-col",
      "max-h-[92vh]",
      "rounded-t-2xl",
      "shadow-2xl",
      "translate-y-0"
    );
    wrapper.classList.add("hidden");
    filtersContainer.classList.add("hidden");

    if (overlay) {
      overlay.classList.add("opacity-0", "pointer-events-none");
      overlay.setAttribute("aria-hidden", "true");
    }

    if (toggleBtn) {
      toggleBtn.setAttribute("aria-expanded", "false");
      const label = toggleBtn.querySelector("[data-toggle-label]");
      if (label) {
        label.textContent = toggleBtn.dataset.labelShow || "Mostrar filtros";
      }
    }

    if (lastFocus && typeof lastFocus.focus === "function") {
      lastFocus.focus();
    }
  }

  function applyAndClose() {
    if (typeof window.fetchDashboardData === "function") {
      window.fetchDashboardData();
    } else {
      document.querySelector("[data-refresh-dashboard]")?.click();
    }
    closeSheet();
  }

  function onKeyDown(e) {
    if (!isOpen) return;
    if (e.key === "Escape") {
      e.preventDefault();
      closeSheet();
      return;
    }
    if (e.key !== "Tab") return;

    const nodes = Array.from(wrapper.querySelectorAll(FOCUSABLE)).filter(
      (el) => el.offsetParent !== null || el === document.activeElement
    );
    if (!nodes.length) return;

    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  function onToggleCapture(e) {
    if (!isMobile() || !toggleBtn || e.currentTarget !== toggleBtn) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if (isOpen) {
      closeSheet();
    } else {
      openSheet();
    }
  }

  function onViewportChange() {
    if (!isMobile()) {
      closeSheet();
      if (overlay) {
        overlay.classList.add("opacity-0", "pointer-events-none");
      }
    }
    updateChips();
  }

  function init() {
    applySheetLayoutClasses();
    if (toggleBtn) {
      toggleBtn.addEventListener("click", onToggleCapture, true);
    }
    mq.addEventListener("change", onViewportChange);
    updateChips();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  window.reportsFiltersSheet = {
    open: openSheet,
    close: closeSheet,
    updateChips,
    isMobile,
  };
})();
