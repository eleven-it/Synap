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
      const card = nodo('div', 'rounded-lg border border-slate-300 p-3 dark:border-slate-600');
      card.append(nodo('p', 'text-xl font-bold', `Caja ${caja.numero_caja} · ${caja.estado}`));
      card.append(nodo('p', 'text-sm', caja.destino_entrega));
      const controls = nodo('div', 'mt-2 flex flex-wrap gap-2');
      const accion = caja.estado === 'Abierta' ? 'cerrar' : 'reabrir';
      if (caja.estado === 'Abierta') {
        const elegir = nodo('button', 'rounded bg-blue-700 px-3 py-2 text-sm font-semibold text-white', 'Usar caja');
        elegir.type = 'button';
        elegir.addEventListener('click', () => { cajaActiva = Number(caja.id_caja); render(); el('prep-codigo').focus(); });
        controls.append(elegir);
      }
      if (caja.estado === 'Abierta' || (caja.estado === 'Cerrada' && !caja.fecha_importacion)) {
        const b = nodo('button', 'rounded border border-slate-400 px-3 py-2 text-sm font-semibold', accion === 'cerrar' ? 'Cerrar caja' : 'Reabrir');
        b.type = 'button';
        b.addEventListener('click', async () => {
          try { await pedir(url('accion'), { id_caja: caja.id_caja, accion }); await refrescar(); aviso(`Caja ${caja.numero_caja}: ${accion === 'cerrar' ? 'cerrada' : 'reabierta'}.`); }
          catch (error) { aviso(error.message, true); }
        });
        controls.append(b);
      }
      card.append(controls); boxList.append(card);
    }
    if (!cajas.length) boxList.append(nodo('p', 'text-sm text-slate-500', 'Todavía no hay cajas.'));
    const articulos = el('prep-articulos');
    articulos.replaceChildren();
    for (const articulo of estado.articulos) {
      const row = nodo('div', 'rounded-lg border border-slate-200 p-3 text-sm dark:border-slate-700');
      row.append(nodo('p', 'font-semibold', articulo.articulo));
      row.append(nodo('p', 'text-slate-500 dark:text-slate-300', `${articulo.nro_pedido} · ${articulo.cliente} · ${articulo.destino}`));
      row.append(nodo('p', 'font-bold', `Pendiente ${numero(articulo.faltante)} / ${numero(articulo.pendiente)}`));
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
  el('prep-scan-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const input = el('prep-codigo');
    const codigo = input.value.trim();
    if (!cajaActiva || !codigo) return;
    input.disabled = true;
    if (!lecturaPendiente || lecturaPendiente.codigo !== codigo || lecturaPendiente.id_caja !== cajaActiva) {
      lecturaPendiente = { codigo, id_caja: cajaActiva, idempotency_key: crypto.randomUUID() };
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
  cargarPreparaciones();
})();
