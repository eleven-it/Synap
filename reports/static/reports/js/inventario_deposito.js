/**
 * Inventario por depósito — UI catálogo Reportes (Alpine).
 */
(function () {
  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    if (match) return decodeURIComponent(match[1]);
    const el = document.querySelector("[name=csrfmiddlewaretoken]");
    return el ? el.value : "";
  }

  function fmtNum(val) {
    const n = Number(val);
    if (!Number.isFinite(n)) return "—";
    return n.toLocaleString("es-AR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function toast(msg, tipo) {
    if (typeof window.mprShowAviso === "function") {
      window.mprShowAviso(msg, tipo || "info");
      return;
    }
    if (window.SynapMessages && typeof window.SynapMessages.show === "function") {
      window.SynapMessages.show(msg, tipo || "info");
    }
  }

  window.inventarioDepositoApp = function inventarioDepositoApp() {
    const root = document.getElementById("inventario-deposito-root");
    return {
      slug: (root && root.dataset.slug) || "inventario-deposito-articulo",
      queryUrl: (root && root.dataset.queryUrl) || "",
      exportUrl: (root && root.dataset.exportUrl) || "",
      filtersUrl: (root && root.dataset.filtersUrl) || "",
      fechaCorte: (root && root.dataset.fechaCorte) || "",
      fechaCorteDisplay: "",
      q: "",
      incluir2da: false,
      depositosOpciones: [],
      marcasOpciones: [],
      depositosSeleccionados: [],
      marcasSeleccionadas: [],
      jerarquia: [],
      kpiDocenas: "0,00",
      kpiDepositos: "0",
      kpiFilas: "0",
      usaStockDeposito: true,
      cargando: false,
      consultado: false,
      tieneDatos: false,
      errorMsg: "",
      avisoMsg: "",

      fmtNum,

      async init() {
        await this.cargarOpcionesFiltros();
        await this.consultar();
      },

      async cargarOpcionesFiltros() {
        if (!this.filtersUrl) return;
        try {
          const [depRes, marcaRes] = await Promise.all([
            fetch(this.filtersUrl + "?type=depositos", { credentials: "same-origin" }),
            fetch(this.filtersUrl + "?type=marcas", { credentials: "same-origin" }),
          ]);
          if (depRes.ok) {
            const data = await depRes.json();
            this.depositosOpciones = data.depositos || data.results || [];
          }
          if (marcaRes.ok) {
            const data = await marcaRes.json();
            this.marcasOpciones = data.marcas || data.results || [];
          }
        } catch (err) {
          console.error("Filtros inventario depósito:", err);
        }
      },

      buildFilters() {
        const filters = {
          fecha_corte: this.fechaCorte || undefined,
          incluir_2da: this.incluir2da ? "1" : "0",
        };
        if (this.depositosSeleccionados && this.depositosSeleccionados.length) {
          filters.depositos = this.depositosSeleccionados.map(Number);
        }
        if (this.marcasSeleccionadas && this.marcasSeleccionadas.length) {
          filters.marcas_incluidos = this.marcasSeleccionadas.map(Number);
        }
        const q = (this.q || "").trim();
        if (q.length >= 2) filters.q = q;
        return filters;
      },

      async consultar() {
        if (!this.queryUrl) return;
        this.cargando = true;
        this.errorMsg = "";
        this.avisoMsg = "";
        try {
          const res = await fetch(this.queryUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken(),
            },
            body: JSON.stringify({
              slug: this.slug,
              filters: this.buildFilters(),
            }),
          });
          const body = await res.json().catch(() => ({}));
          if (!res.ok) {
            this.errorMsg = body.detail || "No se pudo consultar el inventario.";
            this.jerarquia = [];
            this.tieneDatos = false;
            return;
          }
          const meta = body.meta || {};
          const totals = body.totals || {};
          this.jerarquia = meta.depositos_jerarquia || [];
          this.fechaCorteDisplay = meta.fecha_corte_display || "";
          if (meta.fecha_corte) this.fechaCorte = String(meta.fecha_corte).slice(0, 10);
          this.usaStockDeposito = meta.usa_stock_deposito !== false;
          this.kpiDocenas = fmtNum(totals.total_docenas);
          this.kpiDepositos = String(totals.depositos || 0);
          this.kpiFilas = String(totals.filas || 0);
          this.tieneDatos = this.jerarquia.length > 0;
          this.consultado = true;
          if (Array.isArray(body.notes) && body.notes.length > 1) {
            this.avisoMsg = body.notes.slice(1).join(" · ");
          }
        } catch (err) {
          console.error(err);
          this.errorMsg = "Error de red al consultar el inventario.";
          this.tieneDatos = false;
        } finally {
          this.cargando = false;
        }
      },

      async exportarExcel() {
        if (!this.exportUrl) return;
        this.cargando = true;
        try {
          const url = this.exportUrl + (this.exportUrl.includes("?") ? "&" : "?") + "type=xlsx";
          const res = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken(),
            },
            body: JSON.stringify({
              slug: this.slug,
              filters: this.buildFilters(),
            }),
          });
          if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            toast(body.detail || "No se pudo exportar Excel.", "error");
            return;
          }
          const blob = await res.blob();
          const dispo = res.headers.get("Content-Disposition") || "";
          const match = /filename=\"?([^\";]+)\"?/i.exec(dispo);
          const nombre = match ? match[1] : "inventario_deposito.xlsx";
          const a = document.createElement("a");
          a.href = URL.createObjectURL(blob);
          a.download = nombre;
          document.body.appendChild(a);
          a.click();
          a.remove();
          URL.revokeObjectURL(a.href);
          toast("Excel generado.", "success");
        } catch (err) {
          console.error(err);
          toast("Error al exportar Excel.", "error");
        } finally {
          this.cargando = false;
        }
      },
    };
  };
})();
