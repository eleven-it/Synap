/**
 * Carrito / líneas del pedido — compra mayorista (OrderShell F2).
 * Totales exclusivamente de serializar_carrito vía setCart.
 */

/**
 * @returns {Record<string, unknown>}
 */
export function compraMayoristaCarritoMixin() {
  return {
    _requiereCliente() {
      if (this.esCliente || this.clienteActivo) return true;
      this.intentoSinCliente = true;
      this.flash('Seleccioná un cliente antes de continuar.', false);
      document.getElementById('compra_cliente_search')?.focus();
      return false;
    },

    itemOpcionesUom(it) {
      const opciones = it?.presentacion?.opciones;
      if (Array.isArray(opciones) && opciones.length > 1) return opciones;
      return [];
    },

    itemMuestraUom(it) {
      return this.itemOpcionesUom(it).length > 0;
    },

    async agregar(a) {
      if (!this._requiereCliente()) return;
      const cantidad = Math.max(1, Number(a._cant || 1));
      const tipo = a._tipo || 'Unidad';
      const op = ((a.presentacion && a.presentacion.opciones) || []).find((o) => o.tipo === tipo);
      const body = { id_articulo: a.id_articulo, cantidad, tipo_unidad: tipo };
      if (op && op.multiplicador) body.multiplicador = op.multiplicador;
      const presentacion = a.presentacion || null;
      const { ok, data } = await this.api(this.urls.carrito, 'POST', body);
      if (!ok) {
        this.flash((data && data.detail) || 'No se pudo agregar el artículo.', false);
        if (data && data.carrito) this.setCart(data.carrito);
        return;
      }
      this.setCart(data);
      if (presentacion && this.cart.items) {
        const linea = this.cart.items.find((i) => i.id_articulo === a.id_articulo);
        if (linea) linea.presentacion = presentacion;
      }
      this.flash('Artículo agregado al pedido.', true);
    },

    async cambiarCantidad(itemId, cantidad) {
      const qty = Math.max(1, Number(cantidad) || 1);
      const { ok, data } = await this.api(this.itemUrl(itemId), 'PATCH', { cantidad: qty });
      if (!ok) {
        this.flash((data && data.detail) || 'No se pudo actualizar la cantidad.', false);
        if (data && data.carrito) this.setCart(data.carrito);
        return;
      }
      this.setCart(data);
    },

    incrementarCantidad(itemId, actual) {
      this.cambiarCantidad(itemId, Math.max(1, Number(actual) || 1) + 1);
    },

    decrementarCantidad(itemId, actual) {
      const qty = Math.max(1, Number(actual) || 1);
      if (qty <= 1) return;
      this.cambiarCantidad(itemId, qty - 1);
    },

    async quitar(itemId) {
      const { ok, data } = await this.api(this.itemUrl(itemId), 'DELETE');
      if (ok) {
        this.setCart(data);
        this.flash('Línea quitada del pedido.', true);
      } else {
        this.flash((data && data.detail) || 'No se pudo quitar la línea.', false);
      }
    },

    async _ejecutarVaciar() {
      const { ok, data } = await this.api(this.urls.carrito_vaciar, 'POST');
      if (ok) {
        this.setCart(data);
        this.flash('Pedido vaciado.', true);
      } else {
        this.flash((data && data.detail) || 'No se pudo vaciar el pedido.', false);
      }
    },

    async aplicarDescuentoPie() {
      this.descPieError = '';
      const { ok, data } = await this.api(
        this.urls.carrito_descuento_pie,
        'POST',
        { porcentaje: Number(this.descPie || 0) },
      );
      if (ok) {
        this.setCart(data);
        this.descPieError = '';
      } else {
        const msg = (data && data.detail) || 'Descuento inválido.';
        this.descPieError = msg;
        this.flash(msg, false);
      }
    },

    async cambiarUom(itemId, tipoUnidad) {
      const it = (this.cart.items || []).find((i) => i.id === itemId);
      if (!it) return;
      const opciones = this.itemOpcionesUom(it);
      const op = opciones.find((o) => o.tipo === tipoUnidad);
      if (!op) return;
      if ((it.tipo_unidad || 'Unidad') === tipoUnidad) return;

      const { ok: delOk, data: delData } = await this.api(this.itemUrl(itemId), 'DELETE');
      if (!delOk) {
        this.flash((delData && delData.detail) || 'No se pudo cambiar la unidad.', false);
        if (delData && delData.carrito) this.setCart(delData.carrito);
        return;
      }

      const body = {
        id_articulo: it.id_articulo,
        cantidad: Math.max(1, Number(it.cantidad) || 1),
        tipo_unidad: tipoUnidad,
      };
      if (op.multiplicador) body.multiplicador = op.multiplicador;

      const { ok, data } = await this.api(this.urls.carrito, 'POST', body);
      if (!ok) {
        this.flash((data && data.detail) || 'No se pudo cambiar la unidad.', false);
        if (data && data.carrito) this.setCart(data.carrito);
        return;
      }
      this.setCart(data);
      this.flash('Unidad de medida actualizada.', true);
    },

    async refrescarCarrito() {
      const { ok, data } = await this.api(this.urls.carrito, 'GET');
      if (ok) this.setCart(data);
    },

    setCart(data) {
      const prevPresentacion = {};
      (this.cart?.items || []).forEach((it) => {
        if (it.presentacion && it.id_articulo) {
          prevPresentacion[it.id_articulo] = it.presentacion;
        }
      });

      this.cart = data || { items: [] };
      if (this.cart.items) {
        this.cart.items = this.cart.items.map((it) => {
          if (!it.presentacion && prevPresentacion[it.id_articulo]) {
            return { ...it, presentacion: prevPresentacion[it.id_articulo] };
          }
          return it;
        });
      }

      this.tot = (data && data.totales) || {};
      this.descPie = (data && data.descuento_pie_pct) || 0;
      if (data && data.tipo_comprobante) this.tipo = data.tipo_comprobante;
    },
  };
}
