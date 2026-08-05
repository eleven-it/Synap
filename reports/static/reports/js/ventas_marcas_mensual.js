/**
 * Informe Ventas marcas mensual: KPIs + matriz Ven → Cliente × AñoMes.
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "ventas-marcas-mensual") {
    return;
  }

  const VIEW_STATE_KEY = `synap:report-view:${reportSlug}:expanded`;
  const SORT_KEY = `synap:report-view:${reportSlug}:sort`;
  const PRESET_HOMBRE_KEY = `synap:vmm:preset-hombre-applied:${reportSlug}`;
  const COMPARE_TAB_KEY = `synap:report-view:${reportSlug}:compare-tab`;
  const CHV = { expandido: "▾", colapsado: "▸" };

  const SORT_OPTIONS = [
    { value: "f-desc", field: "f", desc: true },
    { value: "f-asc", field: "f", desc: false },
    { value: "u-desc", field: "u", desc: true },
    { value: "u-asc", field: "u", desc: false },
  ];

  const ARS = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  /** KPI grandes (facturación / regalías): sin centavos para caber en 5 columnas. */
  const ARS_KPI = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  const ARS_KPI_DEC = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const NUM = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  const USD_KPI = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const MESES_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
  ];

  let _lastExtra = null;
  let _resizeTimer = null;
  let _activeCompareTab = loadCompareTab();

  function loadCompareTab() {
    try {
      const raw = window.localStorage.getItem(COMPARE_TAB_KEY);
      return raw === "b" ? "b" : "a";
    } catch (_e) {
      return "a";
    }
  }

  function saveCompareTab(side) {
    _activeCompareTab = side === "b" ? "b" : "a";
    try {
      window.localStorage.setItem(COMPARE_TAB_KEY, _activeCompareTab);
    } catch (_e) {
      /* sin localStorage */
    }
  }

  function isCompareActive(extra) {
    return Boolean(extra?.compare?.activo);
  }

  function useFullCompareMatrix() {
    if (window.matchMedia("(min-width: 1024px)").matches) return true;
    return window.matchMedia("(max-width: 1023px) and (orientation: landscape)").matches;
  }

  function useComparePortraitTabs(extra) {
    return isCompareActive(extra) && isPortraitMobile();
  }

  function getModoComparacionValue() {
    const el = document.getElementById("vmm_modo_comparacion");
    return el && el.value === "comparar" ? "comparar" : "una";
  }

  function getMarcaCompareValue(selectId) {
    const sel = document.getElementById(selectId);
    if (!sel) return "";
    return String(sel.value || "").trim();
  }

  function validateCompareFilters(filters) {
    const modo = filters?.modo_comparacion || getModoComparacionValue();
    if (modo !== "comparar") return "";
    const a = String(filters?.marca_a || getMarcaCompareValue("vmm_marca_a") || "").trim();
    const b = String(filters?.marca_b || getMarcaCompareValue("vmm_marca_b") || "").trim();
    if (!a || !b) {
      return "En modo comparar debe seleccionar marca A y marca B.";
    }
    if (a === b) {
      return "Las marcas A y B deben ser distintas.";
    }
    return "";
  }

  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fmtMoney(v) {
    const n = Number(v);
    return Number.isFinite(n) ? ARS.format(n) : "—";
  }

  function fmtMoneyKpi(v, { conDecimales = false } = {}) {
    const n = Number(v);
    if (!Number.isFinite(n)) return "—";
    return (conDecimales ? ARS_KPI_DEC : ARS_KPI).format(n);
  }

  function fmtUsdKpi(v) {
    const n = Number(v);
    if (!Number.isFinite(n)) return "—";
    // Prefijo explícito "USD" (palabra) + número es-AR; no confundir con $ ARS.
    return `USD ${USD_KPI.format(n)}`;
  }

  function fmtNum(v) {
    const n = Number(v);
    return Number.isFinite(n) ? NUM.format(n) : "—";
  }

  /**
   * Escribe el KPI sin truncar: baja el tamaño de fuente si el texto es largo
   * y deja el valor completo en title (hover / accesibilidad).
   */
  function setKpiValue(el, text) {
    if (!el) return;
    const t = String(text ?? "—");
    el.textContent = t;
    el.setAttribute("title", t === "—" ? "" : t);
    const len = t.replace(/\s/g, "").length;
    let size = "1.5rem"; // ~text-2xl
    if (len > 16) size = "1.125rem";
    if (len > 18) size = "1rem";
    if (len > 22) size = "0.875rem";
    if (window.matchMedia("(max-width: 1023px)").matches) {
      size = len > 14 ? "0.95rem" : "1.125rem";
      if (len > 18) size = "0.8125rem";
    }
    el.style.fontSize = size;
  }

  function fmtMesYm(ym) {
    const s = String(ym || "");
    if (s.length !== 6) return s;
    const y = s.slice(0, 4);
    const m = parseInt(s.slice(4, 6), 10);
    if (m < 1 || m > 12) return s;
    return `${MESES_ES[m - 1]} ${y}`;
  }

  function loadExpandedVendedores() {
    try {
      const raw = window.localStorage.getItem(VIEW_STATE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (e) {
      return {};
    }
  }

  function saveExpandedVendedores(map) {
    try {
      window.localStorage.setItem(VIEW_STATE_KEY, JSON.stringify(map || {}));
    } catch (e) {
      /* sin localStorage */
    }
  }

  function loadSortPref() {
    try {
      const raw = window.localStorage.getItem(SORT_KEY);
      if (raw && SORT_OPTIONS.some((o) => o.value === raw)) return raw;
    } catch (e) {
      /* sin localStorage */
    }
    return "f-desc";
  }

  function saveSortPref(value) {
    try {
      window.localStorage.setItem(SORT_KEY, value);
    } catch (e) {
      /* sin localStorage */
    }
  }

  function getSortConfig(value) {
    return SORT_OPTIONS.find((o) => o.value === value) || SORT_OPTIONS[0];
  }

  function sortFilas(filas, sortValue) {
    const cfg = getSortConfig(sortValue);
    const field = cfg.field;
    const desc = cfg.desc;
    return [...filas].sort((a, b) => {
      const av = Number((a.total || {})[field]) || 0;
      const bv = Number((b.total || {})[field]) || 0;
      return desc ? bv - av : av - bv;
    });
  }

  function isPortraitMobile() {
    return window.matchMedia("(max-width: 1023px) and (orientation: portrait)").matches;
  }

  function updateMatrizScrollHint() {
    const hint = document.getElementById("vmm-matriz-scroll-hint");
    if (!hint) return;
    if (isPortraitMobile()) {
      hint.classList.add("hidden");
    } else if (window.matchMedia("(max-width: 1023px)").matches) {
      hint.classList.remove("hidden");
    } else {
      hint.classList.add("hidden");
    }
  }

  function renderKpis(extra) {
    const compareOn = isCompareActive(extra);
    const kpisSection = document.getElementById("vmm-kpis-section");
    const compareSection = document.getElementById("vmm-compare-kpis-section");
    const tabsBar = document.getElementById("vmm-compare-tabs-bar");

    if (compareOn) {
      if (kpisSection) kpisSection.classList.add("hidden");
      if (compareSection) compareSection.classList.remove("hidden");
      if (tabsBar) {
        if (useComparePortraitTabs(extra)) tabsBar.classList.remove("hidden");
        else tabsBar.classList.add("hidden");
      }
      renderCompareKpis(extra);
      return;
    }

    if (kpisSection) kpisSection.classList.remove("hidden");
    if (compareSection) compareSection.classList.add("hidden");
    if (tabsBar) tabsBar.classList.add("hidden");

    const kpis = extra?.kpis || {};
    const modo = extra?.modo_unidades || "packs";
    const unidadLabel = modo === "docenas" ? "Docenas" : "Unidades";
    const elU = document.getElementById("vmm-kpi-unidades");
    const elF = document.getElementById("vmm-kpi-facturacion");
    const elP = document.getElementById("vmm-kpi-precio-medio");
    const elR = document.getElementById("vmm-kpi-regalias");
    const elRtc = document.getElementById("vmm-kpi-regalias-tc");
    const elUL = document.getElementById("vmm-kpi-unidades-label");
    if (elUL) elUL.textContent = unidadLabel;
    setKpiValue(elU, fmtNum(kpis.unidades));
    setKpiValue(elF, fmtMoneyKpi(kpis.facturacion));
    setKpiValue(elP, fmtMoneyKpi(kpis.precio_medio, { conDecimales: true }));
    setKpiValue(elR, fmtMoneyKpi(kpis.regalias));
    setKpiValue(elRtc, fmtUsdKpi(kpis.regalias_tc));
  }

  function renderCompareKpis(extra) {
    const cmp = extra?.compare || {};
    const ma = cmp.marca_a || {};
    const mb = cmp.marca_b || {};
    const kpisA = ma.kpis || {};
    const kpisB = mb.kpis || {};
    const delta = cmp.delta_pct_facturacion;

    const elDelta = document.getElementById("vmm-compare-delta");
    const elLa = document.getElementById("vmm-compare-label-a");
    const elLb = document.getElementById("vmm-compare-label-b");
    const elUa = document.getElementById("vmm-compare-u-a");
    const elUb = document.getElementById("vmm-compare-u-b");
    const elFa = document.getElementById("vmm-compare-f-a");
    const elFb = document.getElementById("vmm-compare-f-b");

    if (elLa) elLa.textContent = ma.nombre ? `Marca A — ${ma.nombre}` : "Marca A";
    if (elLb) elLb.textContent = mb.nombre ? `Marca B — ${mb.nombre}` : "Marca B";
    if (elUa) elUa.textContent = fmtNum(kpisA.unidades);
    if (elUb) elUb.textContent = fmtNum(kpisB.unidades);
    if (elFa) elFa.textContent = fmtMoney(kpisA.facturacion);
    if (elFb) elFb.textContent = fmtMoney(kpisB.facturacion);
    if (elDelta) {
      if (delta == null || Number.isNaN(Number(delta))) {
        elDelta.textContent = "—";
      } else {
        const sign = Number(delta) > 0 ? "+" : "";
        elDelta.textContent = `${sign}${Number(delta).toFixed(2)} %`;
      }
    }

    updateCompareTabLabels(ma.nombre, mb.nombre);
  }

  function updateCompareTabLabels(nomA, nomB) {
    const tabA = document.getElementById("vmm-tab-marca-a");
    const tabB = document.getElementById("vmm-tab-marca-b");
    if (tabA) tabA.textContent = nomA ? `Marca A (${nomA})` : "Marca A";
    if (tabB) tabB.textContent = nomB ? `Marca B (${nomB})` : "Marca B";
  }

  function syncCompareTabUi() {
    const tabA = document.getElementById("vmm-tab-marca-a");
    const tabB = document.getElementById("vmm-tab-marca-b");
    const active = _activeCompareTab === "b" ? "b" : "a";
    [tabA, tabB].forEach((btn) => {
      if (!btn) return;
      const isA = btn.id === "vmm-tab-marca-a";
      const selected = (active === "a" && isA) || (active === "b" && !isA);
      btn.setAttribute("aria-selected", selected ? "true" : "false");
      btn.classList.toggle("border-sky-500", selected);
      btn.classList.toggle("text-sky-700", selected);
      btn.classList.toggle("dark:text-sky-300", selected);
      btn.classList.toggle("border-transparent", !selected);
      btn.classList.toggle("text-slate-500", !selected);
      btn.classList.toggle("dark:text-slate-400", !selected);
    });
  }

  function showSynapAviso(texto, tipo) {
    if (typeof window.SynapMessages !== "undefined" && typeof window.SynapMessages.show === "function") {
      window.SynapMessages.show(texto, tipo || "aviso");
      return;
    }
    if (typeof window.mprShowAviso === "function") {
      window.mprShowAviso(texto, tipo || "aviso");
    }
  }

  function readReportConfig() {
    const el = document.getElementById("report-config-data");
    if (!el || !el.textContent) return {};
    try {
      let parsed = JSON.parse(el.textContent);
      if (typeof parsed === "string") parsed = JSON.parse(parsed);
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_e) {
      return {};
    }
  }

  function readPresetHombreIds() {
    const cfg = readReportConfig();
    const preset = cfg.preset_hombre || {};
    const ids = preset.id_manuales || preset.ids || [];
    return Array.isArray(ids) ? ids.map(String).filter(Boolean) : [];
  }

  function writePresetHombreToReportConfig(preset) {
    const el = document.getElementById("report-config-data");
    if (!el) return;
    const cfg = readReportConfig();
    cfg.preset_hombre = {
      ...(cfg.preset_hombre && typeof cfg.preset_hombre === "object" ? cfg.preset_hombre : {}),
      label: preset?.label || "Hombre",
      id_manuales: Array.isArray(preset?.id_manuales) ? preset.id_manuales.map(String) : [],
    };
    if (preset?.updated_by) cfg.preset_hombre.updated_by = preset.updated_by;
    el.textContent = JSON.stringify(cfg);
  }

  function updatePresetHombreCountLabel(ids) {
    const el = document.getElementById("vmm-preset-hombre-count");
    if (!el) return;
    const n = Array.isArray(ids) ? ids.length : 0;
    if (!n) {
      el.textContent = "Preset «Hombre»: sin SuperArts configurados.";
      return;
    }
    el.textContent = `Preset «Hombre»: ${n} SuperArt${n === 1 ? "" : "s"} configurado${n === 1 ? "" : "s"}.`;
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }

  function getPresetApiUrl() {
    const root = document.getElementById("vmm-preset-hombre-root");
    return (root?.dataset?.presetApiUrl || "").trim();
  }

  function canEditPreset() {
    const root = document.getElementById("vmm-preset-hombre-root");
    return String(root?.dataset?.canEditPreset || "") === "true";
  }

  function filtersApiBase() {
    const root = document.querySelector("#dashboard-root");
    const api = (root?.dataset?.dashboardUrl || "").trim();
    if (api) return api.replace(/\/query\/?$/, "/filters/");
    return "/api/reports/filters/";
  }

  function setPresetModalOpen(open) {
    const modal = document.getElementById("vmm-preset-hombre-modal");
    if (!modal) return;
    if (open) {
      modal.hidden = false;
      modal.classList.remove("hidden");
      modal.classList.add("flex");
      document.body.classList.add("overflow-hidden");
    } else {
      modal.classList.add("hidden");
      modal.classList.remove("flex");
      modal.hidden = true;
      document.body.classList.remove("overflow-hidden");
    }
  }

  function selectedPresetModalIds() {
    const sel = document.getElementById("vmm_preset_hombre_sa");
    if (!sel) return [];
    return Array.from(sel.selectedOptions)
      .map((o) => String(o.value).trim())
      .filter(Boolean);
  }

  async function loadPresetModalSuperArts(selectedIds) {
    const sel = document.getElementById("vmm_preset_hombre_sa");
    if (!sel) return false;
    const idSet = new Set((selectedIds || []).map(String));
    const resp = await fetch(`${filtersApiBase()}?type=superarts`, {
      headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
      credentials: "same-origin",
    });
    if (!resp.ok) throw new Error("No se pudo cargar el catálogo de SuperArt.");
    const json = await resp.json();
    const items = json.superarts || json.id_manuales || [];
    sel.innerHTML = "";
    const known = new Set();
    items.forEach((item) => {
      const value = String(item.value ?? item.id ?? "").trim();
      if (!value) return;
      known.add(value);
      const option = document.createElement("option");
      option.value = value;
      option.textContent = item.label || value;
      option.selected = idSet.has(value);
      sel.appendChild(option);
    });
    // Conservar ids del preset que no estén en el catálogo filtrado (visibles como chips).
    idSet.forEach((id) => {
      if (known.has(id)) return;
      const option = document.createElement("option");
      option.value = id;
      option.textContent = id;
      option.selected = true;
      sel.appendChild(option);
    });
    if (typeof window.initializeTagsFilter === "function") {
      window.initializeTagsFilter("vmm_preset_hombre_sa", "superarts");
    }
    return true;
  }

  async function openPresetConfigModal() {
    const statusEl = document.getElementById("vmm-preset-hombre-modal-status");
    const saveBtn = document.getElementById("vmm-preset-hombre-modal-save");
    if (statusEl) statusEl.textContent = "Cargando…";
    if (saveBtn) saveBtn.disabled = true;
    setPresetModalOpen(true);
    try {
      let ids = readPresetHombreIds();
      const apiUrl = getPresetApiUrl();
      if (apiUrl) {
        const resp = await fetch(apiUrl, {
          headers: { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" },
          credentials: "same-origin",
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(data.detail || "No se pudo leer el preset.");
        if (data.preset_hombre) {
          ids = Array.isArray(data.preset_hombre.id_manuales)
            ? data.preset_hombre.id_manuales.map(String)
            : [];
          writePresetHombreToReportConfig(data.preset_hombre);
          updatePresetHombreCountLabel(ids);
        }
      }
      await loadPresetModalSuperArts(ids);
      if (statusEl) {
        statusEl.textContent =
          ids.length > 0
            ? `${ids.length} SuperArt${ids.length === 1 ? "" : "s"} en el preset.`
            : "Preset vacío: buscá y agregá SuperArts.";
      }
    } catch (err) {
      if (statusEl) statusEl.textContent = err?.message || "Error al abrir la configuración.";
      showSynapAviso(err?.message || "No se pudo abrir la configuración del preset.", "error");
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  async function savePresetConfigModal() {
    const apiUrl = getPresetApiUrl();
    if (!apiUrl) {
      showSynapAviso("URL de configuración no disponible.", "error");
      return;
    }
    const statusEl = document.getElementById("vmm-preset-hombre-modal-status");
    const saveBtn = document.getElementById("vmm-preset-hombre-modal-save");
    const ids = selectedPresetModalIds();
    if (saveBtn) saveBtn.disabled = true;
    if (statusEl) statusEl.textContent = "Guardando…";
    try {
      const csrftoken = getCookie("csrftoken");
      const headers = {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      };
      if (csrftoken) headers["X-CSRFToken"] = csrftoken;
      const resp = await fetch(apiUrl, {
        method: "PATCH",
        headers,
        credentials: "same-origin",
        body: JSON.stringify({ id_manuales: ids }),
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.detail || "No se pudo guardar el preset.");
      const preset = data.preset_hombre || { id_manuales: ids, label: "Hombre" };
      writePresetHombreToReportConfig(preset);
      updatePresetHombreCountLabel(preset.id_manuales || ids);
      setPresetModalOpen(false);
      showSynapAviso(data.message || "Preset «Hombre» actualizado.", "ok");
    } catch (err) {
      if (statusEl) statusEl.textContent = err?.message || "Error al guardar.";
      showSynapAviso(err?.message || "No se pudo guardar el preset.", "error");
    } finally {
      if (saveBtn) saveBtn.disabled = false;
    }
  }

  function initPresetHombreConfig() {
    if (!canEditPreset()) return;
    const openBtn = document.getElementById("vmm-preset-hombre-config-btn");
    const closeBtn = document.getElementById("vmm-preset-hombre-modal-close");
    const cancelBtn = document.getElementById("vmm-preset-hombre-modal-cancel");
    const saveBtn = document.getElementById("vmm-preset-hombre-modal-save");
    const overlay = document.querySelector("[data-vmm-preset-overlay]");
    if (!openBtn) return;

    openBtn.addEventListener("click", () => {
      openPresetConfigModal().catch(() => {});
    });
    const close = () => setPresetModalOpen(false);
    closeBtn?.addEventListener("click", close);
    cancelBtn?.addEventListener("click", close);
    overlay?.addEventListener("click", close);
    saveBtn?.addEventListener("click", () => {
      savePresetConfigModal().catch(() => {});
    });
    document.addEventListener("keydown", (ev) => {
      if (ev.key !== "Escape") return;
      const modal = document.getElementById("vmm-preset-hombre-modal");
      if (modal && !modal.classList.contains("hidden")) close();
    });
  }

  function renderUmDesconocidas(extra) {
    const banner = document.getElementById("vmm-aviso-um-desconocidas");
    const ums = extra?.um_desconocidas;
    if (!Array.isArray(ums) || !ums.length) {
      if (banner) {
        banner.textContent = "";
        banner.classList.add("hidden");
      }
      return;
    }
    const lista = ums.join(", ");
    const msg =
      ums.length === 1
        ? `Unidad de medida no mapeada (${lista}). Se usó factor 1 para docenas.`
        : `${ums.length} unidades de medida no mapeadas (${lista}). Se usó factor 1 para docenas.`;
    if (banner) {
      banner.textContent = msg;
      banner.classList.remove("hidden");
    }
    showSynapAviso(msg, "aviso");
  }

  function setSuperArtSelection(ids) {
    const sel = document.getElementById("vmm_superarts_incluidos");
    if (!sel) return false;
    const idSet = new Set(ids.map(String));
    Array.from(sel.options).forEach((opt) => {
      opt.selected = idSet.has(String(opt.value));
    });
    sel.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  }

  function initPresetHombre() {
    const btn = document.getElementById("vmm-preset-hombre-btn");
    updatePresetHombreCountLabel(readPresetHombreIds());
    if (!btn) return;

    btn.addEventListener("click", () => {
      const ids = readPresetHombreIds();
      if (!ids.length) {
        const msg = canEditPreset()
          ? "El preset «Hombre» aún no tiene SuperArts. Usá «Configurar preset» para cargarlos."
          : "El preset «Hombre» aún no tiene SuperArts configurados en el informe. Contacte al administrador.";
        showSynapAviso(msg, "aviso");
        return;
      }
      if (!setSuperArtSelection(ids)) {
        showSynapAviso("No se pudo aplicar el preset: filtro SuperArt no disponible.", "error");
        return;
      }
      try {
        window.localStorage.setItem(PRESET_HOMBRE_KEY, "1");
      } catch (_e) {
        /* sin localStorage */
      }
      if (window.reportsFiltersSheet && typeof window.reportsFiltersSheet.updateChips === "function") {
        window.reportsFiltersSheet.updateChips();
      }
      showSynapAviso(`Preset «Hombre» aplicado (${ids.length} SuperArt${ids.length === 1 ? "" : "s"}).`, "ok");
    });
    initPresetHombreConfig();
  }

  function initSortControl() {
    const sel = document.getElementById("vmm-sort-select");
    if (!sel) return;
    sel.value = loadSortPref();
    sel.addEventListener("change", () => {
      saveSortPref(sel.value);
      if (_lastExtra) renderMatriz(_lastExtra);
    });
  }

  function renderAviso(extra, notes) {
    const el = document.getElementById("vmm-aviso-meses");
    if (!el) return;
    const msg = extra?.aviso_meses || (Array.isArray(notes) ? notes.find(Boolean) : "") || "";
    if (msg) {
      el.textContent = msg;
      el.classList.remove("hidden");
    } else {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }

  function renderCeldasMes(c, proyActiva, proyCls) {
    const base = c || { u: 0, f: 0 };
    let html = `<td class="px-1 py-1.5 text-right tabular-nums border-l border-slate-100 dark:border-slate-700/60">${fmtNum(base.u)}</td>`;
    html += `<td class="px-1 py-1.5 text-right tabular-nums">${fmtMoney(base.f)}</td>`;
    if (proyActiva) {
      html += `<td class="px-1 py-1.5 text-right tabular-nums ${proyCls}">${fmtNum(base.pu ?? 0)}</td>`;
      html += `<td class="px-1 py-1.5 text-right tabular-nums ${proyCls}">${fmtMoney(base.pf ?? 0)}</td>`;
    }
    return html;
  }

  function pickCompareSide(celda, side) {
    if (!celda) return { u: 0, f: 0 };
    if (celda.a || celda.b) {
      return celda[side] || { u: 0, f: 0 };
    }
    return celda;
  }

  function renderCeldasMesCompare(c, side, proyActiva, proyCls, labelSuffix) {
    const base = pickCompareSide(c, side);
    let html = `<td class="px-1 py-1.5 text-right tabular-nums border-l border-slate-100 dark:border-slate-700/60" title="${escHtml(labelSuffix)}">${fmtNum(base.u)}</td>`;
    html += `<td class="px-1 py-1.5 text-right tabular-nums">${fmtMoney(base.f)}</td>`;
    if (proyActiva) {
      html += `<td class="px-1 py-1.5 text-right tabular-nums ${proyCls}">${fmtNum(base.pu ?? 0)}</td>`;
      html += `<td class="px-1 py-1.5 text-right tabular-nums ${proyCls}">${fmtMoney(base.pf ?? 0)}</td>`;
    }
    return html;
  }

  function renderCeldasMesCompareDual(c, proyActiva, proyCls, nomA, nomB) {
    return (
      renderCeldasMesCompare(c, "a", proyActiva, proyCls, nomA || "A") +
      renderCeldasMesCompare(c, "b", proyActiva, proyCls, nomB || "B")
    );
  }

  function renderMesChips(meses, valoresMes, proyActiva, unidadHdr, side) {
    let html = '<div class="flex flex-wrap gap-1.5">';
    meses.forEach((m) => {
      const raw = (valoresMes || {})[m] || { u: 0, f: 0 };
      const c = side ? pickCompareSide(raw, side) : raw;
      let chip = `<span class="inline-flex flex-col rounded-md bg-slate-100 px-2 py-1 text-[10px] leading-tight text-slate-700 dark:bg-slate-800 dark:text-slate-200">`;
      chip += `<span class="font-semibold">${escHtml(fmtMesYm(m))}</span>`;
      chip += `<span>${unidadHdr} ${fmtNum(c.u)} · ${fmtMoney(c.f)}</span>`;
      if (proyActiva) {
        chip += `<span class="text-slate-500 dark:text-slate-400">proy ${fmtNum(c.pu ?? 0)} · ${fmtMoney(c.pf ?? 0)}</span>`;
      }
      chip += `</span>`;
      html += chip;
    });
    html += "</div>";
    return html;
  }

  function wireVendToggles(container, extra) {
    container.querySelectorAll(".vmm-vend-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const key = btn.getAttribute("data-vend-key") || "";
        const map = loadExpandedVendedores();
        map[key] = !map[key];
        saveExpandedVendedores(map);
        renderMatriz(extra);
      });
    });
  }

  function renderMatrizCards(extra, filas, meses, expanded, proyActiva) {
    const unidadHdr = extra?.modo_unidades === "docenas" ? "Doc." : "U.";
    const side = _activeCompareTab === "b" ? "b" : "a";
    const compareSide = isCompareActive(extra) ? side : null;
    let html = '<div class="vmm-cards-portrait space-y-3 p-3 pb-4">';

    filas.forEach((vend) => {
      const vkey = String(vend.cod ?? "");
      const isExp = Boolean(expanded[vkey]);
      const chev = isExp ? CHV.expandido : CHV.colapsado;
      const totRaw = vend.total || { u: 0, f: 0 };
      const tot = compareSide ? pickCompareSide(totRaw, compareSide) : totRaw;

      html += `<article class="rounded-xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900/40">`;
      html += `<button type="button" class="vmm-vend-toggle flex w-full min-h-[44px] items-center gap-2 px-3 py-2 text-left text-sm font-semibold text-slate-800 hover:bg-slate-50 dark:text-slate-100 dark:hover:bg-slate-800/60" data-vend-key="${escHtml(vkey)}" aria-expanded="${isExp}">`;
      html += `<span class="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center text-base" aria-hidden="true">${chev}</span>`;
      html += `<span class="min-w-0 flex-1">`;
      html += `<span class="block truncate">${escHtml(vend.nombre || vkey)}</span>`;
      html += `<span class="block text-[11px] font-normal text-slate-500 dark:text-slate-400">${unidadHdr} ${fmtNum(tot.u)} · ${fmtMoney(tot.f)}</span>`;
      html += `</span></button>`;

      if (isExp) {
        html += `<div class="space-y-3 border-t border-slate-100 px-3 py-3 dark:border-slate-700">`;
        (vend.clientes || []).forEach((cli) => {
          html += `<div class="rounded-lg bg-slate-50 p-2 dark:bg-slate-800/50">`;
          html += `<p class="text-xs font-medium text-slate-800 dark:text-slate-100">${escHtml(cli.nombre || cli.cod)}</p>`;
          html += renderMesChips(meses, cli.valores_mes, proyActiva, unidadHdr, compareSide);
          html += `</div>`;
        });
        html += `</div>`;
      } else {
        html += `<div class="border-t border-slate-100 px-3 py-2 dark:border-slate-700">`;
        html += renderMesChips(meses, vend.totales_mes, proyActiva, unidadHdr, compareSide);
        html += `</div>`;
      }

      html += `</article>`;
    });

    html += "</div>";
    return html;
  }

  function renderMatrizTable(extra, filas, meses, expanded, proyActiva) {
    const compareOn = isCompareActive(extra);
    const nomA = extra?.compare?.marca_a?.nombre || "A";
    const nomB = extra?.compare?.marca_b?.nombre || "B";
    const portraitSide = _activeCompareTab === "b" ? "b" : "a";
    const showDual = compareOn && useFullCompareMatrix();
    const showSingleCompare = compareOn && useComparePortraitTabs(extra);

    const colspanMes = proyActiva ? 4 : 2;
    const colspanBlock = showDual ? colspanMes * 2 : colspanMes;
    const proyCls = "text-slate-500 dark:text-slate-400";
    const unidadHdr = extra?.modo_unidades === "docenas" ? "Doc." : "U.";
    const stickyCls =
      "sticky left-0 z-[5] bg-slate-50 dark:bg-slate-800/95 shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)] dark:shadow-[2px_0_4px_-2px_rgba(0,0,0,0.35)]";

    let thead = `<thead class="sticky top-0 z-10 bg-slate-100 dark:bg-slate-900"><tr>`;
    thead += `<th class="px-2 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-slate-600 dark:text-slate-300 min-w-[180px] ${stickyCls}">Vendedor / Cliente</th>`;
    meses.forEach((m) => {
      if (showDual) {
        thead += `<th colspan="${colspanBlock}" class="px-1 py-2 text-center text-[10px] font-semibold uppercase text-slate-600 dark:text-slate-300 border-l border-slate-200 dark:border-slate-700">${escHtml(fmtMesYm(m))}</th>`;
      } else {
        thead += `<th colspan="${colspanMes}" class="px-1 py-2 text-center text-[10px] font-semibold uppercase text-slate-600 dark:text-slate-300 border-l border-slate-200 dark:border-slate-700">${escHtml(fmtMesYm(m))}</th>`;
      }
    });
    thead += `<th colspan="${colspanBlock}" class="px-1 py-2 text-center text-[10px] font-semibold uppercase text-slate-700 dark:text-slate-200 border-l border-slate-300 dark:border-slate-600 bg-slate-200/80 dark:bg-slate-800">Total</th>`;
    thead += `</tr>`;

    if (showDual) {
      thead += `<tr><th class="px-2 py-1 ${stickyCls}"></th>`;
      meses.forEach(() => {
        thead += `<th colspan="${colspanMes}" class="px-1 py-1 text-center text-[9px] font-semibold text-violet-700 dark:text-violet-300 border-l border-slate-200 dark:border-slate-700">${escHtml(nomA)}</th>`;
        thead += `<th colspan="${colspanMes}" class="px-1 py-1 text-center text-[9px] font-semibold text-indigo-700 dark:text-indigo-300 border-l border-slate-200 dark:border-slate-700">${escHtml(nomB)}</th>`;
      });
      thead += `<th colspan="${colspanMes}" class="px-1 py-1 text-center text-[9px] font-semibold text-violet-700 dark:text-violet-300 border-l border-slate-300 dark:border-slate-600">${escHtml(nomA)}</th>`;
      thead += `<th colspan="${colspanMes}" class="px-1 py-1 text-center text-[9px] font-semibold text-indigo-700 dark:text-indigo-300 border-l border-slate-300 dark:border-slate-600">${escHtml(nomB)}</th>`;
      thead += `</tr><tr><th class="px-2 py-1 ${stickyCls}"></th>`;
    } else {
      thead += `<tr>`;
      thead += `<th class="px-2 py-1 ${stickyCls}"></th>`;
    }

    const subHdr = (suffix) => {
      let h = `<th class="px-1 py-1 text-right text-[9px] text-slate-500">${unidadHdr}${suffix ? ` ${suffix}` : ""}</th><th class="px-1 py-1 text-right text-[9px] text-slate-500">$</th>`;
      if (proyActiva) {
        h += `<th class="px-1 py-1 text-right text-[9px] text-slate-400">${unidadHdr} proy</th><th class="px-1 py-1 text-right text-[9px] text-slate-400">$ proy</th>`;
      }
      return h;
    };
    meses.forEach(() => {
      if (showDual) {
        thead += subHdr("A");
        thead += subHdr("B");
      } else {
        thead += subHdr(showSingleCompare ? (portraitSide === "b" ? "B" : "A") : "");
      }
    });
    if (showDual) {
      thead += subHdr("A");
      thead += subHdr("B");
    } else {
      thead += subHdr(showSingleCompare ? (portraitSide === "b" ? "B" : "A") : "").replace(/text-slate-500/g, "text-slate-600 font-semibold");
    }
    thead += `</tr></thead>`;

    const renderRowCells = (valores, total) => {
      let rowHtml = "";
      meses.forEach((m) => {
        const c = (valores || {})[m] || { u: 0, f: 0 };
        if (showDual) {
          rowHtml += renderCeldasMesCompareDual(c, proyActiva, proyCls, nomA, nomB);
        } else if (showSingleCompare) {
          rowHtml += renderCeldasMesCompare(c, portraitSide, proyActiva, proyCls, portraitSide === "b" ? nomB : nomA);
        } else {
          rowHtml += renderCeldasMes(c, proyActiva, proyCls);
        }
      });
      const tot = total || { u: 0, f: 0 };
      if (showDual) {
        rowHtml += renderCeldasMesCompareDual(tot, proyActiva, `${proyCls} font-semibold`, nomA, nomB);
      } else if (showSingleCompare) {
        rowHtml += renderCeldasMesCompare(tot, portraitSide, proyActiva, `${proyCls} font-semibold`, "");
      } else {
        rowHtml += renderCeldasMes(tot, proyActiva, `${proyCls} font-semibold`).replace(
          "border-l border-slate-100",
          "border-l border-slate-200 dark:border-slate-600 font-semibold"
        );
      }
      return rowHtml;
    };

    let tbody = "<tbody>";
    filas.forEach((vend) => {
      const vkey = String(vend.cod ?? "");
      const isExp = Boolean(expanded[vkey]);
      const chev = isExp ? CHV.expandido : CHV.colapsado;
      tbody += `<tr class="bg-slate-50 dark:bg-slate-800/80 font-semibold text-xs text-slate-800 dark:text-slate-100 border-t border-slate-200 dark:border-slate-700">`;
      tbody += `<td class="px-2 py-1.5 ${stickyCls}">`;
      tbody += `<button type="button" class="vmm-vend-toggle inline-flex min-h-[44px] w-full items-center gap-1 text-left hover:text-sky-600 dark:hover:text-sky-400" data-vend-key="${escHtml(vkey)}" aria-expanded="${isExp}">`;
      tbody += `<span class="inline-flex min-h-[44px] min-w-[44px] shrink-0 items-center justify-center" aria-hidden="true">${chev}</span>`;
      tbody += `<span class="min-w-0 truncate">${escHtml(vend.nombre || vkey)}</span>`;
      tbody += `</button></td>`;
      tbody += renderRowCells(vend.totales_mes, vend.total);
      tbody += `</tr>`;

      if (isExp) {
        (vend.clientes || []).forEach((cli) => {
          tbody += `<tr class="text-[11px] text-slate-700 dark:text-slate-300">`;
          tbody += `<td class="px-2 py-1 pl-8 ${stickyCls} bg-white dark:bg-slate-900">${escHtml(cli.nombre || cli.cod)}</td>`;
          tbody += renderRowCells(cli.valores_mes, cli.total).replace(/py-1\.5/g, "py-1");
          tbody += `</tr>`;
        });
      }
    });
    tbody += "</tbody>";

    return `<div class="overflow-x-auto"><table class="vmm-matriz-table w-full min-w-max border-collapse text-xs">${thead}${tbody}</table></div>`;
  }

  function renderMatriz(extra) {
    const container = document.getElementById("vmm-matriz-container");
    if (!container) return;

    updateMatrizScrollHint();

    const meses = Array.isArray(extra?.meses) ? extra.meses : [];
    const filasRaw = Array.isArray(extra?.filas) ? extra.filas : [];
    const sortVal = loadSortPref();
    const filas = sortFilas(filasRaw, sortVal);
    const expanded = loadExpandedVendedores();
    const proyActiva = Boolean(extra?.proyeccion?.activa);

    if (!meses.length) {
      container.innerHTML =
        '<p class="px-3 py-4 text-xs text-slate-500 dark:text-slate-400">Sin datos para el período y filtros seleccionados.</p>';
      return;
    }

    if (isPortraitMobile() && !(isCompareActive(extra) && useComparePortraitTabs(extra))) {
      container.innerHTML = renderMatrizCards(extra, filas, meses, expanded, proyActiva);
    } else {
      container.innerHTML = renderMatrizTable(extra, filas, meses, expanded, proyActiva);
    }

    syncCompareTabUi();

    wireVendToggles(container, extra);
  }

  function processData(response) {
    const meta = response?.meta || {};
    const extra = meta.extra || {};
    _lastExtra = extra;
    renderKpis(extra);
    renderAviso(extra, response?.notes);
    renderUmDesconocidas(extra);
    renderMatriz(extra);

    const periodEl = document.getElementById("vmm-summary-period");
    if (periodEl) {
      const fa = meta.filters_applied || {};
      const fmt = (s) => {
        if (!s) return "—";
        const p = String(s).split("-");
        return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : s;
      };
      periodEl.textContent = `Período: ${fmt(fa.fecha_inicio_facturacion)} al ${fmt(fa.fecha_fin_facturacion)}`;
    }
  }

  function initResizeHandler() {
    window.addEventListener("resize", () => {
      if (_resizeTimer) window.clearTimeout(_resizeTimer);
      _resizeTimer = window.setTimeout(() => {
        if (_lastExtra) renderMatriz(_lastExtra);
      }, 150);
    });
    window.matchMedia("(orientation: portrait)").addEventListener("change", () => {
      if (_lastExtra) renderMatriz(_lastExtra);
    });
  }

  function initModoComparacion() {
    const hidden = document.getElementById("vmm_modo_comparacion");
    const block = document.getElementById("vmm-comparar-selectores");
    const marcasWrap = document.querySelector("#vmm_marcas_incluidos_tags_container")?.closest("label");
    const btns = document.querySelectorAll("#vmm-modo-comparacion-buttons .vmm-cmp-btn");
    if (!hidden || !btns.length) return;

    const applyUi = (modo) => {
      const cmp = modo === "comparar";
      hidden.value = cmp ? "comparar" : "una";
      if (block) block.classList.toggle("hidden", !cmp);
      if (marcasWrap) marcasWrap.classList.toggle("hidden", cmp);
      btns.forEach((btn) => {
        const active = btn.getAttribute("data-modo-comparacion") === hidden.value;
        btn.classList.toggle("border-sky-500", active);
        btn.classList.toggle("bg-sky-50", active);
        btn.classList.toggle("dark:bg-sky-900/20", active);
        btn.classList.toggle("text-sky-700", active);
        btn.classList.toggle("dark:text-sky-300", active);
        btn.classList.toggle("shadow-md", active);
        btn.classList.toggle("border-slate-300", !active);
        btn.classList.toggle("dark:border-slate-600", !active);
        btn.classList.toggle("bg-white", !active);
        btn.classList.toggle("dark:bg-slate-800", !active);
        btn.classList.toggle("text-slate-700", !active);
        btn.classList.toggle("dark:text-slate-300", !active);
      });
    };

    applyUi(hidden.value || "una");
    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        applyUi(btn.getAttribute("data-modo-comparacion"));
        if (window.reportsFiltersSheet && typeof window.reportsFiltersSheet.updateChips === "function") {
          window.reportsFiltersSheet.updateChips();
        }
      });
    });
  }

  function populateMarcaCompareSelects(options) {
    ["vmm_marca_a", "vmm_marca_b"].forEach((id) => {
      const sel = document.getElementById(id);
      if (!sel) return;
      const prev = sel.value;
      sel.innerHTML = '<option value="">Seleccionar…</option>';
      (options || []).forEach((opt) => {
        const o = document.createElement("option");
        o.value = String(opt.value ?? opt.id ?? "");
        o.textContent = String(opt.label ?? opt.text ?? opt.value ?? "");
        sel.appendChild(o);
      });
      if (prev) sel.value = prev;
    });
  }

  function initCompareTabs() {
    const tabA = document.getElementById("vmm-tab-marca-a");
    const tabB = document.getElementById("vmm-tab-marca-b");
    if (!tabA || !tabB) return;
    syncCompareTabUi();
    tabA.addEventListener("click", () => {
      saveCompareTab("a");
      if (_lastExtra) renderMatriz(_lastExtra);
    });
    tabB.addEventListener("click", () => {
      saveCompareTab("b");
      if (_lastExtra) renderMatriz(_lastExtra);
    });
  }

  function initExportPwa() {
    window.vmmDownloadExportBlob = function (blob, filename) {
      try {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename || "Ventas_marcas_mensual.xlsx";
        a.rel = "noopener";
        a.style.display = "none";
        document.body.appendChild(a);
        a.click();
        window.setTimeout(() => {
          window.URL.revokeObjectURL(url);
          a.remove();
        }, 1000);
        return true;
      } catch (_e) {
        showSynapAviso(
          "No se pudo iniciar la descarga. En Safari iOS, mantenga pulsado el enlace de exportación o use «Compartir» → «Guardar en Archivos».",
          "aviso"
        );
        return false;
      }
    };
  }

  window.ventasMarcasMensualHandler = {
    processData,
    sortFilas,
    loadSortPref,
    validateCompareFilters,
    populateMarcaCompareSelects,
    showSynapAviso,
  };

  function initTcHint() {
    const tcEl = document.getElementById("vmm_tc");
    const hintEl = document.getElementById("vmm_tc_hint");
    if (!tcEl || !hintEl) return;

    function refreshHint() {
      if (tcEl.value && String(tcEl.value).trim() !== "") {
        hintEl.classList.add("hidden");
        hintEl.textContent = "";
        return;
      }
      fetch("/contabilidad/api/cotizacion/vigente/", {
        credentials: "same-origin",
        headers: { "X-Requested-With": "XMLHttpRequest", Accept: "application/json" },
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (!data || !data.ok || data.valor == null) return;
          hintEl.textContent = `TC vigente BCRA: ${Number(data.valor).toLocaleString("es-AR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })} (automático si deja vacío)`;
          hintEl.classList.remove("hidden");
        })
        .catch(() => {
          /* silencioso */
        });
    }

    tcEl.addEventListener("input", refreshHint);
    refreshHint();
  }

  function initVmmUi() {
    initPresetHombre();
    initSortControl();
    initModoComparacion();
    initCompareTabs();
    initExportPwa();
    initTcHint();
    initResizeHandler();
    updateMatrizScrollHint();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initVmmUi);
  } else {
    initVmmUi();
  }
})();
