/**
 * Modos PED en OrderShell: nuevo | editar_pendiente | consulta.
 * Carga ``?cod_mov=``, acciones Anular/Repetir/PDF/mail y confirmar cambios.
 */

function tplReplaceCod(tpl, codMov) {
  const t = tpl || '';
  if (t.includes('cod_mov=')) {
    return t.replace(/cod_mov=\d+/, `cod_mov=${codMov}`);
  }
  return t.replace(/\/0(\/|$)/, `/${codMov}$1`);
}

/**
 * @returns {Record<string, unknown>}
 */
export function compraMayoristaPedidoMixin() {
  return {
    modo: 'nuevo',
    codMov: null,
    cabeceraPedido: null,
    renglonesConsulta: [],
    vinculosPedido: [],
    stepperPedido: [],
    puedeAnular: false,
    cargandoPedido: false,
    errorPedido: '',
    dialogInput: '',
    dialogInputError: '',

    get esConsulta() {
      return this.modo === 'consulta';
    },
    get esEditarPendiente() {
      return this.modo === 'editar_pendiente';
    },
    get pedidoEditable() {
      return this.modo !== 'consulta';
    },
    get puedeRepetirPedido() {
      const c = this.cabeceraPedido;
      return !!(c && String(c.anulado || '').toLowerCase() !== 'si');
    },
    get breadcrumbPedido() {
      if (!this.codMov || !this.cabeceraPedido) return 'Nuevo pedido';
      return `PED ${this.cabeceraPedido.nro_comprobante || this.codMov}`;
    },
    get pdfPedidoUrl() {
      if (!this.codMov || !this.urls.pdf_tpl) return '#';
      return tplReplaceCod(this.urls.pdf_tpl, this.codMov);
    },
    get heroPedidoSub() {
      const c = this.cabeceraPedido;
      if (!c) return '';
      const nro = c.nro_comprobante || this.codMov || '';
      const cli = c.nombre_cliente || '';
      return [nro && `PED ${nro}`, cli].filter(Boolean).join(' · ');
    },

    get estadoPedidoLabel() {
      const c = this.cabeceraPedido;
      if (!c) return '';
      if (String(c.anulado || '').toLowerCase() === 'si') return 'Anulado';
      const raw = String(c.estado || '').trim();
      const key = raw.toLowerCase();
      const mapa = {
        pendiente: 'Pendiente',
        'en preparación': 'En preparación',
        'en preparacion': 'En preparación',
        preparado: 'Preparado',
        'en remito': 'En remito',
        parcial: 'En remito',
        cerrado: 'Cerrado / Facturado',
        facturado: 'Cerrado / Facturado',
      };
      return mapa[key] || raw || 'Pendiente';
    },

    get estadoPedidoBadgeClass() {
      const label = this.estadoPedidoLabel;
      const clases = {
        Pendiente: 'bg-sky-500/20 text-sky-200 ring-1 ring-inset ring-sky-400/40',
        'En preparación': 'bg-amber-500/20 text-amber-200 ring-1 ring-inset ring-amber-400/40',
        Preparado: 'bg-violet-500/20 text-violet-200 ring-1 ring-inset ring-violet-400/40',
        'En remito': 'bg-teal-500/20 text-teal-200 ring-1 ring-inset ring-teal-400/40',
        'Cerrado / Facturado': 'bg-emerald-500/20 text-emerald-200 ring-1 ring-inset ring-emerald-400/40',
        Anulado: 'bg-rose-500/20 text-rose-200 ring-1 ring-inset ring-rose-400/40',
      };
      return clases[label] || 'bg-slate-500/20 text-slate-200 ring-1 ring-inset ring-slate-400/40';
    },

    _codMovDesdeQuery() {
      try {
        const q = new URLSearchParams(window.location.search);
        const n = Number(q.get('cod_mov'));
        return Number.isFinite(n) && n > 0 ? n : null;
      } catch {
        return null;
      }
    },

    _urlCabecera(cod) {
      return tplReplaceCod(this.urls.cabecera_tpl || '', cod);
    },
    _urlRenglones(cod) {
      return tplReplaceCod(this.urls.renglones_tpl || '', cod);
    },

    _leerBootstrapPedido() {
      const el = document.getElementById('compra-mayorista-pedido-bootstrap');
      if (!el) return null;
      try {
        return JSON.parse(el.textContent);
      } catch {
        return null;
      }
    },

    _aplicarBootstrapPedido(boot) {
      if (!boot || typeof boot !== 'object') return false;
      const cod = Number(boot.cod_mov);
      if (!Number.isFinite(cod) || cod <= 0) return false;
      this.codMov = cod;
      if (boot.error) {
        this.errorPedido = String(boot.error);
        this.modo = 'consulta';
        return true;
      }
      if (!boot.cabecera) return false;
      this.cabeceraPedido = boot.cabecera;
      this.vinculosPedido = boot.vinculos || [];
      this.stepperPedido = boot.stepper || [];
      this.puedeAnular = !!boot.puede_anular;
      this.renglonesConsulta = boot.renglones || [];
      this.modo = boot.modo === 'editar_pendiente' ? 'editar_pendiente' : 'consulta';
      const cab = boot.cabecera;
      const idCliente = cab.id_cliente || cab.codigo_cliente;
      if (cab.nombre_cliente) {
        this.clienteActivo = idCliente || this.clienteActivo;
        this.clienteActivoLabel = cab.nombre_cliente;
        window.dispatchEvent(new CustomEvent('compra-cliente-display', {
          detail: { label: this.clienteActivoLabel },
        }));
      }
      if (cab.forma_entrega) this.formaEntrega = cab.forma_entrega;
      if (cab.observaciones) this.observaciones = cab.observaciones;
      return true;
    },

    async cargarPedidoDesdeQuery() {
      const boot = this._leerBootstrapPedido();
      if (boot) {
        this._aplicarBootstrapPedido(boot);
      }

      const cod = this._codMovDesdeQuery() || this.codMov;
      if (!cod) {
        if (!boot) {
          this.modo = 'nuevo';
          this.codMov = null;
        }
        return;
      }
      this.codMov = cod;
      this.cargandoPedido = !this.cabeceraPedido;
      this.errorPedido = this.errorPedido || '';
      try {
        const cabUrl = this._urlCabecera(cod);
        const detUrl = this._urlRenglones(cod);
        if (!cabUrl || cabUrl.includes('/0/')) {
          throw new Error('URL de cabecera de pedido inválida.');
        }
        const [cabR, detR] = await Promise.all([
          this.api(cabUrl, 'GET'),
          detUrl ? this.api(detUrl, 'GET') : Promise.resolve({ ok: false, data: null }),
        ]);
        if (!cabR.ok || !cabR.data || !cabR.data.ok) {
          throw new Error((cabR.data && (cabR.data.error || cabR.data.detail)) || 'Pedido no encontrado');
        }
        const cab = cabR.data.cabecera;
        this.cabeceraPedido = cab;
        this.vinculosPedido = cabR.data.vinculos || [];
        this.stepperPedido = cabR.data.stepper || [];
        this.puedeAnular = !!cabR.data.puede_anular;
        if (detR.ok && detR.data && detR.data.results) {
          this.renglonesConsulta = detR.data.results;
        }

        const anulado = String(cab.anulado || '').toLowerCase() === 'si';
        const estado = String(cab.estado || '').trim();
        const idCliente = cab.id_cliente || cab.codigo_cliente || cab.Codigo;
        if (idCliente && this.urls.clientes_seleccionar) {
          const selUrl = this.urls.clientes_seleccionar.includes('ajax=')
            ? this.urls.clientes_seleccionar
            : `${this.urls.clientes_seleccionar}?ajax=1`;
          await this.api(selUrl, 'POST', { codigo: idCliente });
          this.clienteActivo = idCliente;
          this.clienteActivoLabel = cab.nombre_cliente || String(idCliente);
          window.dispatchEvent(new CustomEvent('compra-cliente-display', {
            detail: { label: this.clienteActivoLabel },
          }));
        } else if (cab.nombre_cliente) {
          this.clienteActivo = idCliente || this.clienteActivo;
          this.clienteActivoLabel = cab.nombre_cliente;
          window.dispatchEvent(new CustomEvent('compra-cliente-display', {
            detail: { label: this.clienteActivoLabel },
          }));
        }
        if (cab.forma_entrega) this.formaEntrega = cab.forma_entrega;
        if (cab.observaciones) this.observaciones = cab.observaciones;

        if (anulado || estado.toLowerCase() !== 'pendiente') {
          this.modo = 'consulta';
        } else {
          this.modo = 'editar_pendiente';
          await this._hidratarCarritoDesdePedido(cod);
        }
      } catch (e) {
        if (!this.cabeceraPedido) {
          this.errorPedido = e.message || 'Error al cargar el pedido';
          this.modo = 'consulta';
        } else {
          this.flash(e.message || 'No se pudo refrescar el pedido.', false);
        }
      } finally {
        this.cargandoPedido = false;
      }
    },

    async _hidratarCarritoDesdePedido(cod) {
      const { ok, data } = await this.api(this.urls.cargar_desde_pedido, 'POST', {
        codigo_movimiento: cod,
        origen: 'edicion',
        omitir_validacion_stock: true,
      });
      if (!ok || !data) {
        this.flash(
          (data && (data.error || data.detail)) || 'No se pudieron cargar las líneas al carrito.',
          false,
        );
        return;
      }
      if (data.carrito) this.setCart(data.carrito);
      this.origenRepetir = data.origen_nro_comprobante || cod;
      if (data.advertencias && data.advertencias.length) {
        this.flash(data.advertencias.join(' '), true);
      }
    },

    solicitarAnularPedido() {
      if (!this.puedeAnular || !this.codMov) return;
      this.dialogInput = '';
      this.dialogInputError = '';
      this.abrirDialogo('anular_pedido', {
        titulo: 'Anular pedido',
        mensaje: 'Solo es posible en estado Pendiente. Indique el motivo (obligatorio).',
        confirmarTexto: 'Anular pedido',
        cancelarTexto: 'Cancelar',
        variante: 'danger',
        onConfirm: () => this._ejecutarAnularPedido(),
      });
    },

    async _ejecutarAnularPedido() {
      const motivo = String(this.dialogInput || '').trim();
      if (!motivo) {
        this.dialogInputError = 'Debe indicar el motivo de anulación.';
        this.abrirDialogo('anular_pedido', {
          titulo: 'Anular pedido',
          mensaje: 'Solo es posible en estado Pendiente. Indique el motivo (obligatorio).',
          confirmarTexto: 'Anular pedido',
          cancelarTexto: 'Cancelar',
          variante: 'danger',
          onConfirm: () => this._ejecutarAnularPedido(),
        });
        return false;
      }
      const { ok, data } = await this.api(this.urls.anular, 'POST', {
        anularPedido: '1',
        codMovPedido: this.codMov,
        motivo,
      });
      const msgOk = data && (data.msg === 'ok' || data.ok);
      if (!ok || !msgOk) {
        this.flash((data && (data.error || data.detail)) || 'No se pudo anular', false);
        return false;
      }
      this.flash('Pedido anulado.', true);
      await this.cargarPedidoDesdeQuery();
      return true;
    },

    solicitarEnviarMail() {
      if (!this.codMov || !this.cabeceraPedido) return;
      const def = String(this.cabeceraPedido.email_cliente || '').trim();
      this.dialogInput = def;
      this.dialogInputError = '';
      this.abrirDialogo('enviar_mail', {
        titulo: 'Enviar comprobante por mail',
        mensaje: 'Correo del destinatario',
        confirmarTexto: 'Encolar envío',
        cancelarTexto: 'Cancelar',
        onConfirm: () => this._ejecutarEnviarMail(),
      });
    },

    async _ejecutarEnviarMail() {
      const email = String(this.dialogInput || '').trim();
      if (!email || email.indexOf('@') < 1) {
        this.dialogInputError = 'Debe indicar un correo electrónico válido.';
        this.abrirDialogo('enviar_mail', {
          titulo: 'Enviar comprobante por mail',
          mensaje: 'Correo del destinatario',
          confirmarTexto: 'Encolar envío',
          cancelarTexto: 'Cancelar',
          onConfirm: () => this._ejecutarEnviarMail(),
        });
        return false;
      }
      const { ok, data } = await this.api(this.urls.mail_enqueue, 'POST', {
        codMov: this.codMov,
        tipocomprobante: 0,
        email,
      });
      const msgOk = data && (data.msg === 'ok' || data.ok);
      if (!ok || !msgOk) {
        this.flash((data && (data.error || data.detail)) || 'No se pudo encolar el mail', false);
        return false;
      }
      this.flash('Solicitud de envío registrada.', true);
      return true;
    },

    repetirPedidoActual() {
      if (!this.codMov) return;
      SynapRepetirPedido.abrir(this.codMov);
    },

    badgeEstadoPedido(est) {
      const e = String(est || '').toLowerCase();
      if (e === 'pendiente') return 'bg-amber-100 text-amber-800';
      if (e.includes('prepar')) return 'bg-sky-100 text-sky-800';
      if (e === 'preparado') return 'bg-emerald-100 text-emerald-800';
      return 'bg-slate-100 text-slate-700';
    },

    /**
     * Override parcial: en editar_pendiente pide confirmación especial.
     * Se reasigna desde el mixin sobre el método de checkout vía compose order.
     */
    abrirResumen() {
      if (this.esConsulta) {
        this.flash('Este pedido no es modificable (ya entró en producción o está anulado).', false);
        return;
      }
      if (!this._requiereCliente()) return;
      if (!this.cart?.items?.length) {
        this.flash('Agregá al menos una línea al pedido.', false);
        return;
      }
      if (this.esEditarPendiente) {
        this.abrirDialogo('confirmar_cambios', {
          titulo: 'Confirmar cambios del pedido',
          mensaje:
            'Se anulará el pedido pendiente actual y se generará uno nuevo con las líneas del carrito. El número de comprobante cambiará.',
          confirmarTexto: 'Anular y crear nuevo',
          cancelarTexto: 'Volver',
          variante: 'danger',
          onConfirm: () => this._confirmarCambiosPendiente(),
        });
        return;
      }
      this.abrirDialogo('resumen', {
        titulo: `Resumen — ${this.tipoLabel}`,
        confirmarTexto: 'Confirmar',
        cancelarTexto: 'Volver',
        onConfirm: () => this.confirmar(),
      });
    },

    async _confirmarCambiosPendiente() {
      this.confirmando = true;
      const motivo = `Edición Synap: reemplazo PED ${this.cabeceraPedido?.nro_comprobante || this.codMov}`;
      const anular = await this.api(this.urls.anular, 'POST', {
        anularPedido: '1',
        codMovPedido: this.codMov,
        motivo,
      });
      const anuladoOk = anular.data && (anular.data.msg === 'ok' || anular.data.ok);
      if (!anular.ok || !anuladoOk) {
        this.confirmando = false;
        this.flash((anular.data && (anular.data.error || anular.data.detail)) || 'No se pudo anular el origen.', false);
        return;
      }
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
        this.flash(
          (data && data.detail)
            || 'El origen se anuló pero no se pudo crear el nuevo pedido. Revisá el carrito.',
          false,
        );
        this.cerrarDialogo();
        return;
      }
      const nuevo = data && data.codigo_movimiento;
      this.cerrarDialogo();
      if (nuevo) {
        const destino = tplReplaceCod(this.urls.detalle_tpl || this.urls.venta || '', nuevo);
        window.location.href = destino.includes('cod_mov=')
          ? destino
          : `${(this.urls.venta || '').replace(/\/?$/, '/')}?cod_mov=${nuevo}`;
        return;
      }
      this.flash('Pedido reemplazado.', true);
    },
  };
}
