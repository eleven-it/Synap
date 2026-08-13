/**
 * Controlador ligero para Ventas BOM en docenas.
 * La tabla y el export los maneja dashboard.js; aquí KPIs de período y notas.
 */
(function () {
  "use strict";

  var dashboardRoot = document.querySelector("#dashboard-root");
  var reportSlug = (dashboardRoot && dashboardRoot.dataset && dashboardRoot.dataset.reportSlug) || "";
  if (reportSlug !== "ventas-bom-docenas") {
    return;
  }

  function formatPeriodLabel(fi, ff) {
    function fmt(raw) {
      if (!raw) return "";
      var parts = String(raw).split("-");
      if (parts.length !== 3) return String(raw);
      return parts[2] + "/" + parts[1] + "/" + parts[0];
    }
    if (!fi && !ff) return "";
    return "Período " + fmt(fi) + " — " + fmt(ff);
  }

  function syncPeriodLabel() {
    var el = document.getElementById("ventas-bom-summary-period");
    if (!el) return;
    var fi = document.getElementById("fecha_inicio");
    var ff = document.getElementById("fecha_fin");
    el.textContent = formatPeriodLabel(fi && fi.value, ff && ff.value);
  }

  function showNotes(notes) {
    var host = document.getElementById("ventas-bom-notes");
    if (!host) {
      host = document.createElement("div");
      host.id = "ventas-bom-notes";
      host.className = "text-xs text-slate-500 dark:text-slate-400 mb-3 space-y-1";
      var period = document.getElementById("ventas-bom-summary-period");
      if (period && period.parentNode) {
        period.parentNode.insertBefore(host, period.nextSibling);
      } else if (dashboardRoot) {
        dashboardRoot.insertBefore(host, dashboardRoot.firstChild);
      }
    }
    if (!notes || !notes.length) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = notes
      .slice(1)
      .map(function (n) {
        return "<p>" + String(n).replace(/</g, "&lt;") + "</p>";
      })
      .join("");
  }

  var originalFetch = window.fetchDashboardData || null;

  function attachMetaObserver() {
    document.addEventListener("reports:query-result", function (ev) {
      try {
        var detail = ev.detail || {};
        if (detail.slug && detail.slug !== "ventas-bom-docenas") return;
        syncPeriodLabel();
        showNotes(detail.notes || []);
      } catch (e) {
        /* noop */
      }
    });
  }

  // Hook opcional: si dashboard expone último resultado en cache del widget
  function pollLastResult() {
    try {
      var widgets = dashboardRoot.querySelectorAll("[data-widget-id]");
      widgets.forEach(function (w) {
        /* period sync only */
      });
      syncPeriodLabel();
    } catch (e) {
      /* noop */
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    syncPeriodLabel();
    attachMetaObserver();
    ["fecha_inicio", "fecha_fin", "periodo_tipo"].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener("change", syncPeriodLabel);
    });
    document.querySelectorAll(".periodo-tipo-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setTimeout(syncPeriodLabel, 50);
      });
    });
    var refreshBtn = document.querySelector("[data-refresh-dashboard]");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        setTimeout(pollLastResult, 300);
      });
    }
  });

  // Evitar warning unused
  void originalFetch;
})();
