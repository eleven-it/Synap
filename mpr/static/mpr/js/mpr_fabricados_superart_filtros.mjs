/**
 * Filtros informe Fabricados por superartículo: panel colapsable, rango de fechas,
 * marcas (tags + API), superartículo predictivo y sincronización con la URL.
 */
import { initializeTagsFilter } from "/static/reports/js/tags_filter.mjs?v=20261027a";

function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

function buildFabricadosSuperartFiltros(config) {
  const cfg = config || {};
  return {
    panelAbierto: true,
    desde: cfg.desdeInicial || "",
    hasta: cfg.hastaInicial || "",
    presentacion: cfg.presentacion || "docenas",
    qSuperart: cfg.qSuperartInicial || "",
    sugerenciasSuperart: [],
    sugerenciasAbiertas: false,
    sugerenciaActiva: 0,
    buscandoSuperart: false,
    _marcasInit: false,
    _listo: false,

    init() {
      this.$nextTick(() => {
        this.initMarcasTags();
        const sel = document.getElementById("marcas_incluidos");
        if (sel) {
          sel.addEventListener("change", () => this.aplicarFiltros());
        }
        this._listo = true;
      });
      this.$watch(
        "qSuperart",
        debounce(() => {
          this.buscarSuperart();
          this.aplicarFiltros();
        }, 400),
      );
    },

    initMarcasTags() {
      if (this._marcasInit) return;
      const sel = document.getElementById("marcas_incluidos");
      if (!sel) return;
      this._marcasInit = true;
      const marcasUrl = cfg.marcasBuscarUrl || "";
      initializeTagsFilter("marcas_incluidos", "marcas", null, {
        remoteSearch: {
          minChars: 1,
          fetchFn: async (q) => {
            const url = `${marcasUrl}?q=${encodeURIComponent(q)}&limit=25`;
            const resp = await fetch(url, {
              headers: { Accept: "application/json" },
              credentials: "same-origin",
            });
            if (!resp.ok) return [];
            const data = await resp.json();
            return (data.marcas || []).map((m) => ({
              value: String(m.value),
              label: m.label,
            }));
          },
        },
      });
    },

    async buscarSuperart() {
      const q = (this.qSuperart || "").trim();
      if (q.length < 1) {
        this.sugerenciasSuperart = [];
        this.sugerenciasAbiertas = false;
        return;
      }
      this.buscandoSuperart = true;
      try {
        const url = `${cfg.superartBuscarUrl}?q=${encodeURIComponent(q)}&limit=20`;
        const resp = await fetch(url, {
          headers: { Accept: "application/json" },
          credentials: "same-origin",
        });
        if (!resp.ok) {
          this.sugerenciasSuperart = [];
          return;
        }
        const data = await resp.json();
        this.sugerenciasSuperart = data.superarts || [];
        this.sugerenciasAbiertas = this.sugerenciasSuperart.length > 0;
        this.sugerenciaActiva = 0;
      } catch {
        this.sugerenciasSuperart = [];
      } finally {
        this.buscandoSuperart = false;
      }
    },

    seleccionarSuperart(item) {
      this.qSuperart = item.codigo || item.descripcion || "";
      this.sugerenciasAbiertas = false;
      this.aplicarFiltros();
    },

    focoSugerencia(delta) {
      const n = this.sugerenciasSuperart.length;
      if (!n) return;
      this.sugerenciaActiva = (this.sugerenciaActiva + delta + n) % n;
    },

    aplicarSugerenciaActiva() {
      const item = this.sugerenciasSuperart[this.sugerenciaActiva];
      if (item) this.seleccionarSuperart(item);
    },

    marcasSeleccionadas() {
      const sel = document.getElementById("marcas_incluidos");
      if (!sel) return [];
      return Array.from(sel.selectedOptions || [])
        .map((o) => o.value)
        .filter(Boolean);
    },

    buildQueryParams() {
      const params = new URLSearchParams();
      params.set("grupo", "produccion");
      params.set("reporte", "fabricados_superart");
      if (this.desde) params.set("desde", this.desde);
      if (this.hasta) params.set("hasta", this.hasta);
      if (this.presentacion) params.set("presentacion", this.presentacion);
      const q = (this.qSuperart || "").trim();
      if (q) params.set("q_superart", q);
      this.marcasSeleccionadas().forEach((id) => {
        params.append("marcas_incluidos", id);
      });
      return params;
    },

    exportQueryString() {
      return this.buildQueryParams().toString();
    },

    aplicarFiltros() {
      if (!this._listo) return;
      const params = this.buildQueryParams();
      const next = `?${params.toString()}`;
      if (window.location.search === next) return;
      window.location.search = next;
    },
  };
}

document.addEventListener("alpine:init", () => {
  window.Alpine.data(
    "fabricadosSuperartFiltros",
    (config) => buildFabricadosSuperartFiltros(config),
  );
});
