/**
 * Importación Excel — precios terminados (panel lateral 3 pasos).
 */

function preciosTerminadosImportMixin(config) {
  const urls = (config.urls || {});
  return {
    importOpen: false,
    importStep: 1,
    importFile: null,
    importFileName: "",
    importLoading: false,
    importElapsed: 0,
    _importTimer: null,

    _importStartTimer() {
      this.importElapsed = 0;
      clearInterval(this._importTimer);
      const t0 = Date.now();
      this._importTimer = setInterval(() => {
        this.importElapsed = Math.round((Date.now() - t0) / 1000);
      }, 1000);
    },

    _importStopTimer() {
      clearInterval(this._importTimer);
      this._importTimer = null;
    },
    importError: "",
    importPreview: null,
    importFiltroEstado: "todos",
    importCodigosSel: {},
    importExpandedCodigos: {},
    importApplyResult: null,

    abrirImportExcel() {
      this.importOpen = true;
      this.importStep = 1;
      this.importError = "";
      this.importPreview = null;
      this.importApplyResult = null;
      this.importFile = null;
      this.importFileName = "";
      this.importCodigosSel = {};
      this.importExpandedCodigos = {};
    },

    cerrarImportExcel() {
      this.importOpen = false;
    },

    onImportFileChange(event) {
      const f = event.target.files && event.target.files[0];
      this.importFile = f || null;
      this.importFileName = f ? f.name : "";
      this.importError = "";
    },

    async enviarImportPreview() {
      if (!this.importFile || !urls.importPreview) {
        this.importError = "Seleccioná un archivo Excel.";
        return;
      }
      this.importLoading = true;
      this._importStartTimer();
      this.importError = "";
      try {
        const fd = new FormData();
        fd.append("archivo", this.importFile);
        const resp = await fetch(urls.importPreview, {
          method: "POST",
          headers: { "X-CSRFToken": getCsrf() },
          credentials: "same-origin",
          body: fd,
        });
        const data = await resp.json();
        if (!resp.ok || !data.ok) {
          this.importError = data.error || data.error_fatal || "No se pudo procesar el archivo.";
          return;
        }
        this.importPreview = data;
        this.importCodigosSel = {};
        (data.grupos || []).forEach((g) => {
          if (g.selected_default) {
            this.importCodigosSel[g.codigo] = true;
          }
        });
        this.importStep = 2;
      } catch (e) {
        this.importError = "Error de red al subir el archivo.";
      } finally {
        this.importLoading = false;
        this._importStopTimer();
      }
    },

    importGruposFiltrados() {
      const prev = this.importPreview;
      if (!prev || !prev.grupos) return [];
      const f = this.importFiltroEstado;
      if (f === "todos") return prev.grupos;
      return prev.grupos.filter((g) => g.estado === f);
    },

    toggleImportCodigo(codigo) {
      this.importCodigosSel[codigo] = !this.importCodigosSel[codigo];
    },

    toggleImportExpand(codigo) {
      this.importExpandedCodigos[codigo] = !this.importExpandedCodigos[codigo];
    },

    importCheckboxDisabled(grupo) {
      return grupo.estado === "no_encontrado" || grupo.estado === "error";
    },

    fmtImportNum(n) {
      if (n == null || Number.isNaN(Number(n))) return "—";
      return Number(n).toLocaleString("es-AR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
    },

    fmtImportPct(n) {
      if (n == null) return "—";
      return `${Number(n).toFixed(1)}%`;
    },

    importCodigosSeleccionados() {
      return Object.keys(this.importCodigosSel).filter((c) => this.importCodigosSel[c]);
    },

    importResumenAplicar() {
      const prev = this.importPreview;
      if (!prev) return { articulos: 0, codigos: 0 };
      const codigos = this.importCodigosSeleccionados();
      let articulos = 0;
      (prev.grupos || []).forEach((g) => {
        if (!codigos.includes(g.codigo)) return;
        (g.talles || []).forEach((t) => {
          if (t.estado === "actualiza" || t.estado === "advertencia") articulos += 1;
        });
      });
      return { articulos, codigos: codigos.length };
    },

    irImportConfirmar() {
      if (!this.importCodigosSeleccionados().length) {
        this.importError = "Seleccioná al menos un código para aplicar.";
        return;
      }
      this.importError = "";
      this.importStep = 3;
    },

    async descargarIncidenciasImport() {
      if (!urls.importIncidencias || !this.importPreview) return;
      const resp = await fetch(urls.importIncidencias, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrf(),
        },
        credentials: "same-origin",
        body: JSON.stringify({ preview: this.importPreview }),
      });
      if (!resp.ok) return;
      const blob = await resp.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = (this.importPreview.archivo || "incidencias").replace(/\.xlsx$/i, "") + "_incidencias.xlsx";
      a.click();
      URL.revokeObjectURL(a.href);
    },

    async aplicarImportExcel() {
      if (!urls.importAplicar || !this.importPreview) return;
      this.importLoading = true;
      this._importStartTimer();
      this.importError = "";
      try {
        const resp = await fetch(urls.importAplicar, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          credentials: "same-origin",
          body: JSON.stringify({
            preview: this.importPreview,
            codigos_seleccionados: this.importCodigosSeleccionados(),
            nombre_archivo: this.importPreview.archivo || this.importFileName,
          }),
        });
        const data = await resp.json();
        this.importApplyResult = data;
        if (!resp.ok || !data.ok) {
          this.importError = "Algunos artículos no se actualizaron.";
        }
      } catch (e) {
        this.importError = "Error al aplicar cambios.";
      } finally {
        this.importLoading = false;
        this._importStopTimer();
      }
    },

    estadoImportClass(estado) {
      const map = {
        sin_cambios: "bg-slate-100 text-slate-700",
        actualiza: "bg-emerald-100 text-emerald-800",
        advertencia: "bg-amber-100 text-amber-900",
        no_encontrado: "bg-red-100 text-red-800",
        error: "bg-red-100 text-red-800",
      };
      return map[estado] || "bg-slate-100";
    },
  };
}

window.preciosTerminadosImportMixin = preciosTerminadosImportMixin;
