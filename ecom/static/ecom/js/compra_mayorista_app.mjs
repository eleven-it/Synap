/**
 * Core Alpine — compra mayorista (OrderShell).
 * Compone mixins por dominio preservando contrato y payloads API.
 */
import { orderUiStateMixin } from './order_ui_state.mjs';
import { orderDialogsMixin } from './order_dialogs.mjs';
import { compraMayoristaCatalogoMixin } from './compra_mayorista_catalogo.mjs';
import { compraMayoristaCarritoMixin } from './compra_mayorista_carrito.mjs';
import { compraMayoristaCheckoutMixin } from './compra_mayorista_checkout.mjs';

/**
 * Compone mixins Alpine preservando getters (no usar spread/Object.assign).
 * @param  {...(Record<string, unknown>|(() => Record<string, unknown>))} mixins
 * @returns {Record<string, unknown>}
 */
export function compose(...mixins) {
  const target = {};
  for (const m of mixins) {
    const obj = typeof m === 'function' ? m() : m;
    Object.defineProperties(target, Object.getOwnPropertyDescriptors(obj));
  }
  return target;
}

function readUrls() {
  const el = document.getElementById('compra-mayorista-urls');
  return el ? JSON.parse(el.textContent) : {};
}

function readConfig() {
  const el = document.getElementById('compra-mayorista-config');
  if (!el) return { esCliente: false };
  try {
    return JSON.parse(el.textContent);
  } catch {
    return { esCliente: false };
  }
}

function compraMayoristaCore() {
  const { esCliente } = readConfig();
  return {
    urls: readUrls(),
    esCliente,
    searchProductos: '',
    soloPromo: false,
    soloStock: true,
    marcasFiltro: [],
    articulosGrid: [],
    articulosGridLoading: false,
    selectedSearchIndex: -1,
    articulosBusquedaAbort: null,
    cart: { items: [] },
    tot: {},
    descPie: 0,
    tipo: 'PED',
    clienteActivo: null,
    clienteActivoLabel: '',
    creditoWidget: null,
    embalaje: {},
    mostrarEmbalaje: false,
    intentoSinCliente: false,

    get tipoLabel() {
      return { PED: 'pedido', PRE: 'presupuesto', DEV: 'devolución' }[this.tipo] || 'comprobante';
    },
    get clienteCampoLabel() {
      return `Cliente para el ${this.tipoLabel}`;
    },
    get modoShellClass() {
      return {
        PED: 'compra-modo-ped',
        PRE: 'compra-modo-pre',
        DEV: 'compra-modo-dev',
      }[this.tipo] || 'compra-modo-ped';
    },
    get verDetalleLabel() {
      const t = this.ultimoTipo || this.tipo;
      return { PED: 'Ver pedido', PRE: 'Ver presupuesto', DEV: 'Ver devolución' }[t] || 'Ver detalle';
    },
    get verListadoLabel() {
      return 'Ver listado de presupuestos';
    },

    init() {
      SynapRepetirPedido.init({
        previewTpl: this.urls.preview_tpl,
        cargarUrl: this.urls.cargar_desde_pedido,
        esCliente: this.esCliente,
        onCargado: (data) => {
          if (data.carrito) this.setCart(data.carrito);
          this.origenRepetir = data.origen_nro_comprobante || data.origen_codigo_movimiento;
          this.flash('Pedido cargado. Precios actualizados.', true);
        },
      });
      window.addEventListener('compra-cliente-seleccionado', (e) => {
        const d = e.detail || {};
        if (!d.cod) return;
        this.clienteActivo = d.cod;
        this.clienteActivoLabel = d.label || String(d.cod);
        this.intentoSinCliente = false;
        if (!d.fromSession) {
          this.refrescarCarrito();
          this.cargarRecientes();
          this.cargarContexto();
          this.flash('Cliente seleccionado.', true);
        }
      });
      window.addEventListener('compra-cliente-limpiado', () => {
        this.clienteActivo = null;
        this.clienteActivoLabel = '';
        this.creditoWidget = null;
        this.pedidosRecientes = [];
      });
      window.addEventListener('compra-cliente-error', (e) => {
        this.flash((e.detail && e.detail.message) || 'No se pudo seleccionar el cliente.', false);
      });
      window.addEventListener('compra-marcas-cambiadas', (e) => {
        const ids = (e.detail && e.detail.marcas) || [];
        this.marcasFiltro = ids.map((id) => Number(id)).filter((n) => Number.isFinite(n));
        this.recargarBusquedaConFiltros();
      });
      this.refrescarCarrito();
      this.cargarContexto();
      this.$nextTick(() => {
        if (!this.esCliente && !this.clienteActivo) {
          document.getElementById('compra_cliente_search')?.focus();
        } else {
          document.getElementById('pedidos-busqueda-producto')?.focus();
        }
      });
    },

    _limpiarClienteUi() {
      this.clienteActivo = null;
      this.clienteActivoLabel = '';
      this.creditoWidget = null;
      this.pedidosRecientes = [];
      this.intentoSinCliente = false;
      window.dispatchEvent(new CustomEvent('compra-cliente-limpiado'));
    },

    csrf() {
      const el = document.querySelector('[name=csrfmiddlewaretoken]');
      return el ? el.value : '';
    },
    async api(url, method = 'GET', body = null, signal = null) {
      const opts = { method, headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.csrf() } };
      if (body) opts.body = JSON.stringify(body);
      if (signal) opts.signal = signal;
      const r = await fetch(url, opts);
      let data = null;
      try {
        data = await r.json();
      } catch {
        data = null;
      }
      return { ok: r.ok, status: r.status, data };
    },
    money(v) {
      const n = Number(v || 0);
      return `$${n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    itemUrl(id) {
      return this.urls.carrito_item_tpl.replace(/0\/$/, `${id}/`);
    },
  };
}

function register() {
  if (!window.Alpine || window.__synapCompraMayoristaRegistered) return false;

  window.Alpine.data('compraMayorista', () => compose(
    orderUiStateMixin,
    orderDialogsMixin,
    compraMayoristaCarritoMixin,
    compraMayoristaCatalogoMixin,
    compraMayoristaCheckoutMixin,
    compraMayoristaCore,
  ));
  window.__synapCompraMayoristaRegistered = true;
  return true;
}

function remountRoot() {
  const { Alpine } = window;
  const root = document.querySelector('[x-data="compraMayorista()"]')
    || document.querySelector('[x-data*="compraMayorista"]');
  if (!Alpine || !root) return;

  let data;
  try {
    data = Alpine.$data(root);
  } catch {
    data = null;
  }
  if (typeof data?.money !== 'function') {
    Alpine.destroyTree(root);
    Alpine.initTree(root);
  }
}

document.addEventListener('alpine:init', register);

if (window.Alpine) {
  register();
  remountRoot();
}
