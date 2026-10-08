import test from 'node:test';
import assert from 'node:assert/strict';

let crearApp;
globalThis.window = {
  Alpine: { data(nombre, factory) { if (nombre === 'pedidoMasivoApp') crearApp = factory; } },
};
globalThis.document = { addEventListener() {}, querySelector() { return null; } };
await import('../static/ecom/js/pedido_masivo_app.mjs');

function appEditable(modoSimple) {
  const app = crearApp();
  app.modoSimple = modoSimple;
  app.draftId = 1;
  app.draftEstado = 'borrador';
  app.sucursales = [{ id_cliente_domicilio: 7 }];
  return app;
}

test('la selección múltiple se conserva en pedido simple y masivo', () => {
  for (const modoSimple of [true, false]) {
    const app = appEditable(modoSimple);
    app.toggleSeleccionArticulo({ id_articulo: 10, nombre: 'A' });
    app.toggleSeleccionArticulo({ id_articulo: 11, nombre: 'B' });
    assert.deepEqual(Object.keys(app.articulosSeleccionados), ['10', '11']);
    app.toggleSeleccionArticulo({ id_articulo: 10, nombre: 'A' });
    assert.deepEqual(Object.keys(app.articulosSeleccionados), ['11']);
  }
});

test('pedido simple guarda las cantidades de varios artículos y despliega el carrito en línea', async () => {
  const app = appEditable(true);
  const guardados = [];
  app.toggleSeleccionArticulo({ id_articulo: 10, nombre: 'A' });
  app.toggleSeleccionArticulo({ id_articulo: 11, nombre: 'B' });
  app.cantidadesSeleccionadas['10'] = 2;
  app.cantidadesSeleccionadas['11'] = 3;
  app.onCelda = async (id, domicilio, cantidad) => {
    guardados.push([id, domicilio, cantidad]);
    app.celdas[`${id}:${domicilio}`] = cantidad;
    return true;
  };

  await app.agregarSeleccionadosSimple();

  assert.deepEqual(guardados, [['10', 7, '2'], ['11', 7, '3']]);
  assert.deepEqual(app.carritoItems.map((art) => art.id_articulo), [10, 11]);
  assert.equal(app.carritoEnLineaAbierto, true);
  assert.equal(app.cantidadesCarrito['10'], '2');
  assert.equal(app.cantidadSeleccionados, 0);
});

test('la cantidad editada en el carrito se guarda solo al pulsar Actualizar', async () => {
  const app = appEditable(true);
  app.articulos = [{ id_articulo: 10, nombre: 'A' }];
  app.celdas = { '10:7': '2' };
  app.abrirCarritoSimple();
  assert.equal(app.cantidadesCarrito['10'], '2');
  app.cantidadesCarrito['10'] = '5';
  assert.equal(app.celdas['10:7'], '2');
  app.onCelda = async (id, domicilio, cantidad) => {
    app.celdas[`${id}:${domicilio}`] = cantidad;
    return true;
  };
  await app.guardarCantidadCarrito(app.articulos[0]);
  assert.equal(app.celdas['10:7'], '5');
  assert.equal(app.cantidadesCarrito['10'], '5');
});

test('confirmar desde el carrito guarda primero una cantidad pendiente', async () => {
  const app = appEditable(true);
  app.articulos = [{ id_articulo: 10, nombre: 'A' }];
  app.celdas = { '10:7': '2' };
  app.abrirCarritoSimple();
  app.cantidadesCarrito['10'] = '4';
  const orden = [];
  app.onCelda = async (id, domicilio, cantidad) => {
    orden.push('guardar');
    app.celdas[`${id}:${domicilio}`] = cantidad;
    return true;
  };
  app.confirmarLote = async () => { orden.push('confirmar'); };

  await app.confirmarDesdeCarritoSimple();

  assert.deepEqual(orden, ['guardar', 'confirmar']);
  assert.equal(app.celdas['10:7'], '4');
});

test('el resumen simple separa descuento, IVA e impuesto interno sin alterar el total', () => {
  const app = appEditable(true);
  app.articulos = [{ id_articulo: 10, precio_unitario_neto: 100, alicuota_iva: 21, impuesto_interno_pct: 5 }];
  app.celdas = { '10:7': '2' };
  app.descPiePct = 10;
  app.recalcularPreviewEstimado();
  assert.equal(app.resumenPieSimple.bruto, 200);
  assert.equal(app.resumenPieSimple.descuento, 20);
  assert.equal(app.resumenPieSimple.subtotal, 180);
  assert.equal(app.resumenPieSimple.iva, 37.8);
  assert.equal(app.resumenPieSimple.internos, 9);
  assert.equal(app.resumenPieSimple.total, 226.8);
});

test('el estimado del pedido masivo conserva su comportamiento previo', () => {
  const app = appEditable(false);
  app.articulos = [{ id_articulo: 10, precio_unitario_neto: 100, alicuota_iva: 21, impuesto_interno_pct: 5 }];
  app.celdas = { '10:7': '1' };
  app.recalcularPreviewEstimado();
  assert.equal(app.previewEstimado.total, 121);
});

test('la galería pagina fotos sin perder la selección múltiple', async () => {
  const app = appEditable(true);
  app.idCliente = 3;
  app.urls = { articulos: '/articulos' };
  app.vistaCatalogoSimple = 'galeria';
  const urls = [];
  app.getJson = async (url) => {
    urls.push(url);
    return { ok: true, items: url.includes('pagina=2')
      ? [{ id_articulo: 25, nombre: '25', foto_url: 'https://ejemplo/foto.jpg' }]
      : Array.from({ length: 24 }, (_, i) => ({ id_articulo: i + 1, nombre: String(i + 1) })) };
  };
  await app._fetchArticulos({ todos: true, tam: 24 });
  app.toggleSeleccionArticulo(app.articulosBusqueda[0]);
  await app.cargarMasGaleriaSimple();
  assert.equal(app.articulosGaleriaSimple.length, 25);
  assert.equal(app.articulosGaleriaSimple[24].foto_url, 'https://ejemplo/foto.jpg');
  assert.equal(app.cantidadSeleccionados, 1);
  assert.equal(app.hayMasGaleriaSimple, false);
  assert.ok(urls[0].includes('fotos=1'));
  assert.ok(urls[1].includes('pagina=2'));
});

test('el teclado compacto reemplaza la cantidad inicial y conserva la multiselección', () => {
  const app = appEditable(true);
  const art = { id_articulo: 10, nombre: 'A' };
  app.toggleSeleccionArticulo(art);
  assert.equal(app.cantidadesSeleccionadas['10'], 1);
  app.abrirTecladoCantidad(art, 'seleccion');
  app.teclaCantidad('6');
  app.aceptarTecladoCantidad();
  assert.equal(app.cantidadesSeleccionadas['10'], 6);
  assert.equal(app.tecladoCantidadAbierto, false);
  assert.equal(app.cantidadSeleccionados, 1);
});
