/**
 * Informe Salidas por marca y SuperArtículo.
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "salidas-marca-superart") return;

  const root = document.getElementById("smsa-filtros-root");
  const marcasUrl = root?.dataset?.smsaMarcasUrl || "";
  const superartUrl = root?.dataset?.smsaSuperartUrl || "";
  let applyTimer = null;
  let tagsReady = false;

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function debouncedApply() {
    clearTimeout(applyTimer);
    applyTimer = setTimeout(() => {
      syncUrlFromForm();
      if (typeof window.fetchDashboardData === "function") {
        window.fetchDashboardData();
      }
    }, 400);
  }

  function readMultiSelect(id) {
    const sel = document.getElementById(id);
    if (!sel) return [];
    return Array.from(sel.selectedOptions || [])
      .map((o) => o.value)
      .filter(Boolean);
  }

  function syncUrlFromForm() {
    const params = new URLSearchParams();
    const desde = document.getElementById("fecha_inicio")?.value;
    const hasta = document.getElementById("fecha_fin")?.value;
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
    readMultiSelect("marcas_incluidos").forEach((v) => params.append("marcas_incluidos", v));
    readMultiSelect("marcas_excluidos").forEach((v) => params.append("marcas_excluidos", v));
    readMultiSelect("superarts_incluidos").forEach((v) => params.append("q_superart", v));
    readMultiSelect("superarts_excluidos").forEach((v) => params.append("superarts_excluidos", v));
    const next = `${window.location.pathname}?${params.toString()}`;
    if (window.location.href.split("?")[0] + (window.location.search ? "?" + params.toString() : "") !== next) {
      window.history.replaceState({}, "", next);
    }
  }

  function hydrateFormFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const desde = params.get("desde");
    const hasta = params.get("hasta");
    const inicio = document.getElementById("fecha_inicio");
    const fin = document.getElementById("fecha_fin");
    if (desde || hasta) {
      const personalizado = document.querySelector('.periodo-tipo-btn[data-periodo="personalizado"]');
      if (personalizado) personalizado.click();
      if (inicio) {
        inicio.disabled = false;
        if (desde) inicio.value = desde;
      }
      if (fin) {
        fin.disabled = false;
        if (hasta) fin.value = hasta;
      }
    }
    [
      ["marcas_incluidos", "marcas_incluidos"],
      ["marcas_excluidos", "marcas_excluidos"],
      ["superarts_incluidos", "q_superart"],
      ["superarts_excluidos", "superarts_excluidos"],
    ].forEach(([id, param]) => {
      const sel = document.getElementById(id);
      const vals = params.getAll(param);
      if (!sel || !vals.length) return;
      sel.innerHTML = "";
      vals.forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v;
        opt.textContent = v;
        opt.selected = true;
        sel.appendChild(opt);
      });
    });
  }

  async function fetchMarcas(q) {
    const resp = await fetch(`${marcasUrl}?q=${encodeURIComponent(q)}&limit=25`, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!resp.ok) return [];
    const data = await resp.json();
    return (data.marcas || []).map((m) => ({ value: String(m.value), label: m.label }));
  }

  async function fetchSuperarts(q) {
    const resp = await fetch(`${superartUrl}?q=${encodeURIComponent(q)}&limit=25`, {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!resp.ok) return [];
    const data = await resp.json();
    return (data.superarts || []).map((s) => ({
      value: String(s.codigo || ""),
      label: s.descripcion || s.codigo || "",
    }));
  }

  async function initTagsFilters() {
    if (tagsReady || !window.initializeTagsFilter) return;
    tagsReady = true;
    const specs = [];
    if (marcasUrl) {
      specs.push(["marcas_incluidos", "marcas", fetchMarcas]);
      specs.push(["marcas_excluidos", "marcas", fetchMarcas]);
    }
    if (superartUrl) {
      specs.push(["superarts_incluidos", "superart", fetchSuperarts]);
      specs.push(["superarts_excluidos", "superart", fetchSuperarts]);
    }
    specs.forEach(([id, kind, fetchFn]) => {
      if (!document.getElementById(id)) return;
      window.initializeTagsFilter(id, kind, null, { remoteSearch: { minChars: 1, fetchFn } });
      document.getElementById(id)?.addEventListener("change", debouncedApply);
    });
  }

  function bindFilterChanges() {
    document.querySelectorAll(".periodo-tipo-btn").forEach((btn) => {
      btn.addEventListener("click", debouncedApply);
    });
    ["fecha_inicio", "fecha_fin"].forEach((id) => {
      document.getElementById(id)?.addEventListener("change", debouncedApply);
    });
  }

  function renderTable(payload) {
    const wrap = document.getElementById("smsa-table-wrap");
    const kpiPacks = document.getElementById("smsa-kpi-packs");
    const kpiPrendas = document.getElementById("smsa-kpi-prendas");
    const kpiDocenas = document.getElementById("smsa-kpi-docenas");
    const kpiArts = document.getElementById("smsa-kpi-articulos");
    if (!wrap) return;
    const extra = payload?.meta?.extra || {};
    const ctx = extra.salidas_marca_superart || {};
    const filasMarca = ctx.filas_marca || [];
    const totals = payload.totals || {};
    if (kpiPacks) kpiPacks.textContent = ctx.total_packs_display || String(totals.packs ?? "—");
    if (kpiPrendas) kpiPrendas.textContent = ctx.total_prendas_display || String(totals.prendas ?? "—");
    if (kpiDocenas) kpiDocenas.textContent = ctx.total_docenas_display || String(totals.docenas ?? "—");
    if (kpiArts) kpiArts.textContent = String(totals.articulos ?? "—");

    if (!filasMarca.length) {
      wrap.innerHTML =
        '<p class="text-xs text-slate-500 dark:text-slate-400">Sin salidas netas en el período seleccionado.</p>';
      return;
    }
    const meses = ctx.meses_columnas || [];
    const vias = ctx.totales_via_columnas || [];
    let html = '<div class="overflow-x-auto space-y-6">';
    filasMarca.forEach((marca) => {
      html += `<div><h3 class="text-sm font-semibold text-slate-800 dark:text-slate-100 mb-2">${escHtml(marca.marca_codigo)} — ${escHtml(marca.nombre_marca)}</h3>`;
      html += '<table class="min-w-full text-sm mb-2"><thead class="bg-slate-50 dark:bg-slate-800/50"><tr>';
      html += '<th class="px-3 py-2 text-left text-xs font-semibold uppercase">Superartículo</th>';
      meses.forEach((c) => {
        html += `<th class="px-3 py-2 text-right text-xs font-semibold uppercase whitespace-nowrap">${escHtml(c.label || c.ym)}</th>`;
      });
      vias.forEach((v) => {
        html += `<th class="px-3 py-2 text-right text-xs font-semibold uppercase whitespace-nowrap">${escHtml(v.label || v.via)}</th>`;
      });
      html += '<th class="px-3 py-2 text-right text-xs font-semibold uppercase">Total</th></tr></thead><tbody>';
      (marca.filas_superart || []).forEach((sa) => {
        html += "<tr class='border-t border-slate-100 dark:border-slate-800'>";
        html += `<td class="px-3 py-2"><div class="font-semibold tabular-nums">${escHtml(sa.codigo_superart || "—")}</div><div class="text-xs text-slate-500">${escHtml(sa.descripcion_superart)}</div></td>`;
        (sa.columnas_mes || []).forEach((cm) => {
          html += `<td class="px-3 py-2 text-right tabular-nums text-xs">${escHtml(cm.display)}</td>`;
        });
        (sa.columnas_via || []).forEach((cv) => {
          html += `<td class="px-3 py-2 text-right tabular-nums text-xs">${escHtml(cv.packs)}</td>`;
        });
        html += `<td class="px-3 py-2 text-right font-medium tabular-nums text-xs">${escHtml(sa.total_display)}</td></tr>`;
      });
      html += `<tr class="border-t bg-slate-100 font-semibold dark:bg-slate-800"><td class="px-3 py-2">Subtotal marca</td>`;
      (marca.columnas_mes || []).forEach((cm) => {
        html += `<td class="px-3 py-2 text-right tabular-nums text-xs">${escHtml(cm.display)}</td>`;
      });
      (marca.columnas_via || []).forEach((cv) => {
        html += `<td class="px-3 py-2 text-right tabular-nums text-xs">${escHtml(cv.packs)}</td>`;
      });
      html += `<td class="px-3 py-2 text-right tabular-nums text-xs">${escHtml(marca.total_display)}</td></tr>`;
      html += "</tbody></table></div>";
    });
    html += "</div>";
    wrap.innerHTML = html;
  }

  window.salidasMarcaSuperartHandler = { renderTable };

  document.addEventListener("reportDataLoaded", (event) => {
    if (!event.detail || event.detail.slug !== "salidas-marca-superart") return;
    renderTable(event.detail.response || {});
  });

  document.addEventListener("DOMContentLoaded", () => {
    hydrateFormFromUrl();
    bindFilterChanges();
    const mod = document.createElement("script");
    mod.type = "module";
    mod.textContent = `
      import { initializeTagsFilter } from "/static/reports/js/tags_filter.mjs?v=20261029a";
      window.initializeTagsFilter = initializeTagsFilter;
      document.dispatchEvent(new CustomEvent("smsa-tags-ready"));
    `;
    document.head.appendChild(mod);
    document.addEventListener("smsa-tags-ready", () => {
      initTagsFilters();
      debouncedApply();
    });
  });
})();
