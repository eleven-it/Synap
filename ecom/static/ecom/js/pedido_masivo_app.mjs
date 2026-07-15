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
    sucursales: [],
    articulos: [],
    celdas: {},
    descuentosFila: {},
    descPiePct: 0,
    ultimoError: {},
    articulosBusqueda: [],
    qArt: '',
    panelArt: false,
    idxArt: 0,
    cargandoArt: false,
    _artBusquedaSeq: 0,
    _articulosBusquedaAbort: null,
    artDropdownStyle: '',
    _blurArtTimer: null,
    error: '',
    abriendo: false,
    guardadoChip: '',
    confirmando: false,
    confirmProgreso: null,
    anulando: false,
    mensajeOk: '',
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
    condicionesVenta: [],
    listasPrecio: [],
    tipo: 'PED',
    // Contexto comercial compacto por defecto para reservar alto a la matriz.
    contextoAbierto: false,

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
      const e = String(this.draftEstado || 'borrador');
      const map = {
        borrador: 'Borrador',
        confirmando: 'Borrador',
        confirmado: 'Confirmado',
        archivado: 'Archivado',
        anulado: 'Anulado',
      };
      const label = map[e] || 'Borrador';
      return `${label} #${this.draftId}`;
    },

    init() {
      const el = document.getElementById('pm-bootstrap');
      const boot = el ? JSON.parse(el.textContent) : {};
      this.urls = boot.urls || {};
      try {
        const guardado = sessionStorage.getItem('pm-contexto-abierto');
        if (guardado === '1') this.contextoAbierto = true;
      } catch { /* sessionStorage no disponible */ }
      this.cargarCarteraVendedor();
      this.buscarClientes();
      if (boot.draft_id) {
        this.abrirDraft(boot.draft_id);
      }
      // Al hacer scroll de la matriz, cerrar el dropdown (evita menú desfasado).
      this._onMatrixScrollCloseArt = () => {
        if (this.panelArt) this.cerrarPanelArt();
      };
      this.$watch('draftId', () => {
        this.$nextTick(() => this._bindMatrixScrollSync());
      });
      this.$nextTick(() => this._bindMatrixScrollSync());
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
      };
      mid.addEventListener('scroll', () => {
        mirror();
        this._onMatrixScrollCloseArt();
      }, { passive: true });
      // Reenvía la rueda vertical sobre las zonas fijas hacia la zona media.
      const fwdWheel = (e) => {
        if (!e.deltaY) return;
        mid.scrollTop += e.deltaY;
        mirror();
        e.preventDefault();
      };
      if (left) left.addEventListener('wheel', fwdWheel, { passive: false });
      if (right) right.addEventListener('wheel', fwdWheel, { passive: false });
      mid._pmSyncBound = true;
    },
    abrirPanelCli() { this.panelCli = true; },
    cerrarPanelCli() { this.panelCli = false; },
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
    async elegirCliente(c) {
      const id = String(c.id_cliente);
      if (this.abriendo) return;
      if (this.draftId && String(this.idCliente) === id && this.clienteSel === id) return;
      this.clienteSel = id;
      this.clienteNombre = c.nombre || c.etiqueta || '';
      this.qCliente = c.etiqueta || c.nombre || '';
      this._aplicarListaDesdeCliente(c);
      this.cerrarPanelCli();
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
    /** Lee NDJSON línea a línea desde un POST (confirmación masiva con progreso). */
    async postNdjsonStream(url, body, onEvent) {
      const r = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/x-ndjson',
          'X-CSRFToken': this.csrf(),
        },
        body: JSON.stringify(body),
      });
      if (!r.ok && !r.body) {
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
      this.clienteNombre = (m.nombre_cliente || this.clienteNombre || '').trim();
      if (m.cabecera) {
        this.puedeEditarCabecera = !!m.cabecera.puede_editar;
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
      this.sucursales = m.sucursales || [];
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
      }));
      this.celdas = m.celdas || {};
      // Descuentos por fila (REQ-MAS-08/09): mapa id_articulo → % renglón efectivo.
      this.descuentosFila = m.descuentos_fila || {};
      this.descPiePct = Number(m.desc_pie_pct || 0);
      this.ultimoError = m.ultimo_error || {};
      if (!this.clienteNombre) {
        const c = this.clientes.find(x => String(x.id_cliente) === String(this.idCliente));
        if (c) this.clienteNombre = c.nombre || c.etiqueta || '';
      }
      this.marcarTotalesEstimados();
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
      return payloadCabeceraApi(this.cabecera, this.puedeEditarCabecera);
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
        this.error = data.error || '';
        this.clientes = [];
      }
    },
    async abrirCliente() {
      if (!this.clienteSel) return;
      if (this.abriendo) return;
      if (this.draftId && String(this.idCliente) === String(this.clienteSel)) return;
      this.abriendo = true; this.error = ''; this.mensajeOk = '';
      const { data } = await this.postJson(this.urls.abrir, { id_cliente: Number(this.clienteSel) });
      this.abriendo = false;
      if (!data.ok) { this.error = data.error || 'No se pudo abrir.'; return; }
      this.aplicarMatriz(data.matriz);
      const c = this.clientes.find(x => String(x.id_cliente) === String(this.clienteSel));
      if (c) this.clienteNombre = c.nombre || c.etiqueta || this.clienteNombre;
      history.replaceState(null, '', '?draft=' + this.draftId);
    },
    async abrirDraft(id) {
      this.abriendo = true; this.error = '';
      const { data } = await this.postJson(this.urls.abrir, { draft_id: Number(id) });
      this.abriendo = false;
      if (!data.ok) { this.error = data.error || 'No se pudo recuperar el borrador.'; return; }
      this.aplicarMatriz(data.matriz);
    },
    celda(idArt, idDom) {
      return this.celdas[idArt + ':' + idDom] || '';
    },
    fmtPrecio(v) {
      const n = Number(v);
      if (!n && n !== 0) return '—';
      return n.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
        this.error = data.error || 'No se pudo quitar el artículo.';
        return;
      }
      if (data.matriz) this.aplicarMatriz(data.matriz);
      else quitarLocal();
      this.flashGuardado();
    },
    async onCelda(idArt, idDom, raw) {
      const key = idArt + ':' + idDom;
      const val = String(raw || '').trim();
      this.celdas[key] = val;
      this.marcarTotalesEstimados();
      const { data } = await this.postJson(this.urls.celda, {
        draft_id: this.draftId,
        id_articulo: idArt,
        id_cliente_domicilio: idDom,
        cantidad_packs: val === '' ? 0 : val,
      });
      if (!data.ok) {
        this.error = data.error || 'Error al guardar';
        return;
      }
      if (data.celda && data.celda.eliminada) delete this.celdas[key];
      else if (data.celda) this.celdas[key] = data.celda.cantidad_packs;
      this.flashGuardado();
      this.marcarTotalesEstimados();
    },
    async onDescFila(idArt, raw) {
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
      if (!data.ok) { this.error = data.error || 'No se pudo guardar el descuento.'; return; }
      if (data.matriz) this.aplicarMatriz(data.matriz);
      this.flashGuardado();
    },
    async onDescPie(raw) {
      if (!this.draftId || !this.urls.descuento_pie) return;
      const val = String(raw || '').trim();
      this.descPiePct = val === '' ? 0 : Number(val);
      this.marcarTotalesEstimados();
      const { data } = await this.postJson(this.urls.descuento_pie, {
        draft_id: this.draftId,
        desc_pie_pct: val === '' ? 0 : val,
      });
      if (!data.ok) { this.error = data.error || 'No se pudo guardar el descuento de pie.'; return; }
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
          this.error = (data && (data.error || data.message)) || 'No se pudo validar los totales.';
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
        this.cargandoArt = false;
        return;
      }
      if (this._articulosBusquedaAbort) {
        this._articulosBusquedaAbort.abort();
      }
      const seq = ++this._artBusquedaSeq;
      const abortController = new AbortController();
      this._articulosBusquedaAbort = abortController;
      this.cargandoArt = true;
      this.abrirPanelArt();
      const u = this.urls.articulos
        + '?id_cliente=' + this.idCliente
        + '&lista_id=' + (this.cabecera?.lista_id || this.listaId || 1)
        + '&q=' + encodeURIComponent(q)
        + '&tam=20';
      try {
        const data = await this.getJson(u, { signal: abortController.signal });
        if (seq !== this._artBusquedaSeq || abortController.signal.aborted) return;
        if (!data.ok) { this.error = data.error || ''; this.articulosBusqueda = []; return; }
        if (data.sin_marcas) {
          this.error = 'No hay marcas asignadas para este cliente en tu territorio.';
          this.articulosBusqueda = [];
          return;
        }
        this.articulosBusqueda = (data.items || []).map(it => ({
          id_articulo: it.id_articulo || it.IDArt,
          id_manual: it.id_manual || '',
          codigo: it.id_manual || it.codigo || '',
          nombre: it.nombre || it.descripcion || '',
          descripcion: it.nombre || it.descripcion || '',
          precio_unitario_neto: Number(it.precio_unitario_neto || it.precio_lista1 || 0),
          precio_lista1: Number(it.precio_lista1 || 0),
          alicuota_iva: Number(it.alicuota_iva ?? 21),
        }));
        this.idxArt = 0;
      } catch (error) {
        if (error?.name !== 'AbortError' && seq === this._artBusquedaSeq) {
          this.error = 'No se pudieron buscar artículos.';
          this.articulosBusqueda = [];
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
        const el = this.$refs.pmArtInput || document.getElementById('pm-art');
        if (el) {
          el.focus();
          el.scrollIntoView({ block: 'nearest' });
        }
      });
    },
    focusPrimeraCantidad(idArt) {
      this.$nextTick(() => {
        if (!this.sucursales.length) {
          this.focusBuscadorArt();
          return;
        }
        const idDom = this.sucursales[0].id_cliente_domicilio;
        const el = document.querySelector('[data-pm-qty="' + idArt + ':' + idDom + '"]');
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
        const el = document.querySelector('[data-pm-qty="' + idArt + ':' + idDom + '"]');
        if (el) { el.focus(); el.select && el.select(); return; }
      }
      // Fin de línea → buscador de la fila nueva
      this.focusBuscadorArt();
    },
    moverSelArt(delta) {
      if (!this.articulosBusqueda.length) return;
      this.idxArt = (this.idxArt + delta + this.articulosBusqueda.length) % this.articulosBusqueda.length;
    },
    elegirResaltadoArt() {
      if (this.articulosBusqueda[this.idxArt]) this.elegirArticulo(this.articulosBusqueda[this.idxArt]);
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
        this.articulos.push({
          id_articulo: id,
          id_manual: a.id_manual || a.codigo || '',
          codigo: a.id_manual || a.codigo || '',
          nombre: a.nombre || a.descripcion || '',
          descripcion: a.nombre || a.descripcion || '',
          precio_unitario_neto: Number(a.precio_unitario_neto || a.precio_lista1 || 0),
          precio_lista1: Number(a.precio_lista1 || 0),
          porcentaje_descuento: 0,
          alicuota_iva: Number(a.alicuota_iva ?? 21),
        });
      }
      this.qArt = '';
      this.articulosBusqueda = [];
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
        this.error = data.error || 'No se pudo anular el borrador.';
        return;
      }
      if (data.matriz) this.aplicarMatriz(data.matriz);
      this.mensajeOk = data.message || 'Borrador anulado. Podés recuperarlo desde el hub.';
    },
    async confirmarLote() {
      if (!this.draftId || !this.urls.confirmar || this.confirmando) return;
      this.error = '';
      this.mensajeOk = '';
      this.recalcularPreviewEstimado();
      // Abrir modal al instante; la validación servidor corre en paralelo (UI «Validando…»).
      this.abrirDialogo('masivo_confirmar', {
        titulo: 'Confirmar pedido masivo',
        mensaje: 'Se creará un PED por cada sucursal con cantidad cargada.',
        confirmarTexto: 'Confirmar pedido',
        cancelarTexto: 'Cancelar',
        onConfirm: () => this._ejecutarConfirmarLote(),
      });
      this.refrescarPreview();
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
      return (this.sucursales || [])
        .filter((s) => ids.has(Number(s.id_cliente_domicilio)))
        .sort((a, b) => Number(a.id_cliente_domicilio) - Number(b.id_cliente_domicilio));
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
        this.error = 'No se pudo confirmar el pedido: fallo de red o respuesta inválida.';
        return;
      }

      this.confirmando = false;
      if (this.confirmProgreso) {
        this.confirmProgreso.finOk = !!data.ok;
        this.confirmProgreso.finMessage = data.message || '';
      }

      if (data.matriz) this.aplicarMatriz(data.matriz);
      else if (data.errores && typeof data.errores === 'object') {
        this.ultimoError = data.errores;
      }

      if (!data.ok || status === 409 || status >= 400) {
        this.error = this._formatoErrorConfirmacion(data, status);
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
      this.mensajeOk = data.message || 'Pedido confirmado.';
      const cods = data.codigos_movimiento || [];
      if (cods.length) {
        this.mensajeOk += ' PED: ' + cods.join(', ');
      }
      this.flashGuardado();
      setTimeout(() => {
        this.confirmProgreso = null;
        this.cerrarDialogo();
      }, 1500);
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
      const hayContexto = Boolean(this.draftId || this.clienteSel);
      if (!hayContexto) {
        this._aplicarCambioVendedor(cod);
        return;
      }
      this._vendedorPendiente = cod;
      this.abrirDialogo('cambio_vendedor', {
        titulo: 'Cambiar vendedor operativo',
        mensaje: 'Al operar como ' + nombre + ' se limpiará el borrador y el cliente. ¿Continuar?',
        confirmarTexto: 'Cambiar y limpiar',
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
        this.error = data.detail || 'No se pudo cambiar el vendedor.';
        await this.cargarCarteraVendedor();
        return;
      }
      this.vendedorOperativo = data.operativo;
      await this.cargarCarteraVendedor();
      this.draftId = null;
      this.draftEstado = '';
      this.idCliente = null;
      this.clienteNombre = '';
      this.listaPrecio = '';
      this.listaPrecioPdfUrl = '';
      this.clienteSel = '';
      this.qCliente = '';
      this.sucursales = [];
      this.articulos = [];
      this.celdas = {};
      this.descuentosFila = {};
      this.descPiePct = 0;
      this.preview = { sucursales: [], total_lote: { neto: 0, iva: 0, total: 0 }, warning: '' };
      this.previewEstimado = { neto: 0, iva: 0, total: 0 };
      this.previewFuente = 'estimado';
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
