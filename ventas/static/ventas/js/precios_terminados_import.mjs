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
    importFiltroEstado: "revisar",
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
      this.importFiltroEstado = "revisar";
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
        this.importFiltroEstado = "revisar";
        this.importStep = 2;
      } catch (e) {
        this.importError = "Error de red al subir el archivo.";
      } finally {
        this.importLoading = false;
        this._importStopTimer();
      }
    },

    _importTab(grupo) {
      if (grupo.estado === "actualiza") return "actualiza";
      if (grupo.estado === "sin_cambios") return "sin_cambios";
      return "revisar";
    },

    importGruposFiltrados() {
      const prev = this.importPreview;
      if (!prev || !prev.grupos) return [];
      const f = this.importFiltroEstado;
      if (f === "todos") return prev.grupos;
      return prev.grupos.filter((g) => this._importTab(g) === f);
    },

    importErroresFila() {
      const prev = this.importPreview;
      if (!prev) return [];
      if (prev.errores_fila_detalle) return prev.errores_fila_detalle;
      return (prev.errores_fila || []).map((m) => ({ fila: null, mensaje: m }));
    },

    importTabCount(tab) {
      const prev = this.importPreview;
      if (!prev) return 0;
      const grupos = prev.grupos || [];
      if (tab === "todos") return grupos.length + this.importErroresFila().length;
      const n = grupos.filter((g) => this._importTab(g) === tab).length;
      return tab === "revisar" ? n + this.importErroresFila().length : n;
    },

    importMotivos(grupo) {
      if (grupo.motivos && grupo.motivos.length) return grupo.motivos;
      return (grupo.advertencias || []).map((m) => ({ tipo: "advertencia", mensaje: m }));
    },

    importMotivoClass(tipo) {
      if (tipo === "no_encontrado" || tipo === "error_fila") return "text-red-700 dark:text-red-300";
      if (tipo === "ean_no_cargado") return "text-slate-600 dark:text-slate-400";
      return "text-amber-800 dark:text-amber-300";
    },

    importRangoActual(grupo, campo) {
      const r = grupo[campo];
      if (r && r.min != null) {
        if (Math.abs(r.max - r.min) < 0.005) return this.fmtImportMoney(r.min);
        return `${this.fmtImportMoney(r.min)} – ${this.fmtImportMoney(r.max)}`;
      }
      const t = (grupo.talles || [])[0];
      return t ? this.fmtImportMoney(t[campo]) : "—";
    },

    _importVarSigned(actual, nuevo) {
      if (actual == null || nuevo == null) return null;
      if (Number(actual) === 0) return Number(nuevo) === 0 ? 0 : 100;
      return ((Number(nuevo) - Number(actual)) / Number(actual)) * 100;
    },

    importVarGrupo(grupo, campo, nuevo) {
      const r = grupo[campo] || {};
      const ref = r.max != null ? r.max : ((grupo.talles || [])[0] || {})[campo];
      return this._importVarSigned(ref, nuevo);
    },

    importVarTalle(t, lista) {
      if (lista === 1) return this._importVarSigned(t.lista1_neto_actual, t.lista1_neto_nuevo);
      return this._importVarSigned(t.lista5_final_actual, t.lista5_final_nuevo);
    },

    fmtImportVar(v) {
      if (v == null || Number.isNaN(v)) return "—";
      if (Math.abs(v) < 0.05) return "0%";
      const sign = v > 0 ? "+" : "−";
      return `${sign}${Math.abs(v).toLocaleString("es-AR", { maximumFractionDigits: Math.abs(v) >= 10 ? 0 : 1 })}%`;
    },

    importVarClass(v) {
      if (v == null || Math.abs(v) < 0.05) return "text-slate-500";
      return v < 0 ? "text-emerald-700 dark:text-emerald-400" : "text-amber-700 dark:text-amber-400";
    },

    fmtImportMoney(n) {
      if (n == null || Number.isNaN(Number(n))) return "—";
      return "$" + this.fmtImportNum(n);
    },

    importBotonAplicarLabel() {
      const r = this.importResumenAplicar();
      const a = r.articulos === 1 ? "artículo" : "artículos";
      const c = r.codigos === 1 ? "código" : "códigos";
      return `Aplicar ${r.articulos} ${a} (${r.codigos} ${c})`;
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
      let codigosConCambios = 0;
      (prev.grupos || []).forEach((g) => {
        if (!codigos.includes(g.codigo) || this.importCheckboxDisabled(g)) return;
        let n = 0;
        (g.talles || []).forEach((t) => {
          if (t.estado === "actualiza" || t.estado === "advertencia") n += 1;
        });
        articulos += n;
        if (n) codigosConCambios += 1;
      });
      return { articulos, codigos: codigosConCambios };
    },

    irImportConfirmar() {
      if (!this.importResumenAplicar().articulos) {
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
