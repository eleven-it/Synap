/**
 * Informe Ventas mensuales licenciatarios — preview QA, match modal Synap.
 */
(function () {
  "use strict";

  const dashboardRoot = document.querySelector("#dashboard-root");
  const reportSlug = dashboardRoot?.dataset?.reportSlug || "";
  if (reportSlug !== "ventas-mensuales-licenciatarios") {
    return;
  }

  const filtersRoot = document.getElementById("vml-filters-root");
  const matchesApiUrl = filtersRoot?.dataset?.matchesApiUrl || "";
  const anetClientsApiUrl = filtersRoot?.dataset?.anetClientsApiUrl || "";
  const superartQaApiUrl = filtersRoot?.dataset?.superartQaApiUrl || "";
  const canEditMatch = filtersRoot?.dataset?.canEditMatch === "true";
  const canEditSuperart = filtersRoot?.dataset?.canEditSuperart === "true";

  let _lastQaSuperarts = [];

  const NUM = new Intl.NumberFormat("es-AR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
  const ARS = new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function fmtIsoToDisplay(iso) {
    if (!iso) return "—";
    const p = String(iso).slice(0, 10).split("-");
    return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : iso;
  }

  function showAviso(texto, tipo) {
    if (typeof window.mprShowAviso === "function") {
      window.mprShowAviso(texto, tipo || "info");
      return;
    }
    if (typeof window.SynapMessages !== "undefined" && window.SynapMessages.show) {
      window.SynapMessages.show(texto, tipo || "info");
    }
  }

  function getCsrfToken() {
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function syncSummaryPeriod(meta) {
    const el = document.getElementById("vml-summary-period");
    if (!el) return;
    const fa = meta?.filters_applied || {};
    const fi = fa.fecha_inicio_facturacion || document.getElementById("fecha_inicio_facturacion")?.value;
    const ff = fa.fecha_fin_facturacion || document.getElementById("fecha_fin_facturacion")?.value;
    const pack = fa.pack_id || document.getElementById("vml_pack_id")?.value || "—";
    el.textContent = `Pack ${pack} · ${fmtIsoToDisplay(fi)} al ${fmtIsoToDisplay(ff)}`;
  }

  function renderQaPanel(extra) {
    const panel = document.getElementById("vml-qa-panel");
    if (!panel) return;
    const pending = Array.isArray(extra?.pending_clients) ? extra.pending_clients : [];
    const qaArts = Array.isArray(extra?.qa_superarts) ? extra.qa_superarts : [];
    _lastQaSuperarts = qaArts.slice();
    const pendingEl = document.getElementById("vml-qa-pending-count");
    const qaEl = document.getElementById("vml-qa-superart-count");
    const listEl = document.getElementById("vml-qa-pending-list");
    const superartBlock = document.getElementById("vml-qa-superart-block");
    const superartListEl = document.getElementById("vml-qa-superart-list");
    if (pendingEl) pendingEl.textContent = String(pending.length);
    if (qaEl) qaEl.textContent = String(qaArts.length);
    if (listEl) {
      if (!pending.length) {
        listEl.innerHTML = '<li class="text-xs text-slate-500 dark:text-slate-400">Sin clientes pendientes de match.</li>';
      } else {
        listEl.innerHTML = pending
          .slice(0, 8)
          .map(
            (p) =>
              `<li class="text-xs text-amber-800 dark:text-amber-200">${escHtml(p.display_name || p.seed_key || "—")}</li>`,
          )
          .join("");
      }
    }
    if (superartBlock && superartListEl) {
      if (!qaArts.length) {
        superartBlock.classList.add("hidden");
        superartListEl.innerHTML = "";
      } else {
        superartBlock.classList.remove("hidden");
        superartListEl.innerHTML = qaArts
          .slice(0, 12)
          .map((code) => `<li class="text-xs text-violet-900 dark:text-violet-100">${escHtml(code)}</li>`)
          .join("");
      }
    }
    panel.classList.toggle("hidden", !pending.length && !qaArts.length);
    updateSuperartBadgeCount(qaArts.length);
  }

  function updateSuperartBadgeCount(count) {
    const badge = document.getElementById("vml-superart-badge");
    if (!badge) return;
    const n = Number(count) || 0;
    if (n > 0) {
      badge.textContent = String(n);
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  function unidadLabel(unitMode) {
    return String(unitMode || "").toLowerCase() === "dozens" ? "Docenas" : "Packs";
  }

  function escHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function escAttr(value) {
    return String(value ?? "").replace(/"/g, "&quot;");
  }

  function fmtMesYm(ym) {
    const s = String(ym || "");
    if (s.length !== 6) return s;
    const meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
    const mi = Number(s.slice(4, 6)) - 1;
    return `${meses[mi] || s.slice(4)} ${s.slice(0, 4)}`;
  }

  function pivotClientMonths(data, extra) {
    const year = Number(extra?.year) || new Date().getFullYear();
    const monthFrom = Number(extra?.month_from) || 1;
    const monthTo = Number(extra?.month_to) || 12;
    const meses = [];
    for (let m = monthFrom; m <= monthTo; m += 1) {
      meses.push(`${year}${String(m).padStart(2, "0")}`);
    }
    const byId = new Map();
    (Array.isArray(data) ? data : []).forEach((row) => {
      const id = String(row.identity || row.cliente || "");
      if (!id) return;
      let rec = byId.get(id);
      if (!rec) {
        rec = {
          identity: id,
          cliente: row.cliente || "—",
          pendiente: Boolean(row.pendiente),
          months: {},
          totU: 0,
          totF: 0,
        };
        byId.set(id, rec);
      }
      rec.months[String(row.anio_mes || "")] = {
        u: Number(row.unidades) || 0,
        f: Number(row.facturacion) || 0,
      };
      rec.totU += Number(row.unidades) || 0;
      rec.totF += Number(row.facturacion) || 0;
    });
    const filas = Array.from(byId.values()).sort((a, b) => b.totF - a.totF || a.cliente.localeCompare(b.cliente, "es"));
    return { meses, filas };
  }

  function renderMatriz(data, extra) {
    const container = document.getElementById("vml-matriz-container");
    if (!container) return;
    const { meses, filas } = pivotClientMonths(data, extra);
    const q = String(document.getElementById("vml-matriz-search")?.value || "")
      .trim()
      .toLowerCase();
    const visible = q
      ? filas.filter((f) => String(f.cliente).toLowerCase().includes(q) || String(f.identity).toLowerCase().includes(q))
      : filas;
    if (!filas.length) {
      container.innerHTML =
        '<p class="px-3 py-4 text-xs text-slate-500 dark:text-slate-400">Sin datos para el pack y período seleccionados.</p>';
      return;
    }
    if (!visible.length) {
      container.innerHTML =
        '<p class="px-3 py-4 text-xs text-slate-500 dark:text-slate-400">Ningún cliente coincide con la búsqueda.</p>';
      return;
    }
    const unidadHdr = unidadLabel(extra?.unit_mode);
    const sticky =
      "sticky left-0 z-[5] bg-slate-50 dark:bg-slate-800/95 shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]";
    const stickyCli =
      "sticky left-0 z-[5] bg-white dark:bg-slate-900 shadow-[2px_0_4px_-2px_rgba(0,0,0,0.06)]";
    let html = '<table class="min-w-full border-collapse text-xs">';
    html += '<thead class="sticky top-0 z-10 bg-slate-100/95 shadow-sm backdrop-blur-sm dark:bg-slate-900/95"><tr>';
    html += `<th scope="col" class="px-2 py-2.5 text-left text-[10px] font-bold uppercase tracking-wide text-slate-600 dark:text-slate-300 min-w-[14rem] ${sticky}">Cliente</th>`;
    meses.forEach((ym) => {
      html += `<th scope="colgroup" colspan="2" class="px-1 py-2.5 text-center text-[10px] font-bold uppercase tracking-wide text-sky-800 dark:text-sky-200 border-l border-sky-200/70 dark:border-sky-900/50 bg-sky-50/50 dark:bg-sky-950/20">${escHtml(fmtMesYm(ym))}</th>`;
    });
    html += '<th scope="colgroup" colspan="2" class="px-1 py-2.5 text-center text-[10px] font-bold uppercase tracking-wide text-emerald-900 dark:text-emerald-100 border-l border-emerald-300/80 dark:border-emerald-800 bg-emerald-100/70 dark:bg-emerald-950/40">Total</th>';
    html += "</tr><tr>";
    html += `<th class="px-2 py-1 ${sticky}"></th>`;
    const sub = (isTotal) => {
      const uCls = isTotal
        ? "px-1.5 py-1.5 text-right text-[9px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-200 bg-emerald-50/80 dark:bg-emerald-950/30"
        : "px-1.5 py-1.5 text-right text-[9px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400";
      const fCls = isTotal
        ? "px-1.5 py-1.5 text-right text-[9px] font-bold uppercase tracking-wide text-emerald-800 dark:text-emerald-200 bg-emerald-50/80 dark:bg-emerald-950/30"
        : "px-1.5 py-1.5 text-right text-[9px] font-semibold uppercase tracking-wide text-emerald-700/80 dark:text-emerald-300/80";
      return `<th scope="col" class="${uCls}">${escHtml(unidadHdr)}</th><th scope="col" class="${fCls}">Monto</th>`;
    };
    meses.forEach(() => {
      html += sub(false);
    });
    html += sub(true);
    html += "</tr></thead><tbody>";
    visible.forEach((fila, idx) => {
      const zebra = idx % 2 === 1 ? "bg-slate-50/80 dark:bg-slate-900/40" : "bg-white dark:bg-slate-950";
      const nameCls = fila.pendiente
        ? "text-amber-800 dark:text-amber-200"
        : "text-slate-800 dark:text-slate-100";
      html += `<tr class="${zebra}">`;
      html += `<th scope="row" class="px-2 py-1.5 text-left font-medium ${nameCls} ${stickyCli}">${escHtml(fila.cliente)}</th>`;
      meses.forEach((ym) => {
        const cell = fila.months[ym] || { u: 0, f: 0 };
        const empty = !cell.u && !cell.f;
        html += `<td class="px-1.5 py-1.5 text-right tabular-nums border-l border-slate-100 dark:border-slate-800 ${empty ? "text-slate-300 dark:text-slate-600" : "text-slate-700 dark:text-slate-200"}">${empty ? "—" : NUM.format(cell.u)}</td>`;
        html += `<td class="px-1.5 py-1.5 text-right tabular-nums ${empty ? "text-slate-300 dark:text-slate-600" : "text-emerald-800 dark:text-emerald-200"}">${empty ? "—" : ARS.format(cell.f)}</td>`;
      });
      html += `<td class="px-1.5 py-1.5 text-right tabular-nums font-semibold border-l border-emerald-200/80 dark:border-emerald-800 text-slate-800 dark:text-slate-100">${NUM.format(fila.totU)}</td>`;
      html += `<td class="px-1.5 py-1.5 text-right tabular-nums font-semibold text-emerald-900 dark:text-emerald-100">${ARS.format(fila.totF)}</td>`;
      html += "</tr>";
    });
    html += "</tbody>";
    const colTot = { totU: 0, totF: 0, months: {} };
    meses.forEach((ym) => {
      colTot.months[ym] = { u: 0, f: 0 };
    });
    visible.forEach((fila) => {
      colTot.totU += fila.totU;
      colTot.totF += fila.totF;
      meses.forEach((ym) => {
        const cell = fila.months[ym] || { u: 0, f: 0 };
        colTot.months[ym].u += cell.u;
        colTot.months[ym].f += cell.f;
      });
    });
    const stickyTot =
      "sticky left-0 z-[5] bg-slate-200/95 dark:bg-slate-700/95 shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]";
    html += '<tfoot class="sticky bottom-0 z-[6]"><tr class="bg-slate-200/95 dark:bg-slate-700/95 font-bold border-t-2 border-slate-300 dark:border-slate-600">';
    html += `<th scope="row" class="px-2 py-2 text-left text-[10px] uppercase tracking-wide text-slate-800 dark:text-slate-100 ${stickyTot}">Totales</th>`;
    meses.forEach((ym) => {
      const cell = colTot.months[ym];
      const empty = !cell.u && !cell.f;
      html += `<td class="px-1.5 py-2 text-right tabular-nums border-l border-slate-300/60 dark:border-slate-600 text-slate-800 dark:text-slate-100">${empty ? "—" : NUM.format(cell.u)}</td>`;
      html += `<td class="px-1.5 py-2 text-right tabular-nums text-emerald-900 dark:text-emerald-100">${empty ? "—" : ARS.format(cell.f)}</td>`;
    });
    html += `<td class="px-1.5 py-2 text-right tabular-nums border-l border-emerald-400/80 dark:border-emerald-700 text-slate-900 dark:text-slate-50">${NUM.format(colTot.totU)}</td>`;
    html += `<td class="px-1.5 py-2 text-right tabular-nums text-emerald-950 dark:text-emerald-50">${ARS.format(colTot.totF)}</td>`;
    html += "</tr></tfoot></table>";
    container.innerHTML = html;
  }

  let _lastMatriz = { data: [], extra: {} };

  function renderMatrizAndStore(data, extra) {
    _lastMatriz = { data: data || [], extra: extra || {} };
    renderMatriz(_lastMatriz.data, _lastMatriz.extra);
  }

  window.vmlOnDashboardResult = function vmlOnDashboardResult(result) {
    const meta = result?.meta || {};
    const extra = meta.extra || {};
    syncSummaryPeriod(meta);
    renderQaPanel(extra);
    renderMatrizAndStore(result?.data || [], extra);
    refreshPendingBadge();
    refreshSuperartBadge();
  };

  function openModal(modal) {
    if (!modal) return;
    modal.hidden = false;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }

  function closeModal(modal) {
    if (!modal) return;
    modal.hidden = true;
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }

  async function fetchMatches(estado) {
    const url = estado ? `${matchesApiUrl}?estado=${encodeURIComponent(estado)}` : matchesApiUrl;
    const res = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error("No se pudo cargar el listado de matches.");
    return res.json();
  }

  function renderMatchList(matches) {
    const list = document.getElementById("vml-match-list");
    if (!list) return;
    if (!matches.length) {
      list.innerHTML = '<p class="p-4 text-xs text-slate-500 dark:text-slate-400 m-0">No hay registros para mostrar.</p>';
      return;
    }
    list.innerHTML = matches
      .map((m) => {
        const estadoLabel = m.pending ? "Pendiente" : "Matcheado";
        const anet = m.anet_cliente_id ? ` → ANET #${m.anet_cliente_id}` : "";
        const actions = canEditMatch
          ? m.pending
            ? `<button type="button" class="vml-link-btn text-xs font-semibold text-sky-600 dark:text-sky-400" data-match-id="${m.id}" data-seed-name="${String(m.seed_customer_name || "").replace(/"/g, "&quot;")}">Vincular</button>`
            : `<button type="button" class="vml-undo-btn text-xs font-semibold text-red-600 dark:text-red-400" data-match-id="${m.id}" data-seed-name="${String(m.seed_customer_name || "").replace(/"/g, "&quot;")}">Desvincular</button>`
          : "";
        return `<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3">
          <div class="min-w-0">
            <p class="text-xs font-semibold text-slate-800 dark:text-slate-100 m-0 truncate">${m.seed_customer_name || m.seed_key}</p>
            <p class="text-[10px] text-slate-500 dark:text-slate-400 m-0">${estadoLabel}${anet} · ${m.updated_at_display || "—"}</p>
          </div>
          ${actions}
        </div>`;
      })
      .join("");
  }

  async function refreshPendingBadge() {
    const badge = document.getElementById("vml-pending-badge");
    if (!badge || !matchesApiUrl) return;
    try {
      const data = await fetchMatches("pending");
      const n = data.pending_count || 0;
      if (n > 0) {
        badge.textContent = String(n);
        badge.classList.remove("hidden");
      } else {
        badge.classList.add("hidden");
      }
    } catch (_e) {
      badge.classList.add("hidden");
    }
  }

  let searchTimer = null;

  async function searchAnetClients(q) {
    const results = document.getElementById("vml-anet-results");
    if (!results || !anetClientsApiUrl) return;
    if (q.length < 2) {
      results.innerHTML = "";
      return;
    }
    const res = await fetch(`${anetClientsApiUrl}?q=${encodeURIComponent(q)}`, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!res.ok) {
      results.innerHTML = '<li class="px-3 py-2 text-xs text-red-600">Error al buscar clientes.</li>';
      return;
    }
    const data = await res.json();
    const items = data.results || [];
    if (!items.length) {
      results.innerHTML = '<li class="px-3 py-2 text-xs text-slate-500">Sin coincidencias.</li>';
      return;
    }
    results.innerHTML = items
      .map(
        (r) =>
          `<li><button type="button" class="vml-anet-pick w-full text-left px-3 py-2 text-xs hover:bg-sky-50 dark:hover:bg-sky-900/30" data-id="${r.id}" data-text="${String(r.text || "").replace(/"/g, "&quot;")}">#${r.id} — ${r.text}</button></li>`,
      )
      .join("");
  }

  async function applyMatch(matchId, anetId) {
    const res = await fetch(`${matchesApiUrl}${matchId}/`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      credentials: "same-origin",
      body: JSON.stringify({ action: "apply", anet_cliente_id: Number(anetId) }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "No se pudo vincular el cliente.");
    return data;
  }

  async function undoMatch(matchId) {
    const res = await fetch(`${matchesApiUrl}${matchId}/`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      credentials: "same-origin",
      body: JSON.stringify({ action: "undo" }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "No se pudo desvincular.");
    return data;
  }

  async function refreshSuperartBadge() {
    const badge = document.getElementById("vml-superart-badge");
    if (!badge || !superartQaApiUrl) {
      updateSuperartBadgeCount(_lastQaSuperarts.length);
      return;
    }
    try {
      const data = await fetchSuperartPending();
      const apiCount = data.pending_count || 0;
      const merged = Math.max(apiCount, _lastQaSuperarts.length);
      updateSuperartBadgeCount(merged);
    } catch (_e) {
      updateSuperartBadgeCount(_lastQaSuperarts.length);
    }
  }

  async function fetchSuperartPending() {
    const res = await fetch(superartQaApiUrl, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    if (!res.ok) throw new Error("No se pudo cargar SuperArt pendientes.");
    return res.json();
  }

  function renderSuperartList(pending) {
    const list = document.getElementById("vml-superart-list");
    if (!list) return;
    const merged = new Map();
    (Array.isArray(pending) ? pending : []).forEach((p) => {
      merged.set(String(p.superart || ""), p);
    });
    _lastQaSuperarts.forEach((code) => {
      const key = String(code || "").trim();
      if (key && !merged.has(key)) {
        merged.set(key, { superart: key, occurrence_count: 0 });
      }
    });
    const items = Array.from(merged.values());
    if (!items.length) {
      list.innerHTML =
        '<p class="p-4 text-xs text-slate-500 dark:text-slate-400 m-0">No hay SuperArt pendientes de clasificar.</p>';
      return;
    }
    list.innerHTML = items
      .map((p) => {
        const raw = String(p.superart || "—");
        const code = escHtml(raw);
        const attr = escAttr(raw);
        const count = Number(p.occurrence_count) || 0;
        const meta = count > 0 ? `${count} ocurrencia(s)` : "En preview actual";
        const actions = canEditSuperart
          ? `<div class="flex flex-wrap gap-2 shrink-0">
              <button type="button" class="vml-superart-men-btn inline-flex items-center min-h-[36px] px-3 py-1.5 text-[11px] font-semibold rounded-lg border border-sky-400 bg-sky-50 dark:bg-sky-900/30 text-sky-800 dark:text-sky-200 hover:bg-sky-100 dark:hover:bg-sky-900/50" data-superart="${attr}">Men</button>
              <button type="button" class="vml-superart-women-btn inline-flex items-center min-h-[36px] px-3 py-1.5 text-[11px] font-semibold rounded-lg border border-pink-400 bg-pink-50 dark:bg-pink-900/30 text-pink-800 dark:text-pink-200 hover:bg-pink-100 dark:hover:bg-pink-900/50" data-superart="${attr}">Women</button>
            </div>`
          : "";
        return `<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3">
          <div class="min-w-0">
            <p class="text-xs font-semibold text-slate-800 dark:text-slate-100 m-0 truncate">${code}</p>
            <p class="text-[10px] text-slate-500 dark:text-slate-400 m-0">${escHtml(meta)}</p>
          </div>
          ${actions}
        </div>`;
      })
      .join("");
  }

  async function classifySuperart(superart, genero) {
    const res = await fetch(superartQaApiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
      credentials: "same-origin",
      body: JSON.stringify({ superart, genero }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "No se pudo clasificar el SuperArt.");
    return data;
  }

  function removeLocalSuperart(code) {
    const key = String(code || "").trim();
    _lastQaSuperarts = _lastQaSuperarts.filter((c) => String(c).trim() !== key);
    const qaEl = document.getElementById("vml-qa-superart-count");
    if (qaEl) qaEl.textContent = String(_lastQaSuperarts.length);
    const superartListEl = document.getElementById("vml-qa-superart-list");
    const superartBlock = document.getElementById("vml-qa-superart-block");
    if (superartListEl) {
      if (!_lastQaSuperarts.length) {
        superartListEl.innerHTML = "";
        superartBlock?.classList.add("hidden");
        const panel = document.getElementById("vml-qa-panel");
        const pendingCount = Number(document.getElementById("vml-qa-pending-count")?.textContent || 0);
        if (panel && !pendingCount) panel.classList.add("hidden");
      } else {
        superartListEl.innerHTML = _lastQaSuperarts
          .slice(0, 12)
          .map((c) => `<li class="text-xs text-violet-900 dark:text-violet-100">${escHtml(c)}</li>`)
          .join("");
      }
    }
  }

  function wireSuperartQaModal() {
    const modal = document.getElementById("vml-superart-modal");
    const openBtn = document.getElementById("vml-superart-qa-btn");
    const qaOpenBtn = document.getElementById("vml-qa-superart-btn");
    const statusEl = document.getElementById("vml-superart-modal-status");
    const catalogInfo = document.getElementById("vml-superart-catalog-info");
    let classifying = false;

    async function loadAndShow() {
      if (!canEditSuperart) {
        showAviso("Solo usuarios autorizados pueden clasificar SuperArt.", "warning");
        return;
      }
      if (!superartQaApiUrl) {
        showAviso("API de clasificación SuperArt no disponible.", "error");
        return;
      }
      if (statusEl) statusEl.textContent = "Cargando…";
      openModal(modal);
      try {
        const data = await fetchSuperartPending();
        renderSuperartList(data.pending || []);
        if (catalogInfo) {
          const ver = data.catalog_version != null ? `Catálogo activo v${data.catalog_version}` : "Sin catálogo activo (se creará al clasificar)";
          catalogInfo.textContent = ver;
        }
        if (statusEl) {
          statusEl.textContent = `${data.pending_count || 0} pendiente(s) en catálogo QA.`;
        }
        updateSuperartBadgeCount(Math.max(data.pending_count || 0, _lastQaSuperarts.length));
      } catch (err) {
        if (statusEl) statusEl.textContent = err.message || "Error al cargar.";
      }
    }

    openBtn?.addEventListener("click", loadAndShow);
    qaOpenBtn?.addEventListener("click", loadAndShow);
    document.getElementById("vml-superart-modal-close")?.addEventListener("click", () => closeModal(modal));
    document.getElementById("vml-superart-modal-cancel")?.addEventListener("click", () => closeModal(modal));
    modal?.querySelector("[data-vml-superart-overlay]")?.addEventListener("click", () => closeModal(modal));

    document.getElementById("vml-superart-list")?.addEventListener("click", async (ev) => {
      const menBtn = ev.target.closest(".vml-superart-men-btn");
      const womenBtn = ev.target.closest(".vml-superart-women-btn");
      const btn = menBtn || womenBtn;
      if (!btn || classifying) return;
      const code = btn.dataset.superart || "";
      const genero = menBtn ? "men" : "women";
      classifying = true;
      btn.disabled = true;
      try {
        const data = await classifySuperart(code, genero);
        showAviso(data.message || "SuperArt clasificado.", "success");
        removeLocalSuperart(code);
        const refreshed = await fetchSuperartPending();
        renderSuperartList(refreshed.pending || []);
        if (statusEl) statusEl.textContent = `${refreshed.pending_count || 0} pendiente(s).`;
        updateSuperartBadgeCount(Math.max(refreshed.pending_count || 0, _lastQaSuperarts.length));
      } catch (err) {
        showAviso(err.message || "Error al clasificar.", "error");
      } finally {
        classifying = false;
        btn.disabled = false;
      }
    });
  }

  function wireModal() {
    const modal = document.getElementById("vml-match-modal");
    const undoModal = document.getElementById("vml-undo-modal");
    const openBtn = document.getElementById("vml-match-panel-btn");
    const confirmPanel = document.getElementById("vml-match-confirm-panel");
    const confirmBtn = document.getElementById("vml-match-modal-confirm");
    const statusEl = document.getElementById("vml-match-modal-status");
    const searchInput = document.getElementById("vml-anet-search");
    const selectedId = document.getElementById("vml-anet-selected-id");
    const selectedLabel = document.getElementById("vml-anet-selected-label");
    const activeMatchId = document.getElementById("vml-match-active-id");

    function resetConfirm() {
      if (confirmPanel) confirmPanel.classList.add("hidden");
      if (confirmPanel) confirmPanel.classList.remove("flex");
      if (confirmBtn) confirmBtn.classList.add("hidden");
      if (activeMatchId) activeMatchId.value = "";
      if (selectedId) selectedId.value = "";
      if (selectedLabel) selectedLabel.textContent = "";
      if (searchInput) searchInput.value = "";
      const results = document.getElementById("vml-anet-results");
      if (results) results.innerHTML = "";
    }

    async function loadAndShow() {
      if (!canEditMatch) {
        showAviso("Solo usuarios autorizados pueden gestionar vínculos.", "warning");
        return;
      }
      resetConfirm();
      if (statusEl) statusEl.textContent = "Cargando…";
      openModal(modal);
      try {
        const data = await fetchMatches("");
        renderMatchList(data.matches || []);
        if (statusEl) statusEl.textContent = `${data.pending_count || 0} pendiente(s).`;
      } catch (err) {
        if (statusEl) statusEl.textContent = err.message || "Error al cargar.";
      }
    }

    openBtn?.addEventListener("click", loadAndShow);
    document.getElementById("vml-match-modal-close")?.addEventListener("click", () => closeModal(modal));
    document.getElementById("vml-match-modal-cancel")?.addEventListener("click", () => closeModal(modal));
    modal?.querySelector("[data-vml-match-overlay]")?.addEventListener("click", () => closeModal(modal));

    document.getElementById("vml-match-list")?.addEventListener("click", (ev) => {
      const linkBtn = ev.target.closest(".vml-link-btn");
      if (linkBtn) {
        if (activeMatchId) activeMatchId.value = linkBtn.dataset.matchId || "";
        const nameEl = document.getElementById("vml-match-confirm-seed-name");
        if (nameEl) nameEl.textContent = linkBtn.dataset.seedName || "";
        if (confirmPanel) {
          confirmPanel.classList.remove("hidden");
          confirmPanel.classList.add("flex");
        }
        if (confirmBtn) confirmBtn.classList.remove("hidden");
        return;
      }
      const undoBtn = ev.target.closest(".vml-undo-btn");
      if (undoBtn) {
        const undoId = document.getElementById("vml-undo-match-id");
        const undoBody = document.getElementById("vml-undo-modal-body");
        if (undoId) undoId.value = undoBtn.dataset.matchId || "";
        if (undoBody) {
          undoBody.textContent = `¿Desvincular «${undoBtn.dataset.seedName || ""}»? El cliente volverá a pendiente.`;
        }
        openModal(undoModal);
      }
    });

    searchInput?.addEventListener("input", () => {
      clearTimeout(searchTimer);
      const q = (searchInput.value || "").trim();
      searchTimer = setTimeout(() => searchAnetClients(q), 280);
    });

    document.getElementById("vml-anet-results")?.addEventListener("click", (ev) => {
      const pick = ev.target.closest(".vml-anet-pick");
      if (!pick) return;
      if (selectedId) selectedId.value = pick.dataset.id || "";
      if (selectedLabel) selectedLabel.textContent = `Seleccionado: #${pick.dataset.id} — ${pick.dataset.text || ""}`;
    });

    confirmBtn?.addEventListener("click", async () => {
      const mid = activeMatchId?.value;
      const aid = selectedId?.value;
      if (!mid || !aid) {
        showAviso("Seleccione un cliente AdministraNET.", "warning");
        return;
      }
      confirmBtn.disabled = true;
      try {
        await applyMatch(mid, aid);
        showAviso("Cliente vinculado correctamente.", "success");
        resetConfirm();
        const data = await fetchMatches("");
        renderMatchList(data.matches || []);
        refreshPendingBadge();
      } catch (err) {
        showAviso(err.message || "Error al vincular.", "error");
      } finally {
        confirmBtn.disabled = false;
      }
    });

    document.getElementById("vml-undo-modal-cancel")?.addEventListener("click", () => closeModal(undoModal));
    undoModal?.querySelector("[data-vml-undo-overlay]")?.addEventListener("click", () => closeModal(undoModal));
    document.getElementById("vml-undo-modal-confirm")?.addEventListener("click", async () => {
      const mid = document.getElementById("vml-undo-match-id")?.value;
      if (!mid) return;
      try {
        await undoMatch(mid);
        closeModal(undoModal);
        showAviso("Vínculo revocado.", "success");
        const data = await fetchMatches("");
        renderMatchList(data.matches || []);
        refreshPendingBadge();
      } catch (err) {
        showAviso(err.message || "Error al desvincular.", "error");
      }
    });
  }

  function validateBeforeQuery() {
    if (typeof window.vmlValidateCalendarRange === "function" && !window.vmlValidateCalendarRange()) {
      showAviso("El rango debe estar dentro del mismo año calendario (01/01–31/12).", "warning");
      return false;
    }
    const pack = document.getElementById("vml_pack_id")?.value;
    if (!pack) {
      showAviso("Seleccione un pack licenciatario.", "warning");
      return false;
    }
    return true;
  }

  window.vmlValidateBeforeQuery = validateBeforeQuery;

  document.addEventListener("DOMContentLoaded", () => {
    wireModal();
    wireSuperartQaModal();
    refreshPendingBadge();
    refreshSuperartBadge();
    document.getElementById("vml-matriz-search")?.addEventListener("input", () => {
      renderMatriz(_lastMatriz.data, _lastMatriz.extra);
    });
  });
})();
