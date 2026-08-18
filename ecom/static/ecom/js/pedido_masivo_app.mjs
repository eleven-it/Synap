/**
 * Core Alpine — pedido masivo por sucursales (matriz packs × sucursales).
 * Extraído del inline de `pedido_masivo_sucursales.html` (D.4). Compone el mixin
 * de diálogos canon (OrderShell) para reemplazar `confirm()` nativo por el modal
 * `pedidos_modal.html` (D.5). Totales híbridos: estimado FE instantáneo + preview servidor.
 */
import { orderDialogsMixin } from './order_dialogs.mjs';
import {
  addDaysIso,
  cabeceraConDisplay,
  displayToIso,
  isoToDisplay,
  payloadCabeceraApi,
} from './cabecera_comercial_dates.mjs';

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

function roundMoney(n) {
  return Math.round(Number(n || 0) * 100) / 100;
}

/** Múltiplo mínimo de empaque (>0) desde multiplo_cantidad_vta. */
function multiploEmpaque(art) {
  const mc = Number(art?.multiplo_cantidad_vta || 0);
  if (mc > 0) return mc;
  return Number(art?.multiplo_empaque || 1) || 1;
}

/** True si qty es 0/vacía o múltiplo entero de multiplo. */
function cantidadOk(qty, multiplo) {
  const q = parseFloat(String(qty ?? '').trim());
  const m = Number(multiplo || 1);
  if (isNaN(q) || q <= 0 || m <= 1) return true;
  const resto = q % m;
  return Math.abs(resto) < 1e-9;
}

function sugerenciaMultiplo(qty, multiplo) {
  const q = Math.floor(parseFloat(qty) || 0);
  const m = Number(multiplo || 1);
  if (m <= 1) return '';
  const inf = Math.max(m, Math.floor(q / m) * m);
  const sup = inf + m;
  const ejemplos = [];
  if (inf > 0) ejemplos.push(inf);
  ejemplos.push(sup);
  if (sup + m <= sup + m * 2) ejemplos.push(sup + m);
  return 'Usá ' + [...new Set(ejemplos)].join(', ') + '…';
}

