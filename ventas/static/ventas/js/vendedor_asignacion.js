/**
 * Asignación vendedor ↔ cliente / marca (Ventas Synap).
 */
(function () {
  "use strict";

  function csrfToken() {
    var el = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return el ? el.value : "";
  }

  function buildUrl(path, params) {
    var u = new URL(path, window.location.origin);
    Object.keys(params || {}).forEach(function (k) {
      if (params[k] !== null && params[k] !== undefined && params[k] !== "") {
        u.searchParams.set(k, params[k]);
      }
    });
    return u.pathname + u.search;
  }

  window.vaAsignacionApp = function (config) {
    return {
      modo: config.modoInicial || "cliente",
      puedeEditar: !!config.puedeEditar,
      pageSize: config.pageSize || 25,
      cargando: false,
      mensaje: "",
      error: "",

      qVendedor: "",
      qItem: "",
      vendedores: [],
      sinAsignar: 0,
      vendedorSeleccionado: null,
      filtro: "sin_asignar",

      items: [],
      total: 0,
      page: 1,
      totalPages: 1,
      seleccionados: [],

      destinoVendedorId: "",
      destinoBusqueda: "",
      destinoOpciones: [],
      dragIds: [],

      etiquetaModo: function () {
        return this.modo === "marca" ? "Marca" : "Cliente";
      },
      etiquetaModoPlural: function () {
        return this.modo === "marca" ? "Marcas" : "Clientes";
      },

      init: async function () {
        await this.cargarResumen();
        this.filtro = "sin_asignar";
        this.vendedorSeleccionado = null;
        await this.cargarItems();
      },

      mensajeVacio: function () {
        if (this.filtro === "sin_asignar") {
          return "No hay " + this.etiquetaModoPlural().toLowerCase() + " activos sin asignar.";
        }
        if (this.vendedorSeleccionado != null) {
          return "Este vendedor no tiene " + this.etiquetaModoPlural().toLowerCase() + " asignados. Usá «Sin asignar» para ver pendientes.";
        }
        return "Sin resultados.";
      },

      cambiarModo: async function (nuevo) {
        if (this.modo === nuevo) return;
        this.modo = nuevo;
        this.vendedorSeleccionado = null;
        this.filtro = "sin_asignar";
        this.seleccionados = [];
        this.page = 1;
        var u = new URL(window.location.href);
        u.searchParams.set("modo", nuevo);
        window.history.replaceState({}, "", u.pathname + u.search);
        await this.cargarResumen();
        await this.cargarItems();
      },

      seleccionarVendedor: function (id) {
        this.vendedorSeleccionado = id;
        this.filtro = id === null ? "sin_asignar" : "asignados";
        this.page = 1;
        this.seleccionados = [];
        this.cargarItems();
      },

      toggleSeleccion: function (id) {
        var idx = this.seleccionados.indexOf(id);
        if (idx >= 0) {
          this.seleccionados.splice(idx, 1);
        } else {
          this.seleccionados.push(id);
        }
      },

      toggleTodosVisibles: function (ev) {
        var checked = ev.target.checked;
        var ids = this.items.map(function (r) {
          return r.id_item;
        });
        if (checked) {
          var set = {};
          this.seleccionados.forEach(function (x) {
            set[x] = true;
          });
          ids.forEach(function (x) {
            set[x] = true;
          });
          this.seleccionados = Object.keys(set).map(Number);
        } else {
          var vis = {};
          ids.forEach(function (x) {
            vis[x] = true;
          });
          this.seleccionados = this.seleccionados.filter(function (x) {
            return !vis[x];
          });
        }
      },

      cargarResumen: async function () {
        this.cargando = true;
        this.error = "";
        try {
          var url = buildUrl(config.urls.resumen, {
            modo: this.modo,
            q: this.qVendedor,
          });
          var res = await fetch(url, { credentials: "same-origin" });
          var data = await res.json();
          if (!data.ok) throw new Error(data.error || "Error al cargar vendedores");
          this.vendedores = data.vendedores || [];
          this.sinAsignar = data.sin_asignar || 0;
        } catch (e) {
          this.error = e.message || "No se pudo cargar el resumen.";
        } finally {
          this.cargando = false;
        }
      },

      cargarItems: async function () {
        this.cargando = true;
        this.error = "";
        try {
          var params = {
            modo: this.modo,
            filtro: this.filtro,
            q: this.qItem,
            page: this.page,
            page_size: this.pageSize,
          };
          if (this.filtro === "asignados" && this.vendedorSeleccionado != null) {
            params.id_vendedor = this.vendedorSeleccionado;
          }
          var url = buildUrl(config.urls.items, params);
          var res = await fetch(url, { credentials: "same-origin" });
          var data = await res.json();
          if (!data.ok) throw new Error(data.error || "Error al cargar ítems");
          this.items = data.items || [];
          this.total = data.total || 0;
          this.totalPages = data.total_pages || 1;
        } catch (e) {
          this.error = e.message || "No se pudieron cargar los ítems.";
        } finally {
          this.cargando = false;
        }
      },

      irPagina: function (p) {
        p = Math.max(1, Math.min(p, this.totalPages));
        if (p === this.page) return;
        this.page = p;
        this.cargarItems();
      },

      buscarVendedoresDestino: async function () {
        if ((this.destinoBusqueda || "").length < 1) {
          this.destinoOpciones = [];
          return;
        }
        var url = buildUrl(config.urls.vendedoresBuscar, { q: this.destinoBusqueda });
        var res = await fetch(url, { credentials: "same-origin" });
        var data = await res.json();
        this.destinoOpciones = data.results || [];
      },

      idsParaOperar: function () {
        return this.seleccionados.length ? this.seleccionados : this.dragIds;
      },

      asignarA: async function (idVendedor) {
        if (!this.puedeEditar) return;
        var ids = this.idsParaOperar();
        if (!ids.length) {
          this.mensaje = "Seleccioná al menos un ítem.";
          return;
        }
        await this._postAsignar(ids, idVendedor);
      },

      desasignarSeleccionados: async function () {
        if (!this.puedeEditar) return;
        var ids = this.idsParaOperar();
        if (!ids.length) {
          this.mensaje = "Seleccioná al menos un ítem.";
          return;
        }
        await this._postAsignar(ids, null);
      },

      _postAsignar: async function (ids, idVendedor) {
        this.cargando = true;
        this.mensaje = "";
        this.error = "";
        try {
          var res = await fetch(config.urls.asignar, {
            method: "POST",
            credentials: "same-origin",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken(),
            },
            body: JSON.stringify({
              modo: this.modo,
              ids: ids,
              id_vendedor: idVendedor,
            }),
          });
          var data = await res.json();
          if (!data.ok) throw new Error(data.error || "No se pudo guardar.");
          this.mensaje =
            "Actualizado: " + (data.afectados || 0) + " " + this.etiquetaModoPlural().toLowerCase() + ".";
          this.seleccionados = [];
          this.dragIds = [];
          this.cargarResumen();
          this.cargarItems();
        } catch (e) {
          this.error = e.message || "Error al guardar.";
        } finally {
          this.cargando = false;
        }
      },

      onDragStart: function (ev, idItem) {
        if (!this.puedeEditar) {
          ev.preventDefault();
          return;
        }
        var ids =
          this.seleccionados.indexOf(idItem) >= 0 ? this.seleccionados.slice() : [idItem];
        this.dragIds = ids;
        ev.dataTransfer.effectAllowed = "move";
        ev.dataTransfer.setData("text/plain", ids.join(","));
      },

      onDragOver: function (ev) {
        if (!this.puedeEditar) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
      },

      onDropVendedor: async function (ev, idVendedor) {
        if (!this.puedeEditar) return;
        ev.preventDefault();
        var raw = ev.dataTransfer.getData("text/plain");
        if (raw) {
          this.dragIds = raw
            .split(",")
            .map(Number)
            .filter(function (x) {
              return !isNaN(x);
            });
        }
        await this.asignarA(idVendedor);
      },

      onDropDesasignar: async function (ev) {
        if (!this.puedeEditar) return;
        ev.preventDefault();
        var raw = ev.dataTransfer.getData("text/plain");
        if (raw) {
          this.dragIds = raw
            .split(",")
            .map(Number)
            .filter(function (x) {
              return !isNaN(x);
            });
        }
        await this.desasignarSeleccionados();
      },
    };
  };
})();
