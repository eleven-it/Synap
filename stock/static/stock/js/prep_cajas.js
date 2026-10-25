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
  const url = (tipo) => root.dataset[tipo].replace('__CODIGO__', String(prep));
  const numero = (n) => new Intl.NumberFormat('es-AR', { maximumFractionDigits: 4 }).format(Number(n || 0));

  function actualizarModo() {
    const display = el('prep-modo-lectura').value === 'display';
    const ayuda = el('prep-modo-ayuda');
    ayuda.textContent = display
      ? 'Modo Display: el código de unidad suma el pack indicado en cada artículo. La etiqueta 333 conserva su cantidad.'
      : 'Modo Unidad: el código de unidad suma 1. Los códigos propios de display o bulto mantienen su factor.';
    ayuda.className = display ? 'mt-1 text-sm font-bold text-amber-800 dark:text-amber-200' : 'mt-1 text-sm';
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
        const b = nodo('button', 'block w-full rounded-lg border border-slate-200 p-3 text-left text-sm hover:bg-blue-50 dark:border-slate-700 dark:hover:bg-slate-700',
          `${item.numero || `Prep. ${item.codigo}`} · ${item.pedidos} pedido(s)`);
        b.type = 'button';
        b.addEventListener('click', () => seleccionar(Number(item.codigo)));
        lista.append(b);
      }
      if (!data.preparaciones.length) lista.append(nodo('p', 'p-3 text-sm text-slate-500', 'Sin preparaciones encontradas.'));
    } catch (error) { aviso(error.message, true); }
  }
  async function seleccionar(codigo) {
    prep = codigo;
    cajaActiva = null;
    await refrescar();
  }
  async function refrescar() {
    if (!prep) return;
    try {
      estado = await pedir(url('estado'));
      render();
    } catch (error) { aviso(error.message, true); }
  }
  function render() {
    el('prep-sin-seleccion').classList.add('hidden');
    el('prep-contenido').classList.remove('hidden');
    el('prep-titulo').textContent = `Preparación ${prep}`;
    const cajas = estado.cajas || [];
    if (!cajas.some((c) => Number(c.id_caja) === cajaActiva && c.estado === 'Abierta')) cajaActiva = null;
    const activa = cajas.find((c) => Number(c.id_caja) === cajaActiva);
    el('prep-caja-activa').textContent = activa ? `Caja ${activa.numero_caja}` : 'Ninguna';
    el('prep-caja-destino').textContent = activa ? activa.destino_entrega : 'Abrí o seleccioná una caja para escanear.';
    el('prep-codigo').disabled = !activa;
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
    const boxList = el('prep-cajas-lista');
    boxList.replaceChildren();
    for (const caja of cajas) {
      const seleccionada = Number(caja.id_caja) === cajaActiva;
      const card = nodo('div', `rounded-lg border p-3 ${seleccionada
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
        const b = nodo('button', 'rounded border border-slate-400 px-3 py-2 text-sm font-semibold', accion === 'cerrar' ? 'Cerrar caja' : 'Reabrir');
        b.type = 'button';
        b.addEventListener('click', async () => {
          try {
            await pedir(url('accion'), { id_caja: caja.id_caja, accion });
            if (accion === 'reabrir') cajaActiva = Number(caja.id_caja);
            await refrescar();
            aviso(accion === 'cerrar' ? `Caja ${caja.numero_caja} cerrada.`
              : `Caja ${caja.numero_caja} reabierta y seleccionada para escanear.`);
            if (accion === 'reabrir') el('prep-codigo').focus();
          }
          catch (error) { aviso(error.message, true); }
        });
        controls.append(b);
      }
      if ((caja.estado === 'Abierta' || caja.estado === 'Cerrada')
          && !caja.fecha_importacion && Number(caja.lecturas_totales) === 0) {
        const eliminar = nodo('button', 'rounded border border-red-500 px-3 py-2 text-sm font-semibold text-red-700 dark:text-red-300', 'Eliminar caja');
        eliminar.type = 'button';
        eliminar.addEventListener('click', async () => {
          if (!window.confirm(`¿Eliminar la caja ${caja.numero_caja}? El número no se reutilizará.`)) return;
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
          const fila = nodo('li', 'rounded bg-white p-2 dark:bg-slate-800');
          fila.append(nodo('p', 'font-semibold', `${numero(item.unidades)} u. · ${item.nombre}`));
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
    if (!cajas.length) boxList.append(nodo('p', 'text-sm text-slate-500', 'Todavía no hay cajas.'));
    const articulos = el('prep-articulos');
    articulos.replaceChildren();
    for (const articulo of estado.articulos) {
      const row = nodo('div', 'rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700');
      row.append(nodo('p', 'font-semibold', articulo.articulo));
      row.append(nodo('p', 'text-slate-500 dark:text-slate-300', `${articulo.nro_pedido} · ${articulo.cliente} · ${articulo.destino}`));
      row.append(nodo('p', 'font-bold', `Pendiente ${numero(articulo.faltante)} / ${numero(articulo.pendiente)}`));
      row.append(nodo('p', 'text-slate-600 dark:text-slate-300', `Unidades por display: ${numero(articulo.unidades_display)}`));
      articulos.append(row);
    }
    if (!estado.articulos.length) articulos.append(nodo('p', 'text-sm text-slate-500', 'No hay artículos pendientes en administraNET.'));
    const lecturas = el('prep-lecturas');
    lecturas.replaceChildren();
    for (const lectura of estado.lecturas.slice(0, 30)) {
      const row = nodo('div', 'flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 p-2 text-sm dark:border-slate-700');
      row.append(nodo('span', 'min-w-0 flex-1', `Caja ${lectura.numero_caja} · ${lectura.codigo_leido} · ${numero(lectura.cantidad_unidades)} u.`));
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
    el('prep-codigo').focus();
  });
  el('prep-scan-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = el('prep-codigo');
    const codigo = input.value.trim();
    const modo_lectura = el('prep-modo-lectura').value;
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
      input.value = '';
      el('prep-ultimo').textContent = result.repetida
        ? `${codigo} · lectura ya registrada; no se duplicó.`
        : `${result.articulo || codigo} · ${numero(result.cantidad)} unidad(es) · Pedido ${result.pedido || ''}`;
      await refrescar();
      aviso(result.repetida ? 'Lectura recuperada sin duplicar.' : 'Artículo registrado en la caja.');
      if (navigator.vibrate) navigator.vibrate(45);
    } catch (error) { aviso(error.message, true); }
    finally { input.disabled = false; input.focus(); }
  });
  el('prep-modo-lectura').value = 'display';
  actualizarModo();
  cargarPreparaciones();
})();
