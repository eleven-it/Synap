/**
 * Vendedor operativo — selector supervisor + banner «Operando como».
 */

/**
 * @returns {Record<string, unknown>}
 */
export function compraMayoristaVendedorMixin() {
  return {
    vendedorCartera: [],
    vendedorOperativo: null,
    vendedorOperativoNombre: '',
    vendedorPropio: null,
    mostrarSelectorVendedor: false,
    operandoComoOtro: false,
    _vendedorPendiente: null,

    async cargarCarteraVendedor() {
      if (this.esCliente || !this.urls.vendedores_cartera) return;
      try {
        const data = await this.api(this.urls.vendedores_cartera);
        this.vendedorCartera = data.vendedores || [];
        this.vendedorOperativo = data.operativo ?? null;
        this.vendedorPropio = data.propio ?? null;
        this.mostrarSelectorVendedor = Boolean(data.mostrar_selector);
        this.operandoComoOtro = Boolean(data.operando_como_otro);
        const actual = (this.vendedorCartera || []).find(
          (v) => v.cod_viajante === this.vendedorOperativo,
        );
        this.vendedorOperativoNombre = actual ? actual.nombre : '';
      } catch {
        this.mostrarSelectorVendedor = false;
      }
    },

    solicitarCambioVendedor(codRaw) {
      const cod = Number(codRaw);
      if (!Number.isFinite(cod) || cod === this.vendedorOperativo) return;
      const dest = (this.vendedorCartera || []).find((v) => v.cod_viajante === cod);
      const nombre = dest ? dest.nombre : `Vendedor ${cod}`;
      const hayContexto = Boolean(
        this.clienteActivo
        || (this.cart.items && this.cart.items.length)
        || this.draftId,
      );
      if (!hayContexto) {
        this._aplicarCambioVendedor(cod);
        return;
      }
      this._vendedorPendiente = cod;
      this.abrirDialogo('cambio_vendedor', {
        titulo: 'Cambiar vendedor operativo',
        mensaje: `Al operar como ${nombre} se limpiará el cliente y el pedido en curso. ¿Continuar?`,
        confirmarTexto: 'Cambiar vendedor',
        cancelarTexto: 'Cancelar',
        onConfirm: async () => {
          await this._aplicarCambioVendedor(this._vendedorPendiente);
        },
      });
    },

    async _aplicarCambioVendedor(cod) {
      if (!this.urls.vendedor_operativo || !Number.isFinite(cod)) return;
      try {
        const data = await this.api(this.urls.vendedor_operativo, 'POST', { cod_viajante: cod });
        if (!data.ok) {
          this.flash(data.detail || 'No se pudo cambiar el vendedor.', false);
          return;
        }
        this.vendedorOperativo = data.operativo;
        await this.cargarCarteraVendedor();
        this._limpiarClienteUi();
        this.cart = { items: [] };
        this.tot = {};
        this.descPie = 0;
        await this.refrescarCarrito();
        this.flash('Vendedor operativo actualizado.', true);
      } catch (e) {
        this.flash((e && e.message) || 'Error al cambiar vendedor.', false);
        await this.cargarCarteraVendedor();
      } finally {
        this._vendedorPendiente = null;
      }
    },
  };
}
