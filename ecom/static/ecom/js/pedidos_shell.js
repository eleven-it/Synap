/**
 * Shell compartido Synap — Gestión de pedidos (filtros, fullscreen, intervalo).
 * Patrón alineado a reports/static/reports/js/dashboard.js
 */
(function (global) {
  "use strict";

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
      ? '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M9 9H5V5M5 19l4-4m6 0h4v4m0-14l-4 4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> <span class="hidden sm:inline">Salir de pantalla completa</span>'
      : '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true"><path d="M4 8V4h4M4 4l5 5M20 16v4h-4m4 0l-5-5" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg> <span class="hidden sm:inline">Pantalla completa</span>';
    document.querySelectorAll("[data-fullscreen-toggle]").forEach(function (btn) {
      btn.innerHTML = html;
    });
  }

  function syncFullscreenState() {
    var active = Boolean(document.fullscreenElement);
    document.body.classList.toggle("reports-fullscreen", active);
    setFullscreenButtonState(active);
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
    document.addEventListener("fullscreenchange", syncFullscreenState);
  }

  function setupRefreshIntervalButtons(hiddenSelectId) {
    var buttons = document.querySelectorAll(".refresh-interval-btn");
    var hiddenSelect = document.getElementById(hiddenSelectId || "refresh_interval");
    if (!buttons.length || !hiddenSelect) return;

    function updateButtonStates(selectedValue) {
      document.querySelectorAll(".refresh-interval-btn").forEach(function (btn) {
        var interval = btn.dataset.interval;
        var on = interval === selectedValue;
        btn.classList.toggle("active", on);
        btn.classList.toggle("border-sky-500", on);
        btn.classList.toggle("bg-sky-50", on);
        btn.classList.toggle("text-sky-700", on);
        btn.classList.toggle("shadow-md", on);
        btn.classList.toggle("border-slate-300", !on);
        btn.classList.toggle("bg-white", !on);
        btn.classList.toggle("text-slate-700", !on);
      });
    }

    var stored = null;
    try {
      stored = localStorage.getItem("refresh_interval_ecom_pedidos_vendedor");
    } catch (e) {}
    if (stored) {
      hiddenSelect.value = stored;
      updateButtonStates(stored);
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var iv = btn.dataset.interval;
        hiddenSelect.value = iv;
        updateButtonStates(iv);
        try {
          localStorage.setItem("refresh_interval_ecom_pedidos_vendedor", iv);
        } catch (e2) {}
      });
    });
  }

  function init() {
    initFiltersToggle();
    initFullscreen();
  }

  global.SynapPedidosShell = {
    init: init,
    initFiltersToggle: initFiltersToggle,
    initFullscreen: initFullscreen,
    setupRefreshIntervalButtons: setupRefreshIntervalButtons,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
