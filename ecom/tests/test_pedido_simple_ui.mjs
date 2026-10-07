import test from 'node:test';
import assert from 'node:assert/strict';

let crearApp;
globalThis.window = {
  Alpine: { data(nombre, factory) { if (nombre === 'pedidoMasivoApp') crearApp = factory; } },
};
globalThis.document = {
  addEventListener() {},
  querySelector() { return null; },
};
await import('../static/ecom/js/pedido_masivo_app.mjs');

test('pedido simple: selección única, filtros y carrito con cantidades positivas', () => {
  const app = crearApp();
  app.modoSimple = true;
  app.sucursales = [{ id_cliente_domicilio: 7 }];
  app.articulos = [
    { id_articulo: 10, nombre: 'A' },
    { id_articulo: 11, nombre: 'B' },
  ];
  app.celdas = { '10:7': '2', '11:7': '0' };
  assert.deepEqual(app.carritoItems.map((a) => a.id_articulo), [10]);

  app.toggleSeleccionArticulo({ id_articulo: 10, nombre: 'A' });
  app.toggleSeleccionArticulo({ id_articulo: 11, nombre: 'B' });
  assert.deepEqual(Object.keys(app.articulosSeleccionados), ['11']);

  app.marcaFiltro = '3';
  app.rubroFiltro = '4';
  app.subrubroFiltro = '5';
  assert.equal(app.parametrosFiltrosCatalogo(), 'marca_id=3&rubro_id=4&subrubro_id=5');
  assert.equal(app.parametroDomicilioCatalogo(), '&id_cliente_domicilio=7');
});

test('pedido simple: Agregar artículo guarda la cantidad elegida en el domicilio', async () => {
  const app = crearApp();
  app.modoSimple = true;
  app.draftId = 1;
  app.draftEstado = 'borrador';
  app.sucursales = [{ id_cliente_domicilio: 7 }];
  app.articulosSeleccionados = { 10: { id_articulo: 10, nombre: 'A' } };
  app.cantidadNuevoArticulo = 3;
  const llamadas = [];
  app.agregarSeleccionados = async () => { llamadas.push('agregar'); };
  app.onCelda = async (...args) => { llamadas.push(args); };

  await app.agregarArticuloSimple();
  assert.deepEqual(llamadas, ['agregar', [10, 7, '3']]);
  assert.equal(app.cantidadNuevoArticulo, 1);
});
