/**
 * Informe Fabricados por superartículo (reports standalone).
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "fabricados-superart") return;

  const root = document.getElementById("fsa-filtros-root");
  const marcasUrl = root?.dataset?.fsaMarcasUrl || "";
  const superartUrl = root?.dataset?.fsaSuperartUrl || "";
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
    const pres = document.getElementById("fsa_presentacion")?.value;
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
    if (pres) params.set("presentacion", pres);
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
    const pres = params.get("presentacion");
    const inicio = document.getElementById("fecha_inicio");
    const fin = document.getElementById("fecha_fin");
    if (desde || hasta) {
      // Fechas explícitas en URL ⇒ período personalizado (mismo control que Ventas por artículo).
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
    if (pres) document.getElementById("fsa_presentacion").value = pres;
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
    ["fecha_inicio", "fecha_fin", "fsa_presentacion"].forEach((id) => {
      document.getElementById(id)?.addEventListener("change", debouncedApply);
    });
  }

  function renderTable(payload) {
    const wrap = document.getElementById("fsa-table-wrap");
    const kpiTotal = document.getElementById("fsa-kpi-total");
    const kpiCount = document.getElementById("fsa-kpi-superarts");
    const kpiPico = document.getElementById("fsa-kpi-pico");
    if (!wrap) return;
    const extra = payload?.meta?.extra || {};
    const fab = extra.fabricados || {};
    const filas = fab.filas_superart || payload.data || [];
    const kpis = fab.kpis || payload.totals?.kpis || {};
    if (kpiTotal) kpiTotal.textContent = fab.total_general_display || kpis.total_fabricado_primera_display || "—";
    if (kpiCount) kpiCount.textContent = kpis.superarts_con_produccion ?? "—";
    if (kpiPico) kpiPico.textContent = kpis.mes_pico_label || "—";

    if (!filas.length) {
      wrap.innerHTML = '<p class="text-xs text-slate-500 dark:text-slate-400">Sin fabricado de 1ra en el período seleccionado.</p>';
      return;
    }
    const meses = fab.meses_columnas || [];
    let html = '<div class="overflow-x-auto"><table class="min-w-full text-sm"><thead class="bg-slate-50 dark:bg-slate-800/50"><tr>';
    html += '<th class="px-3 py-2 text-left text-xs font-semibold uppercase">Superartículo</th>';
    meses.forEach((c) => {
      html += `<th class="px-3 py-2 text-right text-xs font-semibold uppercase whitespace-nowrap">${escHtml(c.label || c.ym)}</th>`;
    });
    html += '<th class="px-3 py-2 text-right text-xs font-semibold uppercase">Total</th></tr></thead><tbody>';
    filas.forEach((sa) => {
      html += "<tr class='border-t border-slate-100 dark:border-slate-800'>";
      html += `<td class="px-3 py-2"><div class="font-semibold tabular-nums">${escHtml(sa.codigo_superart || "—")}</div><div class="text-xs text-slate-500">${escHtml(sa.descripcion_superart)}</div></td>`;
      (sa.columnas_mes || []).forEach((cm) => {
        html += `<td class="px-3 py-2 text-right tabular-nums">${escHtml(cm.display)}</td>`;
      });
      html += `<td class="px-3 py-2 text-right font-medium tabular-nums">${escHtml(sa.total_display)}</td></tr>`;
    });
    html += "<tr class='border-t bg-slate-100 font-semibold dark:bg-slate-800'><td class='px-3 py-2'>Totales</td>";
    (fab.totales_columnas || []).forEach((cm) => {
      html += `<td class="px-3 py-2 text-right tabular-nums">${escHtml(cm.display)}</td>`;
    });
    html += `<td class="px-3 py-2 text-right tabular-nums">${escHtml(fab.total_general_display)}</td></tr>`;
    html += "</tbody></table></div>";
    wrap.innerHTML = html;
  }

  window.fabricadosSuperartHandler = { renderTable };

  document.addEventListener("reportDataLoaded", (event) => {
    if (!event.detail || event.detail.slug !== "fabricados-superart") return;
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
      document.dispatchEvent(new CustomEvent("fsa-tags-ready"));
    `;
    document.head.appendChild(mod);
    document.addEventListener("fsa-tags-ready", () => {
      initTagsFilters();
      debouncedApply();
    });
  });
})();
