(function () {
  "use strict";

  const root = document.getElementById("alta-recibo-app");
  if (!root) return;

  const altaUrl = root.dataset.altaUrl + "?ajax=1";
  const catalogosBase = root.dataset.catalogosUrl;
  const listadoUrl = root.dataset.imputarListadoUrl + "?ajax=1";
  const accionUrl = root.dataset.imputarAccionUrl + "?ajax=1";
  const idCaja = root.dataset.idCaja || "";
  const writeEnabled = root.dataset.writeEnabled === "1";
  const urlRecibos = root.dataset.urlRecibos || "/ecom/mayoristapp/listado/recibos/";
  const statusEl = document.getElementById("alta-recibo-status");

  let facturasImputadas = {};
  let cotiDolar = 1;
  let saldoAFavorDisponible = 0;
  let catalogos = { puntos_venta: [], cuentas: [], tarjetas: [], retenciones: [] };

  function csrfToken() {
    const input = root.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : "";
  }

  function setStatus(msg, isError) {
    if (!statusEl) return;
    statusEl.textContent = msg || "";
    statusEl.className = "mt-6 text-xs " + (isError ? "text-rose-600" : "text-slate-500");
  }

  async function postJson(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken() },
      credentials: "same-origin",
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({}));
    return { res, data };
  }

  async function getCatalogo(tipo, extra) {
    const q = new URLSearchParams({ tipo });
    if (extra) Object.keys(extra).forEach((k) => q.set(k, extra[k]));
    const res = await fetch(catalogosBase + "?ajax=1&" + q.toString(), { credentials: "same-origin" });
    return res.json().catch(() => ({}));
  }

  function irPaso(n) {
    root.querySelectorAll("[data-step-panel]").forEach((el) => {
      el.classList.toggle("hidden", el.dataset.stepPanel !== String(n));
    });
    root.querySelectorAll("[data-step-tab]").forEach((btn) => {
      const active = btn.dataset.stepTab === String(n);
      btn.className =
        "step-tab rounded-full px-4 py-1.5 text-xs font-semibold " +
        (active ? "bg-sky-100 text-sky-800" : "bg-slate-100 text-slate-600");
    });
  }

  root.querySelectorAll("[data-step-tab]").forEach((btn) => {
    btn.addEventListener("click", () => irPaso(Number(btn.dataset.stepTab)));
  });

  async function cargarCatalogosIniciales() {
    const [pv, coti, acuenta, cuentas, rets, tjs] = await Promise.all([
      getCatalogo("puntos-venta"),
      getCatalogo("cotizacion-dolar"),
      getCatalogo("saldo-a-cuenta"),
      getCatalogo("cuentas-bancarias"),
      getCatalogo("retenciones"),
      getCatalogo("tarjetas", { subtipo: "Credito" }),
    ]);
    catalogos.puntos_venta = pv.puntos_venta || [];
    catalogos.cuentas = cuentas.cuentas || [];
    catalogos.retenciones = rets.retenciones || [];
    catalogos.tarjetas = tjs.tarjetas || [];
    cotiDolar = Number(coti.valor || 1);
    const cotiLbl = document.getElementById("coti-dolar-label");
    if (cotiLbl) cotiLbl.textContent = "Cotización USD: $" + cotiDolar.toFixed(2);
    const acLbl = document.getElementById("saldo-a-cuenta-label");
    if (acLbl && acuenta.acuenta != null) {
      saldoAFavorDisponible = Number(acuenta.acuenta || 0);
      acLbl.textContent = "Saldo a favor (a cuenta): $" + saldoAFavorDisponible.toFixed(2);
    }
    const sfDisp = document.getElementById("saldo-favor-disponible");
    if (sfDisp) {
      sfDisp.textContent =
        saldoAFavorDisponible > 0
          ? "Disponible: $" + saldoAFavorDisponible.toFixed(2)
          : "Sin saldo a favor registrado.";
    }
    const selPv = document.getElementById("selectPv");
    if (selPv) {
      selPv.innerHTML = "";
      catalogos.puntos_venta.forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.value;
        opt.textContent = p.label;
        selPv.appendChild(opt);
      });
    }
    fillSelect("selectCuentaBancaria", catalogos.cuentas);
    fillSelect("selectRetencion", catalogos.retenciones);
    fillSelect("selectTarjeta", catalogos.tarjetas);
  }

  function fillSelect(id, items) {
    const sel = document.getElementById(id);
    if (!sel) return;
    sel.innerHTML = '<option value="">— Seleccionar —</option>';
    (items || []).forEach((it) => {
      const opt = document.createElement("option");
      opt.value = it.id;
      opt.textContent = it.text;
      sel.appendChild(opt);
    });
  }

  document.getElementById("selectTipoNro")?.addEventListener("change", (e) => {
    const wrap = document.getElementById("wrapTalonario");
    if (wrap) wrap.classList.toggle("hidden", e.target.value !== "talonario");
  });

  document.getElementById("selectTarjeta")?.addEventListener("change", async (e) => {
    const raw = e.target.value || "";
    const idTc = raw.split("|")[0];
    if (!idTc) return;
    const data = await getCatalogo("planes-tarjeta", { idTC: idTc });
    fillSelect("selectPlanTarjeta", data.planes || []);
  });

  document.getElementById("btnIniciarRecibo")?.addEventListener("click", async () => {
    if (!writeEnabled) return;
    const tipo = document.getElementById("selectTipoNro")?.value || "sistema";
    const pv = document.getElementById("selectPv")?.value || "";
    const body = { iniciar: 1, tipoNro: tipo, nroPv: pv, puntoVenta: pv };
    if (tipo === "talonario") {
      body.nroRec = document.getElementById("inputNroTalonario")?.value;
    }
    setStatus("Iniciando recibo…");
    const { res, data } = await postJson(altaUrl, body);
    if (!res.ok || data.msg !== "ok") {
      setStatus(data.desc || data.error || "No se pudo iniciar.", true);
      return;
    }
    document.getElementById("nro-recibo-label").textContent = "Recibo: " + (data.numero || "");
    setStatus("Recibo iniciado.");
    irPaso(2);
    cargarFacturas();
  });

  async function cargarFacturas() {
    const { res, data } = await postJson(listadoUrl, { campoBusca: "-", limit: 80 });
    if (!res.ok) return setStatus("Error al cargar facturas.", true);
    const tbody = document.getElementById("facturas-tbody");
    if (!tbody) return;
    tbody.innerHTML = "";
    (data.filas || []).forEach((f) => {
      const id = String(f.id_recibo_factura || f.idrecibofactura || "");
      const saldo = parseFloat(f.Saldo || f.saldo || 0);
      const imp = facturasImputadas[id];
      const tr = document.createElement("tr");
      tr.innerHTML =
        `<td class="px-3 py-2">${f.NroComprobante || ""}</td>` +
        `<td class="px-3 py-2">${saldo.toFixed(2)}</td>` +
        `<td class="px-3 py-2">${imp ? imp.toFixed(2) : "-"}</td>` +
        `<td class="px-3 py-2"><button type="button" class="text-sky-600 text-xs font-semibold btn-imputar">Imputar</button></td>`;
      tr.dataset.factura = JSON.stringify(f);
      tbody.appendChild(tr);
    });
    tbody.querySelectorAll(".btn-imputar").forEach((btn) => {
      btn.addEventListener("click", () => imputarFila(btn.closest("tr")));
    });
  }

  async function imputarFila(tr) {
    if (!tr || !writeEnabled) return;
    const f = JSON.parse(tr.dataset.factura || "{}");
    const saldo = parseFloat(f.Saldo || f.saldo || 0);
    const monto = prompt("Monto a imputar (máx. " + saldo.toFixed(2) + "):", saldo.toFixed(2));
    if (!monto) return;
    const aimputar = parseFloat(monto);
    if (!(aimputar > 0) || aimputar > saldo) return setStatus("Monto inválido.", true);
    const id = String(f.id_recibo_factura || f.idrecibofactura || "");
    const { res, data } = await postJson(accionUrl, {
      imputarFactura: 1,
      idrecibofactura: id,
      codmodfact: f.CodigoMovimiento,
      fecha: f.Fecha,
      nrofactura: f.NroComprobante,
      importe: f.Importe,
      cancelado: f.Cancelado || f.cancelado || 0,
      saldo,
      aimputar,
      tipocomprobante: f.TipoComprobante,
      vencimiento: f.Vencimiento,
      condventa: f.CondVenta,
    });
    if (!res.ok || data.msg !== "ok") return setStatus(data.error || "Error al imputar.", true);
    facturasImputadas[id] = aimputar;
    cargarFacturas();
  }

  document.getElementById("btnCargarFacturas")?.addEventListener("click", cargarFacturas);

  document.getElementById("btnAplicarDescuento")?.addEventListener("click", async () => {
    const pct = document.getElementById("inputDescuentoPct")?.value;
    const { data } = await postJson(altaUrl, { descuento: 1, porcentaje: pct });
    setStatus(data.msg === "ok" ? "Descuento aplicado." : data.error || "Error descuento.", data.msg !== "ok");
  });

  document.getElementById("btnFinImputacion")?.addEventListener("click", async () => {
    const { res, data } = await postJson(accionUrl, { finImputacion: 1 });
    if (!res.ok || data.msg !== "ok") return setStatus("Debe imputar al menos una factura.", true);
    document.getElementById("total-imputado-label").textContent =
      "Total imputado: $" + Number(data.total || 0).toFixed(2);
    irPaso(3);
  });

  document.getElementById("btnGuardarEfectivo")?.addEventListener("click", async () => {
    const pesos = parseFloat(document.getElementById("inputEfectivoPesos")?.value || "0");
    const dolar = parseFloat(document.getElementById("inputEfectivoDolar")?.value || "0");
    if (pesos > 0) {
      await postJson(altaUrl, { efectivo: 1, moneda: "pesos", pesos, idcaja: idCaja, coti: cotiDolar });
    }
    if (dolar > 0) {
      await postJson(altaUrl, { efectivo: 1, moneda: "dolar", dolar, idcaja: idCaja, coti: cotiDolar });
    }
    const { data: resumen } = await postJson(altaUrl, { resumen: 1 });
    document.getElementById("total-efectivo-label").textContent =
      "Efectivo registrado. Total recibo: $" + Number(resumen.total || 0).toFixed(2);
    setStatus("Efectivo actualizado.");
  });

  document.getElementById("btnAgregarCheque")?.addEventListener("click", async () => {
    const { data } = await postJson(altaUrl, {
      cheque: 1,
      numero: document.getElementById("chNumero")?.value,
      importe: document.getElementById("chImporte")?.value,
      librador: document.getElementById("chLibrador")?.value,
      banco: document.getElementById("chBanco")?.value,
      codbanco: "1",
      cobro: document.getElementById("chCobro")?.value,
      emison: document.getElementById("chCobro")?.value,
      idCajaCheque: idCaja,
    });
    if (data.msg === "ok") await refrescarResumenMedios();
    else setStatus(data.error || "Error cheque.", true);
  });

  document.getElementById("btnAgregarTransferencia")?.addEventListener("click", async () => {
    const sel = document.getElementById("selectCuentaBancaria");
    const opt = sel?.selectedOptions[0];
    const { data } = await postJson(altaUrl, {
      transferencia: 1,
      idCuentaBancaria: sel?.value,
      numeroCuenta: opt?.textContent || "",
      nroTransferencia: document.getElementById("trNro")?.value,
      fecha: document.getElementById("trFecha")?.value,
      importe: document.getElementById("trImporte")?.value,
      detalle: document.getElementById("trNro")?.value,
    });
    if (data.msg === "ok") await refrescarResumenMedios();
    else setStatus(data.error || "Error transferencia.", true);
  });

  document.getElementById("btnAgregarTarjeta")?.addEventListener("click", async () => {
    const selTj = document.getElementById("selectTarjeta");
    const selPl = document.getElementById("selectPlanTarjeta");
    const { data } = await postJson(altaUrl, {
      tarjeta: 1,
      clase: selTj?.value,
      nombreClase: selTj?.selectedOptions[0]?.textContent,
      plan: selPl?.value,
      nombrePlan: selPl?.selectedOptions[0]?.textContent,
      numero: document.getElementById("tjNumero")?.value,
      importe: document.getElementById("tjImporte")?.value,
      cupon: document.getElementById("tjCupon")?.value,
      cuotas: 1,
      importeCuota: document.getElementById("tjImporte")?.value,
      tipo: "Credito",
    });
    if (data.msg === "ok") await refrescarResumenMedios();
    else setStatus(data.error || "Error tarjeta.", true);
  });

  document.getElementById("btnAgregarRetencion")?.addEventListener("click", async () => {
    const sel = document.getElementById("selectRetencion");
    const { data } = await postJson(altaUrl, {
      retencion: 1,
      cod: sel?.value,
      tipo: sel?.selectedOptions[0]?.textContent,
      certificado: document.getElementById("retCertificado")?.value,
      monto: document.getElementById("retMonto")?.value,
      fecha: document.getElementById("retFecha")?.value,
      porcentaje: 0,
    });
    if (data.msg === "ok") await refrescarResumenMedios();
    else setStatus(data.error || "Error retención.", true);
  });

  document.getElementById("btnAplicarSaldoAFavor")?.addEventListener("click", async () => {
    const monto = parseFloat(document.getElementById("inputSaldoAFavor")?.value || "0");
    if (!(monto > 0)) return setStatus("Ingrese un monto válido.", true);
    if (monto > saldoAFavorDisponible) {
      return setStatus("El monto supera el saldo a favor disponible.", true);
    }
    const { data } = await postJson(altaUrl, { saldoAFavor: 1, monto });
    if (data.msg !== "ok") return setStatus(data.error || "No se pudo aplicar saldo a favor.", true);
    const lbl = document.getElementById("saldo-favor-aplicado-label");
    if (lbl) lbl.textContent = "Saldo a favor aplicado: $" + Number(data.total || 0).toFixed(2);
    setStatus("Saldo a favor aplicado.");
    await refrescarResumenMedios();
  });

  document.getElementById("btnQuitarSaldoAFavor")?.addEventListener("click", async () => {
    await postJson(altaUrl, { borrarSaldoAFavor: 1 });
    const lbl = document.getElementById("saldo-favor-aplicado-label");
    if (lbl) lbl.textContent = "";
    const inp = document.getElementById("inputSaldoAFavor");
    if (inp) inp.value = "";
    setStatus("Saldo a favor quitado.");
    await refrescarResumenMedios();
  });

  async function refrescarResumenMedios() {
    const { data } = await postJson(altaUrl, { resumen: 1 });
    const ch = document.getElementById("lista-cheques");
    const tr = document.getElementById("lista-transferencias");
    const tj = document.getElementById("lista-tarjetas");
    const rt = document.getElementById("lista-retenciones");
    if (ch) ch.innerHTML = (data.cheques || []).map((c) => `<li>Cheque ${c.numero}: $${c.importe}</li>`).join("");
    if (tr) tr.innerHTML = (data.transferencias || []).map((t, i) => `<li>Transf. ${t.numeroTransferencia}: $${t.total}</li>`).join("");
    if (tj) tj.innerHTML = (data.tarjetas || []).map((t) => `<li>${t.nombreClase || t.numero}: $${t.importe}</li>`).join("");
    if (rt) rt.innerHTML = (data.retenciones || []).map((r) => `<li>${r.tipo}: $${r.monto}</li>`).join("");
    const sfLbl = document.getElementById("saldo-favor-aplicado-label");
    const sfMedio = (data.medios || []).find((m) => m.campo === "Saldo a favor");
    if (sfLbl) {
      sfLbl.textContent = sfMedio
        ? "Saldo a favor aplicado: $" + Number(sfMedio.valor).toFixed(2)
        : "";
    }
  }

  document.getElementById("btnIrResumen")?.addEventListener("click", async () => {
    await mostrarResumen();
    irPaso(4);
  });

  async function mostrarResumen() {
    const { data: resumen } = await postJson(altaUrl, { resumen: 1 });
    const { data: ctrl } = await postJson(altaUrl, { controlFinal: 1 });
    const box = document.getElementById("resumen-recibo");
    const ctrlMsg = document.getElementById("control-final-msg");
    if (box) {
      let html =
        `<p><strong>N.º recibo:</strong> ${resumen.nroRecibo || "-"}</p>` +
        `<p><strong>Total recibo:</strong> $${Number(resumen.total || 0).toFixed(2)}</p>` +
        `<p><strong>Total imputado:</strong> $${Number(resumen.totalImputado || 0).toFixed(2)}</p>`;
      if (resumen.aCuenta) html += `<p><strong>A cuenta:</strong> $${Number(resumen.aCuenta).toFixed(2)}</p>`;
      (resumen.medios || []).forEach((m) => {
        html += `<p>${m.campo}: $${Number(m.valor).toFixed(2)}</p>`;
      });
      box.innerHTML = html;
    }
    if (ctrlMsg) {
      if (ctrl.msg === "ok") {
        ctrlMsg.textContent = "Control OK. Saldo: $" + Number(ctrl.saldo || 0).toFixed(2);
        ctrlMsg.className = "text-sm text-emerald-700 mb-4";
      } else {
        ctrlMsg.textContent = "Falta cubrir: $" + Number(ctrl.deuda || 0).toFixed(2);
        ctrlMsg.className = "text-sm text-amber-700 mb-4";
      }
    }
  }

  document.getElementById("btnGuardarRecibo")?.addEventListener("click", async () => {
    if (!writeEnabled) return;
    setStatus("Guardando recibo…");
    const { res, data } = await postJson(altaUrl, { guardar: 1 });
    if (!res.ok || data.msg !== "ok") return setStatus(data.desc || data.error || "Error al guardar.", true);
    setStatus("Recibo guardado: " + (data.nro_recibo || ""));
    setTimeout(() => { window.location.href = urlRecibos; }, 1200);
  });

  document.getElementById("btnCancelarRecibo")?.addEventListener("click", async () => {
    await postJson(altaUrl, { cancelar: 1 });
    window.location.href = urlRecibos;
  });

  cargarCatalogosIniciales();
})();
