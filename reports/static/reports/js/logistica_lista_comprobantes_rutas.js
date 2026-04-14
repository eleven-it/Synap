/**
 * Filtros en vivo, autocompletado, detalle y registro de entrega — Lista comprobantes en rutas.
 */
(function () {
  const API_BASE = "/api/reports/logistica/lista-comprobantes-rutas";
  const FILTERS_LS_KEY = "report_filters_comprobantes-rutas";
  const FILTERS_LS_KEY_LEGACY = "report_filters_mayoristapp-lista-comprobantes-rutas";

  /** descripcion -> requiere_detalle (catálogo MySQL ``logi_motivo_no_entrega``) */
  let motivoRequiereDetalleMap = new Map();

  /** Lee filtros guardados; migra clave antigua si existe. */
  function readFiltersFromLocalStorage() {
    let raw = localStorage.getItem(FILTERS_LS_KEY);
    if (!raw) {
      raw = localStorage.getItem(FILTERS_LS_KEY_LEGACY);
      if (raw) {
        try {
          localStorage.setItem(FILTERS_LS_KEY, raw);
          localStorage.removeItem(FILTERS_LS_KEY_LEGACY);
        } catch (e) {
          /* ignorar cuota */
        }
      }
    }
    return raw;
  }

  function getCsrf() {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let i = 0; i < cookies.length; i += 1) {
      const cookie = cookies[i].trim();
      if (cookie.startsWith(`${name}=`)) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
  }

  function toastLocal(msg, type) {
    const container = document.createElement("div");
    container.className = `fixed top-5 right-5 z-[250] px-3 py-2 rounded-lg shadow-lg text-xs font-semibold ${
      type === "error" ? "bg-rose-600 text-white" : "bg-emerald-600 text-white"
    }`;
    container.textContent = msg;
    document.body.appendChild(container);
    setTimeout(() => container.remove(), 3500);
  }

  function refetch() {
    if (typeof window.fetchDashboardData === "function") {
      window.fetchDashboardData();
    }
  }

  const modalDet = () => document.getElementById("logistica-modal-detalle");
  const modalEnt = () => document.getElementById("logistica-modal-entrega");

  /** Escapa texto para insertar en innerHTML */
  function esc(s) {
    if (s === null || s === undefined) return "";
    const t = document.createElement("div");
    t.textContent = String(s);
    return t.innerHTML;
  }

  function lowerKeys(obj) {
    const o = {};
    if (!obj || typeof obj !== "object") return o;
    Object.keys(obj).forEach((k) => {
      o[k.toLowerCase()] = obj[k];
    });
    return o;
  }

  function getv(d, ...keys) {
    for (let i = 0; i < keys.length; i += 1) {
      const k = keys[i].toLowerCase();
      const v = d[k];
      if (v !== undefined && v !== null && v !== "") return v;
    }
    return null;
  }

  function formatArs(n) {
    if (n === null || n === undefined || n === "") return "—";
    const num = typeof n === "number" ? n : parseFloat(String(n).replace(",", "."));
    if (Number.isNaN(num)) return esc(String(n));
    try {
      return new Intl.NumberFormat("es-AR", {
        style: "currency",
        currency: "ARS",
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(num);
    } catch (_) {
      return esc(String(n));
    }
  }

  function estadoEntregaLabel(d) {
    const ent = String(getv(d, "entregado") ?? "").trim();
    if (ent === "Si") return "Entregado";
    if (ent === "No") return "No entregado";
    if (ent) return ent;
    return "—";
  }

  /**
   * Material Icons (fuente `Material Icons` en base_app.html). `variant`: cabecera de sección vs fila.
   * `colorClass`: clases Tailwind para el color del glifo (acento semántico).
   */
  function materialIcon(glyphName, variant, colorClass) {
    const size = variant === "section" ? "text-2xl leading-none" : "text-xl leading-none";
    const col = colorClass || "text-indigo-600 dark:text-indigo-400";
    return `<span class="material-icons flex-shrink-0 ${size} ${col}" aria-hidden="true">${glyphName}</span>`;
  }

  const ICON = {
    chain: materialIcon("timeline", "section", "text-sky-600 dark:text-sky-400"),
    clip: materialIcon("receipt_long", "row", "text-amber-600 dark:text-amber-400"),
    doc: materialIcon("receipt", "row", "text-emerald-600 dark:text-emerald-400"),
    map: materialIcon("map", "section", "text-indigo-600 dark:text-indigo-400"),
    sign: materialIcon("route", "row", "text-cyan-600 dark:text-cyan-400"),
    flag: materialIcon("flag", "row", "text-rose-500 dark:text-rose-400"),
    truck: materialIcon("person", "row", "text-violet-600 dark:text-violet-400"),
    remito: materialIcon("local_shipping", "row", "text-blue-600 dark:text-blue-400"),
    entregaOk: materialIcon("verified", "row", "text-emerald-600 dark:text-emerald-400"),
    entregaNo: materialIcon("highlight_off", "row", "text-rose-600 dark:text-rose-400"),
  };

  /**
   * Último paso de Trazabilidad: resultado de entrega en destino (misma envoltura que filaTrazabilidad).
   * @param {Record<string, unknown>} d — fila detalle (keys en minúsculas)
   */
  function filaTrazabilidadPasoEntrega(d) {
    const estado = estadoEntregaLabel(d);
    const fechaHoraEnt = getv(d, "fechahoraentregab") || getv(d, "fecha_hora_entrega");
    const motivo = getv(d, "motivo_no_entrega");
    if (estado !== "Entregado" && estado !== "No entregado") {
      return "";
    }
    const isEnt = estado === "Entregado";
    const stripe = isEnt
      ? "border-l-[3px] border-l-emerald-500/95 dark:border-l-emerald-400/80"
      : "border-l-[3px] border-l-rose-400/95 dark:border-l-rose-400/80";
    const dots = isEnt ? "text-emerald-300 dark:text-emerald-600" : "text-rose-300 dark:text-rose-500";
    const baseWrap =
      "flex gap-3 items-start rounded-xl border border-slate-100/95 dark:border-slate-600/45 bg-slate-50/90 dark:bg-slate-900/35 px-3.5 py-2.5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.6)] dark:shadow-none";
    if (isEnt) {
      const fh =
        fechaHoraEnt != null && String(fechaHoraEnt).trim() !== ""
          ? esc(String(fechaHoraEnt))
          : "—";
      return `
      <div class="${baseWrap} ${stripe}">
        ${ICON.entregaOk}
        <div class="flex flex-nowrap items-baseline gap-x-2 text-sm text-slate-600 dark:text-slate-300 flex-1 min-w-0 overflow-x-auto [scrollbar-width:thin]">
          <span class="whitespace-nowrap">Entrega</span>
          <span class="${dots} flex-shrink-0">·</span>
          <span class="whitespace-nowrap">Fecha y hora <strong class="text-slate-900 dark:text-white font-semibold">${fh}</strong></span>
        </div>
      </div>`;
    }
    const motEsc =
      motivo != null && String(motivo).trim() !== "" ? esc(String(motivo)) : "—";
    return `
      <div class="${baseWrap} ${stripe}">
        ${ICON.entregaNo}
        <div class="flex flex-nowrap items-baseline gap-x-2 text-sm text-slate-600 dark:text-slate-300 flex-1 min-w-0 overflow-x-auto [scrollbar-width:thin]">
          <span class="whitespace-nowrap">Entrega</span>
          <span class="${dots} flex-shrink-0">·</span>
          <span class="whitespace-nowrap">Estado <strong class="text-slate-900 dark:text-white font-semibold">No entregado</strong></span>
          <span class="${dots} flex-shrink-0">·</span>
          <span class="whitespace-nowrap">Motivo <strong class="text-slate-900 dark:text-white font-semibold">${motEsc}</strong></span>
        </div>
      </div>`;
  }

  /** Cliente destacado encima de Trazabilidad (sin sección aparte “Preparación”). */
  function renderClienteDestacado(cli) {
    const nombre = cli != null && String(cli).trim() !== "" ? esc(String(cli)) : "—";
    const icon = materialIcon("business", "section", "text-fuchsia-600 dark:text-fuchsia-400");
    return `
      <div class="mb-5 flex gap-4 rounded-2xl border border-fuchsia-200/50 dark:border-fuchsia-900/40 bg-gradient-to-r from-fuchsia-50/80 via-white to-violet-50/60 dark:from-fuchsia-950/25 dark:via-slate-800/40 dark:to-violet-950/30 px-5 py-4 shadow-md shadow-fuchsia-900/5 ring-1 ring-inset ring-fuchsia-100/80 dark:ring-fuchsia-900/30" role="region" aria-label="Cliente">
        <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-fuchsia-500/20 to-violet-600/25 dark:from-fuchsia-500/30 dark:to-violet-600/35 ring-1 ring-fuchsia-300/70 dark:ring-fuchsia-500/40 shadow-sm">
          ${icon}
        </div>
        <div class="min-w-0 flex-1">
          <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-fuchsia-700/90 dark:text-fuchsia-300/90 mb-1">Cliente</p>
          <p class="text-base sm:text-[1.0625rem] font-semibold text-slate-900 dark:text-slate-50 leading-snug break-words">${nombre}</p>
        </div>
      </div>`;
  }

  /**
   * @param {object} [opts]
   * @param {string} [opts.iconBoxClass] — fondo del recuadro del icono en la cabecera
   * @param {string} [opts.headerBarClass] — barra superior de la sección
   */
  function seccionCard(titulo, iconoSvg, innerHtml, opts) {
    const o = opts || {};
    const iconBox =
      o.iconBoxClass ||
      "bg-white dark:bg-slate-900 shadow-sm ring-1 ring-slate-200/90 dark:ring-slate-600/70";
    const headerBar =
      o.headerBarClass ||
      "bg-gradient-to-r from-slate-50 to-indigo-50/50 dark:from-slate-800/95 dark:to-indigo-950/25 border-b border-slate-100 dark:border-slate-700/55";
    return `
      <section class="mb-4 last:mb-0 overflow-hidden rounded-2xl border border-slate-200/90 dark:border-slate-700/55 bg-white/95 dark:bg-slate-800/40 shadow-sm shadow-slate-900/[0.06] ring-1 ring-inset ring-slate-100/90 dark:ring-slate-700/35">
        <div class="flex items-center gap-3 px-5 py-3.5 ${headerBar}">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${iconBox}">
            ${iconoSvg}
          </div>
          <h4 class="text-sm font-semibold tracking-tight text-slate-800 dark:text-slate-100">${esc(titulo)}</h4>
        </div>
        <div class="space-y-2.5 px-5 py-4">${innerHtml}</div>
      </section>`;
  }

  /**
   * @param {object} [accent] — `stripe` borde izquierdo; `dots` color separadores ·
   */
  function filaTrazabilidad(icono, labelDoc, nro, fecha, total, accent) {
    const a = accent || {};
    const stripe = a.stripe || "";
    const dots = a.dots || "text-slate-300 dark:text-slate-600";
    const n = nro != null && nro !== "" ? esc(String(nro)) : "—";
    const f = fecha != null && fecha !== "" ? esc(String(fecha)) : "—";
    const t = total != null && total !== "" ? formatArs(total) : "—";
    return `
      <div class="flex gap-3 items-start rounded-xl border border-slate-100/95 dark:border-slate-600/45 bg-slate-50/90 dark:bg-slate-900/35 px-3.5 py-2.5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.6)] dark:shadow-none ${stripe}">
        ${icono}
        <div class="flex flex-nowrap items-baseline gap-x-2 text-sm text-slate-600 dark:text-slate-300 flex-1 min-w-0 overflow-x-auto [scrollbar-width:thin]">
          <span class="whitespace-nowrap">${esc(labelDoc)}: <strong class="text-slate-900 dark:text-white font-semibold">${n}</strong></span>
          <span class="${dots} flex-shrink-0">·</span>
          <span class="whitespace-nowrap">Fecha y hora <strong class="text-slate-900 dark:text-white font-semibold">${f}</strong></span>
          <span class="${dots} flex-shrink-0">·</span>
          <span class="whitespace-nowrap">Total <strong class="text-slate-900 dark:text-white font-semibold">${t}</strong></span>
        </div>
      </div>`;
  }

  function badgeEstadoEntrega(estado) {
    let cls =
      "inline-flex items-center rounded-full px-3 py-1.5 text-xs font-semibold ring-1 ";
    if (estado === "Entregado") {
      cls += "bg-emerald-500/12 text-emerald-800 dark:text-emerald-300 ring-emerald-500/30";
    } else if (estado === "No entregado") {
      cls += "bg-rose-500/12 text-rose-800 dark:text-rose-200 ring-rose-500/30";
    } else {
      cls += "bg-slate-500/10 text-slate-700 dark:text-slate-300 ring-slate-500/25";
    }
    return `<div class="mb-4"><span class="${cls}">${esc(estado)}</span></div>`;
  }

  function renderDetalleHtml(dataRaw) {
    const d = lowerKeys(dataRaw);
    const nroRem = getv(d, "nroremito");
    const estado = estadoEntregaLabel(d);

    const meta = `${badgeEstadoEntrega(estado)}`;

    const traz =
      seccionCard(
        "Trazabilidad",
        ICON.chain,
        filaTrazabilidad(ICON.clip, "Pedido", getv(d, "nropedido"), getv(d, "fechahorapedidob", "fechapedidob"), getv(d, "totalpedido"), {
          stripe: "border-l-[3px] border-l-amber-400/95 dark:border-l-amber-500/80",
          dots: "text-amber-300 dark:text-amber-600",
        }) +
          filaTrazabilidad(ICON.doc, "Factura", getv(d, "nrofactura"), getv(d, "fechahorafacturab", "fechafacturab"), getv(d, "totalfactura"), {
            stripe: "border-l-[3px] border-l-emerald-400/95 dark:border-l-emerald-500/80",
            dots: "text-emerald-300 dark:text-emerald-600",
          }) +
          filaTrazabilidad(ICON.remito, "Remito", nroRem, getv(d, "fechahoraremitob", "fecharemitob", "fecharemito"), getv(d, "totalremito"), {
            stripe: "border-l-[3px] border-l-blue-400/95 dark:border-l-blue-500/80",
            dots: "text-blue-300 dark:text-blue-600",
          }) +
          filaTrazabilidadPasoEntrega(d),
        {
          iconBoxClass:
            "bg-gradient-to-br from-sky-100/90 to-cyan-50/70 dark:from-sky-900/50 dark:to-cyan-950/35 ring-1 ring-sky-300/55 dark:ring-sky-600/40 shadow-sm",
          headerBarClass:
            "bg-gradient-to-r from-sky-50/95 via-white to-violet-50/55 dark:from-slate-800 dark:via-slate-800/95 dark:to-violet-950/35 border-b border-sky-100/90 dark:border-slate-700/55",
        },
      );

    const rutaDesc = getv(d, "desc_ruta");
    const rutaEst = getv(d, "estado_ruta");
    const chofer = getv(d, "nombre_chofer");
    const ordenParada = getv(d, "orden_ruta");
    const salidaProg = getv(d, "fecha_salida_ruta_fmt");
    const ventana = getv(d, "ventana_horaria_ruta");
    /** Misma envoltura que ``filaTrazabilidad``: fondo neutro; solo acento en ``border-l``. */
    const filaRuta = (stripeBorder, icono, labelHtml) =>
      `<div class="flex gap-3 items-start rounded-xl border border-slate-100/95 dark:border-slate-600/45 bg-slate-50/90 dark:bg-slate-900/35 px-3.5 py-2.5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.6)] dark:shadow-none border-l-[3px] ${stripeBorder}">
        ${icono}
        <div class="text-sm text-slate-600 dark:text-slate-300 flex-1 min-w-0">${labelHtml}</div>
      </div>`;
    const rutaInner = `
      <div class="space-y-2.5">
        ${filaRuta(
          "border-l-cyan-500/90 dark:border-l-cyan-400/85",
          ICON.sign,
          `Ruta <strong class="text-slate-900 dark:text-white font-semibold">${rutaDesc != null ? esc(String(rutaDesc)) : "—"}</strong>`,
        )}
        ${filaRuta(
          "border-l-rose-400/90 dark:border-l-rose-400/80",
          ICON.flag,
          `Estado ruta <strong class="text-slate-900 dark:text-white font-semibold">${rutaEst != null ? esc(String(rutaEst)) : "—"}</strong>`,
        )}
        ${filaRuta(
          "border-l-amber-500/90 dark:border-l-amber-400/85",
          ICON.sign,
          `Orden en ruta <strong class="text-slate-900 dark:text-white font-semibold">${ordenParada != null && ordenParada !== "" ? esc(String(ordenParada)) : "—"}</strong>`,
        )}
        ${filaRuta(
          "border-l-sky-500/90 dark:border-l-sky-400/85",
          ICON.sign,
          `Salida programada <strong class="text-slate-900 dark:text-white font-semibold">${salidaProg != null ? esc(String(salidaProg)) : "—"}</strong>`,
        )}
        ${filaRuta(
          "border-l-teal-500/90 dark:border-l-teal-400/85",
          ICON.sign,
          `Franja horaria (ruta) <strong class="text-slate-900 dark:text-white font-semibold">${ventana != null ? esc(String(ventana)) : "—"}</strong>`,
        )}
        ${filaRuta(
          "border-l-violet-500/90 dark:border-l-violet-400/85",
          ICON.truck,
          `Chofer <strong class="text-slate-900 dark:text-white font-semibold">${chofer != null ? esc(String(chofer)) : "—"}</strong>`,
        )}
      </div>`;

    const rutaYChofer = seccionCard("Ruta y Chofer", ICON.map, rutaInner, {
      iconBoxClass:
        "bg-gradient-to-br from-indigo-100/90 to-purple-100/75 dark:from-indigo-900/45 dark:to-purple-950/40 ring-1 ring-indigo-300/50 dark:ring-indigo-600/40 shadow-sm",
      headerBarClass:
        "bg-gradient-to-r from-indigo-50/90 via-violet-50/40 to-purple-50/55 dark:from-indigo-950/45 dark:via-slate-800/95 dark:to-purple-950/35 border-b border-indigo-100/85 dark:border-slate-700/55",
    });

    const cli = getv(d, "cliente");
    const clienteBloque = renderClienteDestacado(cli);

    return meta + clienteBloque + traz + rutaYChofer;
  }

  window.SynapLogisticaListaCR = {
    openDetalle(codMov) {
      const m = modalDet();
      const cuerpo = document.getElementById("logistica-detalle-cuerpo");
      if (!m || !cuerpo) return;
      cuerpo.innerHTML = '<p class="text-center py-10 text-slate-500 dark:text-slate-400 text-sm">Cargando…</p>';
      m.classList.remove("hidden");
      fetch(`${API_BASE}/remito/${encodeURIComponent(codMov)}/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((r) => r.json())
        .then((body) => {
          if (body.msg === "ok" && body.data) {
            cuerpo.innerHTML = renderDetalleHtml(body.data);
          } else {
            cuerpo.innerHTML = `<p class="text-center py-8 text-rose-600 dark:text-rose-400 text-sm">${esc(body.detail || body.msg || "Sin datos")}</p>`;
          }
        })
        .catch(() => {
          cuerpo.innerHTML =
            '<p class="text-center py-8 text-rose-600 dark:text-rose-400 text-sm">Error al cargar el detalle.</p>';
        });
    },
    openEntrega({ cod_mov_remito, cod_mov_pedido }) {
      const m = modalEnt();
      if (!m) return;
      document.getElementById("logistica_entrega_cod_remito").value = cod_mov_remito ?? "";
      document.getElementById("logistica_entrega_cod_pedido").value = cod_mov_pedido ?? "";
      document.getElementById("logistica_entrega_estado").value = "";
      document.getElementById("logistica_entrega_detalle").value = "";
      const motivoWrap = document.getElementById("logistica_entrega_motivo_wrap");
      const motivoSel = document.getElementById("logistica_entrega_motivo");
      if (motivoWrap) motivoWrap.classList.add("hidden");
      if (motivoSel) motivoSel.selectedIndex = 0;
      if (typeof window.__logisticaPaintResultado === "function") window.__logisticaPaintResultado("");
      if (typeof window.__logisticaUpdateDetalleHint === "function") window.__logisticaUpdateDetalleHint();
      m.classList.remove("hidden");
      window.SynapLogisticaListaCR.ensureMotivos();
    },
    ensureMotivos() {
      const motivoSel = document.getElementById("logistica_entrega_motivo");
      if (!motivoSel) return Promise.resolve();
      if (motivoSel.dataset.loaded === "1") {
        if (typeof window.__logisticaSyncDetReq === "function") window.__logisticaSyncDetReq();
        return Promise.resolve();
      }
      return fetch(`${API_BASE}/motivos-no-entrega/`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then((r) => r.json())
        .then((body) => {
          motivoRequiereDetalleMap = new Map();
          (body.motivos_catalogo || []).forEach((row) => {
            if (row && row.descripcion) {
              motivoRequiereDetalleMap.set(row.descripcion, !!row.requiere_detalle);
            }
          });
          const motivos = body.motivos || [];
          motivos.forEach((txt) => {
            const o = document.createElement("option");
            o.value = txt;
            o.textContent = txt;
            motivoSel.appendChild(o);
          });
          motivoSel.dataset.loaded = "1";
          if (typeof window.__logisticaSyncDetReq === "function") window.__logisticaSyncDetReq();
        })
        .catch(() => {});
    },
    closeDetalle() {
      modalDet()?.classList.add("hidden");
    },
    closeEntrega() {
      modalEnt()?.classList.add("hidden");
    },
  };

  function wireModals() {
    const SI_ON = [
      "border-emerald-500",
      "bg-emerald-50",
      "dark:bg-emerald-950/50",
      "ring-2",
      "ring-emerald-500/30",
      "shadow-md",
    ];
    const NO_ON = [
      "border-rose-500",
      "bg-rose-50",
      "dark:bg-rose-950/40",
      "ring-2",
      "ring-rose-500/30",
      "shadow-md",
    ];
    function paintResultadoEntrega(val) {
      const si = document.getElementById("logistica_btn_entrega_si");
      const no = document.getElementById("logistica_btn_entrega_no");
      [si, no].forEach((b) => {
        if (!b) return;
        SI_ON.forEach((c) => b.classList.remove(c));
        NO_ON.forEach((c) => b.classList.remove(c));
        b.setAttribute("aria-pressed", "false");
      });
      if (val === "Si" && si) {
        SI_ON.forEach((c) => si.classList.add(c));
        si.setAttribute("aria-pressed", "true");
      } else if (val === "No" && no) {
        NO_ON.forEach((c) => no.classList.add(c));
        no.setAttribute("aria-pressed", "true");
      }
    }
    window.__logisticaPaintResultado = paintResultadoEntrega;

    document.querySelectorAll("[data-logistica-cerrar-detalle]").forEach((el) => {
      el.addEventListener("click", () => window.SynapLogisticaListaCR.closeDetalle());
    });
    document.querySelectorAll("[data-logistica-cerrar-entrega]").forEach((el) => {
      el.addEventListener("click", () => window.SynapLogisticaListaCR.closeEntrega());
    });
    const md = modalDet();
    const me = modalEnt();
    md?.addEventListener("click", (e) => {
      if (e.target === md) window.SynapLogisticaListaCR.closeDetalle();
    });
    me?.addEventListener("click", (e) => {
      if (e.target === me) window.SynapLogisticaListaCR.closeEntrega();
    });
    const est = document.getElementById("logistica_entrega_estado");
    const motivoWrap = document.getElementById("logistica_entrega_motivo_wrap");
    const motivoSel = document.getElementById("logistica_entrega_motivo");
    const detalleTa = document.getElementById("logistica_entrega_detalle");
    const detalleHint = document.getElementById("logistica_entrega_detalle_hint");
    const detalleLabel = document.getElementById("logistica_entrega_detalle_label");
    function updateDetalleHint() {
      const estadoVal = est?.value || "";
      const m = motivoSel?.value || "";
      const need = motivoRequiereDetalleMap.get(m) === true;
      if (detalleHint && detalleLabel) {
        if (estadoVal === "Si") {
          detalleLabel.textContent = "Comentario / detalle";
          detalleHint.textContent = "Opcional: nota interna sobre la entrega.";
        } else if (estadoVal === "No" && need) {
          detalleLabel.textContent = "Comentario / detalle";
          detalleHint.textContent = "Obligatorio para el motivo elegido.";
        } else {
          detalleLabel.textContent = "Comentario / detalle";
          detalleHint.textContent = "Opcional: aclaración para trazabilidad.";
        }
      }
    }
    window.__logisticaUpdateDetalleHint = updateDetalleHint;
    function syncDetalleRequired() {
      const m = motivoSel?.value || "";
      const need = motivoRequiereDetalleMap.get(m) === true;
      if (detalleTa) {
        const estadoVal = est?.value || "";
        const req = estadoVal === "No" && need;
        detalleTa.required = req;
        detalleTa.setAttribute("aria-required", req ? "true" : "false");
      }
      updateDetalleHint();
    }
    window.__logisticaSyncDetReq = syncDetalleRequired;

    document.querySelectorAll("[data-logistica-resultado]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const v = btn.getAttribute("data-logistica-resultado") || "";
        if (est) est.value = v;
        paintResultadoEntrega(v);
        if (v === "No") {
          motivoWrap?.classList.remove("hidden");
          window.SynapLogisticaListaCR.ensureMotivos();
        } else {
          motivoWrap?.classList.add("hidden");
        }
        syncDetalleRequired();
      });
    });

    motivoSel?.addEventListener("change", syncDetalleRequired);
    document.getElementById("logistica-form-entrega")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const codR = document.getElementById("logistica_entrega_cod_remito").value;
      const codP = document.getElementById("logistica_entrega_cod_pedido").value;
      const ent = document.getElementById("logistica_entrega_estado").value;
      const motivo = document.getElementById("logistica_entrega_motivo").value;
      const detalle = document.getElementById("logistica_entrega_detalle").value;
      if (!ent || (ent !== "Si" && ent !== "No")) {
        toastLocal("Seleccioná si el remito quedó entregado o no.", "error");
        return;
      }
      if (
        ent === "No" &&
        motivoRequiereDetalleMap.get(motivo) === true &&
        (!detalle || !String(detalle).trim() || String(detalle).trim() === "-")
      ) {
        toastLocal("Este motivo requiere un comentario en el detalle.", "error");
        return;
      }
      try {
        const r = await fetch(`${API_BASE}/entrega/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({
            cod_mov_remito: parseInt(codR, 10),
            cod_mov_pedido: parseInt(codP, 10),
            entregado: ent,
            motivo_no_entrega: ent === "No" ? motivo : "",
            detalle_no_entrega: detalle,
          }),
        });
        const body = await r.json().catch(() => ({}));
        if (!r.ok) {
          toastLocal(body.detail || "No se pudo guardar.", "error");
          return;
        }
        if (body.msg === "ok") {
          toastLocal(body.mensaje || "Guardado correctamente.", "success");
          window.SynapLogisticaListaCR.closeEntrega();
          refetch();
        } else {
          toastLocal(body.detail || "Error al guardar.", "error");
        }
      } catch (_) {
        toastLocal("Error de red al guardar.", "error");
      }
    });
  }

  /**
   * Cliente: mismo patrón que Estado entrega (chips removibles, caja de búsqueda, desplegable).
   * Resultados desde `GET …/clientes/autocomplete/?q=` (mín. 2 caracteres).
   */
  function initLogisticaClienteTagsFilter() {
    const select = document.getElementById("logistica_id_cliente");
    const container = document.getElementById("logistica_id_cliente_tags_container");
    const chipsContainer = container?.querySelector(".tags-chips");
    const input = document.getElementById("logistica_id_cliente_search");
    const dropdown = document.getElementById("logistica_id_cliente_dropdown");
    if (!select || !container || !chipsContainer || !input || !dropdown) return;
    if (select.dataset.logisticaClienteTagsInit === "1") return;
    select.dataset.logisticaClienteTagsInit = "1";

    const selectedValues = new Set();
    let searchTimeout = null;
    let lastApiResults = [];

    function optByValue(value) {
      return Array.from(select.options).find((o) => o.value === value);
    }

    function renderChips() {
      chipsContainer.innerHTML = "";
      selectedValues.forEach((value) => {
        const option = optByValue(value);
        const label = option ? option.textContent : value;
        const chip = document.createElement("div");
        chip.className =
          "inline-flex items-center gap-1 px-2 py-1 bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200 rounded-full text-xs font-medium";
        chip.dataset.value = value;
        const chipText = document.createElement("span");
        chipText.textContent = label;
        chip.appendChild(chipText);
        const chipRemove = document.createElement("button");
        chipRemove.type = "button";
        chipRemove.className = "ml-1 hover:text-sky-600 dark:hover:text-sky-300 focus:outline-none";
        chipRemove.innerHTML = "×";
        chipRemove.addEventListener("click", (e) => {
          e.stopPropagation();
          removeTag(value);
        });
        chip.appendChild(chipRemove);
        chipsContainer.appendChild(chip);
      });
    }

    function syncSelectDomFromSet() {
      Array.from(select.options).forEach((opt) => {
        opt.selected = selectedValues.has(opt.value);
      });
    }

    function updateSelect() {
      syncSelectDomFromSet();
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function removeTag(value) {
      selectedValues.delete(value);
      const opt = optByValue(value);
      if (opt) opt.remove();
      renderChips();
      updateSelect();
    }

    function addTag(value, label) {
      const v = String(value).trim();
      if (!v || selectedValues.has(v)) return;
      selectedValues.add(v);
      let option = optByValue(v);
      if (!option) {
        option = document.createElement("option");
        option.value = v;
        option.textContent = label || v;
        select.appendChild(option);
      }
      option.selected = true;
      renderChips();
      input.value = "";
      hideDropdown();
      updateSelect();
    }

    function loadFromDom() {
      selectedValues.clear();
      Array.from(select.selectedOptions).forEach((opt) => {
        if (opt.value) selectedValues.add(opt.value);
      });
      renderChips();
    }

    function hideDropdown() {
      dropdown.classList.add("hidden");
    }

    function renderApiDropdown(rows, query) {
      dropdown.innerHTML = "";
      lastApiResults = rows;
      if (rows.length === 0) {
        const noResults = document.createElement("div");
        noResults.className = "px-3 py-2 text-xs text-slate-500 dark:text-slate-400";
        noResults.textContent = query.length >= 2 ? "No se encontraron resultados" : "Escribe al menos 2 caracteres…";
        dropdown.appendChild(noResults);
        dropdown.classList.remove("hidden");
        return;
      }
      rows.forEach((item) => {
        const id = String(item.id ?? "").trim();
        const lab = item.text || item.label || id;
        const isSelected = selectedValues.has(id);
        const itemDiv = document.createElement("div");
        itemDiv.className = `px-3 py-2 text-xs cursor-pointer transition-colors hover:bg-slate-100 dark:hover:bg-slate-700 ${
          isSelected ? "bg-sky-50 dark:bg-sky-950" : ""
        }`;
        const itemContent = document.createElement("div");
        itemContent.className = "flex items-center justify-between";
        const itemLabel = document.createElement("span");
        itemLabel.className = isSelected
          ? "font-medium text-sky-700 dark:text-sky-300"
          : "text-slate-700 dark:text-slate-300";
        itemLabel.textContent = lab;
        itemContent.appendChild(itemLabel);
        if (isSelected) {
          const checkIcon = document.createElement("span");
          checkIcon.className = "text-sky-600 dark:text-sky-400";
          checkIcon.textContent = "✓";
          itemContent.appendChild(checkIcon);
        }
        itemDiv.appendChild(itemContent);
        itemDiv.addEventListener("mousedown", (e) => {
          e.preventDefault();
          if (selectedValues.has(id)) {
            removeTag(id);
          } else {
            addTag(id, lab);
          }
        });
        dropdown.appendChild(itemDiv);
      });
      dropdown.classList.remove("hidden");
    }

    input.addEventListener("input", (e) => {
      const query = e.target.value.trim();
      if (searchTimeout) clearTimeout(searchTimeout);
      if (query.length < 2) {
        hideDropdown();
        dropdown.innerHTML = "";
        return;
      }
      searchTimeout = setTimeout(async () => {
        try {
          const r = await fetch(`${API_BASE}/clientes/autocomplete/?q=${encodeURIComponent(query)}`, {
            headers: { "X-Requested-With": "XMLHttpRequest" },
          });
          if (!r.ok) throw new Error("clientes");
          const data = await r.json();
          renderApiDropdown(data.results || [], query);
        } catch (_) {
          hideDropdown();
        }
      }, 280);
    });

    input.addEventListener("focus", () => {
      const q = input.value.trim();
      if (q.length >= 2 && lastApiResults.length) {
        renderApiDropdown(lastApiResults, q);
      }
    });

    document.addEventListener("click", (e) => {
      if (!container.contains(e.target)) hideDropdown();
    });

    const observer = new MutationObserver(() => {
      loadFromDom();
    });
    observer.observe(select, { childList: true, subtree: true });

    loadFromDom();
  }

  function aplicarFiltrosMultiplesDesdeLocalStorage(cual) {
    try {
      const raw = readFiltersFromLocalStorage();
      if (!raw) return;
      const filters = JSON.parse(raw);
      if (cual === "estado" || cual === "ambos") {
        const est = document.getElementById("logistica_estado_entrega");
        if (est && filters.logistica_estado_entrega != null && filters.logistica_estado_entrega !== "") {
          const vals = Array.isArray(filters.logistica_estado_entrega)
            ? filters.logistica_estado_entrega.map((v) => String(v).trim()).filter(Boolean)
            : [String(filters.logistica_estado_entrega).trim()].filter(Boolean);
          Array.from(est.options).forEach((o) => {
            o.selected = vals.includes(o.value);
          });
          est.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
      if (cual === "cliente" || cual === "ambos") {
        const sel = document.getElementById("logistica_id_cliente");
        const rawId = filters.logistica_id_cliente;
        if (!sel || rawId == null || rawId === "") return;
        sel.innerHTML = "";
        const codes = Array.isArray(rawId) ? rawId : [rawId];
        const etiquetas =
          filters.logistica_cliente_etiquetas && typeof filters.logistica_cliente_etiquetas === "object"
            ? filters.logistica_cliente_etiquetas
            : {};
        codes.forEach((c) => {
          const code = String(c).trim();
          if (!code) return;
          let lab = etiquetas[code];
          if (lab == null || lab === "") {
            lab = !Array.isArray(rawId) && filters.logistica_cliente_label ? filters.logistica_cliente_label : code;
          }
          const o = document.createElement("option");
          o.value = code;
          o.textContent = lab;
          o.selected = true;
          sel.appendChild(o);
        });
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      }
    } catch (_) {
      /* vacío */
    }
  }

  function initTagsFiltrosLogistica() {
    if (typeof window.initializeTagsFilter !== "function") return;
    aplicarFiltrosMultiplesDesdeLocalStorage("estado");
    window.initializeTagsFilter("logistica_estado_entrega", "logistica_estado");
    aplicarFiltrosMultiplesDesdeLocalStorage("cliente");
    initLogisticaClienteTagsFilter();
  }

  function wireFiltrosLive() {
    document.getElementById("logistica_estado_entrega")?.addEventListener("change", refetch);
    document.getElementById("logistica_id_cliente")?.addEventListener("change", refetch);
  }

  /** Campos disponibles para “Agrupar por” en la tabla (mismo criterio visual que BO; datos ya cargados). */
  /** Solo estos campos pueden usarse en «Agrupar por» (alineado a producto). */
  const LOGISTICA_TABLA_GROUP_FIELDS = [
    ["fecha_remito", "Fecha remito"],
    ["estado_entrega", "Estado de entrega"],
    ["cliente", "Cliente"],
    ["nombre_chofer", "Chofer"],
    ["desc_ruta", "Hoja de ruta"],
  ];

  let logisticaTablaToolbarTimer = null;

  function scheduleRefreshTablaToolbar() {
    if (typeof window.refreshLogisticaListaComprobantesTabla !== "function") return;
    if (logisticaTablaToolbarTimer) clearTimeout(logisticaTablaToolbarTimer);
    logisticaTablaToolbarTimer = setTimeout(() => {
      window.refreshLogisticaListaComprobantesTabla();
    }, 400);
  }

  /**
   * Inicializa el bloque “Agrupar por + Buscar en tabla” (patrón BO) sobre la tabla del widget.
   */
  function setupTablaToolbar() {
    const toolbar = document.getElementById("logistica-lista-tabla-toolbar");
    const sel = document.getElementById("logistica-lista-group-by");
    if (!toolbar || !sel || toolbar.dataset.logisticaToolbarReady === "1") return;
    toolbar.dataset.logisticaToolbarReady = "1";
    sel.innerHTML = "";
    LOGISTICA_TABLA_GROUP_FIELDS.forEach(([value, label]) => {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      sel.appendChild(opt);
    });
    if (typeof window.initializeTagsFilter === "function") {
      window.initializeTagsFilter("logistica-lista-group-by", "group_by");
    }
    sel.addEventListener("change", scheduleRefreshTablaToolbar);
    const searchIn = document.getElementById("logistica-lista-tabla-search");
    if (searchIn) {
      searchIn.addEventListener("input", scheduleRefreshTablaToolbar);
    }
  }

  function init() {
    if (!document.getElementById("logistica_estado_entrega")) return;
    wireModals();
    wireFiltrosLive();
    setupTablaToolbar();
    initTagsFiltrosLogistica();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
