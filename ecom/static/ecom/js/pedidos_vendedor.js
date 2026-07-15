/**
 * Pedidos por vendedor — API REST v1 + shell alineado a reportes Synap.
 */
(function () {
  "use strict";

  var STORAGE_INTERVAL = "refresh_interval_ecom_pedidos_vendedor";
  var STORAGE_REALTIME = "workspace_realtime_ecom_pedidos_vendedor";
  var FILTER_DEBOUNCE_MS = 450;

  var realtimeIntervalId = null;
  var filterDebounceId = null;
  var realtimeActive = false;
  var pageUrls = {};

  function loadUrls() {
    var node = document.getElementById("pedidos-vendedor-urls");
    if (!node) return {};
    try {
      return JSON.parse(node.textContent);
    } catch (e) {
      return {};
    }
  }

  function detalleUrl(codMov) {
    var tpl = pageUrls.detalle_tpl || "";
    if (tpl.indexOf("cod_mov=") >= 0) {
      return tpl.replace(/cod_mov=\d+/, "cod_mov=" + codMov);
    }
    return tpl.replace(/\/0\/?$/, "/" + codMov + "/");
  }

  function pdfUrl(codMov) {
    return (pageUrls.pdf_tpl || "").replace(/\/0\/pdf\/?$/, "/" + codMov + "/pdf/");
  }

  function badgeEstado(est) {
    var e = String(est || "").toLowerCase();
    if (e === "pendiente") return "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800";
    if (e.indexOf("prepar") >= 0) return "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold bg-sky-100 text-sky-800";
    if (e === "preparado") return "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold bg-emerald-100 text-emerald-800";
    return "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold bg-slate-100 text-slate-700";
  }

  function badgeAutorizacion(val) {
    var v = String(val || "").trim();
    if (v === "Autorizado") return "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold bg-emerald-100 text-emerald-800";
    return "inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-800";
  }

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
      vendedor: true,
      campo_busca: el("campoBusca").value,
      fecha_desde: el("fechaDesde").value || "",
      fecha_hasta: el("fechaHasta").value || "",
      numero_comp: el("numeroComp").value || "",
      estado_pedido: el("estadoPedido").value,
      tipo_pedido: el("tipoPedido").value,
      lista_ped: el("listaTodos").value,
      filtra_vendedor: el("filtraVendedor").value,
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
    var codMov = pick(r, "CodigoMovimiento");
    var cliente;
    if (usaManual) {
      cliente =
        (pick(r, "id_manual_cli") != null ? String(pick(r, "id_manual_cli")) : "") +
        " — " +
        (pick(r, "nombre_cliente") || "");
    } else {
      cliente =
        (pick(r, "CodigoCliente") != null ? String(pick(r, "CodigoCliente")) : pick(r, "codCliente") != null ? String(pick(r, "codCliente")) : "") +
        " — " +
        (pick(r, "nombre_cliente") || "");
    }
    var viaj = pick(r, "NombViajante") || pick(r, "nombreViajante") || "";
    var anul = String(pick(r, "Anulado") || "").toLowerCase();
    var estado = pick(r, "Estado") || "";
    var aut = pick(r, "autorizacion_sistema") || "";
    var rowClass =
      anul === "si" || anul === "sí"
        ? "text-red-600 dark:text-red-400"
        : "";
    var puedeAnular =
      anul !== "si" &&
      anul !== "sí" &&
      String(estado).trim() === "Pendiente";

    var tr = document.createElement("tr");
    tr.className =
      "border-b border-slate-100 dark:border-slate-800/80 cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/30 " +
      rowClass;
    tr.addEventListener("click", function (ev) {
      if (ev.target.closest("[data-ped-accion]")) return;
      if (codMov != null) window.location.href = detalleUrl(codMov);
    });
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
      '<span class="' +
      badgeEstado(estado) +
      '">' +
      esc(estado) +
      "</span>" +
      "</td>" +
      "<td class=\"py-2.5 pr-3\">" +
      '<span class="' +
      badgeAutorizacion(aut) +
      '">' +
      esc(aut) +
      "</span>" +
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
      '<td class="py-2.5 pr-3 whitespace-nowrap" data-ped-accion>' +
      '<button type="button" class="text-xs font-semibold text-sky-600 hover:text-sky-500 mr-2" data-ver-pedido="' +
      esc(String(codMov || "")) +
      '">Ver</button>' +
      '<button type="button" class="text-xs font-semibold text-slate-600 hover:text-slate-800 mr-2" data-pdf-pedido="' +
      esc(String(codMov || "")) +
      '">PDF</button>' +
      (anul !== "si" && anul !== "sí"
        ? '<button type="button" class="text-xs font-semibold text-indigo-600 hover:text-indigo-500 mr-2" data-repetir-pedido="' +
          esc(String(codMov || "")) +
          '">Repetir</button>'
        : "") +
      (puedeAnular
        ? '<button type="button" class="text-xs font-semibold text-rose-600 hover:text-rose-500 mr-2" data-anular-pedido="' +
          esc(String(codMov || "")) +
          '">Anular</button>'
        : "") +
      '<button type="button" class="text-xs font-semibold text-slate-500 hover:text-slate-700" data-mail-pedido="' +
      esc(String(codMov || "")) +
      '">Mail</button>' +
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
    var foot = el("tabla-pedidos-foot");
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
      '<td colspan="7"></td>' +
      "</tr>";
  }

  function textOfSelect(sel, defaultLabel) {
    if (!sel || sel.selectedIndex < 0) return defaultLabel || "";
    var t = sel.options[sel.selectedIndex].textContent.trim();
    if (!t || t === "—") return defaultLabel || t;
    return t;
  }

  function showTableLoading(show) {
    var loading = el("pedidos-loading");
    var emptyBox = el("pedidos-empty");
    var wrap = el("pedidos-table-wrap");
    if (show) {
      if (loading) {
        loading.classList.remove("hidden");
        loading.setAttribute("aria-hidden", "false");
      }
      if (emptyBox) emptyBox.classList.add("hidden");
      if (wrap) wrap.classList.add("hidden");
    } else if (loading) {
      loading.classList.add("hidden");
      loading.setAttribute("aria-hidden", "true");
    }
  }

  function setEmptyState(kind, message) {
    var emptyBox = el("pedidos-empty");
    if (!emptyBox) return;
    emptyBox.classList.remove("hidden");
    emptyBox.setAttribute("data-empty-kind", kind);
    var title =
      kind === "no-results"
        ? "Sin resultados"
        : kind === "error"
          ? "Error al cargar"
          : "Listado vacío";
    var retryBtn =
      kind === "error"
        ? '<button type="button" id="pedidos-retry" class="mt-4 inline-flex items-center rounded-full px-4 py-2 text-xs font-semibold text-white bg-sky-600 hover:bg-sky-500">Reintentar</button>'
        : "";
    emptyBox.innerHTML =
      '<p class="font-semibold text-slate-700 dark:text-slate-300">' +
      esc(title) +
      "</p>" +
      '<p class="mt-2 text-sm text-slate-500 dark:text-slate-400">' +
      esc(message) +
      "</p>" +
      retryBtn;
    var retry = el("pedidos-retry");
    if (retry) {
      retry.addEventListener("click", function () {
        runSearch();
      });
    }
  }

  function updateFiltersSummary() {
    var sum = el("ped-filters-summary");
    if (!sum) return;
    var parts = [];
    parts.push("Vendedor: " + textOfSelect(el("filtraVendedor"), "Todos"));
    parts.push("Clientes: " + textOfSelect(el("listaTodos"), "Todos"));
    parts.push("Estado: " + textOfSelect(el("estadoPedido"), "Todos los estados"));
    var chkNoAut = el("filtroNoAutorizados");
    if (chkNoAut && chkNoAut.checked) {
      parts.push("Solo no autorizados");
    }
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
    var out = el("ped-last-update");
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
    var root = el("pedidos-app");
    if (!root) return;
    var apiUrl = root.getAttribute("data-api-url");
    var usaManual = root.getAttribute("data-usa-id-manual") === "1";
    var status = el("pedidos-status");
    var btn = el("botonBuscar");
    var emptyBox = el("pedidos-empty");
    var wrap = el("pedidos-table-wrap");
    var tbody = el("tabla-pedidos-body");

    if (!apiUrl) {
      status.textContent = "Error: falta URL de API.";
      return;
    }

    updateFiltersSummary();

    btn.disabled = true;
    status.textContent = "Buscando…";
    showTableLoading(true);

    fetch(apiUrl, {
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
        if (!res.ok) {
          return res.json().catch(function () { return {}; }).then(function (body) {
            var msg = body.error || body.detail || ("HTTP " + res.status);
            throw new Error(msg);
          });
        }
        return res.json();
      })
      .then(function (data) {
        if (data.ok === false) {
          throw new Error(data.error || "Error en API");
        }
        showTableLoading(false);
        var filas = data.results || data.filas || [];
        var soloNoAut = el("filtroNoAutorizados") && el("filtroNoAutorizados").checked;
        if (soloNoAut) {
          filas = filas.filter(function (row) {
            return String(pick(row, "autorizacion_sistema") || "").trim() !== "Autorizado";
          });
        }
        tbody.innerHTML = "";
        if (filas.length === 0) {
          setEmptyState(
            "no-results",
            "No se encontraron pedidos para los filtros indicados. Probá ampliar el rango o quitar restricciones."
          );
          wrap.classList.add("hidden");
          el("tabla-pedidos-foot").innerHTML = "";
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
        showTableLoading(false);
        setEmptyState(
          "error",
          (err && err.message) || "No se pudo cargar el listado. Compruebe la sesión y la base de empresa."
        );
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
        "text-slate-600",
        "dark:text-slate-300",
        "bg-white/10",
        "dark:bg-slate-800/40",
        "hover:bg-white/20",
        "dark:hover:bg-slate-800/60",
        "border-slate-300/60",
        "dark:border-slate-600",
        "border"
      );
      if (indicator) {
        indicator.classList.add("opacity-0");
        indicator.classList.remove("bg-emerald-500", "dark:bg-emerald-400");
      }
      if (label) label.textContent = "Tiempo real";
      if (icon) {
        icon.innerHTML =
          '<path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>';
        icon.classList.remove("text-emerald-600", "dark:text-emerald-400");
        icon.classList.add("text-slate-500", "dark:text-slate-400");
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
    var table = el("tabla-pedidos");
    var wrap = el("pedidos-table-wrap");
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
    a.download = "pedidos_vendedor_" + new Date().toISOString().slice(0, 10) + ".csv";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function wireFilterAutoRefresh() {
    var form = el("pedidos-filters-form");
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

  function wirePedidoAcciones() {
    var root = el("pedidos-app");
    if (!root) return;
    root.addEventListener("click", function (ev) {
      var t = ev.target;
      var ver = t.getAttribute && t.getAttribute("data-ver-pedido");
      if (ver) {
        ev.stopPropagation();
        window.location.href = detalleUrl(ver);
        return;
      }
      var pdf = t.getAttribute && t.getAttribute("data-pdf-pedido");
      if (pdf) {
        ev.stopPropagation();
        window.open(pdfUrl(pdf), "_blank");
        return;
      }
      var rep = t.getAttribute && t.getAttribute("data-repetir-pedido");
      if (rep && window.SynapRepetirPedido) {
        ev.stopPropagation();
        SynapRepetirPedido.abrir(Number(rep));
        return;
      }
      var an = t.getAttribute && t.getAttribute("data-anular-pedido");
      if (an) {
        ev.stopPropagation();
        if (!confirm("¿Anular este pedido? Solo es posible en estado Pendiente.")) return;
        var motivo = prompt("Indique el motivo de anulación (obligatorio):");
        if (!motivo || !String(motivo).trim()) {
          alert("Debe indicar el motivo de anulación.");
          return;
        }
        fetch(pageUrls.anular, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: JSON.stringify({ anularPedido: "1", codMovPedido: Number(an), motivo: String(motivo).trim() }),
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (data) {
            if (data.msg !== "ok") alert(data.error || "No se pudo anular");
            else runSearch();
          });
        return;
      }
      var mail = t.getAttribute && t.getAttribute("data-mail-pedido");
      if (mail) {
        ev.stopPropagation();
        var email = prompt("Correo electrónico del destinatario:");
        if (!email || !String(email).trim() || email.indexOf("@") < 1) {
          alert("Debe indicar un correo electrónico válido.");
          return;
        }
        fetch(pageUrls.mail_enqueue, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
          },
          body: JSON.stringify({ codMov: Number(mail), tipocomprobante: 0, email: String(email).trim() }),
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (data) {
            alert(
              data.msg === "ok" || data.ok
                ? "Solicitud de envío registrada."
                : data.error || data.detail || "No se pudo encolar el mail"
            );
          });
      }
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    pageUrls = loadUrls();
    if (window.SynapRepetirPedido) {
      SynapRepetirPedido.init({
        previewTpl: pageUrls.preview_tpl,
        cargarUrl: pageUrls.cargar_desde_pedido,
        compraUrl: pageUrls.compra,
        esCliente: false,
      });
    }
    wirePedidoAcciones();
    setupRefreshIntervalButtons();
    initRealtimeToggle();

    var refreshBtn = document.querySelector("[data-refresh-pedidos]");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", function () {
        runSearch();
      });
    }

    var exportBtn = document.querySelector("[data-export-excel-pedidos]");
    if (exportBtn) {
      exportBtn.addEventListener("click", function () {
        exportTableToExcel();
      });
    }

    el("campoBusca").addEventListener("change", syncBuscarPor);
    syncBuscarPor();
    el("botonBuscar").addEventListener("click", runSearch);

    var filtroNoAut = el("filtroNoAutorizados");
    if (filtroNoAut) {
      filtroNoAut.addEventListener("change", function () {
        runSearch();
      });
    }

    updateFiltersSummary();
    wireFilterAutoRefresh();

    try {
      var params = new URLSearchParams(window.location.search);
      if (params.get("solo_no_autorizados") === "1") {
        var chk = el("filtroNoAutorizados");
        if (chk) chk.checked = true;
      }
    } catch (eUrl) {}

    runSearch();
  });
})();
