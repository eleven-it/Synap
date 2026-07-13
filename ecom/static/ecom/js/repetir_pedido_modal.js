/**
 * Modal compartido para repetir pedido (preview + carga en borrador del pedido).
 * window.SynapRepetirPedido.init({ previewTpl, cargarUrl, compraUrl, esCliente })
 */
(function () {
  "use strict";

  var cfg = {};
  var state = { codMov: null, preview: null };

  function getCookie(name) {
    var v = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return v ? v.pop() : "";
  }

  function fmtMoney(n) {
    return new Intl.NumberFormat("es-AR", {
      style: "currency",
      currency: "ARS",
      minimumFractionDigits: 2,
    }).format(Number(n || 0));
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function modal() {
    return document.getElementById("repetir-pedido-modal");
  }

  function contenido() {
    return document.getElementById("repetir-pedido-contenido");
  }

  function errorEl() {
    return document.getElementById("repetir-pedido-error");
  }

  function btnConfirmar() {
    return document.getElementById("repetir-pedido-confirmar");
  }

  function previewUrl(codMov) {
    return (cfg.previewTpl || "").replace(/0\/preview\/?$/, codMov + "/preview/");
  }

  function cerrar() {
    var m = modal();
    if (m) {
      m.classList.add("hidden");
      m.setAttribute("aria-hidden", "true");
    }
    state = { codMov: null, preview: null };
  }

  function renderPreview(data) {
    var p = data.preview || data;
    var html = "";
    html +=
      '<p class="text-sm text-slate-600 dark:text-slate-300 mb-3">Pedido <strong>' +
      esc(p.nro_comprobante) +
      "</strong> del " +
      esc(p.fecha) +
      " — precios actuales del motor.</p>";
    if (p.advertencias && p.advertencias.length) {
      html +=
        '<div class="mb-3 rounded-lg bg-amber-50 text-amber-800 text-xs p-3">' +
        esc(p.advertencias.join(" ")) +
        "</div>";
    }
    html += '<table class="min-w-full text-sm"><thead><tr class="text-xs uppercase text-slate-500">';
    html += "<th class=\"py-2 pr-2 text-left\">Artículo</th><th class=\"py-2 pr-2 text-right\">Cant.</th>";
    html += "<th class=\"py-2 pr-2 text-right\">Precio neto</th>";
    if (!cfg.esCliente) {
      html += "<th class=\"py-2 pr-2 text-right text-slate-400\">Ref. hist.</th>";
    }
    html += "<th class=\"py-2 text-right\">Subtotal</th></tr></thead><tbody>";
    (p.renglones || []).forEach(function (r) {
      html += "<tr class=\"border-t border-slate-100 dark:border-slate-800\">";
      html += '<td class="py-2 pr-2">' + esc(r.descripcion || r.codigo) + "</td>";
      html +=
        '<td class="py-2 pr-2 text-right"><input type="number" min="0" step="1" data-art="' +
        r.id_articulo +
        '" value="' +
        r.cantidad +
        '" class="w-16 rounded border border-slate-200 text-right text-sm px-1 py-0.5 repetir-cant-input" /></td>';
      html += '<td class="py-2 pr-2 text-right tabular-nums">' + fmtMoney(r.precio_unitario_neto) + "</td>";
      if (!cfg.esCliente) {
        var hist = r.precio_historico_unitario_neto;
        html +=
          '<td class="py-2 pr-2 text-right tabular-nums text-slate-400">' +
          (hist != null ? fmtMoney(hist) : "—") +
          "</td>";
      }
      html += '<td class="py-2 text-right tabular-nums font-medium">' + fmtMoney(r.subtotal_total) + "</td>";
      html += "</tr>";
    });
    html += "</tbody></table>";
    if (!cfg.esCliente && p.total_historico != null) {
      html +=
        '<p class="mt-3 text-xs text-slate-400">Total histórico (referencia): ' +
        fmtMoney(p.total_historico) +
        "</p>";
    }
    contenido().innerHTML = html;
    btnConfirmar().disabled = false;
  }

  function abrir(codMov) {
    state.codMov = codMov;
    var m = modal();
    if (!m) return;
    m.classList.remove("hidden");
    m.setAttribute("aria-hidden", "false");
    contenido().innerHTML = '<p class="text-sm text-slate-500">Cargando vista previa…</p>';
    errorEl().classList.add("hidden");
    btnConfirmar().disabled = true;

    fetch(previewUrl(codMov), { credentials: "same-origin", headers: { Accept: "application/json" } })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (r) {
        if (!r.ok || !r.data || r.data.ok === false) {
          throw new Error((r.data && r.data.error) || "No se pudo cargar la vista previa.");
        }
        state.preview = r.data.preview || r.data;
        renderPreview(r.data);
      })
      .catch(function (err) {
        contenido().innerHTML = "";
        errorEl().textContent = err.message || "Error al cargar.";
        errorEl().classList.remove("hidden");
      });
  }

  function confirmar() {
    if (!state.codMov) return;
    var cantidades = {};
    document.querySelectorAll(".repetir-cant-input").forEach(function (inp) {
      var id = inp.getAttribute("data-art");
      cantidades[id] = Number(inp.value || 0);
    });
    btnConfirmar().disabled = true;
    fetch(cfg.cargarUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken"),
        Accept: "application/json",
      },
      body: JSON.stringify({
        codigo_movimiento: state.codMov,
        modo: "reemplazar",
        cantidades: cantidades,
      }),
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, data: data };
        });
      })
      .then(function (r) {
        if (!r.ok || !r.data || r.data.ok === false) {
          throw new Error((r.data && r.data.error) || "No se pudo cargar el pedido.");
        }
        cerrar();
        if (cfg.onCargado) cfg.onCargado(r.data);
        else if (cfg.compraUrl) window.location.href = cfg.compraUrl;
      })
      .catch(function (err) {
        errorEl().textContent = err.message || "Error.";
        errorEl().classList.remove("hidden");
        btnConfirmar().disabled = false;
      });
  }

  function init(options) {
    cfg = options || {};
    document.querySelectorAll("[data-repetir-cerrar]").forEach(function (btn) {
      btn.addEventListener("click", cerrar);
    });
    var confirm = btnConfirmar();
    if (confirm) confirm.addEventListener("click", confirmar);
  }

  window.SynapRepetirPedido = { init: init, abrir: abrir, cerrar: cerrar };
})();
