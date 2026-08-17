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
  const canEditMatch = filtersRoot?.dataset?.canEditMatch === "true";

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
    const pendingEl = document.getElementById("vml-qa-pending-count");
    const qaEl = document.getElementById("vml-qa-superart-count");
    const listEl = document.getElementById("vml-qa-pending-list");
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
              `<li class="text-xs text-amber-800 dark:text-amber-200">${String(p.display_name || p.seed_key || "—")}</li>`,
          )
          .join("");
      }
    }
    panel.classList.toggle("hidden", !pending.length && !qaArts.length);
  }

  window.vmlOnDashboardResult = function vmlOnDashboardResult(result) {
    const meta = result?.meta || {};
    const extra = meta.extra || {};
    syncSummaryPeriod(meta);
    renderQaPanel(extra);
    refreshPendingBadge();
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
    refreshPendingBadge();
  });
})();
