/**
 * Presupuestos por vendedor — API relay + shell alineado a reportes Synap (dashboard).
 */
(function () {
  "use strict";

  var STORAGE_INTERVAL = "refresh_interval_ecom_presupuestos_vendedor";
  var STORAGE_REALTIME = "workspace_realtime_ecom_presupuestos_vendedor";
  var FILTER_DEBOUNCE_MS = 450;

  var realtimeIntervalId = null;
  var filterDebounceId = null;
  var realtimeActive = false;

  function getCookie(name) {
    var v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
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

  function el(id) {
    return document.getElementById(id);
  }

  function fmtMoney(n) {
    if (n === null || n === undefined || n === "") return "—";
    var x = Number(n);
    if (Number.isNaN(x)) return String(n);
    try {
      return new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        minimumFractionDigits: 2,
      }).format(x);
    } catch (e) {
      return x.toFixed(2);
    }
  }

  function syncBuscarPor() {
    var v = el("campoBusca").value;
    el("wrap-busca-fecha").classList.toggle("hidden", v !== "Fecha");
    el("wrap-busca-numero").classList.toggle("hidden", v !== "NroComprobante");
    el("wrap-busca-tipo").classList.toggle("hidden", v !== "TipoPedido");
  }

  function buildPayload() {
    return {
      ajax: "true",
      vendedor: "true",
      campoBusca: el("campoBusca").value,
      fechaDesde: el("fechaDesde").value || "",
      fechaHasta: el("fechaHasta").value || "",
      numeroComp: el("numeroComp").value || "",
      estadoPedido: el("estadoPedido").value,
      tipoPedido: el("tipoPedido").value,
      listaPed: el("listaTodos").value,
      filtraVendedor: el("filtraVendedor").value,
    };
  }

  function pick(r, k) {
    if (r[k] !== undefined && r[k] !== null) return r[k];
    var low = k.toLowerCase();
    if (r[low] !== undefined && r[low] !== null) return r[low];
    return r[k];
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function renderRow(r, idx, usaManual) {
    var cliente;
    if (usaManual) {
      cliente =
        (pick(r, "codManualCliente") != null ? String(pick(r, "codManualCliente")) : "") +
        " — " +
        (pick(r, "nombre_cliente") || "");
    } else {
      cliente =
        (pick(r, "codCliente") != null ? String(pick(r, "codCliente")) : "") +
        " — " +
        (pick(r, "nombre_cliente") || "");
    }
    var viaj =
      (pick(r, "codViajante") != null ? String(pick(r, "codViajante")) : "") +
      " — " +
      (pick(r, "nombreViajante") || "");
    var anul = String(pick(r, "Anulado") || "").toLowerCase();
    var estado = String(pick(r, "Estado") || "");
    var codMov = pick(r, "CodigoMovimiento");
    var rowClass =
      anul === "si" || anul === "sí"
        ? "text-red-600 dark:text-red-400"
        : "";

    var tr = document.createElement("tr");
    tr.className = "border-b border-slate-100 dark:border-slate-800/80 " + rowClass;
    tr.innerHTML =
      "<td class=\"py-2.5 pr-3\">" +
      (idx + 1) +
      "</td>" +
      "<td class=\"py-2.5 pr-3 whitespace-nowrap\">" +
      esc(pick(r, "FechaB") || "") +
      "</td>" +
      "<td class=\"py-2.5 pr-3 whitespace-nowrap\">" +
      esc(pick(r, "NroComprobante") || "") +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(cliente) +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(pick(r, "CondVenta") || "") +
      "</td>" +
      "<td class=\"py-2.5 pr-3 text-right tabular-nums\">" +
      fmtMoney(pick(r, "SubTotalDesc")) +
      "</td>" +
      "<td class=\"py-2.5 pr-3 text-right tabular-nums\">" +
      fmtMoney(pick(r, "IVA")) +
      "</td>" +
      "<td class=\"py-2.5 pr-3 text-right tabular-nums font-medium\">" +
      fmtMoney(pick(r, "Total")) +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(pick(r, "TipoPedido") || "") +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(pick(r, "Estado") || "") +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(pick(r, "autorizacion_sistema") || "") +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(pick(r, "FormaEntrega") || "") +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(viaj) +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      esc(pick(r, "Anulado") || "") +
      "</td>" +
      '<td class="py-2.5 pr-3 whitespace-nowrap">' +
      (anul !== "si" && anul !== "sí" && estado.toLowerCase() !== "en pedido"
        ? '<button type="button" class="text-xs font-semibold text-indigo-600 hover:text-indigo-500" data-convertir-pre="' +
          esc(String(codMov || "")) +
          '">Convertir a pedido</button>'
        : "") +
      "</td>";
    return tr;
  }

  function renderFooter(rows) {
    var st = 0,
      iv = 0,
      tot = 0;
    rows.forEach(function (r) {
      st += Number(pick(r, "SubTotalDesc")) || 0;
      iv += Number(pick(r, "IVA")) || 0;
      tot += Number(pick(r, "Total")) || 0;
    });
    var foot = el("tabla-presupuestos-foot");
    foot.innerHTML =
      "<tr>" +
      '<td colspan="5" class="py-3 pr-3 text-right text-slate-600 dark:text-slate-300">Totales</td>' +
      '<td class="py-3 pr-3 text-right tabular-nums">' +
      fmtMoney(st) +
      "</td>" +
      '<td class="py-3 pr-3 text-right tabular-nums">' +
      fmtMoney(iv) +
      "</td>" +
      '<td class="py-3 pr-3 text-right tabular-nums">' +
      fmtMoney(tot) +
      "</td>" +
      '<td colspan="6"></td>' +
      "</tr>";
  }

  function textOfSelect(sel) {
    if (!sel || sel.selectedIndex < 0) return "";
    return sel.options[sel.selectedIndex].textContent.trim();
  }

  function updateFiltersSummary() {
    var sum = el("presup-filters-summary");
    if (!sum) return;
    var parts = [];
    parts.push("Vendedor: " + textOfSelect(el("filtraVendedor")));
    parts.push("Clientes: " + textOfSelect(el("listaTodos")));
    parts.push("Estado: " + textOfSelect(el("estadoPedido")));
    var cb = el("campoBusca").value;
    if (cb && cb !== "-") {
      parts.push("Buscar: " + cb);
      if (cb === "Fecha") {
        parts.push("Desde " + (el("fechaDesde").value || "—") + " hasta " + (el("fechaHasta").value || "—"));
      } else if (cb === "NroComprobante") {
        parts.push("N.º " + (el("numeroComp").value || "—"));
      } else if (cb === "TipoPedido") {
        parts.push("Tipo " + textOfSelect(el("tipoPedido")));
      }
    }
    var selInt = el("refresh_interval");
    if (selInt && selInt.options[selInt.selectedIndex]) {
      parts.push("Intervalo: " + selInt.options[selInt.selectedIndex].textContent.trim());
    }
    sum.textContent = parts.join(" · ");
  }

  function updateLastRefreshTime() {
    var out = el("presup-last-update");
    if (!out) return;
    var now = new Date();
    var s = now.toLocaleString("es-AR", {
      weekday: "long",
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    out.textContent = "Última actualización: " + s;
  }

  function runSearch() {
    var root = el("presupuestos-app");
    if (!root) return;
    var apiUrl = root.getAttribute("data-api-url");
    var usaManual = root.getAttribute("data-usa-id-manual") === "1";
    var status = el("presupuestos-status");
    var btn = el("botonBuscar");
    var emptyBox = el("presupuestos-empty");
    var wrap = el("presupuestos-table-wrap");
    var tbody = el("tabla-presupuestos-body");

    if (!apiUrl) {
      status.textContent = "Error: falta URL de API.";
      return;
    }

    updateFiltersSummary();

    btn.disabled = true;
    status.textContent = "Buscando…";

    var url = apiUrl + (apiUrl.indexOf("?") >= 0 ? "&" : "?") + "ajax=1";

    fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
        Accept: "application/json",
      },
      body: JSON.stringify(buildPayload()),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        var filas = data.filas || [];
        tbody.innerHTML = "";
        if (filas.length === 0) {
          emptyBox.classList.remove("hidden");
          emptyBox.textContent = "No se encontraron resultados para los filtros indicados.";
          wrap.classList.add("hidden");
          el("tabla-presupuestos-foot").innerHTML = "";
          status.textContent = "0 resultados.";
          updateLastRefreshTime();
          return;
        }
        emptyBox.classList.add("hidden");
        wrap.classList.remove("hidden");
        filas.forEach(function (row, i) {
          tbody.appendChild(renderRow(row, i, usaManual));
        });
        renderFooter(filas);
        status.textContent = filas.length + " resultado(s).";
        updateLastRefreshTime();
      })
      .catch(function (err) {
        emptyBox.classList.remove("hidden");
        emptyBox.textContent =
          "No se pudo cargar el listado. Compruebe la sesión y la base de empresa.";
        wrap.classList.add("hidden");
        status.textContent = "Error al buscar.";
        console.error(err);
      })
      .finally(function () {
        btn.disabled = false;
      });
  }

  function scheduleSearchFromFilters() {
    if (!realtimeActive) return;
    if (filterDebounceId) clearTimeout(filterDebounceId);
    filterDebounceId = setTimeout(function () {
      filterDebounceId = null;
      runSearch();
    }, FILTER_DEBOUNCE_MS);
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
    var ms = getRefreshIntervalMs(iv);
    realtimeIntervalId = setInterval(function () {
      runSearch();
    }, ms);
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
        runSearch();
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
        runSearch();
      } else {
        stopRealtimeTimer();
        updateRealtimeUI(false);
      }
    });

    window.addEventListener("beforeunload", stopRealtimeTimer);
  }

  function setupRefreshIntervalButtons() {
    var buttons = document.querySelectorAll(".refresh-interval-btn");
    var hiddenSelect = el("refresh_interval");
    if (!buttons.length || !hiddenSelect) return;

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
    if (saved) {
      hiddenSelect.value = saved;
    }
    updateButtonStates(initial);

    Array.prototype.slice
      .call(document.querySelectorAll(".refresh-interval-btn"))
      .forEach(function (btn) {
        var newBtn = btn.cloneNode(true);
        btn.parentNode.replaceChild(newBtn, btn);
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
        if (realtimeActive) {
          startRealtimeTimer();
        }
      });
    });

    hiddenSelect.addEventListener("change", function () {
      updateButtonStates(hiddenSelect.value);
      try {
        localStorage.setItem(STORAGE_INTERVAL, hiddenSelect.value);
      } catch (e3) {}
      if (realtimeActive) {
        startRealtimeTimer();
      }
    });
  }

  function exportTableToExcel() {
    var table = el("tabla-presupuestos");
    var wrap = el("presupuestos-table-wrap");
    if (!table || !wrap || wrap.classList.contains("hidden")) {
      alert("No hay datos para exportar. Ejecute una búsqueda primero.");
      return;
    }

    var rows = table.querySelectorAll("tr");
    var lines = [];
    rows.forEach(function (tr) {
      var cells = tr.querySelectorAll("th, td");
      var line = [];
      cells.forEach(function (cell) {
        var t = (cell.textContent || "").replace(/\r?\n/g, " ").trim();
        t = t.replace(/"/g, '""');
        line.push('"' + t + '"');
      });
      lines.push(line.join(";"));
    });

    var csv = "\uFEFF" + lines.join("\r\n");
    var blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url;
    a.download = "presupuestos_vendedor_" + new Date().toISOString().slice(0, 10) + ".csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function wireFilterAutoRefresh() {
    var form = el("presupuestos-filters-form");
    if (!form) return;
    form.querySelectorAll("select, input").forEach(function (node) {
      if (node.id === "refresh_interval") return;
      node.addEventListener("change", function () {
        syncBuscarPor();
        scheduleSearchFromFilters();
      });
      node.addEventListener("input", function () {
        scheduleSearchFromFilters();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupRefreshIntervalButtons();
    initRealtimeToggle();

    var refreshBtn = document.querySelector("[data-refresh-presupuestos]");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        runSearch();
      });
    }

    var exportBtn = document.querySelector("[data-export-excel-presupuestos]");
    if (exportBtn) {
      exportBtn.addEventListener("click", function () {
        exportTableToExcel();
      });
    }

    el("campoBusca").addEventListener("change", syncBuscarPor);
    syncBuscarPor();
    el("botonBuscar").addEventListener("click", runSearch);

    updateFiltersSummary();
    wireFilterAutoRefresh();

    var root = el("presupuestos-app");
    var convertTpl = root ? root.getAttribute("data-convertir-url-tpl") : "";
    document.addEventListener("click", function (ev) {
      var t = ev.target;
      var cod = t.getAttribute && t.getAttribute("data-convertir-pre");
      if (!cod || !convertTpl) return;
      ev.stopPropagation();
      if (!confirm("¿Convertir este presupuesto a pedido? Se recalcularán precios vigentes.")) return;
      var url = convertTpl.replace(/\/0\/convertir-pedido\/?$/, "/" + cod + "/convertir-pedido/?ajax=1");
      fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({}),
      })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (!data.ok) alert(data.error || data.detail || "No se pudo convertir.");
          else {
            alert("Pedido " + (data.nro_comprobante || "") + " creado correctamente.");
            runSearch();
          }
        })
        .catch(function () {
          alert("Error al convertir el presupuesto.");
        });
    });
  });
})();
