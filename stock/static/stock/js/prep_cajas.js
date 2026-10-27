(() => {
  const root = document.getElementById('prep-cajas');
  if (!root) return;
  const el = (id) => document.getElementById(id);
  const csrf = root.querySelector('input[name=csrfmiddlewaretoken]').value;
  let prep = null;
  let cajaActiva = null;
  let estado = null;
  let buscando = null;
  let lecturaPendiente = null;
  let seleccionVersion = 0;
  let seleccionSolicitada = null;
  let seleccionando = false;
  let accionCajaEnCurso = false;
  const urlPara = (tipo, codigo) => root.dataset[tipo].replace('__CODIGO__', String(codigo));
  const url = (tipo) => urlPara(tipo, prep);
  const numero = (n) => new Intl.NumberFormat('es-AR', { maximumFractionDigits: 4 }).format(Number(n || 0));
  function factorDisplay(idArticulo, pedido) {
    const articulo = (estado?.articulos || []).find((item) =>
      Number(item.id_articulo) === Number(idArticulo) &&
      (pedido == null || Number(item.pedido) === Number(pedido)));
    const contenido = articulo ? null : (estado?.cajas || []).flatMap((caja) => caja.contenido || []).find((item) =>
      Number(item.id_articulo) === Number(idArticulo) &&
      (pedido == null || Number(item.codigo_movimiento_ped) === Number(pedido)));
    const factor = Number(articulo?.unidades_display || contenido?.unidades_display || 0);
    return factor > 1 ? factor : 0;
  }
  const modoDisplay = () => el('prep-modo-lectura').value === 'display';
  function unidadesYDisplays(unidades, factor) {
    const cantidad = Number(unidades || 0);
    const textoUnidades = `${numero(cantidad)} ${cantidad === 1 ? 'unidad' : 'unidades'}`;
    if (!(factor > 1)) return textoUnidades;
    const displays = Math.floor((cantidad + 0.000001) / factor);
    const resto = Math.max(0, cantidad - displays * factor);
    const textoDisplays = `${numero(displays)} ${displays === 1 ? 'display' : 'displays'}`;
    const presentacion = `${textoDisplays}${resto > 0.000001 ? ` + ${numero(resto)} ${resto === 1 ? 'unidad' : 'unidades'}` : ''}`;
    return modoDisplay()
      ? `${presentacion} · ${textoUnidades} (${numero(factor)} unidades/display)`
      : `${textoUnidades} · ${presentacion} (${numero(factor)} unidades/display)`;
  }
  function resumenCantidades(items, cantidad, factor) {
    const resumen = { unidades: 0, displays: 0, sueltas: 0, tieneDisplay: false };
    for (const item of items) {
      const unidades = Number(cantidad(item) || 0);
      const porDisplay = Number(factor(item) || 0);
      resumen.unidades += unidades;
      if (porDisplay > 1) {
        resumen.tieneDisplay = true;
        const displays = Math.floor((unidades + 0.000001) / porDisplay);
        resumen.displays += displays;
        resumen.sueltas += Math.max(0, unidades - displays * porDisplay);
      } else {
        resumen.sueltas += unidades;
      }
    }
    return resumen;
  }
  function cantidadPrincipal(resumen) {
    if (!modoDisplay() || !resumen.tieneDisplay) return `${numero(resumen.unidades)} unidades`;
    const displays = `${numero(resumen.displays)} ${resumen.displays === 1 ? 'display' : 'displays'}`;
    return resumen.sueltas > 0.000001
      ? `${displays} + ${numero(resumen.sueltas)} unidades`
      : displays;
  }
  function equivalenciaUnidades(resumen) {
    return modoDisplay() && resumen.tieneDisplay ? `${numero(resumen.unidades)} unidades` : '';
  }

  function actualizarModo() {
    const display = el('prep-modo-lectura').value === 'display';
    const ayuda = el('prep-modo-ayuda');
    ayuda.textContent = display
      ? 'Modo Display: el código de unidad suma las unidades de un display indicadas en cada artículo. La etiqueta 333 conserva su cantidad.'
      : 'Modo Unidad: el código de unidad suma 1. Los códigos propios de display o bulto mantienen su factor.';
    ayuda.className = display ? 'mt-1 break-words text-sm font-bold text-amber-800 dark:text-amber-200' : 'mt-1 break-words text-sm';
  }

  function nodo(tag, clase, contenido) {
    const n = document.createElement(tag);
    if (clase) n.className = clase;
    if (contenido !== undefined) n.textContent = contenido;
    return n;
  }
  function aviso(mensaje, error = false) {
    const target = el('prep-aviso');
    target.textContent = mensaje;
    target.className = `rounded-xl border p-3 text-sm font-semibold ${error
      ? 'border-red-400 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100'
      : 'border-emerald-400 bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100'}`;
    if (error && navigator.vibrate) navigator.vibrate([90, 50, 90]);
  }
  async function pedir(endpoint, payload) {
    const response = await fetch(endpoint, payload === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || data.detail || 'No se pudo completar la operación.');
    return data;
  }
  async function cargarPreparaciones() {
    const texto = el('prep-buscar').value.trim();
    try {
      const data = await pedir(`${root.dataset.buscar}?q=${encodeURIComponent(texto)}`);
      const lista = el('prep-lista');
      lista.replaceChildren();
      for (const item of data.preparaciones) {
        const b = nodo('button', 'block w-full rounded-lg border border-slate-200 bg-white p-3 text-left text-sm text-slate-900 hover:bg-blue-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100 dark:hover:bg-slate-700');
        b.type = 'button';
        b.append(nodo('span', 'block font-semibold', `Preparación ${item.numero || item.codigo}`));
        b.append(nodo('span', 'mt-1 block text-xs text-slate-600 dark:text-slate-300',
          `Movimiento ${item.codigo} · ${item.pedidos} pedido(s)`));
        b.addEventListener('click', () => seleccionar(Number(item.codigo)));
        lista.append(b);
      }
      if (!data.preparaciones.length) lista.append(nodo('p', 'p-3 text-sm text-slate-500 dark:text-slate-300', 'Sin preparaciones encontradas.'));
    } catch (error) { aviso(error.message, true); }
  }
  async function seleccionar(codigo) {
    if (codigo === prep && !seleccionando) return;
    const version = ++seleccionVersion;
    seleccionSolicitada = codigo;
    const anterior = prep;
    const estadoAnterior = estado;
    const cajaAnterior = cajaActiva;
    let reservaTomada = false;
    seleccionando = true;
    el('prep-aviso').classList.add('hidden');
    el('prep-contenido').classList.add('hidden');
    el('prep-sin-seleccion').textContent = `Cargando preparación ${codigo}...`;
    el('prep-sin-seleccion').classList.remove('hidden');
    try {
      await pedir(urlPara('reserva', codigo), { accion: 'tomar' });
      reservaTomada = true;
      if (version !== seleccionVersion) return;
      const nuevoEstado = await pedir(urlPara('estado', codigo));
      if (version !== seleccionVersion) return;
      prep = codigo;
      cajaActiva = null;
      lecturaPendiente = null;
      el('prep-ultimo').textContent = '';
      estado = nuevoEstado;
      seleccionando = false;
      render();
      if (anterior && anterior !== codigo) {
        try { await pedir(urlPara('reserva', anterior), { accion: 'liberar' }); }
        catch (error) { aviso(`No se pudo liberar la preparación anterior: ${error.message}`, true); }
      }
    } catch (error) {
      if (version !== seleccionVersion) return;
      prep = anterior;
      estado = estadoAnterior;
      cajaActiva = cajaAnterior;
      seleccionando = false;
      seleccionSolicitada = anterior;
      if (estadoAnterior) render();
      else quitarPreparacionDePantalla();
      aviso(error.message, true);
    } finally {
      if (reservaTomada && codigo !== prep && codigo !== seleccionSolicitada) {
        try { await pedir(urlPara('reserva', codigo), { accion: 'liberar' }); }
        catch (error) { /* La reserva transitoria vence sola si otro usuario la tomó. */ }
      }
    }
  }

  function quitarPreparacionDePantalla() {
    prep = null;
    cajaActiva = null;
    estado = null;
    lecturaPendiente = null;
    el('prep-contenido').classList.add('hidden');
    el('prep-sin-seleccion').classList.remove('hidden');
  }
  async function refrescar() {
    if (!prep || seleccionando) return false;
    const codigo = prep;
    const version = seleccionVersion;
    try {
      const estabanListas = Boolean(estado?.cajas_listas);
      const nuevoEstado = await pedir(urlPara('estado', codigo));
      if (prep !== codigo || version !== seleccionVersion || seleccionando) return false;
      estado = nuevoEstado;
      render();
      if (estado.cajas_listas && !estabanListas) {
        el('prep-finalizacion').scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
      return true;
    } catch (error) {
      if (prep === codigo && version === seleccionVersion && !seleccionando) aviso(error.message, true);
      return false;
    }
  }
  function renderFinalizacion(cajas) {
    const sinFaltantes = Boolean(estado.sin_faltantes);
    const cajasListas = Boolean(estado.cajas_listas);
    const panel = el('prep-finalizacion');
    panel.className = `rounded-xl border p-4 ${sinFaltantes || cajasListas ? '' : 'hidden '}${cajasListas && sinFaltantes
      ? 'border-emerald-400 bg-emerald-50 text-emerald-950 dark:bg-emerald-950/50 dark:text-emerald-100'
      : 'border-amber-400 bg-amber-50 text-amber-950 dark:bg-amber-950/50 dark:text-amber-100'}`;
    el('prep-resumen-datos').classList.toggle('hidden', !cajasListas);
    el('prep-resumen-faltantes').classList.toggle('hidden', !cajasListas || sinFaltantes);
    if (!sinFaltantes && !cajasListas) return;
    const numeroPrep = estado.numero_preparacion || String(prep);
    el('prep-finalizacion-titulo').textContent = cajasListas
      ? `Armado de cajas ${numeroPrep} ${sinFaltantes ? 'completo' : 'parcial'}: listo para control de salida`
      : `Preparación ${numeroPrep}: todas las unidades previstas fueron leídas`;
    if (!cajasListas) {
      const abiertas = cajas.filter((c) => c.estado === 'Abierta').map((c) => c.numero_caja);
      const vacias = cajas.filter((c) => Number(c.lecturas_activas) === 0).map((c) => c.numero_caja);
      el('prep-finalizacion-ayuda').textContent = abiertas.length
        ? `No quedan artículos por leer. Cerrá ${abiertas.map((n) => `Caja ${n}`).join(', ')} para llevarla a control de salida.`
        : vacias.length
          ? `No quedan artículos por leer. Eliminá ${vacias.map((n) => `Caja ${n}`).join(', ')} porque está vacía.`
          : 'No quedan artículos por leer. Revisá el estado de las cajas.';
      return;
    }
    const articulos = estado.articulos || [];
    const total = articulos.reduce((suma, item) => suma + Number(item.pendiente || 0), 0);
    const leido = articulos.reduce((suma, item) => suma + Number(item.en_cajas || 0), 0);
    const faltante = articulos.reduce((suma, item) => suma + Number(item.faltante || 0), 0);
    el('prep-finalizacion-ayuda').textContent = sinFaltantes
      ? `${numero(leido)} de ${numero(total)} unidades en cajas cerradas. Usá el código de movimiento en el control de salida de administraNET.`
      : `${numero(leido)} de ${numero(total)} unidades en cajas cerradas; faltan ${numero(faltante)}. Controlá estas cajas en administraNET y dejá pendiente lo que no se pudo preparar.`;
    const pendientes = el('prep-resumen-faltantes-lista');
    pendientes.replaceChildren();
    if (!sinFaltantes) {
      for (const articulo of articulos.filter((item) => Number(item.faltante) > 0)) {
        pendientes.append(nodo('li', 'rounded border border-amber-400 px-2 py-1 dark:border-amber-700',
          `Faltan ${unidadesYDisplays(articulo.faltante, Number(articulo.unidades_display))} · ${articulo.articulo} · Pedido ${articulo.nro_pedido}`));
      }
    }
    el('prep-resumen-movimiento').textContent = String(estado.codigo || prep);
    el('prep-resumen-numero').textContent = numeroPrep;
    const lista = el('prep-resumen-cajas');
    lista.replaceChildren();
    for (const caja of cajas) {
      const contenido = caja.contenido || [];
      const unidades = contenido.reduce((total, item) => total + Number(item.cantidad_unidades || 0), 0);
      const card = nodo('div', 'rounded-lg border border-emerald-300 bg-white p-3 text-slate-900 dark:border-emerald-700 dark:bg-slate-900 dark:text-white');
      card.append(nodo('p', 'text-xl font-bold', `Caja ${caja.numero_caja} · ${numero(unidades)} unidades`));
      card.append(nodo('p', 'mt-1 text-sm text-slate-600 dark:text-slate-300', caja.destino_entrega));
      const detalle = nodo('ul', 'mt-2 space-y-1 border-t border-slate-200 pt-2 text-sm dark:border-slate-700');
      for (const item of contenido) {
        detalle.append(nodo('li', '', `${unidadesYDisplays(item.cantidad_unidades, factorDisplay(item.id_articulo, item.codigo_movimiento_ped))} · ${item.articulo} · Código ${item.codigo_leido} · Pedido ${item.nro_pedido}`));
      }
      card.append(detalle);
      lista.append(card);
    }
  }
  function renderProgreso() {
    const articulos = estado.articulos || [];
    const total = articulos.reduce((suma, item) => suma + Number(item.pendiente || 0), 0);
    const faltante = articulos.reduce((suma, item) => suma + Number(item.faltante || 0), 0);
    const leido = articulos.reduce((suma, item) => suma + Number(item.en_cajas || 0), 0);
    const porLeer = resumenCantidades(articulos, (item) => item.faltante, (item) => item.unidades_display);
    const enCajas = resumenCantidades(articulos, (item) => item.en_cajas, (item) => item.unidades_display);
    const completos = articulos.filter((item) => Number(item.faltante) <= 0).length;
    const pendientes = articulos.filter((item) => Number(item.faltante) > 0);
    const porcentaje = total > 0 ? Math.min(100, Math.max(0, Math.round(100 * leido / total))) : 0;
    el('prep-progreso-titulo').textContent = `Avance de preparación ${estado.numero_preparacion || prep}`;
    el('prep-progreso-faltante').textContent = cantidadPrincipal(porLeer);
    el('prep-progreso-faltante-unidades').textContent = modoDisplay() && porLeer.tieneDisplay
      ? `${equivalenciaUnidades(porLeer)} de ${numero(total)} previstas` : `de ${numero(total)} previstas`;
    el('prep-progreso-leido').textContent = cantidadPrincipal(enCajas);
    el('prep-progreso-leido-unidades').textContent = equivalenciaUnidades(enCajas);
    el('prep-progreso-articulos').textContent = `${completos} de ${articulos.length}`;
    el('prep-progreso-barra').setAttribute('aria-valuenow', String(porcentaje));
    el('prep-progreso-relleno').style.width = `${porcentaje}%`;
    const proximos = el('prep-proximos');
    proximos.replaceChildren();
    for (const item of pendientes.slice(0, 3)) {
      proximos.append(nodo('p', 'rounded bg-amber-50 px-2 py-1 font-medium text-amber-950 dark:bg-amber-950/40 dark:text-amber-100',
        `Faltan ${unidadesYDisplays(item.faltante, Number(item.unidades_display))} · ${item.articulo}`));
    }
    if (pendientes.length > 3) proximos.append(nodo('p', 'text-slate-600 dark:text-slate-300',
      `Y ${pendientes.length - 3} artículo(s) más. Ver lista completa abajo.`));
    if (!pendientes.length && articulos.length) proximos.append(nodo('p', 'font-bold text-emerald-800 dark:text-emerald-200',
      'Lectura completa: no quedan artículos pendientes.'));
    if (!articulos.length && Number(estado.articulos_en_otra_preparacion) > 0) {
      proximos.append(nodo('p', 'font-bold text-amber-900 dark:text-amber-200',
        'Las unidades pendientes ya están en cajas de otra preparación del mismo pedido.'));
    }

  }
  async function cambiarEstadoCaja(caja, accion) {
    if (accionCajaEnCurso) return;
    accionCajaEnCurso = true;
    el('prep-cerrar-activa').disabled = true;
    try {
      await pedir(url('accion'), { id_caja: caja.id_caja, accion });
      if (accion === 'reabrir') cajaActiva = Number(caja.id_caja);
      await refrescar();
      if (!estado.cajas_listas) aviso(accion === 'cerrar' ? `Caja ${caja.numero_caja} cerrada.`
        : `Caja ${caja.numero_caja} reabierta y seleccionada para escanear.`);
      if (accion === 'reabrir') el('prep-codigo').focus();
    } catch (error) { aviso(error.message, true); }
    finally {
      accionCajaEnCurso = false;
      el('prep-cerrar-activa').disabled = false;
    }
  }
  function render() {
    el('prep-sin-seleccion').classList.add('hidden');
    el('prep-contenido').classList.remove('hidden');
    el('prep-titulo').textContent = `Preparación ${estado.numero_preparacion || prep}`;
    el('prep-codigo-movimiento').textContent = String(estado.codigo || prep);
    const cajas = estado.cajas || [];
    renderFinalizacion(cajas);
    renderProgreso();
    el('prep-lectura-panel').classList.toggle('hidden', Boolean(estado.cajas_listas));
    if (estado.cajas_listas || estado.sin_faltantes) el('prep-aviso').classList.add('hidden');
    if (!cajas.some((c) => Number(c.id_caja) === cajaActiva && c.estado === 'Abierta')) cajaActiva = null;
    const activa = cajas.find((c) => Number(c.id_caja) === cajaActiva);
    el('prep-caja-activa').textContent = activa ? `Caja ${activa.numero_caja}` : 'Ninguna';
    el('prep-caja-destino').textContent = activa ? activa.destino_entrega : 'Abrí o seleccioná una caja para escanear.';
    el('prep-cerrar-activa').classList.toggle('hidden', !activa);
    el('prep-cerrar-activa').setAttribute('aria-label', activa ? `Cerrar caja ${activa.numero_caja}` : 'Cerrar caja');
    el('prep-cerrar-activa').onclick = activa ? () => cambiarEstadoCaja(activa, 'cerrar') : null;
    el('prep-caja-resumen').classList.toggle('hidden', !activa);
    if (activa) {
      const agrupado = new Map();
      for (const item of activa.contenido || []) {
        const clave = `${item.id_articulo}:${item.codigo_movimiento_ped}`;
        if (!agrupado.has(clave)) agrupado.set(clave, { unidades: 0, factor: factorDisplay(item.id_articulo, item.codigo_movimiento_ped) });
        agrupado.get(clave).unidades += Number(item.cantidad_unidades || 0);
      }
      const contenido = resumenCantidades([...agrupado.values()], (item) => item.unidades, (item) => item.factor);
      el('prep-caja-cantidad').textContent = cantidadPrincipal(contenido);
      el('prep-caja-equivalencia').textContent = equivalenciaUnidades(contenido);
    }
    el('prep-codigo').disabled = !activa || Boolean(estado.sin_faltantes);
    const selector = el('prep-pedido');
    const elegido = selector.value;
    selector.replaceChildren();
    const pedidos = new Map();
    for (const articulo of estado.articulos) {
      if (Number(articulo.faltante) <= 0) continue;
      if (!pedidos.has(String(articulo.pedido))) pedidos.set(String(articulo.pedido), articulo);
    }
    for (const [pedido, articulo] of pedidos) {
      const option = nodo('option', '', `${articulo.nro_pedido} · ${articulo.cliente} · ${articulo.destino}`);
      option.value = pedido;
      selector.append(option);
    }
    if (pedidos.has(elegido)) selector.value = elegido;
    el('prep-abrir').disabled = !pedidos.size;
    el('prep-abrir-fila').classList.toggle('hidden', !pedidos.size);
    const boxList = el('prep-cajas-lista');
    boxList.replaceChildren();
    for (const caja of cajas) {
      const seleccionada = Number(caja.id_caja) === cajaActiva;
      const card = nodo('div', `rounded-lg border p-3 text-slate-900 dark:text-slate-100 ${seleccionada
        ? 'border-blue-600 bg-blue-50 dark:border-blue-400 dark:bg-blue-950/40'
        : 'border-slate-300 dark:border-slate-600'}`);
      const vacia = caja.estado === 'Cerrada' && Number(caja.lecturas_activas) === 0;
      card.append(nodo('p', 'text-xl font-bold', `Caja ${caja.numero_caja} · ${caja.estado}${vacia ? ' · Vacía' : ''}`));
      card.append(nodo('p', 'text-sm', caja.destino_entrega));
      if (seleccionada) card.append(nodo('p', 'mt-1 text-sm font-bold text-blue-800 dark:text-blue-200', 'Caja de lectura activa'));
      const controls = nodo('div', 'mt-2 flex flex-wrap gap-2');
      const accion = caja.estado === 'Abierta' ? 'cerrar' : 'reabrir';
      if (caja.estado === 'Abierta') {
        const elegir = nodo('button', 'rounded bg-blue-700 px-3 py-2 text-sm font-semibold text-white',
          seleccionada ? 'Usando esta caja' : 'Usar caja');
        elegir.type = 'button';
        elegir.disabled = seleccionada;
        elegir.addEventListener('click', () => { cajaActiva = Number(caja.id_caja); render(); el('prep-codigo').focus(); });
        controls.append(elegir);
      }
      if (caja.estado === 'Abierta' || (caja.estado === 'Cerrada' && !caja.fecha_importacion)) {
        const b = nodo('button', 'rounded border border-slate-400 bg-white px-3 py-2 text-sm font-semibold text-slate-900 dark:bg-slate-900 dark:text-slate-100', accion === 'cerrar' ? 'Cerrar caja' : 'Reabrir');
        b.type = 'button';
        b.addEventListener('click', () => cambiarEstadoCaja(caja, accion));
        controls.append(b);
      }
      if ((caja.estado === 'Abierta' || caja.estado === 'Cerrada')
          && !caja.fecha_importacion && Number(caja.lecturas_activas) === 0) {
        const eliminar = nodo('button', 'rounded border border-red-500 px-3 py-2 text-sm font-semibold text-red-700 dark:text-red-300', 'Eliminar caja');
        eliminar.type = 'button';
        eliminar.addEventListener('click', async () => {
          if (!window.confirm(`¿Eliminar la caja ${caja.numero_caja}? Se conservará el historial de lecturas anuladas. Si no quedan cajas, la próxima empezará nuevamente en 1.`)) return;
          try {
            await pedir(url('accion'), { id_caja: caja.id_caja, accion: 'eliminar' });
            if (cajaActiva === Number(caja.id_caja)) cajaActiva = null;
            await refrescar();
            aviso(`Caja ${caja.numero_caja} eliminada. Su número no se reutilizará.`);
          } catch (error) { aviso(error.message, true); }
        });
        controls.append(eliminar);
      }
      card.append(controls);
      const contenido = caja.contenido || [];
      const articulos = new Map();
      for (const item of contenido) {
        const id = Number(item.id_articulo);
        if (!articulos.has(id)) articulos.set(id, {
          id, nombre: item.articulo || `Artículo ${id}`, unidades: 0,
          codigos: new Set(), tipos: new Set(), pedidos: new Set(),
        });
        const grupo = articulos.get(id);
        grupo.unidades += Number(item.cantidad_unidades || 0);
        grupo.codigos.add(item.codigo_leido);
        grupo.tipos.add(item.tipo_lectura);
        grupo.pedidos.add(item.nro_pedido || item.codigo_movimiento_ped);
      }
      const unidades = [...articulos.values()].reduce((total, item) => total + item.unidades, 0);
      card.append(nodo('p', 'mt-3 border-t border-slate-300 pt-2 text-sm font-semibold dark:border-slate-600',
        articulos.size ? `Contenido: ${numero(unidades)} unidad(es) · ${articulos.size} artículo(s)` : 'Sin artículos en esta caja'));
      if (articulos.size) {
        const lista = nodo('ul', 'mt-2 max-h-48 space-y-2 overflow-y-auto text-sm');
        for (const item of articulos.values()) {
          const fila = nodo('li', 'rounded bg-white p-2 text-slate-900 dark:bg-slate-800 dark:text-slate-100');
          fila.append(nodo('p', 'font-semibold', `${unidadesYDisplays(item.unidades, factorDisplay(item.id))} · ${item.nombre}`));
          fila.append(nodo('p', 'break-all text-slate-600 dark:text-slate-300',
            `Código(s): ${[...item.codigos].join(', ')} · ${[...item.tipos].join(', ')} · Pedido(s): ${[...item.pedidos].join(', ')}`));
          if (caja.estado === 'Abierta') {
            const quitar = nodo('button', 'mt-2 rounded border border-red-500 px-2 py-1 font-semibold text-red-700 dark:text-red-300', 'Eliminar artículo');
            quitar.type = 'button';
            quitar.setAttribute('aria-label', `Eliminar ${item.nombre} de la caja ${caja.numero_caja}`);
            quitar.addEventListener('click', async () => {
              if (!window.confirm(`¿Eliminar ${numero(item.unidades)} unidad(es) de ${item.nombre} de la caja ${caja.numero_caja}? Las lecturas quedarán anuladas.`)) return;
              try {
                await pedir(url('accion'), { id_caja: caja.id_caja, accion: 'anular_articulo', id_articulo: item.id });
                lecturaPendiente = null;
                el('prep-ultimo').textContent = '';
                await refrescar();
                aviso(`Artículo quitado de la caja ${caja.numero_caja}. Las unidades volvieron al pendiente.`);
              } catch (error) { aviso(error.message, true); }
            });
            fila.append(quitar);
          }
          lista.append(fila);
        }
        card.append(lista);
        if (caja.estado === 'Cerrada' && !caja.fecha_importacion) {
          card.append(nodo('p', 'mt-2 text-xs text-slate-600 dark:text-slate-300',
            'Reabrí la caja para eliminar un artículo.'));
        }
      }
      boxList.append(card);
    }
    if (!cajas.length) boxList.append(nodo('p', 'text-sm text-slate-500 dark:text-slate-300', 'Todavía no hay cajas.'));
    const articulos = el('prep-articulos');
    articulos.replaceChildren();
    el('prep-articulos-titulo').textContent = `${estado.sin_faltantes ? 'Artículos preparados' : 'Artículos pendientes'} · Preparación ${estado.numero_preparacion || prep}`;
    el('prep-articulos-ayuda').textContent = estado.sin_faltantes
      ? 'Todos los artículos de esta preparación fueron leídos.'
      : 'El faltante se reduce con cada lectura. Si no hay stock, cerrá las cajas para continuar con un armado parcial; lo no preparado queda pendiente para el control de salida.';
    const ordenados = [...estado.articulos].sort((a, b) => Number(b.faltante > 0) - Number(a.faltante > 0));
    for (const articulo of ordenados) {
      const completo = Number(articulo.faltante) <= 0;
      const total = Number(articulo.pendiente || 0);
      const leido = Number(articulo.en_cajas || 0);
      const porcentaje = total > 0 ? Math.min(100, Math.max(0, Math.round(100 * leido / total))) : 0;
      const row = nodo('div', `rounded-lg border p-3 text-sm ${completo
        ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-950/30'
        : 'border-amber-300 bg-amber-50/50 dark:border-amber-800 dark:bg-amber-950/20'}`);
      row.append(nodo('p', 'font-semibold', articulo.articulo));
      row.append(nodo('p', 'text-slate-500 dark:text-slate-300', `${articulo.nro_pedido} · ${articulo.cliente} · ${articulo.destino}`));
      row.append(nodo('p', `font-bold ${completo ? 'text-emerald-800 dark:text-emerald-200' : 'text-amber-900 dark:text-amber-200'}`,
        completo ? 'Completo · Faltan 0 unidades'
          : `Faltan ${unidadesYDisplays(articulo.faltante, Number(articulo.unidades_display))}`));
      row.append(nodo('p', 'font-medium', `En cajas ${numero(leido)} de ${numero(total)} unidades`));
      const barra = nodo('div', 'mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700');
      const relleno = nodo('div', 'h-full rounded-full bg-emerald-600');
      relleno.style.width = `${porcentaje}%`;
      barra.append(relleno);
      row.append(barra);
      if (articulo.barra_interna) {
        row.append(nodo('p', 'break-all font-medium text-slate-700 dark:text-slate-200',
          `Código de barra interno: ${articulo.barra_interna}`));
      }
      row.append(nodo('p', 'text-slate-600 dark:text-slate-300', `Unidades por display: ${numero(articulo.unidades_display)}`));
      articulos.append(row);
    }
    if (!estado.articulos.length) articulos.append(nodo('p', 'text-sm text-slate-600 dark:text-slate-300',
      Number(estado.articulos_en_otra_preparacion) > 0
        ? 'Los artículos pendientes ya se registraron en cajas de otra preparación del mismo pedido. No vuelvas a leerlos aquí.'
        : 'No hay artículos pendientes en administraNET.'));
    const lecturas = el('prep-lecturas');
    lecturas.replaceChildren();
    for (const lectura of estado.lecturas.slice(0, 30)) {
      const row = nodo('div', 'flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 p-2 text-sm dark:border-slate-700');
      row.append(nodo('span', 'min-w-0 flex-1', `Caja ${lectura.numero_caja} · ${lectura.codigo_leido} · ${unidadesYDisplays(lectura.cantidad_unidades, factorDisplay(lectura.id_articulo, lectura.codigo_movimiento_ped))}`));
      if (Number(lectura.id_caja) === cajaActiva) {
        const deshacer = nodo('button', 'rounded border border-red-400 px-2 py-1 text-red-700 dark:text-red-300', 'Deshacer');
        deshacer.type = 'button';
        deshacer.addEventListener('click', async () => {
          try { await pedir(url('accion'), { id_caja: cajaActiva, accion: 'anular_lectura', id_lectura: lectura.id_lectura }); await refrescar(); aviso('Lectura anulada.'); }
          catch (error) { aviso(error.message, true); }
        });
        row.append(deshacer);
      }
      lecturas.append(row);
    }
  }
  el('prep-buscar').addEventListener('input', () => {
    clearTimeout(buscando); buscando = setTimeout(cargarPreparaciones, 250);
  });
  async function liberarPreparacion(elegirOtra = false) {
    if (!prep) return;
    try {
      await pedir(url('reserva'), { accion: 'liberar' });
      quitarPreparacionDePantalla();
      aviso('Preparación liberada. Otro usuario ya puede trabajarla.');
      if (elegirOtra) {
        el('prep-buscar').value = '';
        await cargarPreparaciones();
        el('prep-buscar').scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (error) { aviso(error.message, true); }
  }
  el('prep-liberar').addEventListener('click', () => liberarPreparacion());
  el('prep-otra').addEventListener('click', () => liberarPreparacion(true));
  setInterval(async () => {
    if (!prep) return;
    try { await pedir(url('reserva'), { accion: 'renovar' }); }
    catch (error) {
      quitarPreparacionDePantalla();
      aviso(`Se perdió la reserva de la preparación: ${error.message}`, true);
    }
  }, 60000);
  el('prep-abrir').addEventListener('click', async () => {
    try {
      const data = await pedir(url('abrir'), { pedido: Number(el('prep-pedido').value) });
      cajaActiva = Number(data.id_caja); await refrescar();
      aviso(`Caja ${data.numero_caja} abierta.`); el('prep-codigo').focus();
    } catch (error) { aviso(error.message, true); }
  });
  el('prep-teclado').addEventListener('change', (event) => {
    el('prep-codigo').setAttribute('inputmode', event.target.checked ? 'text' : 'none');
    el('prep-codigo').focus();
  });
  el('prep-modo-lectura').addEventListener('change', () => {
    lecturaPendiente = null;
    actualizarModo();
    if (estado) render();
    el('prep-codigo').focus();
  });
  el('prep-scan-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = el('prep-codigo');
    const codigo = input.value.trim();
    const modo_lectura = el('prep-modo-lectura').value;
    input.value = '';
    if (!cajaActiva || !codigo) return;
    input.disabled = true;
    if (!lecturaPendiente || lecturaPendiente.codigo !== codigo || lecturaPendiente.id_caja !== cajaActiva
        || lecturaPendiente.modo_lectura !== modo_lectura) {
      lecturaPendiente = { codigo, id_caja: cajaActiva, modo_lectura, idempotency_key: crypto.randomUUID() };
    }
    try {
      const result = await pedir(url('lectura'), {
        ...lecturaPendiente,
      });
      lecturaPendiente = null;
      const actualizado = await refrescar();
      const articulo = actualizado && (estado.articulos || []).find((item) =>
        Number(item.id_articulo) === Number(result.id_articulo)
        && Number(item.pedido) === Number(result.codigo_movimiento_ped));
      const ultimo = el('prep-ultimo');
      ultimo.className = 'mt-2 text-sm font-bold text-emerald-900 dark:text-emerald-200';
      ultimo.textContent = result.repetida
        ? `${codigo} · lectura ya registrada; no se duplicó.`
        : `${result.articulo || codigo} · leídas ${unidadesYDisplays(result.cantidad, factorDisplay(result.id_articulo, result.codigo_movimiento_ped))}. ${articulo
          ? `Quedan ${unidadesYDisplays(articulo.faltante, Number(articulo.unidades_display))} de ${unidadesYDisplays(articulo.pendiente, Number(articulo.unidades_display))} para este artículo.`
          : `Pedido ${result.pedido || ''}.`}`;
      if (!estado.sin_faltantes) aviso(result.repetida
        ? 'Lectura recuperada sin duplicar.' : 'Artículo registrado en la caja.');
      if (navigator.vibrate) navigator.vibrate(45);
    } catch (error) {
      aviso(error.message, true);
      const ultimo = el('prep-ultimo');
      ultimo.className = 'mt-2 text-sm font-bold text-red-800 dark:text-red-300';
      ultimo.textContent = `Lectura rechazada: ${error.message}`;
    }
    finally {
      input.value = '';
      input.disabled = !cajaActiva || Boolean(estado?.sin_faltantes);
      if (!input.disabled) input.focus();
    }
  });
  el('prep-modo-lectura').value = 'display';
  actualizarModo();
  cargarPreparaciones();
})();
