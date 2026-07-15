/**
 * Checkout y contexto — compra mayorista (OrderShell F3).
 * Confirmación, tipo comprobante, contexto PV/entrega, cabecera comercial y pedidos recientes.
 */

function isoToDisplay(iso) {
  if (!iso) return '';
  const parts = String(iso).split('-');
  if (parts.length !== 3) return '';
  const [y, m, d] = parts;
  return `${d.padStart(2, '0')}/${m.padStart(2, '0')}/${y}`;
}

function displayToIso(display) {
  const m = String(display || '').trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!m) return null;
  return `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}`;
}

function addDaysIso(iso, dias) {
  if (!iso) return null;
  const d = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(d.getTime())) return null;
  d.setDate(d.getDate() + Number(dias || 0));
  return d.toISOString().slice(0, 10);
}

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
    cabecera: null,
    puedeEditarCabecera: false,
    condicionesVenta: [],
    listasPrecio: [],

    clienteLabel(c) {
      const cod = c.Codigo != null ? c.Codigo : c.codigo;
      const nombre = (c.nombre_cliente || c.nombre || '').trim();
      return nombre && cod != null ? `${nombre} (#${cod})` : (nombre || String(cod || ''));
    },

    _hidratarCabeceraDesdeApi(raw) {
      if (!raw || raw.error) {
        this.cabecera = null;
        return;
      }
      this.puedeEditarCabecera = !!raw.puede_editar;
      this.cabecera = {
        fecha_pedido: raw.fecha_pedido,
        fecha_entrega: raw.fecha_entrega,
        vencimiento: raw.vencimiento,
        fecha_pedido_display: isoToDisplay(raw.fecha_pedido),
        fecha_entrega_display: isoToDisplay(raw.fecha_entrega),
        vencimiento_display: isoToDisplay(raw.vencimiento),
        id_condventa: raw.id_condventa,
        cond_venta: raw.cond_venta,
        lista_id: raw.lista_id,
        dias_condicion: raw.dias_condicion || 0,
      };
    },

    async _cargarCatalogosCabecera(idCondventa) {
      const qCv = idCondventa != null ? `?id_condventa=${idCondventa}` : '';
      const qLista = this.cabecera?.lista_id != null
        ? `?cod_lista_cliente=${this.cabecera.lista_id}`
        : '';
      const [rCv, rLp] = await Promise.all([
        this.urls.condiciones_venta
          ? this.api(`${this.urls.condiciones_venta}${qCv}`, 'GET')
          : { ok: false, data: [] },
        this.urls.lista_precio
          ? this.api(`${this.urls.lista_precio}${qLista}`, 'GET')
          : { ok: false, data: [] },
      ]);
      if (rCv.ok && Array.isArray(rCv.data)) this.condicionesVenta = rCv.data;
      if (rLp.ok && Array.isArray(rLp.data)) this.listasPrecio = rLp.data;
    },

    _recalcVencimientoDisplay() {
      if (!this.cabecera) return;
      const fp = this.cabecera.fecha_pedido || displayToIso(this.cabecera.fecha_pedido_display);
      if (!fp) return;
      this.cabecera.fecha_pedido = fp;
      const cv = this.condicionesVenta.find(
        (c) => Number(c.Codigo) === Number(this.cabecera.id_condventa),
      );
      const dias = cv ? Number(cv.Dias || 0) : Number(this.cabecera.dias_condicion || 0);
      const ven = addDaysIso(fp, dias);
      if (ven) {
        this.cabecera.vencimiento = ven;
        if (!this.puedeEditarCabecera) {
          this.cabecera.vencimiento_display = isoToDisplay(ven);
        }
      }
    },

    onCabeceraFechaChange(campo) {
      if (!this.cabecera) return;
      const map = {
        fecha_pedido: 'fecha_pedido_display',
        fecha_entrega: 'fecha_entrega_display',
        vencimiento: 'vencimiento_display',
      };
      const iso = displayToIso(this.cabecera[map[campo]]);
      if (!iso) return;
      this.cabecera[campo] = iso;
      if (campo === 'fecha_pedido') this._recalcVencimientoDisplay();
      if (campo === 'vencimiento' && !this.puedeEditarCabecera) {
        this._recalcVencimientoDisplay();
      }
    },

    onCabeceraCondicionChange() {
      if (!this.cabecera) return;
      const cv = this.condicionesVenta.find(
        (c) => Number(c.Codigo) === Number(this.cabecera.id_condventa),
      );
      if (cv) {
        this.cabecera.cond_venta = cv.Descripcion;
        this.cabecera.dias_condicion = Number(cv.Dias || 0);
      }
      this._recalcVencimientoDisplay();
    },

    async onCabeceraListaChange() {
      if (!this.cabecera || !this.puedeEditarCabecera) return;
      if (!this.urls.carrito_lista) return;
      const { ok, data } = await this.api(this.urls.carrito_lista, 'PATCH', {
        lista_id: this.cabecera.lista_id,
      });
      if (!ok) {
        this.flash((data && data.detail) || 'No se pudo recalcular precios con la nueva lista.', false);
        return;
      }
      if (data) this.setCart(data);
      this.agendarPreview?.();
    },

    _payloadCabeceraConfirmar() {
      if (!this.cabecera) return {};
      const fp = this.cabecera.fecha_pedido || displayToIso(this.cabecera.fecha_pedido_display);
      const fe = this.cabecera.fecha_entrega || displayToIso(this.cabecera.fecha_entrega_display);
      const ven = this.cabecera.vencimiento || displayToIso(this.cabecera.vencimiento_display);
      const payload = {
        fecha_pedido: fp,
        fecha_entrega: fe || undefined,
        vencimiento: ven,
        id_condventa: this.cabecera.id_condventa,
        lista_id: this.cabecera.lista_id,
      };
      if (this.puedeEditarCabecera) return payload;
      return {
        fecha_pedido: fp,
        fecha_entrega: fe || undefined,
      };
    },

    async cargarContexto() {
      const { ok, data } = await this.api(this.urls.compra_contexto, 'GET');
      if (!ok || !data) return;
      this.puntosVenta = data.puntos_venta || [];
      if (data.id_punto_venta_default) this.pv = data.id_punto_venta_default;
      this.puedeEditarCabecera = !!data.puede_editar_cabecera;
      if (data.cliente) {
        this.clienteActivo = data.idcliente;
        this.clienteActivoLabel = this.clienteLabel(data.cliente);
        this._setCreditoWidget(data.cliente, data.autoriza_credito);
        this._setListaPrecio(data.cliente, data);
        this._hidratarCabeceraDesdeApi(data.cabecera || {});
        await this._cargarCatalogosCabecera(this.cabecera?.id_condventa);
      } else {
        this.clienteActivo = null;
        this.clienteActivoLabel = '';
        this.creditoWidget = null;
        this.listaPrecio = '';
        this.listaPrecioPdfUrl = '';
        this.pedidosRecientes = [];
        this.cabecera = null;
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

    _setListaPrecio(cliente, extras) {
      const c = cliente || {};
      const x = extras || {};
      const lp = c.listaPrecio || c.lista_precio || x.listaPrecio || '';
      if (lp && typeof lp === 'object') {
        this.listaPrecio = String(lp.nombre || lp.name || (lp.codigo != null ? `Lista ${lp.codigo}` : '')).trim();
      } else {
        this.listaPrecio = String(lp || '').trim();
      }
      this.listaPrecioPdfUrl = String(
        x.lista_precio_pdf_url
        || c.lista_precio_pdf_url
        || c.lista_precios_pdf
        || c.listaPrecioPdf
        || x.lista_precios_pdf
        || '',
      ).trim();
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
      const tpl = this.urls.detalle_tpl || this.urls.venta || '';
      if (tpl.includes('cod_mov=')) {
        return tpl.replace(/cod_mov=\d+/, `cod_mov=${codMov}`);
      }
      if (this.urls.venta) {
        return `${this.urls.venta.replace(/\/?$/, '/')}?cod_mov=${codMov}`;
      }
      return tpl.replace(/\/0\/?$/, `/${codMov}/`);
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
        ...this._payloadCabeceraConfirmar(),
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
