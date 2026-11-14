/**
 * Listado mayoristapp genérico (F1/F2) — config vía data-* en #listado-app.
 */
(function () {
  "use strict";
  var filasActuales = [];

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

  function renderHead(columns, withAcciones, withDetalle) {
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
    if (withAcciones || withDetalle) {
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

  function renderRows(rows, columns, accCfg, withDetalle) {
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
      } else if (withDetalle) {
        tds.push('<td class="py-2.5 pr-3"><button type="button" class="text-xs font-semibold text-sky-700 hover:underline dark:text-sky-300" data-ver-comprobante="' + idx + '">Ver detalle</button></td>');
      }
      var tr = document.createElement("tr");
      tr.className =
        "border-b border-slate-100 dark:border-slate-800/80 " + rowClass;
      tr.innerHTML = tds.join("");
      tbody.appendChild(tr);
    });
  }

  function abrirDetalleComprobante(fila, columns) {
    var modal = el("comprobante-detalle-modal");
    var datos = el("comprobante-detalle-datos");
    if (!modal || !datos || !fila) return;
    var campos = columns.slice();
    [
      ["CondVenta", "Condición de venta"], ["Vencimiento", "Vencimiento"],
      ["Estado", "Estado"], ["Anulado", "Anulado"], ["Vencido", "Vencido"],
      ["Recibo", "Recibo"], ["Detalle", "Detalle"], ["NroFactura", "Factura relacionada"],
    ].forEach(function (extra) {
      if (!campos.some(function (c) { return c.key === extra[0]; }) && pick(fila, extra[0]) != null) {
        campos.push({ key: extra[0], label: extra[1] });
      }
    });
    datos.innerHTML = campos.map(function (campo) {
      var valor = pick(fila, campo.key);
      var texto = campo.fmt === "money" ? fmtMoney(valor) : (valor == null || valor === "" ? "—" : String(valor));
      return '<div class="min-w-0"><dt class="text-xs text-slate-500 dark:text-slate-400">' + esc(campo.label) +
        '</dt><dd class="break-words font-medium text-slate-900 dark:text-slate-100">' + esc(texto) + '</dd></div>';
    }).join("");
    modal.classList.remove("hidden");
    modal.querySelector("[data-cerrar-detalle]")?.focus();
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

    var withDetalle = root.getAttribute("data-detalle-comprobante") === "1";
    renderHead(columns, !!accCfg, withDetalle);
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
        var saldoTotal = el("listado-saldo-total");
        if (saldoTotal) saldoTotal.textContent = "Total a cobrar: " + fmtMoney(data.saldo_al_dia || 0);
        var filas = data[resultsKey] || data.filas || data.results || [];
        filasActuales = filas;
        if (!filas.length) {
          if (emptyBox) {
            emptyBox.classList.remove("hidden");
            emptyBox.textContent = root.getAttribute("data-empty-message") || "No se encontraron resultados.";
          }
          if (wrap) wrap.classList.add("hidden");
          if (status) status.textContent = "0 resultados.";
          return;
        }
        if (emptyBox) emptyBox.classList.add("hidden");
        if (wrap) wrap.classList.remove("hidden");
        renderRows(filas, columns, accCfg, withDetalle);
        if (status) status.textContent = filas.length + " resultado(s).";
        var lu = el("list-last-update");
        if (lu) {
          lu.textContent =
            "Última actualización: " +
            new Date().toLocaleString("es-AR", { hour12: false });
        }
      })
      .catch(function () {
        var saldoTotal = el("listado-saldo-total");
        if (saldoTotal) saldoTotal.textContent = "";
        filasActuales = [];
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
    if (!filasActuales.length) return;
    var lines = [columns.map(function (c) { return c.label; }).join(";")];
    filasActuales.forEach(function (row) {
      var cells = columns.map(function (c) {
        return String(pick(row, c.key) ?? "").replace(/[;\r\n]/g, " ");
      });
      lines.push(cells.join(";"));
    });
    var blob = new Blob(["\ufeff" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download =
      (root.getAttribute("data-slug") || "listado") +
      "_" +
      new Date().toISOString().slice(0, 10) +
      ".csv";
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function exportPdf() {
    var root = el("listado-app");
    if (!root || !filasActuales.length) return;
    var columns = parseJsonAttr(root, "data-columns", []);
    var title = root.getAttribute("data-slug") === "cuenta-corriente" ?
      "Cuenta corriente por cliente" : "Comprobantes a cobrar por cliente";
    var empresa = root.getAttribute("data-empresa-nombre") || "administraNET";
    var cliente = root.getAttribute("data-cliente-nombre") || "";
    var clienteCodigo = root.getAttribute("data-cliente-codigo") || "";
    var date = new Date().toLocaleString("es-AR");
    var desde = el("fechaDesde")?.value || "—";
    var hasta = el("fechaHasta")?.value || "—";
    var saldo = root.getAttribute("data-slug") === "no-cancelados" ?
      filasActuales.reduce(function (s, row) { return s + Number(row.SaldoSigned || 0); }, 0) :
      Number(filasActuales[0]?.saldo || 0);
    var logo = empresa.toLowerCase().includes("best sox") ?
      '<img class="company-logo" src="' + esc(new URL(root.getAttribute("data-logo-empresa"), location.href).href) + '" alt="">' :
      '<strong class="company-name">' + esc(empresa) + '</strong>';
    var analytics = esc(new URL(root.getAttribute("data-logo-analytics"), location.href).href);
    var headers = columns.map(function (c) { return "<th>" + esc(c.label) + "</th>"; }).join("");
    var filasImpresion = root.getAttribute("data-slug") === "cuenta-corriente" ?
      filasActuales.slice().reverse() : filasActuales;
    var rows = filasImpresion.map(function (row) {
      return "<tr>" + columns.map(function (c) {
        var value = pick(row, c.key);
        return "<td" + (c.fmt === "money" ? ' class="money"' : "") + ">" +
          esc(c.fmt === "money" ? fmtMoney(value) : value) + "</td>";
      }).join("") + "</tr>";
    }).join("");
    var printWindow = window.open("", "_blank");
    if (!printWindow) return;
    printWindow.document.write('<!doctype html><html lang="es"><head><meta charset="utf-8"><title>' + esc(title) +
      '</title><style>@page{size:A4 landscape;margin:13mm 10mm}body{font:10px Arial,sans-serif;color:#17233c;margin:0}header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #08336d;padding-bottom:8px;margin-bottom:10px}.company-logo{width:105px;height:55px;object-fit:contain}.company-name{color:#08336d;font-size:18px}h1{font-size:19px;margin:0 0 5px;color:#08336d}.subtitle{color:#4b5f76;margin:2px 0}.client{background:#e6eef8;border-left:4px solid #08336d;padding:8px;margin:10px 0 12px;font-weight:bold}table{width:100%;border-collapse:collapse;table-layout:fixed}th{background:#08336d;color:#fff;text-align:left;font-size:9px;padding:5px 3px;overflow-wrap:anywhere}td{padding:5px 3px;border-bottom:1px solid #dbe4ee;overflow-wrap:anywhere}tr:nth-child(even){background:#f1f6fa}.money{text-align:right;white-space:nowrap}.total{margin:12px 0 0;text-align:right;font-size:13px;font-weight:bold;color:#08336d}footer{position:fixed;bottom:0;left:0;right:0;border-top:1px solid #08336d;padding-top:5px;display:flex;justify-content:space-between;align-items:center;color:#526375;font-size:9px}footer img{height:19px;width:auto}@media print{thead{display:table-header-group}tr{break-inside:avoid}}</style></head><body>' +
      '<header><div><h1>' + esc(title) + '</h1><p class="subtitle"><b>Empresa:</b> ' + esc(empresa) + ' · <b>CUIT:</b> ' + esc(root.getAttribute("data-empresa-cuit") || "—") + '</p><p class="subtitle"><b>Período:</b> ' + esc(desde) + ' a ' + esc(hasta) + ' · <b>Fecha de impresión:</b> ' + esc(date) + '</p></div>' + logo + '</header>' +
      '<div class="client">Cliente: ' + esc(cliente) + ' · Código: ' + esc(clienteCodigo) +
      ' · CUIT: ' + esc(root.getAttribute("data-cliente-cuit") || "—") +
      '<br>Domicilio: ' + esc(root.getAttribute("data-cliente-domicilio") || "—") + '</div><table><thead><tr>' + headers +
      '</tr></thead><tbody>' + rows + '</tbody></table><div class="total">Saldo final: ' + esc(fmtMoney(saldo)) +
      '</div><footer><span>administraNET · Synap</span><img src="' + analytics + '" alt="NL Analytics"><span>' + esc(date) + '</span></footer></body></html>');
    printWindow.document.close();
    var imprimir = function () {
      var images = Array.from(printWindow.document.images);
      Promise.all(images.map(function (img) {
        if (img.complete) return Promise.resolve();
        return new Promise(function (resolve) {
          img.addEventListener("load", resolve, { once: true });
          img.addEventListener("error", resolve, { once: true });
        });
      })).then(function () { printWindow.focus(); printWindow.print(); });
    };
    if (printWindow.document.readyState === "complete") imprimir();
    else printWindow.addEventListener("load", imprimir, { once: true });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = el("listado-app");
    var accCfg = pedidosAccionesCfg(root);
    if (root && root.getAttribute("data-detalle-comprobante") === "1") {
      document.addEventListener("click", function (ev) {
        var boton = ev.target.closest?.("[data-ver-comprobante]");
        if (boton) {
          var indice = Number(boton.getAttribute("data-ver-comprobante"));
          abrirDetalleComprobante(filasActuales[indice], parseJsonAttr(root, "data-columns", []));
        }
        if (ev.target.closest?.("[data-cerrar-detalle]") || ev.target.id === "comprobante-detalle-modal") {
          el("comprobante-detalle-modal")?.classList.add("hidden");
        }
      });
      document.addEventListener("keydown", function (ev) {
        if (ev.key === "Escape") el("comprobante-detalle-modal")?.classList.add("hidden");
      });
    }
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
    var form = el("listado-filters-form");
    if (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        runSearch();
      });
      form.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.defaultPrevented && event.target.matches("input")) {
          event.preventDefault();
          runSearch();
        }
      });
    }
    var ref = document.querySelector("[data-refresh-listado]");
    if (ref) ref.addEventListener("click", runSearch);
    var exp = document.querySelector("[data-export-excel-listado]");
    if (exp) exp.addEventListener("click", exportCsv);
    var pdf = document.querySelector("[data-export-pdf-listado]");
    if (pdf) pdf.addEventListener("click", exportPdf);
    if (root && ["no-cancelados", "cuenta-corriente"].includes(root.getAttribute("data-slug"))) runSearch();
  });
})();
