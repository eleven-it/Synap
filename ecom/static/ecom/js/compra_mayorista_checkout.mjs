/**
 * Checkout y contexto — compra mayorista (OrderShell F3).
 * Confirmación, tipo comprobante, contexto PV/entrega y pedidos recientes.
 */

/**
 * @returns {Record<string, unknown>}
 */
export function compraMayoristaCheckoutMixin() {
  return {
    pv: null,
    formaEntrega: '',
    observaciones: '',
    confirmando: false,
    pedidosRecientes: [],
    exitoCheckout: '',
    ultimoCodMov: null,
    ultimoTipo: 'PED',
    origenRepetir: null,
    puntosVenta: [],
    descPieError: '',

    clienteLabel(c) {
      const cod = c.Codigo != null ? c.Codigo : c.codigo;
      const nombre = (c.nombre_cliente || c.nombre || '').trim();
      return nombre && cod != null ? `${nombre} (#${cod})` : (nombre || String(cod || ''));
    },

    async cargarContexto() {
      const { ok, data } = await this.api(this.urls.compra_contexto, 'GET');
      if (!ok || !data) return;
      this.puntosVenta = data.puntos_venta || [];
      if (data.id_punto_venta_default) this.pv = data.id_punto_venta_default;
      if (data.cliente) {
        this.clienteActivo = data.idcliente;
        this.clienteActivoLabel = this.clienteLabel(data.cliente);
        this._setCreditoWidget(data.cliente, data.autoriza_credito);
      } else {
        this.clienteActivo = null;
        this.clienteActivoLabel = '';
        this.creditoWidget = null;
        this.pedidosRecientes = [];
      }
      if (data.embalaje) {
        this.embalaje = data.embalaje;
        this.mostrarEmbalaje = data.embalaje.utiliza_bulto_cerrado === 'Si'
          || data.embalaje.utiliza_display === 'Si'
          || data.embalaje.utiliza_embalaje === 'Si';
      }
      if (data.idcliente) {
        this.cargarRecientes();
      }
    },

    _setCreditoWidget(cliente, autoriza) {
      const saldo = Number(cliente.saldo || cliente.Saldo || 0);
      const lim = Number(cliente.credito_limite_dias || cliente.Credito || 0);
      const aut = autoriza || {};
      const limTxt = (aut.limite_credito_dias || '').toString();
      this.creditoWidget = {
        saldo,
        limite_dias: lim,
        autorizado: limTxt.toLowerCase() !== 'no autorizado',
        dias_exceso: Number(aut.dias_exceso_limite || 0),
      };
    },

    detalleUrl(codMov) {
      return (this.urls.detalle_tpl || '').replace(/\/0\/?$/, `/${codMov}/`);
    },

    detalleTrasExitoUrl(codMov) {
      const t = this.ultimoTipo || this.tipo;
      if (t === 'PED') return this.detalleUrl(codMov);
      return (this.urls.comprobante_detalle_tpl || '').replace(/\/0\/?$/, `/${codMov}/`);
    },

    listadoTrasExitoUrl() {
      const t = this.ultimoTipo || this.tipo;
      if (t === 'PRE') return this.urls.listado_presupuestos;
      return this.urls.listado_pedidos;
    },

    async _ejecutarCambiarTipo(nuevo) {
      const t = String(nuevo || '').toUpperCase();
      if (!t || t === this.tipo) return;
      const { ok, data } = await this.api(this.urls.carrito_tipo, 'PATCH', { tipo: t });
      if (!ok) {
        this.flash((data && data.detail) || 'No se pudo cambiar el tipo de comprobante.', false);
        return;
      }
      this.setCart(data);
      this.flash(`Modo ${this.tipoLabel} activado.`, true);
    },

    repetirPedido(codMov) {
      SynapRepetirPedido.abrir(codMov);
    },

    async cargarRecientes() {
      const { ok, data } = await this.api(this.urls.pedidos_recientes, 'GET');
      if (ok && data && data.results) this.pedidosRecientes = data.results;
    },

    abrirResumen() {
      if (!this._requiereCliente()) return;
      if (!this.cart?.items?.length) {
        this.flash('Agregá al menos una línea al pedido.', false);
        return;
      }
      this.abrirDialogo('resumen', {
        titulo: `Resumen — ${this.tipoLabel}`,
        confirmarTexto: 'Confirmar',
        cancelarTexto: 'Volver',
        onConfirm: () => this.confirmar(),
      });
    },

    async confirmar() {
      this.confirmando = true;
      this.mensaje = '';
      const body = {
        tipo: this.tipo,
        forma_entrega: this.formaEntrega,
        observaciones: this.observaciones,
      };
      if (this.esCliente) body.es_cliente = true;
      if (this.pv) body.id_punto_venta = this.pv;
      const { ok, data } = await this.api(this.urls.checkout, 'POST', body);
      this.confirmando = false;
      if (!ok) {
        this.flash((data && data.detail) || 'No se pudo confirmar el comprobante.', false);
        return;
      }
      const nro = (data && data.nro_comprobante) ? data.nro_comprobante : '';
      const aut = (data && data.autorizacion) ? ` · ${data.autorizacion}` : '';
      this.ultimoTipo = this.tipo;
      this.ultimoCodMov = (data && data.codigo_movimiento) ? data.codigo_movimiento : null;
      this.exitoCheckout = `${this.tipoLabel[0].toUpperCase() + this.tipoLabel.slice(1)} ${nro}${aut}`;
      this.cerrarDialogo();
      this.flash('', true);
      this._limpiarClienteUi();
      this.refrescarCarrito();
      this.cargarRecientes();
    },
  };
}
