/**
 * Listado mayoristapp genérico (F1/F2) — config vía data-* en #listado-app.
 */
(function () {
  "use strict";

  function el(id) {
    return document.getElementById(id);
  }

  function getCookie(name) {
    var v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function pick(r, k) {
    if (r[k] !== undefined && r[k] !== null) return r[k];
    var low = k.toLowerCase();
    if (r[low] !== undefined && r[low] !== null) return r[low];
    return r[k];
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

  function parseJsonAttr(node, attr, fallback) {
    try {
      var raw = node.getAttribute(attr);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  }

  function buildPayload(root, basePayload) {
    var p = Object.assign({}, basePayload || {});
    var fv = el("filtraVendedor");
    var lt = el("listaTodos");
    var ep = el("estadoPedido");
    var cb = el("campoBusca");
    var fd = el("fechaDesde");
    var fh = el("fechaHasta");
    var nc = el("numeroComp");
    var tp = el("tipoPedido");
    if (fv) {
      p.filtraVendedor = fv.value;
      p.vendedor = "true";
    }
    if (lt) p.listaPed = lt.value;
    if (ep) p.estadoPedido = ep.value;
    if (cb) p.campoBusca = cb.value;
    if (fd) p.fechaDesde = fd.value || "";
    if (fh) p.fechaHasta = fh.value || "";
    if (nc) p.numeroComp = nc.value || "";
    if (tp) p.tipoPedido = tp.value;
    return p;
  }

  function syncBuscarPor() {
    var cb = el("campoBusca");
    if (!cb) return;
    var v = cb.value;
    var wf = el("wrap-busca-fecha");
    var wn = el("wrap-busca-numero");
    var wt = el("wrap-busca-tipo");
    if (wf) wf.classList.toggle("hidden", v !== "Fecha");
    if (wn) wn.classList.toggle("hidden", v !== "NroComprobante");
    if (wt) wt.classList.toggle("hidden", v !== "TipoPedido");
  }

  function renderHead(columns, withAcciones) {
    var head = el("tabla-listado-head");
    if (!head) return;
    var ths = ['<th class="py-3 pr-3 font-semibold">#</th>'];
    columns.forEach(function (c) {
      var cls = c.fmt === "money" ? " text-right" : "";
      ths.push(
        '<th class="py-3 pr-3 font-semibold whitespace-nowrap' +
          cls +
          '">' +
          esc(c.label) +
          "</th>"
      );
    });
    if (withAcciones) {
      ths.push('<th class="py-3 pr-3 font-semibold">Acciones</th>');
    }
    head.innerHTML =
      '<tr class="border-b border-slate-200 dark:border-slate-700 text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">' +
      ths.join("") +
      "</tr>";
  }

  function pedidosAccionesCfg(root) {
    if (!root || root.getAttribute("data-pedidos-acciones") !== "1") return null;
    return {
      urls: parseJsonAttr(root, "data-pedidos-urls", {}),
      esCliente: root.getAttribute("data-es-cliente") === "1",
    };
  }

  function detalleUrl(tpl, codMov) {
    var t = tpl || "";
    if (t.indexOf("cod_mov=") >= 0) {
      return t.replace(/cod_mov=\d+/, "cod_mov=" + codMov);
    }
    return t.replace(/\/0\/?$/, "/" + codMov + "/");
  }

  function renderRows(rows, columns, accCfg) {
    var tbody = el("tabla-listado-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    rows.forEach(function (r, idx) {
      var anul = String(pick(r, "Anulado") || "").toLowerCase();
      var rowClass =
        anul === "si" || anul === "sí"
          ? "text-red-600 dark:text-red-400"
          : "";
      var tds = ['<td class="py-2.5 pr-3">' + (idx + 1) + "</td>"];
      columns.forEach(function (c) {
        var val = pick(r, c.key);
        var txt = c.fmt === "money" ? fmtMoney(val) : esc(val != null ? val : "");
        var cls = c.fmt === "money" ? " text-right tabular-nums" : "";
        tds.push('<td class="py-2.5 pr-3' + cls + '">' + txt + "</td>");
      });
      if (accCfg) {
        var codMov = pick(r, "CodigoMovimiento") || pick(r, "codigo_movimiento");
        var btns =
          '<button type="button" class="text-xs font-semibold text-sky-600 hover:text-sky-500 mr-2" data-ver-pedido="' +
          esc(String(codMov || "")) +
          '">Ver</button>';
        if (anul !== "si" && anul !== "sí" && codMov) {
          btns +=
            '<button type="button" class="text-xs font-semibold text-indigo-600 hover:text-indigo-500" data-repetir-pedido="' +
            esc(String(codMov)) +
            '">Repetir</button>';
        }
        tds.push('<td class="py-2.5 pr-3 whitespace-nowrap">' + btns + "</td>");
      }
      var tr = document.createElement("tr");
      tr.className =
        "border-b border-slate-100 dark:border-slate-800/80 " + rowClass;
      tr.innerHTML = tds.join("");
      tbody.appendChild(tr);
    });
  }

  function runSearch() {
    var root = el("listado-app");
    if (!root) return;
    var apiUrl = root.getAttribute("data-api-url");
    var method = (root.getAttribute("data-api-method") || "POST").toUpperCase();
    var resultsKey = root.getAttribute("data-results-key") || "filas";
    var columns = parseJsonAttr(root, "data-columns", []);
    var basePayload = parseJsonAttr(root, "data-payload-base", {});
    var accCfg = pedidosAccionesCfg(root);
    var status = el("listado-status");
    var btn = el("botonBuscar");
    var emptyBox = el("listado-empty");
    var wrap = el("listado-table-wrap");

    if (!apiUrl) {
      if (status) status.textContent = "Error: falta URL de API.";
      return;
    }

    renderHead(columns, !!accCfg);
    if (btn) btn.disabled = true;
    if (status) status.textContent = "Buscando…";

    var opts = {
      method: method,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
      },
    };
    if (method === "POST") {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(buildPayload(root, basePayload));
    }

    fetch(apiUrl, opts)
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        if (data.ok === false) throw new Error(data.error || "Error API");
        var filas = data[resultsKey] || data.filas || data.results || [];
        if (!filas.length) {
          if (emptyBox) {
            emptyBox.classList.remove("hidden");
            emptyBox.textContent = "No se encontraron resultados.";
          }
          if (wrap) wrap.classList.add("hidden");
          if (status) status.textContent = "0 resultados.";
          return;
        }
        if (emptyBox) emptyBox.classList.add("hidden");
        if (wrap) wrap.classList.remove("hidden");
        renderRows(filas, columns, accCfg);
        if (status) status.textContent = filas.length + " resultado(s).";
        var lu = el("list-last-update");
        if (lu) {
          lu.textContent =
            "Última actualización: " +
            new Date().toLocaleString("es-AR", { hour12: false });
        }
      })
      .catch(function () {
        if (emptyBox) {
          emptyBox.classList.remove("hidden");
          emptyBox.textContent = "No se pudo cargar el listado.";
        }
        if (wrap) wrap.classList.add("hidden");
        if (status) status.textContent = "Error al buscar.";
      })
      .finally(function () {
        if (btn) btn.disabled = false;
      });
  }

  function exportCsv() {
    var root = el("listado-app");
    if (!root) return;
    var columns = parseJsonAttr(root, "data-columns", []);
    var tbody = el("tabla-listado-body");
    if (!tbody || !tbody.rows.length) return;
    var lines = [columns.map(function (c) { return c.label; }).join(";")];
    Array.prototype.forEach.call(tbody.rows, function (tr) {
      var cells = Array.prototype.map.call(tr.cells, function (td, i) {
        if (i === 0) return "";
        return (td.textContent || "").replace(/;/g, ",");
      });
      lines.push(cells.slice(1).join(";"));
    });
    var blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download =
      (root.getAttribute("data-slug") || "listado") +
      "_" +
      new Date().toISOString().slice(0, 10) +
      ".csv";
    a.click();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = el("listado-app");
    var accCfg = pedidosAccionesCfg(root);
    if (accCfg && window.SynapRepetirPedido) {
      SynapRepetirPedido.init({
        previewTpl: accCfg.urls.preview_tpl,
        cargarUrl: accCfg.urls.cargar_desde_pedido,
        compraUrl: accCfg.urls.compra,
        esCliente: accCfg.esCliente,
      });
      document.addEventListener("click", function (ev) {
        var t = ev.target;
        var ver = t.getAttribute && t.getAttribute("data-ver-pedido");
        if (ver) {
          ev.preventDefault();
          window.location.href = detalleUrl(accCfg.urls.detalle_tpl, ver);
          return;
        }
        var rep = t.getAttribute && t.getAttribute("data-repetir-pedido");
        if (rep) {
          ev.preventDefault();
          SynapRepetirPedido.abrir(rep);
        }
      });
    }
    var cb = el("campoBusca");
    if (cb) cb.addEventListener("change", syncBuscarPor);
    syncBuscarPor();
    var btn = el("botonBuscar");
    if (btn) btn.addEventListener("click", runSearch);
    var ref = document.querySelector("[data-refresh-listado]");
    if (ref) ref.addEventListener("click", runSearch);
    var exp = document.querySelector("[data-export-excel-listado]");
    if (exp) exp.addEventListener("click", exportCsv);
  });
})();
