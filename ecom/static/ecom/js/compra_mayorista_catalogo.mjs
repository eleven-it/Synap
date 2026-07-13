/**
 * Catálogo / búsqueda TPV — compra mayorista (OrderShell F2).
 * AbortController, navegación ↑↓, Enter/Esc, match código de barras.
 */

/**
 * @returns {Record<string, unknown>}
 */
export function compraMayoristaCatalogoMixin() {
  return {
    articuloEtiqueta(a) {
      const cod = a.id_manual || a.codigo || a.codigo_articulo || '';
      const precio = this.money(a.precio);
      const stock = a.stock_disponible != null ? ` · Disp. ${a.stock_disponible}` : '';
      return `${cod} · ${precio}${stock}`;
    },

    _filtrosCatalogo() {
      const filtros = { busqueda_tpv: true };
      const term = (this.searchProductos || '').trim();
      if (term) filtros.q = term;
      if (this.soloPromo) filtros.solo_promocion = true;
      if (this.marcasFiltro && this.marcasFiltro.length) filtros.marcas = this.marcasFiltro;
      return filtros;
    },

    recargarBusquedaConFiltros() {
      const q = (this.searchProductos || '').trim();
      if (q.length) {
        this.cargarArticulos();
        return;
      }
      if (this.marcasFiltro.length || this.soloPromo || this.soloStock) {
        this.desplegarArticulosCompletos();
        return;
      }
      this.articulosGrid = [];
      this.selectedSearchIndex = -1;
    },

    _filtrarPorStock(items) {
      if (!this.soloStock) return items;
      return items.filter((a) => {
        const stock = a.stock_disponible;
        if (stock == null || stock === '') return false;
        return Number(stock) > 0;
      });
    },

    _aplicarResultadosCatalogo(items, { preferExactMatch = false, search = '' } = {}) {
      const mapped = items.map((a) => this._mapearArticuloGrid(a));
      this.articulosGrid = this._filtrarPorStock(mapped);
      this.articulosGridLoading = false;
      if (preferExactMatch) {
        const match = this._buscarMatchExacto(search);
        if (match) {
          this.selectedSearchIndex = this.articulosGrid.indexOf(match);
        } else {
          this.selectedSearchIndex = this.articulosGrid.length > 0 ? 0 : -1;
        }
      } else {
        this.selectedSearchIndex = this.articulosGrid.length > 0 ? 0 : -1;
      }
      this.$nextTick(() => this.scrollBusquedaSeleccionado());
    },

    _mapearArticuloGrid(item) {
      return {
        ...item,
        codigo_articulo: item.id_manual || item.codigo || '',
        descripcion: item.nombre || '',
        _raw: item,
      };
    },

    _codigosArticulo(art) {
      const raw = art._raw || art;
      return [
        raw.id_manual,
        raw.codigo,
        raw.codigo_articulo,
        art.codigo_articulo,
        raw.CodigoArticuloT,
      ]
        .filter((v) => v != null && String(v).trim() !== '')
        .map((v) => String(v).trim().toLowerCase());
    },

    _buscarMatchExacto(term) {
      const q = (term || '').trim().toLowerCase();
      if (!q || !this.articulosGrid.length) return null;
      const exactos = this.articulosGrid.filter((art) => this._codigosArticulo(art).includes(q));
      if (exactos.length === 1) return exactos[0];
      return null;
    },

    onBusquedaProductosInput() {
      const q = (this.searchProductos || '').trim();
      if (!q.length) {
        if (this.articulosBusquedaAbort) {
          try {
            this.articulosBusquedaAbort.abort();
          } catch {
            /* noop */
          }
          this.articulosBusquedaAbort = null;
        }
        this.articulosGrid = [];
        this.articulosGridLoading = false;
        this.selectedSearchIndex = -1;
        return;
      }
      this.cargarArticulos();
    },

    async cargarArticulos() {
      const search = (this.searchProductos || '').trim();
      if (!search.length) {
        this.articulosGrid = [];
        this.selectedSearchIndex = -1;
        return;
      }
      if (this.articulosBusquedaAbort) {
        try {
          this.articulosBusquedaAbort.abort();
        } catch {
          /* noop */
        }
      }
      this.articulosBusquedaAbort = new AbortController();
      const ac = this.articulosBusquedaAbort;
      this.articulosGridLoading = true;
      const { ok, data } = await this.api(this.urls.listado, 'POST', {
        filtros: this._filtrosCatalogo(),
        pagina: 1,
        tam: this.soloStock ? 50 : 25,
      }, ac.signal);
      if (ac.signal.aborted) return;
      if ((this.searchProductos || '').trim() !== search) return;
      if (!ok) {
        this.articulosGrid = [];
        this.articulosGridLoading = false;
        this.selectedSearchIndex = -1;
        this.flash((data && data.detail) || 'No se pudo buscar artículos.', false);
        return;
      }
      const items = (data && data.items) ? data.items : [];
      this._aplicarResultadosCatalogo(items, { preferExactMatch: true, search });
    },

    async desplegarArticulosCompletos() {
      if (this.articulosBusquedaAbort) {
        try {
          this.articulosBusquedaAbort.abort();
        } catch {
          /* noop */
        }
      }
      this.articulosBusquedaAbort = new AbortController();
      const ac = this.articulosBusquedaAbort;
      this.articulosGridLoading = true;
      const { ok, data } = await this.api(this.urls.listado, 'POST', {
        filtros: this._filtrosCatalogo(),
        pagina: 1,
        tam: this.soloStock ? 50 : 25,
      }, ac.signal);
      if (ac.signal.aborted) return;
      if (!ok) {
        this.articulosGrid = [];
        this.articulosGridLoading = false;
        this.selectedSearchIndex = -1;
        this.flash((data && data.detail) || 'No se pudo cargar el catálogo.', false);
        return;
      }
      const items = (data && data.items) ? data.items : [];
      this._aplicarResultadosCatalogo(items);
    },

    onBusquedaProductosKeydown(e) {
      const k = e.key;
      if (k === 'ArrowDown') {
        e.preventDefault();
        if (!this.articulosGrid.length && !this.articulosGridLoading) {
          const q = (this.searchProductos || '').trim();
          if (q.length) this.cargarArticulos();
          else this.desplegarArticulosCompletos();
          return;
        }
        this.navegarBusqueda(1);
        return;
      }
      if (k === 'ArrowUp') {
        e.preventDefault();
        this.navegarBusqueda(-1);
      }
    },

    onTablaBusquedaKeydown(e) {
      const k = e.key;
      if (k === 'ArrowDown') {
        e.preventDefault();
        this.navegarBusqueda(1);
        return;
      }
      if (k === 'ArrowUp') {
        e.preventDefault();
        this.navegarBusqueda(-1);
        return;
      }
      if (k === 'Escape') {
        e.preventDefault();
        document.getElementById('pedidos-busqueda-producto')?.focus();
      }
    },

    navegarBusqueda(delta) {
      if (this.articulosGrid.length === 0) return;
      let next = this.selectedSearchIndex + delta;
      if (next < 0) next = 0;
      if (next >= this.articulosGrid.length) next = this.articulosGrid.length - 1;
      this.selectedSearchIndex = next;
      this.$nextTick(() => this.scrollBusquedaSeleccionado());
    },

    onFocusTablaBusqueda() {
      if (this.articulosGrid.length && this.selectedSearchIndex < 0) {
        this.selectedSearchIndex = 0;
        this.$nextTick(() => this.scrollBusquedaSeleccionado());
      }
    },

    scrollBusquedaSeleccionado() {
      const el = this.$refs.busquedaDropdownList;
      if (!el || this.selectedSearchIndex < 0) return;
      const row = el.querySelector(`[data-search-index="${this.selectedSearchIndex}"]`);
      if (row) row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    },

    async onBusquedaProductosEnter() {
      const q = (this.searchProductos || '').trim();
      if (q.length && !this.articulosGrid.length && !this.articulosGridLoading) {
        await this.cargarArticulos();
      }
      const matchExacto = this._buscarMatchExacto(q);
      if (matchExacto) {
        await this.agregarDesdeBusqueda(matchExacto);
        return;
      }
      const idx = this.selectedSearchIndex;
      const hayResultados = this.articulosGrid && this.articulosGrid.length > 0;
      const filaValida = hayResultados && idx >= 0 && idx < this.articulosGrid.length;
      const art = filaValida ? this.articulosGrid[idx] : null;
      if (art) {
        await this.agregarDesdeBusqueda(art);
        return;
      }
      if (q.length) await this.cargarArticulos();
    },

    async agregarDesdeBusqueda(art) {
      const raw = art._raw || art;
      const pres = raw.presentacion || {};
      const opciones = pres.opciones || [];
      const tipoDefecto = pres.tipo_unidad_defecto || 'Unidad';
      const item = {
        ...raw,
        _cant: 1,
        _tipo: tipoDefecto,
        presentacion: pres,
      };
      await this.agregar(item);
      this.searchProductos = '';
      this.articulosGrid = [];
      this.selectedSearchIndex = -1;
      document.getElementById('pedidos-busqueda-producto')?.focus();
    },

    toggleSoloPromo() {
      this.soloPromo = !this.soloPromo;
      this.recargarBusquedaConFiltros();
    },

    toggleSoloStock() {
      this.soloStock = !this.soloStock;
      this.recargarBusquedaConFiltros();
    },
  };
}
