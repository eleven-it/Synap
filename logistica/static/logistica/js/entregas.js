/**
 * Módulo Logística — Entregas (API bajo /logistica/api/entregas/).
 * Ruta: botón + modal táctil. Estado de entrega: «Mi ruta» → solo no entregados; «Hoy» → todos (sin filtro).
 */
(function () {
  const root = document.getElementById("logistica-entregas-app");
  if (!root) return;

  const API_BASE = (root.dataset.apiBase || "/logistica/api/entregas").replace(/\/$/, "");

  const state = {
    modo: "hoy",
    clienteCod: "",
    clienteLabel: "",
    lastFilas: [],
    /** Catálogo de rutas devuelto por API (para el modal). */
    rutasCatalogo: [],
    /** Tras la primera respuesta del servidor, enviar siempre id_ruta en la query para alinear sesión. */
    rutaFiltroInicializado: false,
    idRutaSeleccion: "",
    idChoferSeleccion: "",
    puedeFiltrarChofer: false,
  };

  let clienteSearchTimer = null;
  /** descripcion -> requiere_detalle (catálogo MySQL ``logi_motivo_no_entrega``) */
  let motivoRequiereDetalleMap = new Map();

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

  function esc(s) {
    if (s === null || s === undefined) return "";
    const t = document.createElement("div");
    t.textContent = String(s);
    return t.innerHTML;
  }

  function toast(msg, type) {
    const container = document.createElement("div");
    container.className = `fixed top-5 right-5 z-[250] px-3 py-2 rounded-lg shadow-lg text-xs font-semibold ${
      type === "error" ? "bg-rose-600 text-white" : "bg-emerald-600 text-white"
    }`;
    container.textContent = msg;
    document.body.appendChild(container);
    setTimeout(() => container.remove(), 3500);
  }

  const modalEnt = () => document.getElementById("logistica-modal-entrega");

  window.SynapLogisticaListaCR = {
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
        credentials: "same-origin",
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

    document.querySelectorAll("[data-logistica-cerrar-entrega]").forEach((el) => {
      el.addEventListener("click", () => window.SynapLogisticaListaCR.closeEntrega());
    });
    const me = modalEnt();
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
        toast("Seleccioná si el remito quedó entregado o no.", "error");
        return;
      }
      if (
        ent === "No" &&
        motivoRequiereDetalleMap.get(motivo) === true &&
        (!detalle || !String(detalle).trim() || String(detalle).trim() === "-")
      ) {
        toast("Este motivo requiere un comentario en el detalle.", "error");
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
          credentials: "same-origin",
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
          toast(body.detail || "No se pudo guardar.", "error");
          return;
        }
        if (body.msg === "ok") {
          toast(body.mensaje || "Guardado correctamente.", "success");
          window.SynapLogisticaListaCR.closeEntrega();
          cargarListado();
        } else {
          toast(body.detail || "Error al guardar.", "error");
        }
      } catch (_) {
        toast("Error de red al guardar.", "error");
      }
    });
  }

  function setTabStyles() {
    document.querySelectorAll(".logistica-tab").forEach((btn) => {
      const active = btn.dataset.modo === state.modo;
      btn.setAttribute("aria-selected", active ? "true" : "false");
      btn.className = active
        ? "logistica-tab px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 border border-amber-300/80 dark:border-amber-700 bg-white dark:bg-slate-900 text-amber-900 dark:text-amber-100 shadow-sm"
        : "logistica-tab px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200 border border-transparent text-slate-600 dark:text-slate-400 hover:bg-white/70 dark:hover:bg-slate-700/50";
    });
  }

  /** Nombre para tarjeta (sin código) y dirección en líneas separadas. */
  function clienteNombreYDir(row) {
    const nom = (row.nombre_cliente != null && String(row.nombre_cliente).trim() !== ""
      ? String(row.nombre_cliente).trim()
      : "");
    let nombre = nom;
    if (!nombre) {
      const c = String(row.cliente || "").trim();
      const m = c.match(/^(.+?)\s*\([^)]*\)\s*$/);
      nombre = m ? m[1].trim() : c || "—";
    }
    const direccion =
      row.direccion_entrega != null && String(row.direccion_entrega).trim() !== ""
        ? String(row.direccion_entrega).trim()
        : "";
    return { nombre, direccion };
  }

  function renderFilaCard(row) {
    const codR = row.cod_mov_remito;
    const codP = row.cod_mov_pedido;
    const est = row.estado_entrega || "—";
    let badge =
      "inline-flex items-center justify-center rounded-2xl px-4 py-2 min-w-[8.5rem] text-center text-base sm:text-lg font-extrabold tracking-tight ring-2 shadow-sm ";
    if (est === "Entregado") {
      badge += "bg-emerald-100 text-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-200 ring-emerald-400/50 dark:ring-emerald-500/40";
    } else if (est === "No entregado") {
      badge += "bg-rose-100 text-rose-900 dark:bg-rose-950/50 dark:text-rose-100 ring-rose-400/50 dark:ring-rose-500/40";
    } else {
      badge += "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 ring-slate-400/40";
    }
    const dataAttrs =
      codR != null ? `data-cod-remito="${String(codR)}" data-cod-pedido="${String(codP ?? "")}"` : "";
    const { nombre: nomCli, direccion: dirCli } = clienteNombreYDir(row);
    const bloqueDir = dirCli
      ? `<p class="text-sm font-normal text-slate-600 dark:text-slate-400 mt-0.5 break-words leading-snug">${esc(
          dirCli,
        )}</p>`
      : "";
    return `
      <article class="group relative rounded-3xl border border-slate-200/90 dark:border-slate-700/70 bg-white dark:bg-slate-900/50 p-4 sm:p-5 shadow-md shadow-slate-900/5 dark:shadow-black/20 ring-1 ring-slate-900/5 dark:ring-white/5 transition-all duration-300 hover:shadow-lg hover:border-sky-200/80 dark:hover:border-sky-800/60" ${dataAttrs}>
        <div class="absolute inset-x-6 -top-0.5 h-[3px] rounded-full bg-gradient-to-r from-sky-400 via-indigo-500 to-purple-500 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none" aria-hidden="true"></div>
        <div class="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div class="min-w-0">
            <p class="text-[11px] uppercase tracking-wider text-slate-400 dark:text-slate-500 font-semibold">${esc(row.fecha_remito || "—")}</p>
            <p class="text-sm font-semibold text-slate-900 dark:text-slate-50 mt-0.5">Remito <span class="text-sky-700 dark:text-sky-300">${esc(String(row.nro_remito ?? "—"))}</span></p>
            <p class="text-sm font-medium text-slate-800 dark:text-slate-100 mt-2 break-words leading-snug">${esc(
              nomCli,
            )}</p>${bloqueDir}
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
              <span class="material-icons text-[15px] text-amber-600 dark:text-amber-400" aria-hidden="true">format_list_numbered</span>
              ${row.orden_ruta != null && row.orden_ruta !== "" ? esc(String(row.orden_ruta)) : "—"}
              <span class="text-slate-300 dark:text-slate-600">·</span>
              <span class="material-icons text-[15px] text-sky-600 dark:text-sky-400" aria-hidden="true">schedule</span>
              ${esc(String(row.fecha_salida_ruta_fmt || "—"))}
              <span class="text-slate-300 dark:text-slate-600">·</span>
              <span class="material-icons text-[15px] text-teal-600 dark:text-teal-400" aria-hidden="true">timer</span>
              ${esc(String(row.ventana_horaria_ruta || "—"))}
            </p>
          </div>
          <div class="flex flex-col items-stretch sm:items-end gap-3 shrink-0 w-full sm:w-auto">
            <span class="${badge}">${esc(est)}</span>
            <div class="flex flex-wrap gap-2 w-full sm:justify-end">
              <button type="button" class="flex-1 sm:flex-none min-h-[44px] px-4 py-2 rounded-xl text-xs font-semibold text-white bg-gradient-to-r from-sky-500 via-indigo-500 to-purple-600 shadow-md shadow-indigo-500/20 hover:brightness-105 active:scale-[0.98] transition-all"
                data-action="entrega" data-cod-r="${String(codR ?? "")}" data-cod-p="${String(
      codP ?? "",
    )}">Registrar entrega</button>
            </div>
          </div>
        </div>
      </article>`;
  }

  function renderLista(filas) {
    const wrap = document.getElementById("logistica-entregas-lista");
    const empty = document.getElementById("logistica-entregas-empty");
    if (!wrap || !empty) return;
    wrap.innerHTML = "";
    if (!filas.length) {
      empty.classList.remove("hidden");
      return;
    }
    empty.classList.add("hidden");
    wrap.innerHTML = filas.map(renderFilaCard).join("");
    wrap.querySelectorAll('button[data-action="entrega"]').forEach((btn) => {
      btn.addEventListener("click", () => {
        window.SynapLogisticaListaCR.openEntrega({
          cod_mov_remito: btn.getAttribute("data-cod-r"),
          cod_mov_pedido: btn.getAttribute("data-cod-p"),
        });
      });
    });
  }

  function mostrarNotas(notas) {
    const el = document.getElementById("logistica-entregas-notas");
    if (!el) return;
    if (notas && notas.length) {
      el.textContent = notas.join(" ");
      el.classList.remove("hidden");
    } else {
      el.textContent = "";
      el.classList.add("hidden");
    }
  }

  function aplicarParametrosListado(p) {
    p.set("modo", state.modo);
    if (state.modo === "mi_ruta") {
      p.set("estado", "No");
    }
    if (state.clienteCod) p.set("cliente", state.clienteCod);
    if (state.rutaFiltroInicializado) {
      p.set("id_ruta", state.idRutaSeleccion);
    }
    if (state.puedeFiltrarChofer && state.idChoferSeleccion) {
      p.set("id_chofer", state.idChoferSeleccion);
    }
  }

  async function cargarListado() {
    const loading = document.getElementById("logistica-entregas-loading");
    const empty = document.getElementById("logistica-entregas-empty");
    if (loading) loading.classList.remove("hidden");
    if (empty) empty.classList.add("hidden");

    const p = new URLSearchParams();
    aplicarParametrosListado(p);

    try {
      const r = await fetch(`${API_BASE}/lista/?${p.toString()}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        toast(body.detail || "No se pudo cargar el listado.", "error");
        state.lastFilas = [];
        renderLista([]);
        mostrarNotas([]);
        return;
      }
      state.lastFilas = body.filas || [];
      mostrarNotas(body.notas || []);
      if (typeof body.puede_filtrar_chofer === "boolean") {
        state.puedeFiltrarChofer = body.puede_filtrar_chofer;
        const wrapCh = document.getElementById("logistica-entregas-wrap-chofer");
        if (wrapCh) {
          wrapCh.classList.toggle("hidden", !state.puedeFiltrarChofer);
        }
      }
      const selR = document.getElementById("logistica-entregas-sel-ruta");
      if (selR && body.id_ruta_sesion != null && body.id_ruta_sesion !== "") {
        const v = String(body.id_ruta_sesion);
        selR.value = v;
        state.idRutaSeleccion = v;
      }
      if (!state.rutaFiltroInicializado) {
        state.rutaFiltroInicializado = true;
        if (selR) state.idRutaSeleccion = selR.value || "";
      }
      actualizarTextoBotonRuta();
      renderLista(state.lastFilas);
      deepLinkSiAplica();
    } catch (_) {
      toast("Error de red al cargar el listado.", "error");
      state.lastFilas = [];
      renderLista([]);
    } finally {
      if (loading) loading.classList.add("hidden");
    }
  }

  function deepLinkSiAplica() {
    const params = new URLSearchParams(window.location.search);
    const preR = params.get("cod_mov_remito");
    const preP = params.get("cod_mov_pedido");
    if (!preR || !state.lastFilas.length) return;
    const escSel = window.CSS && window.CSS.escape ? window.CSS.escape(preR) : preR.replace(/"/g, '\\"');
    const card = document.querySelector(`[data-cod-remito="${escSel}"]`);
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.add("ring-2", "ring-amber-400", "dark:ring-amber-500");
      setTimeout(() => card.classList.remove("ring-2", "ring-amber-400", "dark:ring-amber-500"), 2500);
    }
    if (params.get("abrir") === "entrega") {
      window.SynapLogisticaListaCR.openEntrega({
        cod_mov_remito: preR,
        cod_mov_pedido: preP || "",
      });
    }
  }

  function wireTabs() {
    document.querySelectorAll(".logistica-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.modo = btn.dataset.modo || "hoy";
        setTabStyles();
        cargarListado();
      });
    });
  }

  function actualizarTextoBotonRuta() {
    const span = document.getElementById("logistica-entregas-btn-ruta-texto");
    const sel = document.getElementById("logistica-entregas-sel-ruta");
    if (!span || !sel) return;
    const v = sel.value || "";
    if (!v) {
      span.textContent = "Todas las rutas";
      return;
    }
    const opt = sel.options[sel.selectedIndex];
    span.textContent = opt && opt.textContent ? opt.textContent.trim() : "Ruta";
  }

  function cerrarModalRuta() {
    const m = document.getElementById("logistica-modal-ruta");
    const btn = document.getElementById("logistica-entregas-btn-ruta");
    if (m) {
      m.classList.add("hidden");
      m.setAttribute("aria-hidden", "true");
    }
    btn?.setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  function abrirModalRuta() {
    const wrap = document.getElementById("logistica-modal-ruta-lista");
    const m = document.getElementById("logistica-modal-ruta");
    if (!wrap || !m) return;
    wrap.innerHTML = "";
    function addBtn(val, titulo, subtitulo) {
      const b = document.createElement("button");
      b.type = "button";
      b.className =
        "w-full min-h-[52px] text-left rounded-2xl border-2 border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-900/80 px-4 py-3 text-base font-semibold text-slate-900 dark:text-slate-100 shadow-sm hover:bg-slate-50 dark:hover:bg-slate-800 active:scale-[0.99] transition-transform";
      b.dataset.val = val;
      const sub = subtitulo
        ? `<span class="block text-xs font-normal text-slate-500 dark:text-slate-400 mt-1">${esc(subtitulo)}</span>`
        : "";
      b.innerHTML = `<span class="block leading-snug">${esc(titulo)}</span>${sub}`;
      b.addEventListener("click", () => {
        seleccionarRutaDesdeModal(val);
      });
      wrap.appendChild(b);
    }
    addBtn("", "Todas las rutas", "Ver comprobantes de todas las hojas disponibles");
    (state.rutasCatalogo || []).forEach((row) => {
      const id = row.id != null ? String(row.id) : "";
      const text = String(row.text != null ? row.text : id);
      addBtn(id, text, "");
    });
    m.classList.remove("hidden");
    m.setAttribute("aria-hidden", "false");
    document.getElementById("logistica-entregas-btn-ruta")?.setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }

  function seleccionarRutaDesdeModal(val) {
    const sel = document.getElementById("logistica-entregas-sel-ruta");
    if (sel) sel.value = val;
    state.idRutaSeleccion = val || "";
    state.rutaFiltroInicializado = true;
    actualizarTextoBotonRuta();
    cerrarModalRuta();
    cargarListado();
  }

  function wireModalRuta() {
    document.getElementById("logistica-entregas-btn-ruta")?.addEventListener("click", () => abrirModalRuta());
    document.getElementById("logistica-modal-ruta-cerrar")?.addEventListener("click", () => cerrarModalRuta());
    document.getElementById("logistica-modal-ruta-backdrop")?.addEventListener("click", () => cerrarModalRuta());
    document.addEventListener("keydown", (e) => {
      if (e.key !== "Escape") return;
      const modal = document.getElementById("logistica-modal-ruta");
      if (modal && !modal.classList.contains("hidden")) cerrarModalRuta();
    });
  }

  async function cargarCatalogos() {
    try {
      const selCPre = document.getElementById("logistica-entregas-sel-chofer");
      if (state.puedeFiltrarChofer && selCPre && selCPre.value) {
        state.idChoferSeleccion = selCPre.value;
      }
      const catParams = new URLSearchParams();
      if (state.puedeFiltrarChofer && state.idChoferSeleccion) {
        catParams.set("id_chofer", state.idChoferSeleccion);
      }
      const catQs = catParams.toString();
      const catUrl = catQs ? `${API_BASE}/catalogos/?${catQs}` : `${API_BASE}/catalogos/`;
      const r = await fetch(catUrl, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        toast(body.detail || "No se pudieron cargar las rutas.", "error");
        state.rutasCatalogo = [];
        return;
      }
      state.rutasCatalogo = body.rutas || [];
      const selR = document.getElementById("logistica-entregas-sel-ruta");
      const selC = document.getElementById("logistica-entregas-sel-chofer");
      if (selR) {
        selR.innerHTML = "";
        const o0 = document.createElement("option");
        o0.value = "";
        o0.textContent = "Todas las rutas";
        selR.appendChild(o0);
        (body.rutas || []).forEach((row) => {
          const o = document.createElement("option");
          o.value = row.id != null ? String(row.id) : "";
          o.textContent = String(row.text != null ? row.text : row.id ?? "");
          selR.appendChild(o);
        });
        if (body.id_ruta_sesion != null && body.id_ruta_sesion !== "") {
          const v = String(body.id_ruta_sesion);
          selR.value = v;
          state.idRutaSeleccion = v;
        } else {
          state.idRutaSeleccion = "";
        }
      }
      if (selC) {
        selC.innerHTML = "";
        const c0 = document.createElement("option");
        c0.value = "";
        c0.textContent = "Todos los choferes";
        selC.appendChild(c0);
        (body.choferes || []).forEach((row) => {
          const o = document.createElement("option");
          o.value = row.id != null ? String(row.id) : "";
          o.textContent = String(row.text != null ? row.text : row.id ?? "");
          selC.appendChild(o);
        });
        if (state.idChoferSeleccion) {
          const okOpt = [...selC.options].some((opt) => opt.value === state.idChoferSeleccion);
          if (okOpt) selC.value = state.idChoferSeleccion;
        }
      }
      if (typeof body.puede_filtrar_chofer === "boolean") {
        state.puedeFiltrarChofer = body.puede_filtrar_chofer;
        const wrapCh = document.getElementById("logistica-entregas-wrap-chofer");
        if (wrapCh) wrapCh.classList.toggle("hidden", !state.puedeFiltrarChofer);
      }
    } catch (_) {
      toast("Error de red al cargar rutas.", "error");
      state.rutasCatalogo = [];
    } finally {
      const selR = document.getElementById("logistica-entregas-sel-ruta");
      if (selR && selR.options.length === 0) {
        selR.innerHTML = "";
        const o0 = document.createElement("option");
        o0.value = "";
        o0.textContent = "Todas las rutas";
        selR.appendChild(o0);
      }
      actualizarTextoBotonRuta();
    }
  }

  function wireFiltrosRutaChofer() {
    const selC = document.getElementById("logistica-entregas-sel-chofer");
    selC?.addEventListener("change", async () => {
      state.idChoferSeleccion = selC.value || "";
      await cargarCatalogos();
      await cargarListado();
    });
  }

  function wireFiltros() {
    const qIn = document.getElementById("logistica-entregas-cliente-q");
    const dd = document.getElementById("logistica-entregas-cliente-dd");
    const chip = document.getElementById("logistica-entregas-cliente-chip");
    const hid = document.getElementById("logistica-entregas-cliente-cod");

    function hideDd() {
      dd?.classList.add("hidden");
    }

    function setCliente(cod, label) {
      state.clienteCod = cod || "";
      state.clienteLabel = label || "";
      if (hid) hid.value = state.clienteCod;
      if (chip && cod) {
        chip.innerHTML = `<span>${esc(label || cod)}</span><button type="button" class="ml-1 hover:opacity-80" aria-label="Quitar cliente">&times;</button>`;
        chip.classList.remove("hidden");
        chip.querySelector("button")?.addEventListener("click", () => {
          state.clienteCod = "";
          state.clienteLabel = "";
          if (hid) hid.value = "";
          chip.classList.add("hidden");
          chip.innerHTML = "";
          if (qIn) qIn.value = "";
          cargarListado();
        });
      } else if (chip) {
        chip.classList.add("hidden");
        chip.innerHTML = "";
      }
      cargarListado();
    }

    qIn?.addEventListener("input", () => {
      const q = qIn.value.trim();
      if (clienteSearchTimer) clearTimeout(clienteSearchTimer);
      if (q.length < 2) {
        hideDd();
        if (dd) dd.innerHTML = "";
        return;
      }
      clienteSearchTimer = setTimeout(async () => {
        try {
          const r = await fetch(`${API_BASE}/clientes/autocomplete/?q=${encodeURIComponent(q)}`, {
            credentials: "same-origin",
          });
          const data = await r.json();
          const rows = data.results || [];
          if (!dd) return;
          dd.innerHTML = "";
          if (!rows.length) {
            const d = document.createElement("div");
            d.className = "px-3 py-2 text-xs text-slate-500";
            d.textContent = "Sin resultados";
            dd.appendChild(d);
          } else {
            rows.forEach((item) => {
              const id = String(item.id ?? "").trim();
              const lab = item.text || id;
              const row = document.createElement("button");
              row.type = "button";
              row.className =
                "w-full text-left px-3 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-700";
              row.textContent = lab;
              row.addEventListener("click", () => {
                qIn.value = "";
                hideDd();
                setCliente(id, lab);
              });
              dd.appendChild(row);
            });
          }
          dd.classList.remove("hidden");
        } catch (_) {
          hideDd();
        }
      }, 280);
    });

    document.addEventListener("click", (e) => {
      if (!qIn || !dd) return;
      if (!qIn.closest("#logistica-entregas-app")?.contains(e.target)) hideDd();
    });
  }

  async function init() {
    setTabStyles();
    wireTabs();
    wireModalRuta();
    wireFiltrosRutaChofer();
    wireFiltros();
    wireModals();
    await cargarCatalogos();
    await cargarListado();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
