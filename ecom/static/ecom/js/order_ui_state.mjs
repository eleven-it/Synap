/**
 * Estado UI compartido — flashes, mensajes y aria-live (OrderShell).
 */

/**
 * Anuncia un mensaje a lectores de pantalla.
 * @param {string} message
 * @param {'polite'|'assertive'} politeness
 */
export function announceAriaLive(message, politeness = 'polite') {
  if (!message) return;
  let region = document.getElementById('pedidos-aria-live');
  if (!region) {
    region = document.createElement('div');
    region.id = 'pedidos-aria-live';
    region.setAttribute('aria-atomic', 'true');
    region.className = 'sr-only';
    document.body.appendChild(region);
  }
  region.setAttribute('aria-live', politeness);
  region.textContent = '';
  requestAnimationFrame(() => {
    region.textContent = message;
  });
}

/**
 * Mixin Alpine: mensajes flash y helpers de estado vacío/carga.
 * @returns {Record<string, unknown>}
 */
export function orderUiStateMixin() {
  return {
    mensaje: '',
    mensajeOk: false,
    summaryMobileExpanded: false,

    flash(msg, ok) {
      this.mensaje = msg;
      this.mensajeOk = !!ok;
      if (msg) {
        announceAriaLive(msg, ok ? 'polite' : 'assertive');
      }
    },

    clearFlash() {
      this.mensaje = '';
      this.mensajeOk = false;
    },

    toggleSummaryMobile() {
      this.summaryMobileExpanded = !this.summaryMobileExpanded;
    },

    get pedidoVacio() {
      return !this.cart?.items?.length;
    },
  };
}
