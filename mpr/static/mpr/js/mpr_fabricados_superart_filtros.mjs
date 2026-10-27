/**
 * Filtros informe Fabricados por superartículo: panel colapsable, rango de fechas,
 * marcas y superartículos (tags + API), sincronización con la URL.
 */
import { initializeTagsFilter } from "/static/reports/js/tags_filter.mjs?v=20261027b";

function buildFabricadosSuperartFiltros(config) {
  const cfg = config || {};
  return {
    panelAbierto: true,
    desde: cfg.desdeInicial || "",
    hasta: cfg.hastaInicial || "",
    presentacion: cfg.presentacion || "docenas",
    _marcasInit: false,
    _superartInit: false,
    _listo: false,

    init() {
      this.$nextTick(() => {
        this.initMarcasTags();
        this.initSuperartTags();
        this._listo = true;
      });
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
      sel.addEventListener("change", () => this.aplicarFiltros());
    },

    initSuperartTags() {
      if (this._superartInit) return;
      const sel = document.getElementById("superarts_incluidos");
      if (!sel) return;
      this._superartInit = true;
      const superartUrl = cfg.superartBuscarUrl || "";
      initializeTagsFilter("superarts_incluidos", "superart", null, {
        remoteSearch: {
          minChars: 1,
          fetchFn: async (q) => {
            const url = `${superartUrl}?q=${encodeURIComponent(q)}&limit=25`;
            const resp = await fetch(url, {
              headers: { Accept: "application/json" },
              credentials: "same-origin",
            });
            if (!resp.ok) return [];
            const data = await resp.json();
            return (data.superarts || []).map((s) => ({
              value: String(s.codigo || s.descripcion || ""),
              label: s.descripcion || s.codigo || "",
            }));
          },
        },
      });
      sel.addEventListener("change", () => this.aplicarFiltros());
    },

    marcasSeleccionadas() {
      const sel = document.getElementById("marcas_incluidos");
      if (!sel) return [];
      return Array.from(sel.selectedOptions || [])
        .map((o) => o.value)
        .filter(Boolean);
    },

    superartsSeleccionados() {
      const sel = document.getElementById("superarts_incluidos");
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
      this.marcasSeleccionadas().forEach((id) => {
        params.append("marcas_incluidos", id);
      });
      this.superartsSeleccionados().forEach((code) => {
        params.append("q_superart", code);
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
