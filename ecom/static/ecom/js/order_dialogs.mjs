/**
 * Modales del canon OrderShell — reemplaza confirm()/prompt()/alert() nativos.
 * Focus trap, cierre con Esc y retorno de foco.
 */

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

/**
 * @param {HTMLElement} container
 * @returns {() => void}
 */
function activarFocusTrap(container) {
  const nodos = Array.from(container.querySelectorAll(FOCUSABLE_SELECTOR))
    .filter((el) => el.offsetParent !== null || el === document.activeElement);
  const primero = nodos[0];
  const ultimo = nodos[nodos.length - 1];

  function onTab(e) {
    if (e.key !== 'Tab' || nodos.length === 0) return;
    if (e.shiftKey) {
      if (document.activeElement === primero) {
        e.preventDefault();
        ultimo?.focus();
      }
    } else if (document.activeElement === ultimo) {
      e.preventDefault();
      primero?.focus();
    }
  }

  container.addEventListener('keydown', onTab);
  primero?.focus();

  return () => container.removeEventListener('keydown', onTab);
}

/**
 * @returns {Record<string, unknown>}
 */
export function orderDialogsMixin() {
  return {
    dialogKind: null,
    dialogTitulo: '',
    dialogMensaje: '',
    dialogConfirmarTexto: 'Confirmar',
    dialogCancelarTexto: 'Cancelar',
    dialogVariante: 'primary',
    _dialogCallback: null,
    _dialogFocusCleanup: null,
    _dialogFocoPrevio: null,
    _tipoPendiente: null,

    get dialogAbierto() {
      return !!this.dialogKind;
    },

    abrirDialogo(kind, opciones = {}) {
      this._dialogFocoPrevio = document.activeElement;
      this.dialogKind = kind;
      this.dialogTitulo = opciones.titulo || '';
      this.dialogMensaje = opciones.mensaje || '';
      this.dialogConfirmarTexto = opciones.confirmarTexto || 'Confirmar';
      this.dialogCancelarTexto = opciones.cancelarTexto || 'Cancelar';
      this.dialogVariante = opciones.variante || 'primary';
      this._dialogCallback = typeof opciones.onConfirm === 'function' ? opciones.onConfirm : null;

      this.$nextTick(() => {
        const panel = document.getElementById('pedidos-dialog-panel');
        if (panel) {
          this._desactivarFocusTrap();
          this._dialogFocusCleanup = activarFocusTrap(panel);
        }
      });
    },

    cerrarDialogo() {
      if (this.confirmando && (
        this.dialogKind === 'resumen'
        || this.dialogKind === 'confirmar_cambios'
        || this.dialogKind === 'masivo_progreso'
      )) return;
      this._desactivarFocusTrap();
      this.dialogKind = null;
      this._dialogCallback = null;
      this._tipoPendiente = null;
      const prev = this._dialogFocoPrevio;
      this._dialogFocoPrevio = null;
      if (prev && typeof prev.focus === 'function') {
        requestAnimationFrame(() => prev.focus());
      }
    },

    async confirmarDialogo() {
      const cb = this._dialogCallback;
      if (
        this.dialogKind === 'resumen'
        || this.dialogKind === 'confirmar_cambios'
        || this.dialogKind === 'masivo_confirmar'
      ) {
        if (cb) await cb();
        return;
      }
      this.cerrarDialogo();
      if (cb) await cb();
    },

    _desactivarFocusTrap() {
      if (this._dialogFocusCleanup) {
        this._dialogFocusCleanup();
        this._dialogFocusCleanup = null;
      }
    },

    onDialogEscape() {
      if (this.dialogAbierto) this.cerrarDialogo();
    },

    solicitarVaciar() {
      if (!this.cart?.items?.length) {
        this.flash('No hay líneas en el pedido.', false);
        return;
      }
      this.abrirDialogo('vaciar', {
        titulo: 'Vaciar pedido',
        mensaje: '¿Quitar todas las líneas del pedido? El borrador quedará sin renglones.',
        confirmarTexto: 'Vaciar pedido',
        cancelarTexto: 'Cancelar',
        variante: 'danger',
        onConfirm: () => this._ejecutarVaciar(),
      });
    },

    solicitarCambiarTipo(nuevo) {
      const t = String(nuevo || '').toUpperCase();
      if (!t || t === this.tipo) return;

      const etiquetas = { PED: 'pedido', PRE: 'presupuesto', DEV: 'devolución' };
      const destino = etiquetas[t] || 'comprobante';

      if (this.cart?.items?.length) {
        this._tipoPendiente = t;
        this.abrirDialogo('cambio_tipo', {
          titulo: `Cambiar a ${destino}`,
          mensaje: 'El pedido actual se mantiene, pero cambia el comportamiento de stock y confirmación.',
          confirmarTexto: `Cambiar a ${destino}`,
          cancelarTexto: 'Cancelar',
          onConfirm: () => this._ejecutarCambiarTipo(this._tipoPendiente || t),
        });
        return;
      }
      this._ejecutarCambiarTipo(t);
    },
  };
}
