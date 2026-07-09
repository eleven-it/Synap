/**
 * Tabla editable — precios terminados: recálculo neto/final, dirty state, guardado y masivo.
 */

function q2(n) {
  return Math.round(n * 100) / 100;
}

function calcFinal(neto, alic, imp) {
  return q2(neto + (neto * alic) / 100 + (neto * imp) / 100);
}

function calcNeto(final, alic, imp) {
  const factor = 1 + (alic + imp) / 100;
  return factor > 0 ? q2(final / factor) : 0;
}

function getCsrf() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

function preciosTerminadosTabla(config) {
  const historial = typeof historialPreciosMixin === "function" ? historialPreciosMixin(config) : {};
  return {
    ...historial,
    busqueda: "",
    dirtyCount: 0,
    guardarModalOpen: false,
    masivoModalOpen: false,
    masivoPreview: null,
    masivoLoading: false,
    guardarLoading: false,
    masivo: {
      ambito: "precio_neto",
      tipo_operacion: "porcentaje_mas",
      valor: 10,
      listas: [(config.listasIncluidas || [1])[0]],
    },
    filtrosSnapshot: config.filtrosSnapshot || {},
    filtrosExpandidos: true,
    listasIncluidas: config.listasIncluidas || [1],
    listasNombres: config.listasNombres || {},

    init() {
      this.recountDirty();
      const key = "synap-precios-terminados-filtros-expandidos";
      const saved = localStorage.getItem(key);
      if (saved !== null) {
        this.filtrosExpandidos = saved === "1";
      } else {
        this.filtrosExpandidos = !this.tieneFiltrosSecundarios();
      }
    },

    tieneFiltrosSecundarios() {
      const f = this.filtrosSnapshot || {};
      return Boolean(
        (f.marcas_incluidos && f.marcas_incluidos.length) ||
          (f.codigos_incluidos && f.codigos_incluidos.length) ||
          (f.proveedores_incluidos && f.proveedores_incluidos.length) ||
          (f.rubros_incluidos && f.rubros_incluidos.length) ||
          (f.subrubros_incluidos && f.subrubros_incluidos.length),
      );
    },

    toggleFiltros() {
      this.filtrosExpandidos = !this.filtrosExpandidos;
      localStorage.setItem(
        "synap-precios-terminados-filtros-expandidos",
        this.filtrosExpandidos ? "1" : "0",
      );
      if (!this.filtrosExpandidos) {
        document.querySelectorAll(".tags-dropdown:not(.hidden)").forEach((el) => {
          el.classList.add("hidden");
        });
      }
    },

    matchesBusqueda(descripcion) {
      if (!this.busqueda.trim()) return true;
      return (descripcion || "").includes(this.busqueda.toLowerCase());
    },

    filaVisible(el) {
      return this.matchesBusqueda(el && el.dataset ? el.dataset.descripcion : "");
    },

    collectIdsVisibles() {
      const ids = [];
      document
        .querySelectorAll("#tabla-precios-terminados tr[data-id-art]")
        .forEach((tr) => {
          if (!this.matchesBusqueda(tr.dataset.descripcion || "")) return;
          const id = parseInt(tr.dataset.idArt, 10);
          if (id) ids.push(id);
        });
      return ids;
    },

    countVisiblesEnTabla() {
      return this.collectIdsVisibles().length;
    },

    nombreLista(n) {
      return this.listasNombres[n] || `Lista ${n}`;
    },

    isListaMasivoSelected(n) {
      return (this.masivo.listas || []).includes(n);
    },

    toggleListaMasivo(n) {
      const cur = [...(this.masivo.listas || [])];
      const idx = cur.indexOf(n);
      if (idx >= 0) {
        if (cur.length > 1) cur.splice(idx, 1);
      } else {
        cur.push(n);
        cur.sort((a, b) => a - b);
      }
      this.masivo.listas = cur;
      this.masivoPreview = null;
    },

    masivoPayload() {
      return {
        filtros: this.filtrosSnapshot,
        operacion: this.masivo,
        ids_articulos: this.collectIdsVisibles(),
      };
    },

    abrirMasivo() {
      this.masivoModalOpen = true;
      this.masivoPreview = null;
      this.previewMasivo();
    },

    onPrecioInput(ev, idArt, lista, campo) {
      const tr = ev.target.closest("tr");
      if (!tr) return;
      const alic = parseFloat(tr.dataset.alicuota || "21");
      const imp = parseFloat(tr.dataset.impuestoInterno || "0");
      const raw = parseFloat(ev.target.value);
      if (Number.isNaN(raw)) return;

      const netoInp = tr.querySelector(`input[data-campo="neto"][data-lista="${lista}"]`);
      const finalInp = tr.querySelector(`input[data-campo="final"][data-lista="${lista}"]`);
      if (!netoInp || !finalInp) return;

      if (campo === "neto") {
        finalInp.value = calcFinal(raw, alic, imp).toFixed(2);
        this.markDirty(netoInp);
        this.markDirty(finalInp);
      } else {
        netoInp.value = calcNeto(raw, alic, imp).toFixed(2);
        this.markDirty(finalInp);
        this.markDirty(netoInp);
      }
      this.recountDirty();
    },

    onReservaInput(ev) {
      this.markDirty(ev.target);
      this.recountDirty();
    },

    markDirty(input) {
      const orig = input.dataset.original;
      const cur = input.value;
      const changed = String(orig) !== String(cur);
      input.classList.toggle("ring-2", changed);
      input.classList.toggle("ring-amber-400", changed);
      input.classList.toggle("bg-amber-50", changed);
      input.classList.toggle("dark:bg-amber-950/30", changed);
      input.dataset.dirty = changed ? "1" : "0";
    },

    recountDirty() {
      const inputs = document.querySelectorAll(
        "#tabla-precios-terminados input[data-original][data-dirty='1']",
      );
      const arts = new Set();
      inputs.forEach((inp) => {
        const tr = inp.closest("tr");
        if (tr) arts.add(tr.dataset.idArt);
      });
      this.dirtyCount = arts.size;
    },

    deshacerPagina() {
      document
        .querySelectorAll("#tabla-precios-terminados input[data-original]")
        .forEach((inp) => {
          inp.value = inp.dataset.original;
          inp.classList.remove("ring-2", "ring-amber-400", "bg-amber-50", "dark:bg-amber-950/30");
          inp.dataset.dirty = "0";
        });
      this.recountDirty();
    },

    collectCambios() {
      const porArt = new Map();
      document
        .querySelectorAll("#tabla-precios-terminados tr[data-id-art]")
        .forEach((tr) => {
          const idArt = parseInt(tr.dataset.idArt, 10);
          if (!idArt) return;
          let entry = null;
          tr.querySelectorAll("input[data-original]").forEach((inp) => {
            if (inp.dataset.dirty !== "1") return;
            if (!entry) entry = { id_articulo: idArt, precios: {} };
            const lista = inp.dataset.lista;
            const campo = inp.dataset.campo;
            if (lista && campo) {
              const li = parseInt(lista, 10);
              if (!entry.precios[li]) entry.precios[li] = {};
              entry.precios[li][campo] = parseFloat(inp.value) || 0;
            } else if (inp.name === "stock_reserva") {
              entry.stock_reserva = parseFloat(inp.value) || 0;
            }
          });
          if (entry) porArt.set(idArt, entry);
        });
      return Array.from(porArt.values());
    },

    async guardar() {
      const items = this.collectCambios();
      if (!items.length) return;
      this.guardarLoading = true;
      try {
        const r = await fetch(config.urls.guardar, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
            "X-Requested-With": "XMLHttpRequest",
          },
          body: JSON.stringify({ items }),
        });
        const data = await r.json();
        if (data.ok) {
          window.location.reload();
        } else {
          alert(data.error || "No se pudo guardar.");
        }
      } catch (e) {
        alert("Error de red al guardar.");
      } finally {
        this.guardarLoading = false;
        this.guardarModalOpen = false;
      }
    },

    async previewMasivo() {
      const ids = this.collectIdsVisibles();
      if (!ids.length) {
        this.masivoPreview = { total_articulos: 0 };
        return;
      }
      if (
        ["precio_neto", "precio_final"].includes(this.masivo.ambito) &&
        !(this.masivo.listas || []).length
      ) {
        alert("Seleccione al menos una lista de precios.");
        return;
      }
      this.masivoLoading = true;
      this.masivoPreview = null;
      try {
        const r = await fetch(config.urls.masivoPreview, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify(this.masivoPayload()),
        });
        const data = await r.json();
        if (data.ok) this.masivoPreview = data;
        else alert(data.error === "listas_requeridas" ? "Seleccione al menos una lista de precios." : "No se pudo calcular la vista previa.");
      } finally {
        this.masivoLoading = false;
      }
    },

    async aplicarMasivo() {
      const ids = this.collectIdsVisibles();
      if (!ids.length) {
        alert("No hay artículos visibles en la tabla para actualizar.");
        return;
      }
      if (!this.masivoPreview) await this.previewMasivo();
      if (!this.masivoPreview || !this.masivoPreview.total_articulos) return;
      const n = this.masivoPreview.total_articulos || 0;
      if (
        n > 500 &&
        !window.confirm(`Se actualizarán ${n} artículos. ¿Continuar?`)
      ) {
        return;
      }
      this.masivoLoading = true;
      try {
        const r = await fetch(config.urls.masivoAplicar, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify(this.masivoPayload()),
        });
        const data = await r.json();
        if (data.ok) {
          window.location.reload();
        } else {
          const msg =
            data.error === "listas_requeridas"
              ? "Seleccione al menos una lista de precios."
              : data.error === "sin_articulos_visibles"
                ? "No hay artículos visibles en la tabla."
                : "Error en cambio masivo.";
          alert(msg);
        }
      } finally {
        this.masivoLoading = false;
        this.masivoModalOpen = false;
      }
    },
  };
}

window.preciosTerminadosTabla = preciosTerminadosTabla;
