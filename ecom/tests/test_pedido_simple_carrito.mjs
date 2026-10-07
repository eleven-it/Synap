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

test('pedido simple guarda las cantidades de varios artículos y abre el carrito', async () => {
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
  assert.equal(app.carritoAbierto, true);
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