function pedidoMasivoCore() {
  return {
    urls: {},
    draftId: null,
    draftEstado: '',
    idCliente: null,
    clienteNombre: '',
    listaPrecio: '',
    listaPrecioPdfUrl: '',
    listaId: 1,
    clientes: [],
    clienteSel: '',
    qCliente: '',
    panelCli: false,
    idxCli: 0,
    cargandoCli: false,
    opcionesSucursal: [],
    sucursalSel: null,
    qSucursal: '',
    panelSuc: false,
    idxSuc: 0,
    cargandoSuc: false,
    sucursales: [],
    articulos: [],
    celdas: {},
    celdasInvalidas: {},
    descuentosFila: {},
    descPiePct: 0,
    ultimoError: {},
    articulosBusqueda: [],
    qArt: '',
    panelArt: false,
    idxArt: 0,
    cargandoArt: false,
    artBusquedaHecha: false,
    _artBusquedaSeq: 0,
    _articulosBusquedaAbort: null,
    artDropdownStyle: '',
    _blurArtTimer: null,
    // Modal detalle sucursal (NroCalle / cliente_domicilio).
    modalSucursalAbierto: false,
    sucursalDetalle: null,
    error: '',
    abriendo: false,
    /** true = abriendo PED (cod_mov); false = abriendo borrador/draft. */
    abriendoEsPedido: false,
    guardadoChip: '',
    confirmando: false,
    confirmProgreso: null,
    anulando: false,
    mensajeOk: '',
    nuevoMenuAbierto: false,
    _chipTimer: null,
    // Preview híbrido: estimado FE instantáneo + validación servidor (debounce).
    preview: { sucursales: [], total_lote: { neto: 0, iva: 0, total: 0 }, warning: '' },
    previewEstimado: { neto: 0, iva: 0, total: 0 },
    previewFuente: 'estimado',
    previewCargando: false,
    _previewTimer: null,
    _previewSeq: 0,
    // Vendedor operativo (supervisor) — el include reutiliza `esCliente`.
    esCliente: false,
    vendedorCartera: [],
    vendedorOperativo: null,
    vendedorOperativoNombre: '',
    vendedorPropio: null,
    mostrarSelectorVendedor: false,
    selectorVendedorInline: false,
    selectorVendedorHero: true,
    operandoComoOtro: false,
    _vendedorPendiente: null,
    cabecera: null,
    puedeEditarCabecera: false,
    puedeEditarLista: false,
    puedeEditarCondicion: false,
    puedeEditarVencimiento: false,
    puedeEditarDescPie: false,
    puedeEditarDescRenglon: false,
    condicionesVenta: [],
    listasPrecio: [],
    tipo: 'PED',
    // Contexto comercial compacto por defecto para reservar alto a la matriz.
    contextoAbierto: false,
    // ── Pedido simple (masivo 1 columna) ──
    modoSimple: false,
    idDomicilioInicial: null,
    codMovOrigen: null,
    // PED cargado/consultado (acciones hero mail/repetir/PDF/anular).
    pedidoCodMov: null,
    pedidoNro: '',
    pedidoEstado: '',
    pedidoEditable: true,
    pedidoRepetido: false,
    puedeAnularPedido: false,
    readonly: false,
    aprobacionPedidosActiva: false,
    urlResumenLote: '',
    emailCliente: '',
    credito: null,
    advertenciasCarga: [],
    // Input compartido para modales mail/anular (contrato pedidos_modal.html).
    dialogInput: '',
    dialogInputError: '',
    // Catálogo completo en matriz (Mostrar/Ocultar todos).
    catalogoDesplegado: false,
    articulosSeleccionados: {},
    esperaOperacion: false,
    esperaMensaje: 'Procesando…',
    importArchivo: null,
    importNombreArchivo: '',
    importErrores: [],
    importErroresTotal: 0,
    importando: false,

    get totalesPie() {
      if (this.previewFuente === 'servidor') {
        return this.preview.total_lote || { neto: 0, iva: 0, total: 0 };
      }
      return this.previewEstimado || { neto: 0, iva: 0, total: 0 };
    },

    /**
     * Solo avisos que pueden impedir o truncar el guardado (p. ej. artículo inválido).
     * Omite timeouts / límites blandos de preview: no bloquean confirmar.
     */
    get previewWarningBloqueante() {
      return this._filtroWarningPreview(this.preview?.warning || '');
    },

    get previewResumenSucursales() {
      const desdeServidor = (this.preview.sucursales || []).length;
      if (desdeServidor > 0) {
        return `${desdeServidor} sucursal${desdeServidor === 1 ? '' : 'es'} con carga`;
      }
      // Fallback FE: domicilios con al menos una cantidad > 0.
      const ids = new Set();
      for (const [key, raw] of Object.entries(this.celdas || {})) {
        const qty = parseFloat(raw);
        if (!isNaN(qty) && qty > 0) {
          const parts = String(key).split(':');
          if (parts[1]) ids.add(parts[1]);
        }
      }
      const n = ids.size;
      return `${n} sucursal${n === 1 ? '' : 'es'} con carga`;
    },

    get esBorradorEditable() {
      const e = String(this.draftEstado || 'borrador');
      return e === 'borrador' || e === 'confirmando';
    },

    get puedeAnularBorrador() {
      return Boolean(this.draftId && this.esBorradorEditable && this.urls.anular);
    },

    get etiquetaEstadoDraft() {
      if (!this.draftId) return '';
      // PED origen no editable: no confundir con borrador activo.
      if (this.pedidoSoloConsulta) return '';
      const e = String(this.draftEstado || 'borrador');
      const map = {
        borrador: 'Borrador',
        confirmando: 'Confirmando',
        confirmado: 'Confirmado',
        archivado: 'Archivado',
        anulado: 'Anulado',
      };
      const label = map[e] || 'Borrador';
      return `${label} #${this.draftId}`;
    },

    /** Clase de color del badge de estado en el hero (oscuro). */
    get claseEstadoDraft() {
      const e = String(this.draftEstado || 'borrador');
      const map = {
        borrador: 'pedidos-badge-estado--borrador',
        confirmando: 'pedidos-badge-estado--confirmando',
        confirmado: 'pedidos-badge-estado--confirmado',
        archivado: 'pedidos-badge-estado--archivado',
        anulado: 'pedidos-badge-estado--anulado',
      };
      return map[e] || map.borrador;
    },

    /** Texto de carga: pedido vs borrador (no confundir PED con draft). */
    get abriendoMensaje() {
      return this.abriendoEsPedido ? 'Abriendo pedido…' : 'Abriendo borrador…';
    },

    /** Etiqueta hero del PED cargado: «PED 0001-… · Pendiente». */
    get etiquetaPedidoCargado() {
      if (!this.pedidoCodMov) return '';
      const nro = this.pedidoNro
        ? `PED ${this.pedidoNro}`
        : `PED #${this.pedidoCodMov}`;
      const est = String(this.pedidoEstado || '').trim();
      return est ? `${nro} · ${est}` : nro;
    },

    /**
     * Color del badge PED según estado MySQL (paridad visual con OrderShell /
     * compra_mayorista_pedido).
     */
    get clasePedidoEstado() {
      const raw = String(this.pedidoEstado || '').trim().toLowerCase();
      const map = {
        pendiente: 'pedidos-badge-estado--ped-pendiente',
        'en preparación': 'pedidos-badge-estado--ped-preparacion',
        'en preparacion': 'pedidos-badge-estado--ped-preparacion',
        preparado: 'pedidos-badge-estado--ped-preparado',
        'en remito': 'pedidos-badge-estado--ped-remito',
        parcial: 'pedidos-badge-estado--ped-remito',
        cerrado: 'pedidos-badge-estado--ped-facturado',
        facturado: 'pedidos-badge-estado--ped-facturado',
        anulado: 'pedidos-badge-estado--anulado',
      };
      return map[raw] || 'pedidos-badge-estado--ped-otro';
    },

    // ── Pedido simple: título, consulta/edición y acciones hero ──
    get tituloPantalla() {
      return this.modoSimple ? 'Pedido simple' : 'Pedido masivo por sucursales';
    },
    /** PED cargado que NO es editable (en producción/anulado) → solo lectura. */
    get pedidoSoloConsulta() {
      return Boolean(this.modoSimple && this.pedidoCodMov && !this.pedidoEditable);
    },
    /** La matriz acepta ediciones (borrador editable, no consulta, no readonly). */
    get matrizEditable() {
      return this.esBorradorEditable && !this.pedidoSoloConsulta && !this.readonly;
    },
    get puedeConfirmar() {
      return Boolean(this.draftId && this.matrizEditable);
    },
    get puedeToggleCatalogo() {
      return Boolean(this.matrizEditable && this.idCliente && this.draftId);
    },
    get puedeImportarExcel() {
      return Boolean(this.matrizEditable && this.draftId && this.urls.importar);
    },
    get cantidadSeleccionados() {
      return Object.keys(this.articulosSeleccionados || {}).length;
    },
    /** Un PED está cargado o consultado → habilita PDF / repetir / mail. */
    get pedidoCargado() {
      return Boolean(this.modoSimple && this.pedidoCodMov);
    },
    /** Tras confirmar (o PED en solo consulta): ofrecer Nuevo como en el Hub. */
    get mostrarBotonNuevo() {
      return (
        this.pedidoSoloConsulta
        || String(this.draftEstado || '') === 'confirmado'
      );
    },
    get pdfPedidoUrl() {
      if (!this.pedidoCodMov || !this.urls.pdf_tpl) return '#';
      const t = String(this.urls.pdf_tpl);
      if (t.includes('cod_mov=')) return t.replace(/cod_mov=\d+/, `cod_mov=${this.pedidoCodMov}`);
      return t.replace(/\/0(\/|$)/, `/${this.pedidoCodMov}$1`);
    },

    init() {
      const el = document.getElementById('pm-bootstrap');
      const boot = el ? JSON.parse(el.textContent) : {};
      this.urls = boot.urls || {};
      this.modoSimple = String(boot.modo || '') === 'simple';
      this.idDomicilioInicial = boot.id_domicilio || null;
      this.readonly = Boolean(boot.readonly);
      this.aprobacionPedidosActiva = Boolean(boot.aprobacion_pedidos_activa);
      try {
        const guardado = sessionStorage.getItem('pm-contexto-abierto');
        if (guardado === '1') this.contextoAbierto = true;
      } catch { /* sessionStorage no disponible */ }
      this.cargarCarteraVendedor();
      this.buscarClientes();
      // Prioridad: abrir PED (cod_mov) → recuperar borrador → nuevo simple.
      if (boot.cod_mov) {
        this.modoSimple = true;
        const consulta = Boolean(
          boot.consulta || (boot.readonly && boot.cod_mov),
        );
        this.abrirPedido(boot.cod_mov, !!boot.repetir, consulta);
      } else if (boot.draft_id) {
        this.abrirDraft(boot.draft_id);
      }
      // Al hacer scroll de la matriz, cerrar el dropdown (evita menú desfasado).
      this._onMatrixScrollCloseArt = () => {
        if (this.panelArt) this.cerrarPanelArt();
      };
      this.$watch('draftId', () => {
        this.$nextTick(() => {
          this._bindMatrixScrollSync();
          this._syncTotalesBarLayout();
        });
      });
      this.$watch(
        () => (this.articulos || []).length,
        () => this.$nextTick(() => this._syncTotalesBarLayout()),
      );
      this.$watch(
        () => (this.sucursales || []).length,
        () => this.$nextTick(() => this._syncTotalesBarLayout()),
      );
      this.$watch('mostrarTotalesPorSucursal', (on) => {
        if (on) this.$nextTick(() => this._syncTotalesBarLayout());
      });
      if (typeof ResizeObserver !== 'undefined') {
        this._pmTotalesRo = new ResizeObserver(() => this._syncTotalesBarLayout());
        this.$nextTick(() => {
          const mid = this.$refs.pmZoneMid;
          if (mid) this._pmTotalesRo.observe(mid);
        });
      }
      this.$nextTick(() => {
        this._bindMatrixScrollSync();
        this._syncTotalesBarLayout();
      });
    },
    /**
     * Sincroniza el scroll vertical del shell de 3 zonas (desktop): la zona media
     * (`pmZoneMid`) es el único contenedor con overflow-y; su `scrollTop` se espeja
     * a las zonas fijas izquierda/derecha (overflow oculto) para mantener las filas
     * alineadas. La rueda del ratón sobre las zonas fijas se reenvía a la zona media.
     * El scroll horizontal ocurre solo en la zona media (solo sucursales).
     */
    _bindMatrixScrollSync() {
      const mid = this.$refs.pmZoneMid;
      if (!mid || mid._pmSyncBound) return;
      const left = this.$refs.pmZoneLeft;
      const right = this.$refs.pmZoneRight;
      const mirror = () => {
        const t = mid.scrollTop;
        if (left) left.scrollTop = t;
        if (right) right.scrollTop = t;
        const totMid = this.$refs.pmTotalesMid;
        if (totMid) totMid.scrollLeft = mid.scrollLeft;
      };
      mid.addEventListener('scroll', () => {
        mirror();
        this._onMatrixScrollCloseArt();
      }, { passive: true });
      // Reenvía la rueda vertical sobre las zonas fijas hacia la zona media,
      // excepto cuando el puntero está sobre el dropdown de artículos (debe scrollear el listbox).
      const fwdWheel = (e) => {
        if (!e.deltaY) return;
        if (e.target && typeof e.target.closest === 'function'
            && e.target.closest('.pm-art-dropdown')) {
          return;
        }
        mid.scrollTop += e.deltaY;
        mirror();
        e.preventDefault();
      };
      if (left) left.addEventListener('wheel', fwdWheel, { passive: false });
      if (right) right.addEventListener('wheel', fwdWheel, { passive: false });
      mid._pmSyncBound = true;
      this.$nextTick(() => this._syncTotalesBarLayout());
    },
    /**
     * Alinea la barra de totales con anchos reales del shell (thead / zonas).
     * Necesario porque la zona media estira columnas (`min-width:100%`) y puede
     * tener scrollbar vertical que reduce el clientWidth.
     */
    _syncTotalesBarLayout() {
      if (!this.mostrarTotalesPorSucursal) return;
      const left = this.$refs.pmZoneLeft;
      const mid = this.$refs.pmZoneMid;
      const right = this.$refs.pmZoneRight;
      const bar = this.$refs.pmTotalesBar;
      const totMid = this.$refs.pmTotalesMid;
      const totInner = this.$refs.pmTotalesMidInner;
      if (!bar || !mid) return;

      const leftEl = bar.querySelector('.pm-totales-left');
      const rightEl = bar.querySelector('.pm-totales-right');
      if (left && leftEl) leftEl.style.width = `${left.offsetWidth}px`;
      if (right && rightEl) rightEl.style.width = `${right.offsetWidth}px`;

      const ths = mid.querySelectorAll('thead th.pm-c-suc');
      const cells = totInner ? totInner.querySelectorAll('.pm-totales-suc') : [];
      let innerW = 0;
      ths.forEach((th, i) => {
        const w = th.getBoundingClientRect().width;
        innerW += w;
        const cell = cells[i];
        if (!cell) return;
        cell.style.flex = `0 0 ${w}px`;
        cell.style.width = `${w}px`;
        cell.style.minWidth = `${w}px`;
        cell.style.maxWidth = `${w}px`;
      });
      if (totInner && innerW > 0) totInner.style.width = `${innerW}px`;
      if (totMid) totMid.scrollLeft = mid.scrollLeft;
    },
    abrirPanelCli() { this.panelCli = true; },
    cerrarPanelCli() { this.panelCli = false; },
    abrirPanelSuc() {
      if (!this.clienteSel) return;
      this.panelSuc = true;
      if (!this.opcionesSucursal.length && !this.cargandoSuc) {
        this.cargarOpcionesSucursal(this.clienteSel);
      }
    },
    cerrarPanelSuc() { this.panelSuc = false; },
    _etiquetaSucursal(s) {
      return String(
        s?.etiqueta || s?.nombre || s?.NroCalle || s?.nro || s?.id_cliente_domicilio || '',
      ).trim();
    },
    get sucursalesFiltradas() {
      const q = String(this.qSucursal || '').trim().toLowerCase();
      if (!q) return this.opcionesSucursal;
      return this.opcionesSucursal.filter((s) => this._etiquetaSucursal(s).toLowerCase().includes(q));
    },
    _aplicarSucursal(s) {
      if (!s) return;
      this.sucursalSel = s;
      this.qSucursal = this._etiquetaSucursal(s);
      this.idDomicilioInicial = Number(s.id_cliente_domicilio);
    },
    async cargarOpcionesSucursal(idCliente) {
      if (!this.urls.sucursales || !idCliente) {
        this.opcionesSucursal = [];
        return [];
      }
      const id = String(idCliente);
      this.cargandoSuc = true;
      try {
        const data = await this.getJson(
          `${this.urls.sucursales}?id_cliente=${encodeURIComponent(id)}`,
        );
        if (String(this.clienteSel || '') !== id) return [];
        if (!data.ok) {
          this.mostrarAviso(data.error || 'No se pudieron cargar las sucursales.', 'error');
          this.opcionesSucursal = [];
          return [];
        }
        this.opcionesSucursal = this._ordenarSucursalesAsc(data.sucursales || []);
        this.idxSuc = 0;
        return this.opcionesSucursal;
      } finally {
        if (String(this.clienteSel || '') === id) this.cargandoSuc = false;
      }
    },
    async elegirSucursal(s) {
      this._aplicarSucursal(s);
      this.cerrarPanelSuc();
      await this.abrirCliente();
    },
    moverSelSuc(delta) {
      const items = this.sucursalesFiltradas;
      if (!items.length) return;
      this.idxSuc = (this.idxSuc + delta + items.length) % items.length;
    },
    elegirResaltadoSuc() {
      const s = this.sucursalesFiltradas[this.idxSuc];
      if (s) this.elegirSucursal(s);
    },
    _aplicarListaDesdeCliente(c) {
      const lp = c?.lista_precio || c?.listaPrecio;
      if (!lp) return;
      if (lp && typeof lp === 'object') {
        this.listaPrecio = String(lp.nombre || lp.name || (lp.codigo != null ? `Lista ${lp.codigo}` : '')).trim();
      } else {
        this.listaPrecio = String(lp || '').trim();
      }
      const pdf = c?.lista_precio_pdf_url || c?.lista_precios_pdf || c?.listaPrecioPdf;
      if (pdf) this.listaPrecioPdfUrl = String(pdf).trim();
    },
    /** Nombre visible del cliente sin sufijo «(cod: N)». */
    _nombreClienteVisible(raw) {
      const s = String(raw || '').trim();
      if (!s) return '';
      return s.replace(/\s*\(cod:\s*\d+\)\s*$/i, '').trim() || s;
    },
    async elegirCliente(c) {
      const id = String(c.id_cliente);
      if (this.abriendo) return;
      if (!this.modoSimple && this.draftId && String(this.idCliente) === id && this.clienteSel === id) return;
      this.clienteSel = id;
      const nombre = this._nombreClienteVisible(c.nombre || c.etiqueta || '');
      this.clienteNombre = nombre;
      this.qCliente = nombre;
      this._aplicarListaDesdeCliente(c);
      this.cerrarPanelCli();
      if (this.modoSimple) {
        this.opcionesSucursal = [];
        this.sucursalSel = null;
        this.qSucursal = '';
        this.idDomicilioInicial = null;
        const sucursales = await this.cargarOpcionesSucursal(id);
        if (!sucursales.length) {
          this.mostrarAviso('Este cliente no tiene sucursales activas.', 'error');
          return;
        }
        if (sucursales.length === 1) {
          this._aplicarSucursal(sucursales[0]);
          await this.abrirCliente();
          return;
        }
        this.panelSuc = true;
        return;
      }
      await this.abrirCliente();
    },
    moverSelCli(delta) {
      if (!this.clientes.length) return;
      this.idxCli = (this.idxCli + delta + this.clientes.length) % this.clientes.length;
    },
    elegirResaltadoCli() {
      if (this.clientes[this.idxCli]) this.elegirCliente(this.clientes[this.idxCli]);
    },
    csrf() {
      const m = document.cookie.match(/csrftoken=([^;]+)/);
      return m ? decodeURIComponent(m[1]) : '';
    },
    money(v) {
      const n = Number(v || 0);
      return `$${n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    },
    /**
     * Feedback operativo en modal (fuente de verdad MPR: `mprShowAviso`).
     * `tipo`: 'error' (default) | 'success' | 'warning' | 'info'. `titulo` opcional.
     */
    mostrarAviso(texto, tipo, titulo) {
      if (typeof window.mprShowAviso === 'function') {
        if (titulo) {
          window.mprShowAviso('', { tipo: tipo || 'error', titulo, mensaje: texto || '' });
        } else {
          window.mprShowAviso(texto || '', tipo || 'error');
        }
        return;
      }
      window.alert(texto || '');
    },
    async getJson(url, options = {}) {
      const r = await fetch(url, {
        credentials: 'same-origin',
        headers: { 'Accept': 'application/json' },
        signal: options.signal,
      });
      return r.json();
    },
    async postJson(url, body) {
      const r = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-CSRFToken': this.csrf(),
        },
        body: JSON.stringify(body),
      });
      const data = await r.json().catch(() => ({}));
      return { status: r.status, data };
    },
    abrirImportarExcel() {
      this.importArchivo = null;
      this.importNombreArchivo = '';
      this.importErrores = [];
      this.importErroresTotal = 0;
      this.abrirDialogo('masivo_importar', {
        titulo: 'Importar pedido',
        mensaje: 'Solo completá cantidades (packs) en la plantilla de este cliente. Hay una fila por color/SKU. El archivo reemplaza el borrador. No uses una planilla de otro cliente.',
        confirmarTexto: 'Importar y reemplazar',
        cancelarTexto: 'Cancelar',
      });
    },
    onSeleccionarExcel(ev) {
      const f = ev?.target?.files?.[0] || null;
      this.importArchivo = f;
      this.importNombreArchivo = f ? f.name : '';
      this.importErrores = [];
      this.importErroresTotal = 0;
    },
    descargarPlantillaExcel() {
      if (!this.draftId || !this.urls.plantilla_excel) return;
      const u = `${this.urls.plantilla_excel}?draft_id=${encodeURIComponent(this.draftId)}`;
      window.location.href = u;
    },
    async ejecutarImportarExcel() {
      if (!this.draftId || !this.urls.importar || !this.importArchivo || this.importando) return;
      this.importando = true;
      this.esperaOperacion = true;
      this.esperaMensaje = 'Importando Excel…';
      this.importErrores = [];
      try {
        const fd = new FormData();
        fd.append('draft_id', String(this.draftId));
        fd.append('archivo', this.importArchivo);
        const r = await fetch(this.urls.importar, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'X-CSRFToken': this.csrf(),
          },
          body: fd,
        });
        const data = await r.json().catch(() => ({}));
        if (!data.ok) {
          this.importErrores = Array.isArray(data.errores) ? data.errores : [];
          this.importErroresTotal = Number(data.errores_total || this.importErrores.length);
          if (!this.importErrores.length) {
            this.mostrarAviso(data.error || 'No se pudo importar el Excel.', 'error');
          }
          return;
        }
        this.cerrarDialogo();
        if (data.matriz) this.aplicarMatriz(data.matriz);
        this.catalogoDesplegado = false;
        this.mostrarAviso(data.message || 'Pedido importado.', 'success');
      } catch (e) {
        this.mostrarAviso('No se pudo importar el Excel.', 'error');
      } finally {
        this.importando = false;
        this.esperaOperacion = false;
      }
    },
    /** Lee NDJSON línea a línea desde un POST (confirmación masiva con progreso). */
    async postNdjsonStream(url, body, onEvent) {
      const r = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          // Preferimos */*; la vista también declara renderer NDJSON como defensa.
          // La respuesta sigue siendo NDJSON vía StreamingHttpResponse.
          'Accept': '*/*',
          'X-CSRFToken': this.csrf(),
        },
        body: JSON.stringify(body),
      });
      const ct = (r.headers.get('content-type') || '').toLowerCase();
      if (!r.ok && !ct.includes('ndjson')) {
        const data = await r.json().catch(() => ({}));
        return { status: r.status, fin: data };
      }
      if (!r.body) {
        const data = await r.json().catch(() => ({}));
        return { status: r.status, fin: data };
      }
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let fin = null;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          let ev;
          try {
            ev = JSON.parse(trimmed);
          } catch {
            continue;
          }
          if (typeof onEvent === 'function') onEvent(ev);
          if (ev.event === 'fin') fin = ev;
        }
      }
      const rest = buffer.trim();
      if (rest) {
        try {
          const ev = JSON.parse(rest);
          if (typeof onEvent === 'function') onEvent(ev);
          if (ev.event === 'fin') fin = ev;
        } catch { /* línea parcial ignorada */ }
      }
      return { status: r.status, fin };
    },
    aplicarMatriz(m) {
      this.draftId = m.draft_id;
      this.draftEstado = m.estado || 'borrador';
      this.idCliente = m.id_cliente;
      this.clienteSel = String(m.id_cliente || '');
      this.clienteNombre = this._nombreClienteVisible(m.nombre_cliente || this.clienteNombre || '');
      this.qCliente = this.clienteNombre;
      if (m.cabecera) {
        this.puedeEditarCabecera = !!m.cabecera.puede_editar;
        this.puedeEditarLista = m.cabecera.puede_editar_lista != null
          ? !!m.cabecera.puede_editar_lista
          : this.puedeEditarCabecera;
        this.puedeEditarCondicion = m.cabecera.puede_editar_condicion != null
          ? !!m.cabecera.puede_editar_condicion
          : this.puedeEditarCabecera;
        this.puedeEditarVencimiento = m.cabecera.puede_editar_vencimiento != null
          ? !!m.cabecera.puede_editar_vencimiento
          : this.puedeEditarCabecera;
        this.puedeEditarDescPie = m.cabecera.puede_editar_descuento_pie != null
          ? !!m.cabecera.puede_editar_descuento_pie
          : this.puedeEditarCabecera;
        this.puedeEditarDescRenglon = m.cabecera.puede_editar_descuento_renglon != null
          ? !!m.cabecera.puede_editar_descuento_renglon
          : this.puedeEditarCabecera;
        this.cabecera = cabeceraConDisplay(m.cabecera);
        this.listaId = Number(this.cabecera?.lista_id || m.lista_id || 1);
        this._cargarCatalogosCabecera();
      }
      // Lista de precios en solo lectura (nombre + PDF cuando el backend los provea).
      const lp = m.lista_precio || m.listaPrecio || '';
      if (lp && typeof lp === 'object') {
        this.listaPrecio = String(lp.nombre || lp.name || (lp.codigo != null ? `Lista ${lp.codigo}` : '')).trim();
      } else {
        this.listaPrecio = String(lp || '').trim();
      }
      this.listaPrecioPdfUrl = String(
        m.lista_precio_pdf_url || m.lista_precios_pdf || m.listaPrecioPdf || '',
      ).trim();
      this.listaId = Number(m.lista_id || 1);
      this.sucursales = this._ordenarSucursalesAsc(m.sucursales || []);
      this.articulos = (m.articulos || []).map(a => ({
        id_articulo: a.id_articulo,
        id_manual: a.id_manual || a.codigo || '',
        codigo: a.codigo || a.id_manual || '',
        nombre: a.nombre || a.descripcion || '',
        descripcion: a.descripcion || a.nombre || '',
        // Precio real del motor de precios para la lista del cliente (REQ-MAS-07).
        precio_unitario_neto: Number(a.precio_unitario_neto || a.precio_lista1 || 0),
        precio_lista1: Number(a.precio_lista1 || 0),
        porcentaje_descuento: Number(a.porcentaje_descuento || 0),
        alicuota_iva: Number(a.alicuota_iva ?? 21),
        multiplo_cantidad_vta: Number(a.multiplo_cantidad_vta || 0),
        multiplo_empaque: Number(a.multiplo_empaque || multiploEmpaque(a)),
        stock_disponible_packs: a.stock_disponible_packs != null && a.stock_disponible_packs !== undefined
          ? Number(a.stock_disponible_packs)
          : null,
      }));
      this.celdas = m.celdas || {};
      this.celdasInvalidas = {};
      // Descuentos por fila (REQ-MAS-08/09): mapa id_articulo → % renglón efectivo.
      this.descuentosFila = m.descuentos_fila || {};
      this.descPiePct = Number(m.desc_pie_pct || 0);
      this.ultimoError = m.ultimo_error || {};
      // Modo simple + metadata de origen (REQ-PSU-02/03) y crédito hero.
      if (String(m.modo || '') === 'simple') this.modoSimple = true;
      if (this.modoSimple && this.sucursales[0]) {
        this._aplicarSucursal(this.sucursales[0]);
        if (!this.opcionesSucursal.length && this.idCliente) {
          this.cargarOpcionesSucursal(this.idCliente);
        }
      }
      this.codMovOrigen = m.cod_mov_origen || null;
      // Revalidar PED origen al recuperar borrador (puede haber dejado de ser Pendiente).
      const origen = m.origen_pedido || null;
      if (this.codMovOrigen && origen) {
        this.pedidoCodMov = origen.cod_mov || this.codMovOrigen;
        this.pedidoNro = String(origen.nro_comprobante || this.pedidoNro || '').trim();
        this.pedidoEstado = String(origen.estado || '').trim();
        this.puedeAnularPedido = !!origen.puede_anular;
        this.pedidoEditable = origen.editable !== false && !!origen.puede_anular;
        if (!this.puedeAnularPedido) {
          this.mostrarAviso(
            `El PED ${this.pedidoNro || this.pedidoCodMov} está en «${this.pedidoEstado || 'otro estado'}» y ya no se puede anular. Solo consulta; usá «Repetir» para un pedido nuevo.`,
            'warning',
            'Pedido no editable',
          );
        }
        // URL refleja consulta del PED (no un borrador “activo” confuso).
        if (this.draftId && this.pedidoCodMov) {
          history.replaceState(
            null,
            '',
            `?modo=simple&draft=${this.draftId}&cod_mov=${this.pedidoCodMov}`,
          );
        }
      }
      if (m.credito) this.credito = m.credito;
      if (!this.clienteNombre) {
        const c = this.clientes.find(x => String(x.id_cliente) === String(this.idCliente));
        if (c) {
          this.clienteNombre = this._nombreClienteVisible(c.nombre || c.etiqueta || '');
          this.qCliente = this.clienteNombre;
        }
      }
      this.marcarTotalesEstimados();
      this.$nextTick(() => this._syncTotalesBarLayout());
    },
    async _cargarCatalogosCabecera() {
      if (!this.urls.condiciones_venta && !this.urls.lista_precio) return;
      const qCv = this.cabecera?.id_condventa != null
        ? `?id_condventa=${this.cabecera.id_condventa}`
        : '';
      const qLista = this.cabecera?.lista_id != null
        ? `?cod_lista_cliente=${this.cabecera.lista_id}`
        : '';
      const tasks = [];
      if (this.urls.condiciones_venta) {
        tasks.push(this.getJson(`${this.urls.condiciones_venta}${qCv}`));
      }
      if (this.urls.lista_precio) {
        tasks.push(this.getJson(`${this.urls.lista_precio}${qLista}`));
      }
      const results = await Promise.all(tasks);
      let i = 0;
      if (this.urls.condiciones_venta) {
        const data = results[i++];
        if (Array.isArray(data)) this.condicionesVenta = data;
      }
      if (this.urls.lista_precio) {
        const data = results[i++];
        if (Array.isArray(data)) this.listasPrecio = data;
      }
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
        if (!this.puedeEditarVencimiento) {
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
      if (campo === 'vencimiento' && !this.puedeEditarVencimiento) {
        this._recalcVencimientoDisplay();
      }
    },
    /**
     * Cambio desde `input type="date"` (valor ISO ligado a `cabecera[campo]`).
     * Sincroniza el espejo `*_display` (dd/MM/yyyy) y reutiliza la lógica
     * existente (recalcular vencimiento) vía `onCabeceraFechaChange`.
     */
    onCabeceraFechaIso(campo) {
      if (!this.cabecera) return;
      const map = {
        fecha_pedido: 'fecha_pedido_display',
        fecha_entrega: 'fecha_entrega_display',
        vencimiento: 'vencimiento_display',
      };
      this.cabecera[map[campo]] = isoToDisplay(this.cabecera[campo]) || '';
      this.onCabeceraFechaChange(campo);
    },
    onCabeceraCondicionChange() {
      if (!this.cabecera || !this.puedeEditarCondicion) return;
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
      if (!this.cabecera || !this.puedeEditarLista) return;
      this.listaId = Number(this.cabecera.lista_id || 1);
      // Totales: el estimado FE usa precios ya en memoria; revalidar con el botón
      // «Validar totales» o al confirmar (lista nueva implica reabrir/reprecio al refrescar).
    },
    /** Expande/compacta la sección «Contexto comercial» (persistido por sesión). */
    toggleContexto() {
      this.contextoAbierto = !this.contextoAbierto;
      try {
        sessionStorage.setItem('pm-contexto-abierto', this.contextoAbierto ? '1' : '0');
      } catch { /* sessionStorage no disponible */ }
    },
    _payloadCabecera() {
      return payloadCabeceraApi(this.cabecera, {
        puedeEditar: this.puedeEditarCabecera,
        puedeEditarLista: this.puedeEditarLista,
        puedeEditarCondicion: this.puedeEditarCondicion,
        puedeEditarVencimiento: this.puedeEditarVencimiento,
      });
    },
    async buscarClientes() {
      if (!this.urls.clientes) return;
      this.cargandoCli = true;
      const data = await this.getJson(this.urls.clientes + '?q=' + encodeURIComponent(this.qCliente || ''));
      this.cargandoCli = false;
      if (data.ok) {
        this.clientes = data.items || [];
        this.idxCli = 0;
      } else {
        if (data.error) this.mostrarAviso(data.error, 'error');
        this.clientes = [];
      }
    },
    async abrirCliente() {
      if (!this.clienteSel) return;
      if (this.abriendo) return;
      if (this.modoSimple && !this.idDomicilioInicial) {
        const sucursales = this.opcionesSucursal.length
          ? this.opcionesSucursal
          : await this.cargarOpcionesSucursal(this.clienteSel);
        if (!sucursales.length) {
          this.mostrarAviso('Este cliente no tiene sucursales activas.', 'error');
        } else {
          this.mostrarAviso('Elegí la sucursal del pedido.', 'info');
          this.panelSuc = sucursales.length > 1;
        }
        return;
      }
      const domicilioActual = this.sucursales[0]?.id_cliente_domicilio;
      if (
        this.draftId
        && String(this.idCliente) === String(this.clienteSel)
        && (!this.modoSimple || Number(domicilioActual) === Number(this.idDomicilioInicial))
      ) return;
      this.abriendoEsPedido = false;
      this.abriendo = true; this.error = ''; this.mensajeOk = '';
      const body = { id_cliente: Number(this.clienteSel) };
      if (this.modoSimple) {
        body.modo = 'simple';
        body.id_domicilio = Number(this.idDomicilioInicial);
      }
      const { data } = await this.postJson(this.urls.abrir, body);
      this.abriendo = false;
      if (!data.ok) { this.mostrarAviso(data.error || 'No se pudo abrir.', 'error'); return; }
      // Cliente nuevo elegido a mano: no arrastra PED cargado previo.
      this._resetPedidoCargado();
      this.aplicarMatriz(data.matriz);
      const c = this.clientes.find(x => String(x.id_cliente) === String(this.clienteSel));
      if (c) {
        this.clienteNombre = this._nombreClienteVisible(c.nombre || c.etiqueta || this.clienteNombre);
        this.qCliente = this.clienteNombre;
      }
      this._replaceHistoryDraft();
    },
    async abrirDraft(id) {
      this.abriendoEsPedido = false;
      this.abriendo = true; this.error = '';
      const body = { draft_id: Number(id) };
      if (this.modoSimple) body.modo = 'simple';
      if (this.readonly) body.readonly = true;
      const { data } = await this.postJson(this.urls.abrir, body);
      this.abriendo = false;
      if (!data.ok) { this.mostrarAviso(data.error || 'No se pudo recuperar el borrador.', 'error'); return; }
      this.aplicarMatriz(data.matriz);
    },
    /** Reemplaza la URL preservando modo=simple + draft para F5/bookmark. */
    _replaceHistoryDraft() {
      if (!this.draftId) return;
      const modoQ = this.modoSimple ? 'modo=simple&' : '';
      const roQ = this.readonly ? '&readonly=1' : '';
      history.replaceState(null, '', `?${modoQ}draft=${this.draftId}${roQ}`);
    },
    _resetPedidoCargado() {
      this.pedidoCodMov = null;
      this.pedidoNro = '';
      this.pedidoEstado = '';
      this.pedidoEditable = true;
      this.pedidoRepetido = false;
      this.puedeAnularPedido = false;
      this.emailCliente = '';
      this.advertenciasCarga = [];
    },
    /**
     * Carga un PED (``cod_mov``) en un borrador simple. Con ``repetir`` copia las
     * líneas a un borrador nuevo sin anular el origen (REQ-PSU-07/CAR-008).
     */
    async abrirPedido(cod, repetir = false, consulta = false) {
      const codMov = Number(cod);
      if (!Number.isFinite(codMov) || codMov <= 0 || !this.urls.abrir_pedido) return;
      this.abriendoEsPedido = true;
      this.abriendo = true;
      this.error = '';
      this.mensajeOk = '';
      const body = {
        cod_mov: codMov,
        repetir: !!repetir,
      };
      if (consulta) body.consulta = true;
      const { data } = await this.postJson(this.urls.abrir_pedido, body);
      this.abriendo = false;
      if (!data.ok) {
        this.mostrarAviso(data.error || 'No se pudo cargar el pedido.', 'error');
        return;
      }
      this.modoSimple = true;
      this.aplicarMatriz(data.matriz);
      this._aplicarPedidoInfo(data.pedido, data.advertencias);
      const esConsulta = consulta || !!(data.pedido && data.pedido.consulta);
      if (this.draftId) {
        const codQ = this.pedidoCodMov ? `&cod_mov=${this.pedidoCodMov}` : '';
        if (esConsulta) {
          history.replaceState(null, '', `?modo=simple${codQ}&consulta=1`);
        } else {
          history.replaceState(null, '', `?modo=simple&draft=${this.draftId}${codQ}`);
        }
      }
    },
    _aplicarPedidoInfo(info, advertencias) {
      const p = info || {};
      this.pedidoCodMov = p.cod_mov || null;
      this.pedidoNro = String(p.nro_comprobante || '').trim();
      this.pedidoEstado = String(p.estado || '').trim();
      this.pedidoEditable = p.editable !== false;
      this.pedidoRepetido = !!p.repetido;
      this.puedeAnularPedido = !!p.puede_anular;
      this.emailCliente = String(p.email_cliente || '').trim();
      this.advertenciasCarga = Array.isArray(advertencias) ? advertencias : [];
      if (p.repetido) {
        this.mostrarAviso('Pedido copiado a un borrador nuevo. Revisá y confirmá para generar un PED.', 'success');
      } else if (this.pedidoSoloConsulta) {
        // Badge del hero ya muestra nro + estado; aviso corto sin repetir el PED.
        this.mostrarAviso('Pedido en solo lectura.', 'info');
      }
      // Avisos de conversión/redondeo al cargar el PED (prioridad sobre el info anterior).
      if (this.advertenciasCarga.length) {
        this.mostrarAviso(this.advertenciasCarga.join('\n'), 'warning', 'Avisos al cargar el pedido');
      }
    },
    celda(idArt, idDom) {
      return this.celdas[idArt + ':' + idDom] || '';
    },
    celdaInvalida(idArt, idDom) {
      return !!this.celdasInvalidas[idArt + ':' + idDom];
    },
    _marcarCeldaInvalida(idArt, idDom, invalido) {
      const key = idArt + ':' + idDom;
      if (invalido) this.celdasInvalidas[key] = true;
      else delete this.celdasInvalidas[key];
    },
    _artPorId(idArt) {
      return (this.articulos || []).find(
        (a) => String(a.id_articulo) === String(idArt),
      );
    },
    _escanearInfraccionesMultiplo() {
      const out = [];
      for (const art of this.articulos || []) {
        const multiplo = multiploEmpaque(art);
        if (multiplo <= 1) continue;
        for (const su of this.sucursales || []) {
          const idDom = su.id_cliente_domicilio;
          const qty = parseFloat(this.celda(art.id_articulo, idDom));
          if (isNaN(qty) || qty <= 0) continue;
          if (cantidadOk(qty, multiplo)) continue;
          out.push({
            id_articulo: art.id_articulo,
            id_cliente_domicilio: idDom,
            codigo: art.codigo || art.id_manual || '',
            nombre: art.nombre || art.descripcion || '',
            cantidad: qty,
            multiplo_empaque: multiplo,
          });
          this._marcarCeldaInvalida(art.id_articulo, idDom, true);
        }
      }
      return out;
    },
    _lineaInfraccionMultiplo(item) {
      const cod = item.codigo ? `${item.codigo} — ` : '';
      const nom = item.nombre || `Art. ${item.id_articulo}`;
      return `${cod}${nom}: ${item.cantidad} (empaque ${item.multiplo_empaque})`;
    },
    _mostrarModalMultiploCelda(idArt, idDom, qty, multiplo, onClose) {
      const art = this._artPorId(idArt);
      const cod = (art && (art.codigo || art.id_manual)) || '';
      const nom = (art && (art.nombre || art.descripcion)) || `Art. ${idArt}`;
      const sugerencia = sugerenciaMultiplo(qty, multiplo);
      const lineas = [
        `${cod ? cod + ' — ' : ''}${nom}`,
        `Cantidad ingresada: ${qty}`,
        `Unidad de empaquetado: ${multiplo}`,
      ];
      if (sugerencia) lineas.push(sugerencia);
      this.abrirDialogo('aviso', {
        titulo: 'Cantidad inválida',
        mensaje: lineas.join('\n'),
        confirmarTexto: 'Entendido',
        variante: 'warning',
        onConfirm: () => {
          if (typeof onClose === 'function') onClose();
          else {
            const el = this._qtyInputVisible(idArt, idDom);
            if (el) {
              el.focus();
              el.select && el.select();
            }
          }
        },
      });
      const el = this._qtyInputVisible(idArt, idDom);
      if (el) this._dialogFocoPrevio = el;
    },
    _mostrarModalListaInfracciones(infracciones) {
      const lineas = infracciones.map((it) => this._lineaInfraccionMultiplo(it));
      this.abrirDialogo('aviso', {
        titulo: 'Cantidades inválidas',
        mensaje: [
          'Corregí las cantidades antes de continuar. Deben ser múltiplo de la unidad de empaquetado:',
          '',
          ...lineas,
        ].join('\n'),
        confirmarTexto: 'Entendido',
        variante: 'warning',
      });
    },
    fmtPrecio(v) {
      const n = Number(v);
      if (!n && n !== 0) return '—';
      return n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },
    /** Packs enteros/tabular para columna stock (valor > 0). */
    fmtStockPacks(v) {
      if (v == null || v === undefined) return '—';
      const n = Number(v);
      if (Number.isNaN(n)) return '—';
      if (Math.abs(n - Math.round(n)) < 1e-9) {
        return Math.round(n).toLocaleString('es-AR');
      }
      return n.toLocaleString('es-AR', { maximumFractionDigits: 3 });
    },
    /** Sublínea PWA: «stock 12» / «sin stock» / «stock —». */
    stockPacksTexto(art) {
      const v = art?.stock_disponible_packs;
      if (v == null || v === undefined) return 'stock —';
      const n = Number(v);
      if (Number.isNaN(n) || n === 0) return 'sin stock';
      return `stock ${this.fmtStockPacks(v)}`;
    },
    _mapArticuloItem(it) {
      return {
        id_articulo: it.id_articulo || it.IDArt,
        id_manual: it.id_manual || '',
        codigo: it.id_manual || it.codigo || '',
        nombre: it.nombre || it.descripcion || '',
        descripcion: it.nombre || it.descripcion || '',
        precio_unitario_neto: Number(it.precio_unitario_neto || it.precio_lista1 || 0),
        precio_lista1: Number(it.precio_lista1 || 0),
        alicuota_iva: Number(it.alicuota_iva ?? 21),
        stock_disponible_packs: it.stock_disponible_packs != null && it.stock_disponible_packs !== undefined
          ? Number(it.stock_disponible_packs)
          : null,
        multiplo_cantidad_vta: Number(it.multiplo_cantidad_vta || 0),
        multiplo_empaque: Number(it.multiplo_empaque || multiploEmpaque(it)),
      };
    },
    _mapArticuloFila(a) {
      const mapped = this._mapArticuloItem(a);
      return {
        ...mapped,
        id_articulo: Number(mapped.id_articulo),
        porcentaje_descuento: Number(a.porcentaje_descuento || 0),
      };
    },
    _sumaPacksFilaNumerica(idArt) {
      let s = 0;
      for (const su of this.sucursales || []) {
        const v = parseFloat(this.celda(idArt, su.id_cliente_domicilio));
        if (!Number.isNaN(v)) s += v;
      }
      return s;
    },
    _iniciarEspera(msg) {
      this.esperaMensaje = msg || 'Procesando…';
      this.esperaOperacion = true;
    },
    _finEspera() {
      this.esperaOperacion = false;
    },
    _limpiarSeleccionArticulos() {
      this.articulosSeleccionados = {};
    },
    estaSeleccionado(a) {
      const id = this._idArticuloKey(a);
      return !!(id && (this.articulosSeleccionados || {})[id]);
    },
    _idArticuloKey(a) {
      const n = Number(a?.id_articulo ?? a?.IDArt ?? 0);
      return n > 0 ? String(n) : '';
    },
    toggleSeleccionArticulo(a) {
      const id = this._idArticuloKey(a);
      if (!id) return;
      const next = { ...(this.articulosSeleccionados || {}) };
      if (next[id]) delete next[id];
      else next[id] = this._mapArticuloItem(a);
      this.articulosSeleccionados = next;
    },
    /** Espacio: marca/desmarca el ítem resaltado del dropdown. */
    onSpaceArt() {
      if (!this.panelArt || !this.articulosBusqueda.length) return;
      const a = this.articulosBusqueda[this.idxArt];
      if (a) this.toggleSeleccionArticulo(a);
    },
    async toggleCatalogo() {
      if (!this.puedeToggleCatalogo) return;
      if (this.catalogoDesplegado) {
        await this.ocultarTodosSinCantidad();
      } else {
        await this.mostrarTodosCatalogo();
      }
    },
    async _yieldUi() {
      await this.$nextTick();
      await new Promise((r) => setTimeout(r, 30));
    },
    async mostrarTodosCatalogo() {
      if (!this.idCliente || !this.urls.articulos || !this.draftId) return;
      this._iniciarEspera('Procesando…');
      await this._yieldUi();
      try {
        const u = `${this.urls.articulos}?id_cliente=${encodeURIComponent(this.idCliente)}`
          + `&lista_id=${encodeURIComponent(String(this.cabecera?.lista_id || this.listaId || 1))}`
          + '&tam=5000&todos=1';
        const data = await this.getJson(u);
        if (!data.ok) {
          this.mostrarAviso(data.error || 'No se pudo cargar el catálogo.', 'error');
          return;
        }
        if (data.sin_marcas) {
          this.mostrarAviso('No hay marcas asignadas para este cliente en tu territorio.', 'error');
          return;
        }
        const existentes = new Set((this.articulos || []).map((x) => Number(x.id_articulo)));
        const nuevos = [];
        for (const it of data.items || []) {
          const fila = this._mapArticuloFila(it);
          const id = Number(fila.id_articulo);
          if (!id || existentes.has(id)) continue;
          nuevos.push(fila);
          existentes.add(id);
        }
        if (nuevos.length) {
          this.articulos = [...(this.articulos || []), ...nuevos];
          this.marcarTotalesEstimados();
        }
        this.catalogoDesplegado = true;
      } catch {
        this.mostrarAviso('No se pudo cargar el catálogo.', 'error');
      } finally {
        this._finEspera();
      }
    },
    async ocultarTodosSinCantidad() {
      this._iniciarEspera('Procesando…');
      await this._yieldUi();
      try {
        this.articulos = (this.articulos || []).filter(
          (art) => this._sumaPacksFilaNumerica(art.id_articulo) > 0,
        );
        this.marcarTotalesEstimados();
        this.catalogoDesplegado = false;
      } finally {
        this._finEspera();
      }
    },
    async agregarSeleccionados() {
      const items = Object.values(this.articulosSeleccionados || {});
      if (!items.length) return;
      const usarEspera = items.length > 15;
      if (usarEspera) {
        this._iniciarEspera('Procesando…');
        await this._yieldUi();
      }
      try {
        const existentes = new Set((this.articulos || []).map((x) => Number(x.id_articulo)));
        const nuevos = [];
        let ultimoAgregado = null;
        for (const a of items) {
          const id = Number(a.id_articulo || a.IDArt);
          if (!id || existentes.has(id)) continue;
          nuevos.push(this._mapArticuloFila(a));
          existentes.add(id);
          ultimoAgregado = id;
        }
        if (nuevos.length) {
          this.articulos = [...(this.articulos || []), ...nuevos];
          this.marcarTotalesEstimados();
        }
        this.qArt = '';
        this.articulosBusqueda = [];
        this.artBusquedaHecha = false;
        this._limpiarSeleccionArticulos();
        this.cerrarPanelArt();
        if (ultimoAgregado != null) {
          this.focusPrimeraCantidad(ultimoAgregado);
        } else {
          this.focusBuscadorArt();
        }
      } finally {
        if (usarEspera) this._finEspera();
      }
    },
    descFila(idArt) {
      const v = this.descuentosFila[idArt] ?? this.descuentosFila[String(idArt)];
      const n = Number(v);
      return Number.isFinite(n) && n > 0 ? n : '';
    },
    sumaFila(idArt) {
      let s = 0;
      for (const su of this.sucursales) {
        const v = parseFloat(this.celda(idArt, su.id_cliente_domicilio));
        if (!isNaN(v)) s += v;
      }
      return s ? s.toLocaleString('es-AR', { maximumFractionDigits: 3 }) : '—';
    },
    get mostrarTotalesPorSucursal() {
      return (this.articulos || []).length > 1;
    },
    /** Suma packs de todas las líneas para una sucursal. */
    sumaColumnaSucursal(idDom) {
      let s = 0;
      for (const art of this.articulos || []) {
        const v = parseFloat(this.celda(art.id_articulo, idDom));
        if (!isNaN(v)) s += v;
      }
      return s ? s.toLocaleString('es-AR', { maximumFractionDigits: 3 }) : '—';
    },
    /** Suma packs de todas las celdas (para columna Total del pie). */
    sumaTotalMatriz() {
      let s = 0;
      for (const art of this.articulos || []) {
        for (const su of this.sucursales || []) {
          const v = parseFloat(this.celda(art.id_articulo, su.id_cliente_domicilio));
          if (!isNaN(v)) s += v;
        }
      }
      return s ? s.toLocaleString('es-AR', { maximumFractionDigits: 3 }) : '—';
    },
    get alertasUltimoError() {
      const u = this.ultimoError || {};
      return Object.keys(u).map((k) => {
        const v = u[k];
        const texto = typeof v === 'string' ? v : (v && v.error) || JSON.stringify(v);
        if (k === '_lote') return texto;
        return `Sucursal ${k}: ${texto}`;
      });
    },
    async eliminarFila(idArt) {
      const id = Number(idArt);
      if (!id) return;
      this.error = '';
      if (this.catalogoDesplegado) this.catalogoDesplegado = false;
      const quitarLocal = () => {
        this.articulos = this.articulos.filter((a) => Number(a.id_articulo) !== id);
        Object.keys(this.celdas || {}).forEach((k) => {
          if (k.startsWith(`${id}:`)) delete this.celdas[k];
        });
        if (this.descuentosFila) {
          delete this.descuentosFila[id];
          delete this.descuentosFila[String(id)];
        }
        this.marcarTotalesEstimados();
      };
      if (!this.draftId || !this.urls.eliminar_fila) {
        quitarLocal();
        return;
      }
      const { data } = await this.postJson(this.urls.eliminar_fila, {
        draft_id: this.draftId,
        id_articulo: id,
      });
      if (!data.ok) {
        this.mostrarAviso(data.error || 'No se pudo quitar el artículo.', 'error');
        return;
      }
      if (data.matriz) this.aplicarMatriz(data.matriz);
      else quitarLocal();
      this.flashGuardado();
    },
    async onCelda(idArt, idDom, raw) {
      if (this.readonly || !this.matrizEditable) return;
      const key = idArt + ':' + idDom;
      const val = String(raw || '').trim();
      const prev = this.celdas[key] || '';
      this.celdas[key] = val;
      this.marcarTotalesEstimados();
      const qtyNum = val === '' ? 0 : parseFloat(val);
      const art = this._artPorId(idArt);
      const multiplo = multiploEmpaque(art || {});
      if (!isNaN(qtyNum) && qtyNum > 0 && !cantidadOk(qtyNum, multiplo)) {
        this._marcarCeldaInvalida(idArt, idDom, true);
        this.celdas[key] = prev;
        this._mostrarModalMultiploCelda(idArt, idDom, qtyNum, multiplo);
        this.marcarTotalesEstimados();
        return;
      }
      this._marcarCeldaInvalida(idArt, idDom, false);
      const { data } = await this.postJson(this.urls.celda, {
        draft_id: this.draftId,
        id_articulo: idArt,
        id_cliente_domicilio: idDom,
        cantidad_packs: val === '' ? 0 : val,
      });
      if (!data.ok) {
        if (data.code === 'multiplo_empaque' || /empaquetado/i.test(data.error || '')) {
          const mult = Number(data.multiplo_empaque || multiplo);
          this.celdas[key] = prev;
          this._marcarCeldaInvalida(idArt, idDom, true);
          this._mostrarModalMultiploCelda(idArt, idDom, qtyNum, mult);
          this.marcarTotalesEstimados();
          return;
        }
        this.mostrarAviso(data.error || 'Error al guardar', 'error');
        return;
      }
      if (data.celda && data.celda.eliminada) delete this.celdas[key];
      else if (data.celda) this.celdas[key] = data.celda.cantidad_packs;
      this.flashGuardado();
      this.marcarTotalesEstimados();
    },
    async onDescFila(idArt, raw) {
      if (this.readonly || !this.matrizEditable || !this.puedeEditarDescRenglon) return;
      if (!this.draftId || !this.urls.descuento_fila) return;
      const val = String(raw || '').trim();
      const pct = val === '' ? 0 : Number(val);
      this.descuentosFila[idArt] = pct;
      this.descuentosFila[String(idArt)] = pct;
      this.marcarTotalesEstimados();
      const { data } = await this.postJson(this.urls.descuento_fila, {
        draft_id: this.draftId,
        id_articulo: idArt,
        porcentaje_descuento: val === '' ? 0 : val,
      });
      if (!data.ok) { this.mostrarAviso(data.error || 'No se pudo guardar el descuento.', 'error'); return; }
      if (data.matriz) this.aplicarMatriz(data.matriz);
      this.flashGuardado();
    },
    async onDescPie(raw) {
      if (this.readonly || !this.matrizEditable || !this.puedeEditarDescPie) return;
      if (!this.draftId || !this.urls.descuento_pie) return;
      const val = String(raw || '').trim();
      this.descPiePct = val === '' ? 0 : Number(val);
      this.marcarTotalesEstimados();
      const { data } = await this.postJson(this.urls.descuento_pie, {
        draft_id: this.draftId,
        desc_pie_pct: val === '' ? 0 : val,
      });
      if (!data.ok) { this.mostrarAviso(data.error || 'No se pudo guardar el descuento de pie.', 'error'); return; }
      if (data.matriz) this.aplicarMatriz(data.matriz);
      this.flashGuardado();
    },
    /** Pie en modo estimado (FE). No dispara preview servidor. */
    marcarTotalesEstimados() {
      this.recalcularPreviewEstimado();
      this.previewFuente = 'estimado';
      if (this.preview) this.preview.warning = '';
    },
    /**
     * Aproximación transparente de totales en el cliente (sin round-trip).
     * Prorratea el desc. de pie sobre líneas y aplica alícuota IVA por artículo.
     */
    recalcularPreviewEstimado() {
      const descPiePct = Math.min(100, Math.max(0, Number(this.descPiePct || 0)));
      const factorPie = 1 - descPiePct / 100;
      let netoBruto = 0;
      const lineas = [];

      for (const art of this.articulos) {
        const idArt = art.id_articulo;
        const precio = Number(art.precio_unitario_neto || 0);
        const rawDesc = this.descuentosFila[idArt] ?? this.descuentosFila[String(idArt)]
          ?? art.porcentaje_descuento ?? 0;
        const pctDescFila = Math.min(100, Math.max(0, Number(rawDesc || 0)));
        const factorFila = 1 - pctDescFila / 100;
        const alic = Number(art.alicuota_iva ?? 21);

        let netoLinea = 0;
        for (const su of this.sucursales) {
          const qty = parseFloat(this.celda(idArt, su.id_cliente_domicilio));
          if (!isNaN(qty) && qty > 0) {
            netoLinea += precio * qty * factorFila;
          }
        }
        if (netoLinea > 0) {
          netoBruto += netoLinea;
          lineas.push({ neto: netoLinea, alic });
        }
      }

      const neto = netoBruto * factorPie;
      let iva = 0;
      for (const ln of lineas) {
        iva += ln.neto * factorPie * (ln.alic / 100);
      }

      this.previewEstimado = {
        neto: roundMoney(neto),
        iva: roundMoney(iva),
        total: roundMoney(neto + iva),
      };
    },
    /** Quita avisos informativos de preview que no frenan el confirm. */
    _filtroWarningPreview(raw) {
      const text = String(raw || '').trim();
      if (!text) return '';
      const partes = text.split(/(?<=\.)\s+/).map((p) => p.trim()).filter(Boolean);
      const bloqueantes = partes.filter((p) => {
        if (/tiempo límite/i.test(p)) return false;
        if (/Podés confirmar el lote igualmente/i.test(p)) return false;
        if (/límite recomendado/i.test(p) && /puede demorar/i.test(p)) return false;
        return true;
      });
      return bloqueantes.join(' ');
    },
    /**
     * Preview servidor bajo demanda (botón «Validar totales» o al abrir modal de confirm).
     * No se agenda en cada edición: el pie usa estimado FE.
     */
    async refrescarPreview() {
      if (!this.draftId || !this.urls.preview) return;
      const infracciones = this._escanearInfraccionesMultiplo();
      if (infracciones.length) {
        this._mostrarModalListaInfracciones(infracciones);
        return;
      }
      if (this._previewTimer) {
        clearTimeout(this._previewTimer);
        this._previewTimer = null;
      }
      const seq = ++this._previewSeq;
      this.previewCargando = true;
      try {
        const { data } = await this.postJson(this.urls.preview, {
          draft_id: this.draftId,
          desc_pie_pct: this.descPiePct,
          ...this._payloadCabecera(),
        });
        if (seq !== this._previewSeq) return;
        if (!data || !data.ok) {
          this.mostrarAviso((data && (data.error || data.message)) || 'No se pudo validar los totales.', 'error');
          return;
        }
        this.preview = {
          sucursales: data.sucursales || [],
          total_lote: data.total_lote || { neto: 0, iva: 0, total: 0 },
          warning: this._filtroWarningPreview(data.warning || ''),
        };
        this.recalcularPreviewEstimado();
        const serverTotal = Number(this.preview.total_lote.total || 0);
        const estimadoTotal = Number(this.previewEstimado?.total || 0);
        // Timeout / preview vacío: conservar estimado en el pie/modal (no mostrar $0).
        if (data.preview_incompleto || (serverTotal <= 0 && estimadoTotal > 0)) {
          this.previewFuente = 'estimado';
        } else {
          this.previewFuente = 'servidor';
        }
      } finally {
        if (seq === this._previewSeq) {
          this.previewCargando = false;
        }
      }
    },
    totalSucursal(idDom) {
      const s = (this.preview.sucursales || []).find(
        x => String(x.id_cliente_domicilio) === String(idDom),
      );
      return s ? this.money(s.total) : '—';
    },
    flashGuardado() {
      this.guardadoChip = 'Guardado';
      clearTimeout(this._chipTimer);
      this._chipTimer = setTimeout(() => { this.guardadoChip = ''; }, 1500);
    },
    async buscarArticulos() {
      if (!this.idCliente || !this.urls.articulos) return;
      const q = (this.qArt || '').trim();
      if (q.length < 2) {
        ++this._artBusquedaSeq;
        if (this._articulosBusquedaAbort) {
          this._articulosBusquedaAbort.abort();
          this._articulosBusquedaAbort = null;
        }
        this.articulosBusqueda = [];
        this.artBusquedaHecha = false;
        this.cargandoArt = false;
        return;
      }
      await this._fetchArticulos({ q, todos: false, tam: 20 });
    },
    /**
     * Catálogo completo filtrado (Terminado + e-commerce + marcas territorio).
     * Disparado por flecha abajo / botón «ver todos» en desktop y móvil.
     */
    async listarTodosArticulos() {
      if (!this.idCliente || !this.urls.articulos) return;
      await this._fetchArticulos({ q: '', todos: true, tam: 5000 });
    },
    async _fetchArticulos({ q = '', todos = false, tam = 20 } = {}) {
      if (!this.idCliente || !this.urls.articulos) return;
      if (this._articulosBusquedaAbort) {
        this._articulosBusquedaAbort.abort();
      }
      const seq = ++this._artBusquedaSeq;
      const abortController = new AbortController();
      this._articulosBusquedaAbort = abortController;
      this.cargandoArt = true;
      this.abrirPanelArt();
      let u = this.urls.articulos
        + '?id_cliente=' + this.idCliente
        + '&lista_id=' + (this.cabecera?.lista_id || this.listaId || 1)
        + '&tam=' + encodeURIComponent(String(tam));
      if (todos) {
        u += '&todos=1';
      } else {
        u += '&q=' + encodeURIComponent(q || '');
      }
      try {
        const data = await this.getJson(u, { signal: abortController.signal });
        if (seq !== this._artBusquedaSeq || abortController.signal.aborted) return;
        if (!data.ok) { if (data.error) this.mostrarAviso(data.error, 'error'); this.articulosBusqueda = []; this.artBusquedaHecha = true; return; }
        if (data.sin_marcas) {
          this.mostrarAviso('No hay marcas asignadas para este cliente en tu territorio.', 'error');
          this.articulosBusqueda = [];
          this.artBusquedaHecha = true;
          return;
        }
        this.articulosBusqueda = (data.items || []).map((it) => this._mapArticuloItem(it));
        this.idxArt = 0;
        this.artBusquedaHecha = true;
      } catch (error) {
        if (error?.name !== 'AbortError' && seq === this._artBusquedaSeq) {
          this.mostrarAviso('No se pudieron buscar artículos.', 'error');
          this.articulosBusqueda = [];
          this.artBusquedaHecha = true;
        }
      } finally {
        if (seq === this._artBusquedaSeq) this.cargandoArt = false;
        if (this._articulosBusquedaAbort === abortController) {
          this._articulosBusquedaAbort = null;
        }
      }
    },
    abrirPanelArt() {
      if (this._blurArtTimer) {
        clearTimeout(this._blurArtTimer);
        this._blurArtTimer = null;
      }
      this.panelArt = true;
    },
    /**
     * Cierra el panel al salir el foco del buscador/dropdown (no al clickear una opción).
     */
    onFocusOutBuscadorArt(event) {
      const root = event.currentTarget;
      const next = event.relatedTarget;
      if (next && root && root.contains(next)) return;
      if (this._blurArtTimer) clearTimeout(this._blurArtTimer);
      this._blurArtTimer = setTimeout(() => {
        this.cerrarPanelArt();
        this._blurArtTimer = null;
      }, 80);
    },
    onBlurBuscadorArt() {
      // Compat: mismo cierre que focusout.
      this.onFocusOutBuscadorArt({ currentTarget: null, relatedTarget: null });
    },
    cerrarPanelArt() {
      if (this._blurArtTimer) {
        clearTimeout(this._blurArtTimer);
        this._blurArtTimer = null;
      }
      this.panelArt = false;
      this.artDropdownStyle = '';
    },
    actualizarPosDropdownArt() {
      // Dropdown anclado con CSS absolute al input; no requiere coords fixed.
    },
    /** Baja la matriz hasta la fila-buscador (línea nueva al pie). */
    scrollBuscadorIntoView() {
      const mid = this.$refs.pmZoneMid;
      if (mid) mid.scrollTop = mid.scrollHeight;
      const left = this.$refs.pmZoneLeft;
      const right = this.$refs.pmZoneRight;
      if (left) left.scrollTop = mid ? mid.scrollTop : left.scrollHeight;
      if (right) right.scrollTop = mid ? mid.scrollTop : right.scrollHeight;
    },
    focusBuscadorArt() {
      this.$nextTick(() => {
        this.scrollBuscadorIntoView();
        // En viewport <lg el buscador desktop está oculto: preferimos #pm-art-mob.
        const esMovil = typeof window !== 'undefined'
          && window.matchMedia
          && window.matchMedia('(max-width: 1023px)').matches;
        const desktop = this.$refs.pmArtInput || document.getElementById('pm-art');
        const movil = document.getElementById('pm-art-mob');
        let el;
        if (esMovil && movil) {
          el = movil;
        } else if (desktop && desktop.offsetParent !== null) {
          el = desktop;
        } else {
          el = movil || desktop;
        }
        if (el) {
          el.focus();
          el.scrollIntoView({ block: 'nearest' });
        }
      });
    },
    /**
     * Devuelve el input de cantidad VISIBLE para (idArt, idDom). El markup
     * duplica los inputs (desktop matriz + móvil acordeón/lista) con el mismo
     * `data-pm-qty`; enfocar a ciegas caía en el clon oculto. Elegimos el que
     * está pintado (`offsetParent !== null`) según el viewport activo.
     */
    _qtyInputVisible(idArt, idDom) {
      const sel = '[data-pm-qty="' + idArt + ':' + idDom + '"]';
      const nodes = document.querySelectorAll(sel);
      for (const el of nodes) {
        if (el.offsetParent !== null) return el;
      }
      return nodes[0] || null;
    },
    focusPrimeraCantidad(idArt) {
      this.$nextTick(() => {
        if (!this.sucursales.length) {
          this.focusBuscadorArt();
          return;
        }
        const idDom = this.sucursales[0].id_cliente_domicilio;
        const el = this._qtyInputVisible(idArt, idDom);
        if (el) {
          el.focus();
          el.select && el.select();
        } else {
          this.focusBuscadorArt();
        }
      });
    },
    onEnterCantidad(idArt, si) {
      const next = si + 1;
      if (next < this.sucursales.length) {
        const idDom = this.sucursales[next].id_cliente_domicilio;
        const el = this._qtyInputVisible(idArt, idDom);
        if (el) { el.focus(); el.select && el.select(); return; }
      }
      // Fin de línea → buscador de la fila nueva
      this.focusBuscadorArt();
    },
    /**
     * Flecha abajo: si no hay lista abierta, trae todo el catálogo; si hay, navega.
     */
    async onArrowDownArt() {
      if (this.articulosBusqueda.length) {
        this.moverSelArt(1);
        return;
      }
      await this.listarTodosArticulos();
    },
    moverSelArt(delta) {
      if (!this.articulosBusqueda.length) return;
      this.idxArt = (this.idxArt + delta + this.articulosBusqueda.length) % this.articulosBusqueda.length;
      this.$nextTick(() => this.scrollArtResaltado());
    },
    /** Mantiene visible el ítem resaltado dentro del dropdown (max-h + overflow). */
    scrollArtResaltado() {
      const roots = [this.$refs.pmArtDropdown, this.$refs.pmArtDropdownMob].filter(Boolean);
      for (const root of roots) {
        if (getComputedStyle(root).display === 'none') continue;
        const list = root.querySelector('.pm-art-dropdown-list') || root;
        const row = list.querySelector(`[data-art-index="${this.idxArt}"]`);
        if (row) {
          row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
          return;
        }
      }
    },
    elegirResaltadoArt() {
      if (this.cantidadSeleccionados > 0) {
        this.agregarSeleccionados();
        return;
      }
      if (this.articulosBusqueda[this.idxArt]) this.elegirArticulo(this.articulosBusqueda[this.idxArt]);
    },
    /** Nº de sucursal = cliente_domicilio.NroCalle (campo `nro` en la matriz). */
    nroSucursal(s) {
      if (!s) return '—';
      const nro = String(s.nro || '').trim();
      if (nro && nro !== '-') return nro;
      return String(s.id_cliente_domicilio || '—');
    },
    /** Orden ascendente numérico por NroCalle (fallback id domicilio). */
    _nroSucursalSortKey(s) {
      const raw = String(s?.nro || '').trim();
      const m = raw.match(/\d+/);
      const idDom = Number(s?.id_cliente_domicilio || 0);
      if (m) return [0, Number(m[0]), idDom];
      return [1, idDom, 0];
    },
    _ordenarSucursalesAsc(list) {
      return [...(list || [])].sort((a, b) => {
        const ka = this._nroSucursalSortKey(a);
        const kb = this._nroSucursalSortKey(b);
        for (let i = 0; i < ka.length; i += 1) {
          if (ka[i] !== kb[i]) return ka[i] - kb[i];
        }
        return 0;
      });
    },
    etiquetaSucursalCompleta(s) {
      if (!s) return '';
      const parts = [s.calle, s.nro, s.dpto, s.distrito, s.provincia, s.zona]
        .map(x => String(x || '').trim())
        .filter(x => x && x !== '-');
      return parts.join(' · ') || (s.nombre || s.etiqueta || '');
    },
    abrirDetalleSucursal(s) {
      if (!s) return;
      this.sucursalDetalle = {
        id_cliente_domicilio: s.id_cliente_domicilio,
        nro: this.nroSucursal(s),
        calle: String(s.calle || '').trim(),
        dpto: String(s.dpto || '').trim(),
        distrito: String(s.distrito || '').trim(),
        provincia: String(s.provincia || '').trim(),
        zona: String(s.zona || '').trim(),
        nombre: s.nombre || s.etiqueta || '',
      };
      this.modalSucursalAbierto = true;
    },
    cerrarDetalleSucursal() {
      this.modalSucursalAbierto = false;
      this.sucursalDetalle = null;
    },
    elegirArticulo(a) {
      if (this._blurArtTimer) {
        clearTimeout(this._blurArtTimer);
        this._blurArtTimer = null;
      }
      const id = Number(a.id_articulo || a.IDArt);
      if (!id) return;
      const ya = this.articulos.some(x => Number(x.id_articulo) === id);
      if (!ya) {
        this.articulos.push(this._mapArticuloFila(a));
      }
      this.qArt = '';
      this.articulosBusqueda = [];
      this.artBusquedaHecha = false;
      this._limpiarSeleccionArticulos();
      this.cerrarPanelArt();
      if (!ya) this.marcarTotalesEstimados();
      if (ya || !this.sucursales.length) {
        this.focusBuscadorArt();
      } else {
        this.focusPrimeraCantidad(id);
      }
    },
    // ── Confirmación con modal canon (D.5) — reemplaza confirm() nativo ──
    anularBorrador() {
      if (!this.puedeAnularBorrador) return;
      this.error = '';
      this.abrirDialogo('masivo_anular', {
        titulo: 'Anular borrador masivo',
        mensaje: 'El borrador quedará en la columna Anulado del hub. Podés recuperarlo con Continuar.',
        confirmarTexto: 'Anular borrador',
        cancelarTexto: 'Cancelar',
        onConfirm: () => this._ejecutarAnularBorrador(),
      });
    },
    async _ejecutarAnularBorrador() {
      if (!this.draftId || !this.urls.anular) return;
      this.anulando = true;
      this.error = '';
      this.mensajeOk = '';
      const { data } = await this.postJson(this.urls.anular, { draft_id: this.draftId });
      this.anulando = false;
      if (!data.ok) {
        this.mostrarAviso(data.error || 'No se pudo anular el borrador.', 'error');
        return;
      }
      if (data.matriz) this.aplicarMatriz(data.matriz);
      this.mostrarAviso(data.message || 'Borrador anulado. Podés recuperarlo desde el hub.', 'success');
    },
    // ── Acciones hero PED (mail / repetir / PDF / anular) — REQ-PSU-07 ──
    verPdfPedido() {
      const url = this.pdfPedidoUrl;
      if (!url || url === '#') return;
      window.open(url, '_blank', 'noopener');
    },
    repetirPedido() {
      if (!this.pedidoCodMov) return;
      this.abrirPedido(this.pedidoCodMov, true);
    },
    /** Mismo destino que el Hub: captura limpia simple o masiva. */
    onNuevoSimple() {
      const u = this.urls.nuevo_simple;
      if (u) window.location.href = u;
    },
    onNuevoMasivo() {
      const u = this.urls.nuevo_masivo;
      if (u) window.location.href = u;
    },
    solicitarEnviarMail() {
      if (!this.pedidoCodMov || !this.urls.mail_enqueue) return;
      this.dialogInput = this.emailCliente || '';
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
        return;
      }
      const { data } = await this.postJson(this.urls.mail_enqueue, {
        codMov: this.pedidoCodMov,
        tipocomprobante: 0,
        email,
      });
      const okMsg = data && (data.msg === 'ok' || data.ok);
      if (!okMsg) {
        this.mostrarAviso((data && (data.error || data.detail)) || 'No se pudo encolar el mail.', 'error');
        return;
      }
      this.mostrarAviso('Solicitud de envío registrada.', 'success');
    },
    solicitarAnularPedido() {
      if (!this.puedeAnularPedido || !this.pedidoCodMov || !this.urls.anular_pedido) return;
      this.dialogInput = '';
      this.dialogInputError = '';
      this.abrirDialogo('anular_pedido', {
        titulo: 'Anular pedido',
        mensaje: 'Solo es posible en estado Pendiente. Indicá el motivo (obligatorio).',
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
          mensaje: 'Solo es posible en estado Pendiente. Indicá el motivo (obligatorio).',
          confirmarTexto: 'Anular pedido',
          cancelarTexto: 'Cancelar',
          variante: 'danger',
          onConfirm: () => this._ejecutarAnularPedido(),
        });
        return;
      }
      const { data } = await this.postJson(this.urls.anular_pedido, {
        anularPedido: '1',
        codMovPedido: this.pedidoCodMov,
        motivo,
      });
      const okMsg = data && (data.msg === 'ok' || data.ok);
      if (!okMsg) {
        this.mostrarAviso((data && (data.error || data.detail)) || 'No se pudo anular el pedido.', 'error');
        return;
      }
      this.mostrarAviso('Pedido anulado.', 'success');
      this.puedeAnularPedido = false;
      this.pedidoEditable = false;
      // Recargar el PED anulado en consulta (solo lectura).
      this.abrirPedido(this.pedidoCodMov, false);
    },
    async confirmarLote() {
      if (!this.draftId || !this.urls.confirmar || this.confirmando) return;
      if (this.pedidoSoloConsulta) {
        this.mostrarAviso('Este pedido no es editable (en producción o anulado). Solo consulta.', 'warning');
        return;
      }
      this.error = '';
      this.mensajeOk = '';
      const fe = (
        this.cabecera?.fecha_entrega
        || displayToIso(this.cabecera?.fecha_entrega_display)
        || ''
      ).toString().trim();
      if (!fe) {
        this.contextoAbierto = true;
        this.$nextTick(() => {
          const elFecha = document.getElementById('pm-fecha-entrega');
          this.abrirDialogo('aviso', {
            titulo: 'Fecha de entrega requerida',
            mensaje: 'Completá la fecha de entrega antes de confirmar el pedido.',
            confirmarTexto: 'Entendido',
            variante: 'warning',
            onConfirm: () => this.focusFechaEntrega(),
          });
          // Esc / cierre también deja el foco en el campo.
          if (elFecha) this._dialogFocoPrevio = elFecha;
        });
        return;
      }
      const infracciones = this._escanearInfraccionesMultiplo();
      if (infracciones.length) {
        this._mostrarModalListaInfracciones(infracciones);
        return;
      }
      this.recalcularPreviewEstimado();
      // Modo simple: mensaje según sea alta nueva o edición (anula+crea REQ-PSU-06).
      let titulo = 'Confirmar pedido masivo';
      let mensaje = 'Se creará un PED por cada sucursal con cantidad cargada.';
      let confirmarTexto = 'Confirmar pedido';
      let variante = 'primary';
      if (this.modoSimple) {
        if (this.codMovOrigen && !this.puedeAnularPedido) {
          this.mostrarAviso(
            `No se puede confirmar: el PED origen ${this.pedidoNro || this.codMovOrigen} está en «${this.pedidoEstado || 'otro estado'}» y ya no se puede anular.`,
            'error',
            'No se pudo confirmar',
          );
          return;
        }
        if (this.codMovOrigen) {
          titulo = 'Confirmar cambios del pedido simple';
          mensaje = `Se anulará el PED ${this.pedidoNro || this.codMovOrigen} y se creará uno nuevo con las cantidades cargadas. El número de comprobante cambiará.`;
          confirmarTexto = 'Anular y crear nuevo';
          variante = 'danger';
        } else {
          titulo = 'Confirmar pedido simple';
          mensaje = 'Se creará un PED con las cantidades cargadas para la sucursal seleccionada.';
        }
      }
      // Abrir modal al instante; la validación servidor corre en paralelo (UI «Validando…»).
      this.abrirDialogo('masivo_confirmar', {
        titulo,
        mensaje,
        confirmarTexto,
        cancelarTexto: 'Cancelar',
        variante,
        onConfirm: () => this._ejecutarConfirmarLote(),
      });
      this.refrescarPreview();
    },
    /** Abre el contexto comercial y enfoca el campo fecha de entrega. */
    focusFechaEntrega() {
      this.contextoAbierto = true;
      this.$nextTick(() => {
        const el = document.getElementById('pm-fecha-entrega');
        if (!el) return;
        el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        el.focus();
        el.classList.add('ring-2', 'ring-amber-500', 'border-amber-500');
        setTimeout(() => {
          el.classList.remove('ring-2', 'ring-amber-500', 'border-amber-500');
        }, 2500);
      });
    },
    /** Sucursales con al menos una celda con cantidad > 0 (orden id asc). */
    _sucursalesConCarga() {
      const ids = new Set();
      for (const [key, raw] of Object.entries(this.celdas || {})) {
        const qty = parseFloat(raw);
        if (!isNaN(qty) && qty > 0) {
          const parts = String(key).split(':');
          if (parts[1]) ids.add(Number(parts[1]));
        }
      }
      return this._ordenarSucursalesAsc(
        (this.sucursales || []).filter((s) => ids.has(Number(s.id_cliente_domicilio))),
      );
    },
    _nombreSucursal(idDom) {
      const su = (this.sucursales || []).find(
        (s) => String(s.id_cliente_domicilio) === String(idDom),
      );
      return (su && (su.nombre || su.etiqueta)) || `Sucursal #${idDom}`;
    },
    _initConfirmProgreso() {
      const items = this._sucursalesConCarga().map((su) => ({
        id: Number(su.id_cliente_domicilio),
        nombre: su.nombre || su.etiqueta || `Sucursal #${su.id_cliente_domicilio}`,
        estado: 'pendiente',
        codigo: null,
        nro: '',
        error: '',
      }));
      this.confirmProgreso = {
        total: items.length,
        hechos: 0,
        actualIndex: 0,
        actualNombre: '',
        finOk: null,
        finMessage: '',
        items,
      };
    },
    _aplicarEventoProgreso(ev) {
      if (!this.confirmProgreso || !ev) return;
      if (ev.event === 'inicio') {
        this.confirmProgreso.total = Number(ev.total || this.confirmProgreso.total);
        return;
      }
      if (ev.event !== 'sucursal') return;
      const idDom = Number(ev.id_cliente_domicilio);
      let item = this.confirmProgreso.items.find((i) => i.id === idDom);
      if (!item) {
        item = {
          id: idDom,
          nombre: ev.nombre || this._nombreSucursal(idDom),
          estado: 'pendiente',
          codigo: null,
          nro: '',
          error: '',
        };
        this.confirmProgreso.items.push(item);
      }
      if (ev.nombre) item.nombre = ev.nombre;
      if (ev.estado === 'procesando') {
        item.estado = 'procesando';
        this.confirmProgreso.actualIndex = Number(ev.index || 0);
        this.confirmProgreso.actualNombre = item.nombre;
        return;
      }
      if (ev.estado === 'ok') {
        item.estado = 'ok';
        item.codigo = ev.codigo_movimiento ?? null;
        item.nro = ev.nro_comprobante || '';
        this.confirmProgreso.hechos = this.confirmProgreso.items.filter(
          (i) => i.estado === 'ok',
        ).length;
        return;
      }
      if (ev.estado === 'error') {
        item.estado = 'error';
        item.error = ev.error || 'Error al confirmar.';
      }
    },
    get confirmProgresoPct() {
      const p = this.confirmProgreso;
      if (!p || !p.total) return 0;
      return Math.min(100, Math.round((p.hechos / p.total) * 100));
    },
    /**
     * Arma un mensaje accionable con la causa del fallo de confirmación.
     * Prioriza message/error/detail y detalla errores por sucursal (payload o matriz).
     */
    _formatoErrorConfirmacion(data, status) {
      const d = data || {};
      const primario = [d.message, d.error, d.detail]
        .map((x) => String(x || '').trim())
        .find(Boolean) || '';
      const mapa = (d.errores && typeof d.errores === 'object')
        ? d.errores
        : ((d.matriz && d.matriz.ultimo_error) || {});
      const detalles = [];
      Object.keys(mapa || {}).forEach((k) => {
        if (k === '_compensacion') return;
        const v = mapa[k];
        const texto = typeof v === 'string' ? v : (v && (v.error || v.message)) || JSON.stringify(v);
        if (!texto) return;
        if (k === '_lote') detalles.push(texto);
        else detalles.push(`Sucursal ${k}: ${texto}`);
      });
      if (Array.isArray(d.compensacion) && d.compensacion.length) {
        detalles.push(`Compensación: ${d.compensacion.join('; ')}`);
      }
      const unidos = detalles.filter(Boolean);
      if (primario && unidos.length) {
        const yaIncluye = unidos.some((t) => t.includes(primario) || primario.includes(t));
        return yaIncluye ? unidos.join(' · ') : `${primario} — ${unidos.join(' · ')}`;
      }
      if (primario) return primario;
      if (unidos.length) return unidos.join(' · ');
      if (status === 406) {
        return 'El servidor rechazó el formato de respuesta (406). Recargá la página con Ctrl+F5 e intentá de nuevo.';
      }
      if (status && status >= 400) {
        return `No se pudo confirmar el pedido (error HTTP ${status}). Revisá permisos, sesión o reintentá.`;
      }
      return 'No se pudo confirmar el pedido. Revisá cantidades, artículos y punto de venta.';
    },
    async _ejecutarConfirmarLote() {
      if (!this.draftId || !this.urls.confirmar) return;
      this.confirmando = true;
      this.error = '';
      this.mensajeOk = '';
      this._initConfirmProgreso();
      this.dialogKind = 'masivo_progreso';
      this.dialogTitulo = 'Creando pedidos…';
      this.dialogMensaje = 'Se genera un PED por cada sucursal con cantidad cargada.';

      let status = 0;
      let data = {};
      try {
        const res = await this.postNdjsonStream(
          this.urls.confirmar,
          {
            draft_id: this.draftId,
            desc_pie_pct: this.descPiePct,
            stream: true,
            ...this._payloadCabecera(),
          },
          (ev) => this._aplicarEventoProgreso(ev),
        );
        status = res.status;
        data = res.fin || {};
      } catch (e) {
        this.confirmando = false;
        this.confirmProgreso = null;
        this.dialogKind = 'masivo_confirmar';
        this.mostrarAviso('No se pudo confirmar el pedido: fallo de red o respuesta inválida.', 'error', 'No se pudo confirmar');
        return;
      }

      this.confirmando = false;
      if (this.confirmProgreso) {
        this.confirmProgreso.finOk = !!data.ok;
        this.confirmProgreso.finMessage = data.message
          || ((!data.ok && status >= 400) ? this._formatoErrorConfirmacion(data, status) : '');
      }

      if (data.matriz) this.aplicarMatriz(data.matriz);
      else if (data.errores && typeof data.errores === 'object') {
        this.ultimoError = data.errores;
      }

      if (!data.ok || status === 409 || status >= 400) {
        this.mostrarAviso(this._formatoErrorConfirmacion(data, status), 'error', 'No se pudo confirmar');
        if (data.matriz?.ultimo_error) this.ultimoError = data.matriz.ultimo_error;
        else if (data.errores) this.ultimoError = data.errores;
        // Volver al resumen editable tras breve pausa para leer el error en el modal.
        setTimeout(() => {
          this.confirmProgreso = null;
          this.dialogKind = 'masivo_confirmar';
        }, 2500);
        return;
      }

      this.ultimoError = {};
      let okMsg = data.message || 'Pedido confirmado.';
      this.draftEstado = 'confirmado';
      const cods = data.codigos_movimiento || [];
      if (cods.length) {
        okMsg += ' PED: ' + cods.join(', ');
      }
      const tplResumen = this.urls.resumen_lote_tpl || '';
      const esMasivoMultiped = !this.modoSimple && cods.length > 1;
      const lotePendiente = String(
        data.estado_aprobacion_lote
        || data.matriz?.estado_aprobacion_lote
        || (this.aprobacionPedidosActiva ? 'pendiente' : '-'),
      ) === 'pendiente';
      if (this.draftId && tplResumen && (esMasivoMultiped || lotePendiente)) {
        this.urlResumenLote = String(tplResumen).replace('{draft_id}', String(this.draftId));
        if (lotePendiente && this.aprobacionPedidosActiva) {
          okMsg += ' El lote quedó pendiente de autorización comercial a nivel lote.';
        }
        okMsg += ' Podés ver el resumen del lote desde el enlace inferior.';
      } else {
        this.urlResumenLote = '';
      }
      if (this.confirmProgreso) {
        this.confirmProgreso.finMessage = okMsg;
      }
      this.mostrarAviso(okMsg, 'success');
      // Modo simple: habilitar acciones hero (PDF/mail/anular) sobre el PED creado.
      if (this.modoSimple && cods.length) {
        this.pedidoCodMov = Number(cods[0]);
        this.pedidoNro = '';
        this.pedidoEditable = false;
        this.puedeAnularPedido = true;
        this.codMovOrigen = null;
      }
      this.flashGuardado();
      if (!this.urlResumenLote) {
        setTimeout(() => {
          this.confirmProgreso = null;
          this.cerrarDialogo();
        }, 1500);
      }
    },
    async cargarCarteraVendedor() {
      if (!this.urls.vendedores_cartera) return;
      try {
        const data = await this.getJson(this.urls.vendedores_cartera);
        this.vendedorCartera = data.vendedores || [];
        this.vendedorOperativo = data.operativo ?? null;
        this.vendedorPropio = data.propio ?? null;
        this.mostrarSelectorVendedor = Boolean(data.mostrar_selector);
        this.operandoComoOtro = Boolean(data.operando_como_otro);
        const actual = (this.vendedorCartera || []).find(v => v.cod_viajante === this.vendedorOperativo);
        this.vendedorOperativoNombre = actual ? actual.nombre : '';
      } catch {
        this.mostrarSelectorVendedor = false;
      }
    },
    // ── Cambio de vendedor operativo con modal canon (D.5) ──
    solicitarCambioVendedor(codRaw) {
      const cod = Number(codRaw);
      if (!Number.isFinite(cod) || cod === this.vendedorOperativo) return;
      const dest = (this.vendedorCartera || []).find(v => v.cod_viajante === cod);
      const nombre = dest ? dest.nombre : ('Vendedor ' + cod);
      const hayBorrador = Boolean(this.draftId);
      if (!hayBorrador && !this.clienteSel) {
        this._aplicarCambioVendedor(cod);
        return;
      }
      this._vendedorPendiente = cod;
      this.abrirDialogo('cambio_vendedor', {
        titulo: 'Cambiar vendedor operativo',
        mensaje: hayBorrador
          ? ('El borrador se cargará a nombre de ' + nombre + '. Se actualizarán las sucursales de su territorio.')
          : ('Vas a operar como ' + nombre + '.'),
        confirmarTexto: 'Cambiar vendedor',
        cancelarTexto: 'Cancelar',
        onConfirm: async () => { await this._aplicarCambioVendedor(this._vendedorPendiente); },
      });
      // Si el usuario cancela, revierte el <select> al vendedor vigente.
      this.$nextTick(() => this.cargarCarteraVendedor());
    },
    async _aplicarCambioVendedor(cod) {
      this._vendedorPendiente = null;
      if (!this.urls.vendedor_operativo || !Number.isFinite(cod)) return;
      const { data } = await this.postJson(this.urls.vendedor_operativo, { cod_viajante: cod });
      if (!data.ok) {
        this.mostrarAviso(data.detail || 'No se pudo cambiar el vendedor.', 'error');
        await this.cargarCarteraVendedor();
        return;
      }
      this.vendedorOperativo = data.operativo;
      await this.cargarCarteraVendedor();
      if (this.draftId) {
        await this.abrirDraft(this.draftId);
        this.mostrarAviso('Vendedor del borrador actualizado.', 'success');
        return;
      }
      this.buscarClientes();
    },
  };
}

function register() {
  if (!window.Alpine || window.__synapPedidoMasivoRegistered) return false;
  window.Alpine.data('pedidoMasivoApp', () => compose(
    orderDialogsMixin,
    pedidoMasivoCore,
  ));
  window.__synapPedidoMasivoRegistered = true;
  return true;
}

function remountRoot() {
  const { Alpine } = window;
  const root = document.querySelector('[x-data="pedidoMasivoApp()"]')
    || document.querySelector('[x-data*="pedidoMasivoApp"]');
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
