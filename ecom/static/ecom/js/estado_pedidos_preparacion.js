/**
 * Estado de pedidos (Kanban) — paridad mayoristapp + shell Synap (reportes).
 */
(function () {
  "use strict";

  var STORAGE_INTERVAL = "refresh_interval_ecom_estado_pedidos";
  var STORAGE_REALTIME = "workspace_realtime_ecom_estado_pedidos";
  var realtimeIntervalId = null;
  var realtimeActive = false;
  var lastPayload = null;
  var sucursales = [];

  function el(id) {
    return document.getElementById(id);
  }

  function getRefreshIntervalMs(interval) {
    switch (interval) {
      case "interval_30s":
      case "realtime":
        return 30000;
      case "interval_5m":
      case "hourly":
        return 300000;
      case "interval_10m":
      case "daily":
        return 600000;
      case "interval_1h":
      case "weekly":
        return 3600000;
      case "interval_2h":
      case "monthly":
        return 7200000;
      default:
        return 600000;
    }
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  /** variant: prep | enprep | remito — acento lateral alineado a cabecera de columna Synap */
  function cardHtml(item, showUser, variant) {
    var comp = item.comprobante || "";
    var u = item.usuario;
    var accent =
      variant === "prep"
        ? "border-l-4 border-l-amber-500"
        : variant === "enprep"
          ? "border-l-4 border-l-sky-500"
          : "border-l-4 border-l-emerald-500";
    var baseCard =
      "group relative rounded-2xl border border-slate-200 dark:border-slate-700/90 bg-white dark:bg-slate-900 px-4 py-3.5 text-center shadow-md shadow-slate-900/8 dark:shadow-black/25 " +
      accent +
      " transition-all duration-300 hover:shadow-lg hover:shadow-slate-900/12 hover:-translate-y-0.5 hover:border-slate-300 dark:hover:border-slate-600";

    if (showUser) {
      var usuarioMostrar =
        u && String(u).trim() && String(u).toLowerCase() !== "null"
          ? String(u).trim()
          : "Sin asignar";
      return (
        '<div class="' +
        baseCard +
        '">' +
        '<div class="absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent via-slate-200/80 to-transparent dark:via-slate-600/50 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>' +
        '<div class="text-lg sm:text-xl font-semibold text-slate-900 dark:text-white tracking-tight tabular-nums">' +
        esc(comp) +
        "</div>" +
        '<div class="mt-2 text-xs sm:text-sm font-medium text-slate-500 dark:text-slate-400 leading-snug">' +
        esc(usuarioMostrar) +
        "</div></div>"
      );
    }
    return (
      '<div class="' +
      baseCard +
      '">' +
      '<div class="text-lg sm:text-xl font-semibold text-slate-900 dark:text-white tracking-tight tabular-nums">' +
      esc(comp) +
      "</div></div>"
    );
  }

  function renderColumn(listId, countId, items, showUser, variant) {
    var ul = el(listId);
    var ct = el(countId);
    if (!ul || !ct) return;
    ul.innerHTML = "";
    var arr = items || [];
    ct.textContent = String(arr.length);
    arr.forEach(function (item) {
      var li = document.createElement("li");
      li.className = "m-0";
      li.innerHTML = cardHtml(item, showUser, variant);
      ul.appendChild(li);
    });
  }

  function updateSummary() {
    var sum = el("ep-filters-summary");
    if (!sum) return;
    var sel = el("ep-sucursal");
    if (sel && sel.options.length && sel.selectedIndex >= 0) {
      sum.textContent =
        "Sucursal: " + sel.options[sel.selectedIndex].textContent.trim();
    } else {
      sum.textContent = "";
    }
  }

  function updateLastRefresh() {
    var out = el("ep-last-update");
    if (!out) return;
    var now = new Date();
    var fecha = now.toLocaleString("es-AR", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    out.innerHTML =
      '<strong class="font-bold">Última actualización:</strong> ' + esc(fecha);
  }

  function fetchKanban() {
    var root = el("estado-pedidos-app");
    var loading = el("ep-kanban-loading");
    var status = el("ep-status");
    if (!root) return;
    var baseUrl = root.getAttribute("data-api-url");
    var sel = el("ep-sucursal");
    if (!baseUrl || !sel || !sel.value) {
      if (status) status.textContent = "Seleccione sucursal.";
      return;
    }
    var url =
      baseUrl +
      (baseUrl.indexOf("?") >= 0 ? "&" : "?") +
      "ajax=1&cod_sucursal=" +
      encodeURIComponent(sel.value);
    if (loading) loading.classList.remove("hidden");
    if (status) status.textContent = "Actualizando…";

    fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        lastPayload = data;
        renderColumn("ep-list-preparado", "ep-count-preparado", data.preparado, false, "prep");
        renderColumn("ep-list-en-prep", "ep-count-en-prep", data.en_preparacion, true, "enprep");
        renderColumn("ep-list-remito", "ep-count-remito", data.en_remito, true, "remito");
        updateLastRefresh();
        updateSummary();
        if (status) status.textContent = "";
      })
      .catch(function (err) {
        console.error(err);
        if (status) status.textContent = "No se pudo cargar el tablero.";
      })
      .finally(function () {
        if (loading) loading.classList.add("hidden");
      });
  }

  function stopRealtimeTimer() {
    if (realtimeIntervalId) {
      clearInterval(realtimeIntervalId);
      realtimeIntervalId = null;
    }
  }

  function startRealtimeTimer() {
    stopRealtimeTimer();
    var sel = el("refresh_interval");
    var iv = sel ? sel.value : "interval_10m";
    realtimeIntervalId = setInterval(fetchKanban, getRefreshIntervalMs(iv));
  }

  function updateRealtimeUI(active) {
    var realtimeButton = document.querySelector("[data-realtime-toggle]");
    if (!realtimeButton) return;
    var label = realtimeButton.querySelector("[data-realtime-label]");
    var indicator = realtimeButton.querySelector("[data-realtime-indicator]");
    var icon = realtimeButton.querySelector("[data-realtime-icon]");
    if (active) {
      realtimeButton.classList.remove(
        "text-rose-600",
        "dark:text-rose-400",
        "bg-rose-50",
        "dark:bg-rose-900/20",
        "hover:bg-rose-100",
        "dark:hover:bg-rose-900/30",
        "border-rose-300",
        "dark:border-rose-700"
      );
      realtimeButton.classList.add(
        "text-emerald-700",
        "dark:text-emerald-400",
        "bg-emerald-50",
        "dark:bg-emerald-900/20",
        "hover:bg-emerald-100",
        "dark:hover:bg-emerald-900/30",
        "border-emerald-300",
        "dark:border-emerald-700",
        "border"
      );
      if (indicator) {
        indicator.classList.remove("opacity-0");
        indicator.classList.add("bg-emerald-500", "dark:bg-emerald-400");
        indicator.classList.remove("bg-rose-500", "dark:bg-rose-400");
      }
      if (label) label.textContent = "Detener tiempo real";
      if (icon) {
        icon.innerHTML =
          '<path d="M6 6h12v12H6z" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
        icon.classList.remove("text-rose-600", "dark:text-rose-400");
        icon.classList.add("text-emerald-600", "dark:text-emerald-400");
      }
    } else {
      realtimeButton.classList.remove(
        "text-emerald-700",
        "dark:text-emerald-400",
        "bg-emerald-50",
        "dark:bg-emerald-900/20",
        "hover:bg-emerald-100",
        "dark:hover:bg-emerald-900/30",
        "border-emerald-300",
        "dark:border-emerald-700"
      );
      realtimeButton.classList.add(
        "text-rose-600",
        "dark:text-rose-400",
        "bg-rose-50",
        "dark:bg-rose-900/20",
        "hover:bg-rose-100",
        "dark:hover:bg-rose-900/30",
        "border-rose-300",
        "dark:border-rose-700",
        "border"
      );
      if (indicator) {
        indicator.classList.add("opacity-0");
        indicator.classList.add("bg-rose-500", "dark:bg-rose-400");
        indicator.classList.remove("bg-emerald-500", "dark:bg-emerald-400");
      }
      if (label) label.textContent = "Tiempo real";
      if (icon) {
        icon.innerHTML =
          '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
        icon.classList.remove("text-emerald-600", "dark:text-emerald-400");
        icon.classList.add("text-rose-600", "dark:text-rose-400");
      }
    }
    realtimeButton.setAttribute("data-realtime-active", String(active));
  }

  function initRealtimeToggle() {
    var realtimeButton = document.querySelector("[data-realtime-toggle]");
    if (!realtimeButton) return;
    try {
      if (localStorage.getItem(STORAGE_REALTIME) === "true") {
        realtimeActive = true;
        updateRealtimeUI(true);
        startRealtimeTimer();
      } else {
        updateRealtimeUI(false);
      }
    } catch (e) {
      updateRealtimeUI(false);
    }
    realtimeButton.addEventListener("click", function () {
      realtimeActive = !realtimeActive;
      try {
        localStorage.setItem(STORAGE_REALTIME, realtimeActive ? "true" : "false");
      } catch (e2) {}
      if (realtimeActive) {
        startRealtimeTimer();
        updateRealtimeUI(true);
        fetchKanban();
      } else {
        stopRealtimeTimer();
        updateRealtimeUI(false);
      }
    });
    window.addEventListener("beforeunload", stopRealtimeTimer);
  }

  function initFiltersToggle() {
    var filtersToggleButton = document.querySelector("[data-filters-toggle]");
    var filtersContainer = document.querySelector("[data-filters-container]");
    var filtersWrapper = document.querySelector("[data-filters-wrapper]");
    if (!filtersToggleButton || !filtersContainer) return;
    var showLabel = filtersToggleButton.dataset.labelShow || "Mostrar filtros";
    var hideLabel = filtersToggleButton.dataset.labelHide || "Ocultar filtros";
    var newToggleButton = filtersToggleButton.cloneNode(true);
    filtersToggleButton.parentNode.replaceChild(newToggleButton, filtersToggleButton);
    function setState(visible) {
      var labelElement = newToggleButton.querySelector("[data-toggle-label]");
      if (labelElement) labelElement.textContent = visible ? hideLabel : showLabel;
      newToggleButton.setAttribute("aria-expanded", String(visible));
      if (filtersWrapper) {
        if (visible) {
          filtersWrapper.classList.remove("hidden");
          window.dispatchEvent(new CustomEvent("reportPeriodFiltersReady"));
        } else {
          filtersWrapper.classList.add("hidden");
        }
      }
    }
    newToggleButton.addEventListener("click", function () {
      var isHidden = filtersContainer.classList.toggle("hidden");
      setState(!isHidden);
    });
    filtersContainer.classList.add("hidden");
    if (filtersWrapper) filtersWrapper.classList.add("hidden");
    setState(false);
  }

  function setFullscreenButtonState(isActive) {
    var html = isActive
      ? '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 9H5V5M5 19l4-4m6 0h4v4m0-14l-4 4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> <span class="hidden sm:inline">Salir de pantalla completa</span>'
      : '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M4 8V4h4M4 4l5 5M20 16v4h-4m4 0l-5-5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> <span class="hidden sm:inline">Pantalla completa</span>';
    document.querySelectorAll("[data-fullscreen-toggle]").forEach(function (btn) {
      btn.innerHTML = html;
    });
  }

  function initFullscreen() {
    document.querySelectorAll("[data-fullscreen-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(function () {});
        } else {
          document.exitFullscreen().catch(function () {});
        }
      });
    });
    setFullscreenButtonState(false);
    document.addEventListener("fullscreenchange", function () {
      document.body.classList.toggle("reports-fullscreen", Boolean(document.fullscreenElement));
      setFullscreenButtonState(Boolean(document.fullscreenElement));
    });
  }

  function setupRefreshIntervalButtons() {
    var hiddenSelect = el("refresh_interval");
    if (!hiddenSelect) return;

    function updateButtonStates(selectedValue) {
      document.querySelectorAll(".refresh-interval-btn").forEach(function (btn) {
        var interval = btn.dataset.interval;
        if (interval === selectedValue) {
          btn.classList.add(
            "active",
            "border-sky-500",
            "bg-sky-50",
            "dark:bg-sky-900/20",
            "text-sky-700",
            "dark:text-sky-300",
            "shadow-md"
          );
          btn.classList.remove(
            "border-slate-300",
            "dark:border-slate-600",
            "bg-white",
            "dark:bg-slate-800",
            "text-slate-700",
            "dark:text-slate-300"
          );
        } else {
          btn.classList.remove(
            "active",
            "border-sky-500",
            "bg-sky-50",
            "dark:bg-sky-900/20",
            "text-sky-700",
            "dark:text-sky-300",
            "shadow-md"
          );
          btn.classList.add(
            "border-slate-300",
            "dark:border-slate-600",
            "bg-white",
            "dark:bg-slate-800",
            "text-slate-700",
            "dark:text-slate-300"
          );
        }
      });
    }

    var saved = null;
    try {
      saved = localStorage.getItem(STORAGE_INTERVAL);
    } catch (e) {}
    var initial = saved || hiddenSelect.value || "interval_10m";
    if (saved) hiddenSelect.value = saved;
    updateButtonStates(initial);

    Array.prototype.slice
      .call(document.querySelectorAll(".refresh-interval-btn"))
      .forEach(function (btn) {
        var nb = btn.cloneNode(true);
        btn.parentNode.replaceChild(nb, btn);
      });

    document.querySelectorAll(".refresh-interval-btn").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        var interval = btn.dataset.interval;
        if (!interval) return;
        hiddenSelect.value = interval;
        try {
          localStorage.setItem(STORAGE_INTERVAL, interval);
        } catch (e2) {}
        updateButtonStates(interval);
        if (realtimeActive) startRealtimeTimer();
      });
    });
    hiddenSelect.addEventListener("change", function () {
      updateButtonStates(hiddenSelect.value);
      try {
        localStorage.setItem(STORAGE_INTERVAL, hiddenSelect.value);
      } catch (e3) {}
      if (realtimeActive) startRealtimeTimer();
    });
  }

  function exportCsv() {
    if (!lastPayload) {
      alert("No hay datos cargados.");
      return;
    }
    var lines = [];
    lines.push('"Columna";"Comprobante";"Usuario"');
    (lastPayload.preparado || []).forEach(function (x) {
      lines.push('"Preparado";"' + String(x.comprobante || "").replace(/"/g, '""') + '";""');
    });
    (lastPayload.en_preparacion || []).forEach(function (x) {
      lines.push(
        '"En preparación";"' +
          String(x.comprobante || "").replace(/"/g, '""') +
          '";"' +
          String(x.usuario || "").replace(/"/g, '""') +
          '"'
      );
    });
    (lastPayload.en_remito || []).forEach(function (x) {
      lines.push(
        '"En remito";"' +
          String(x.comprobante || "").replace(/"/g, '""') +
          '";"' +
          String(x.usuario || "").replace(/"/g, '""') +
          '"'
      );
    });
    var csv = "\uFEFF" + lines.join("\r\n");
    var blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "estado_pedidos_" + new Date().toISOString().slice(0, 10) + ".csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function loadSucursales() {
    var root = el("estado-pedidos-app");
    if (!root) return Promise.resolve();
    var baseUrl = root.getAttribute("data-api-url");
    if (!baseUrl) return Promise.resolve();
    var url = baseUrl + (baseUrl.indexOf("?") >= 0 ? "&" : "?") + "sucursales=1";
    return fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        sucursales = data.sucursales || [];
        var sel = el("ep-sucursal");
        var dom = el("ep-domicilio-sucursal");
        sel.innerHTML = "";
        sucursales.forEach(function (s) {
          var o = document.createElement("option");
          o.value = String(s.id_sucursal);
          o.textContent = s.nombre_sucursal || o.value;
          sel.appendChild(o);
        });
        if (sucursales.length) {
          sel.selectedIndex = 0;
          if (dom) dom.textContent = sucursales[0].domicilio_sucursal || "";
        }
        sel.addEventListener("change", function () {
          var id = sel.value;
          var s = sucursales.find(function (x) {
            return String(x.id_sucursal) === String(id);
          });
          if (dom) dom.textContent = (s && s.domicilio_sucursal) || "";
          updateSummary();
          fetchKanban();
        });
        fetchKanban();
      })
      .catch(function (e) {
        console.error(e);
        var st = el("ep-status");
        if (st) st.textContent = "No se pudieron cargar las sucursales.";
        return Promise.resolve();
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initFiltersToggle();
    initFullscreen();
    setupRefreshIntervalButtons();

    var refreshBtn = document.querySelector("[data-refresh-estado-pedidos]");
    if (refreshBtn) refreshBtn.addEventListener("click", fetchKanban);
    var ex = document.querySelector("[data-export-csv-estado-pedidos]");
    if (ex) ex.addEventListener("click", exportCsv);

    var ri = el("refresh_interval");
    if (ri) {
      ri.addEventListener("change", function () {
        if (realtimeActive) startRealtimeTimer();
      });
    }

    loadSucursales().then(function () {
      initRealtimeToggle();
    });
  });
})();
