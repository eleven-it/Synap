/**
 * Modal de historial de precios — drill-down desde tabla precios terminados.
 */

function historialPreciosMixin(config) {
  const apiTpl = config.urls && config.urls.historialArticulo;
  const listas = config.listasIncluidas || [1];

  return {
    historialOpen: false,
    historialLoading: false,
    historialError: "",
    historialArticulo: null,
    historialLista: listas[0] || 1,
    historialFilas: [],
    historialResumen: null,
    listasIncluidas: listas,

    async abrirHistorial(idArticulo, codigo, nombre) {
      this.historialArticulo = { id: idArticulo, codigo, nombre };
      this.historialLista = listas[0] || 1;
      this.historialOpen = true;
      this.historialError = "";
      await this.cargarHistorial();
    },

    async cargarHistorial() {
      if (!apiTpl || !this.historialArticulo) return;
      const url = apiTpl.replace(/\/0\/?$/, `/${this.historialArticulo.id}/`)
        + `?lista=${encodeURIComponent(this.historialLista)}`;
      this.historialLoading = true;
      this.historialError = "";
      try {
        const res = await fetch(url, { credentials: "same-origin" });
        const data = await res.json();
        if (!res.ok || !data.ok) {
          this.historialError = data.error || "No se pudo cargar el historial.";
          this.historialFilas = [];
          this.historialResumen = null;
          return;
        }
        this.historialFilas = data.filas || [];
        this.historialResumen = data.resumen || null;
      } catch (e) {
        this.historialError = "Error de red al cargar el historial.";
        this.historialFilas = [];
        this.historialResumen = null;
      } finally {
        this.historialLoading = false;
      }
    },

    cerrarHistorial() {
      this.historialOpen = false;
      this.historialArticulo = null;
      this.historialFilas = [];
      this.historialResumen = null;
      this.historialError = "";
    },

    fmtPct(val) {
      if (val === null || val === undefined) return "—";
      const n = Number(val);
      if (Number.isNaN(n)) return "—";
      const sign = n > 0 ? "+" : "";
      return `${sign}${n.toFixed(2)}%`;
    },

    fmtFecha(iso) {
      if (!iso) return "—";
      const p = String(iso).split("-");
      if (p.length !== 3) return iso;
      return `${p[2]}/${p[1]}/${p[0]}`;
    },
  };
}
