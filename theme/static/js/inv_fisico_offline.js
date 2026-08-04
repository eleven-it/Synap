/**
 * Inventario físico — IndexedDB offline-first (conteo ciego).
 * Expone window.InvFisicoOffline para templates móviles Synap.
 */
(function (global) {
  'use strict';

  var DB_NAME = 'synap_inv_fisico';
  var DB_VERSION = 1;
  var STORE_CATALOGO = 'catalogo';
  var STORE_COLA = 'cola';
  var STORE_META = 'meta';

  function promisifyRequest(req) {
    return new Promise(function (resolve, reject) {
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error || new Error('IndexedDB error')); };
    });
  }

  function txDone(tx) {
    return new Promise(function (resolve, reject) {
      tx.oncomplete = function () { resolve(); };
      tx.onerror = function () { reject(tx.error || new Error('IndexedDB tx error')); };
      tx.onabort = function () { reject(tx.error || new Error('IndexedDB tx abort')); };
    });
  }

  function openDB() {
    return new Promise(function (resolve, reject) {
      if (!global.indexedDB) {
        reject(new Error('IndexedDB no disponible en este navegador.'));
        return;
      }
      var req = global.indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = function (ev) {
        var db = ev.target.result;
        if (!db.objectStoreNames.contains(STORE_CATALOGO)) {
          var cat = db.createObjectStore(STORE_CATALOGO, { keyPath: 'id_articulo' });
          cat.createIndex('ean', 'ean', { multiEntry: true });
        }
        if (!db.objectStoreNames.contains(STORE_COLA)) {
          db.createObjectStore(STORE_COLA, { keyPath: 'client_event_id' });
        }
        if (!db.objectStoreNames.contains(STORE_META)) {
          db.createObjectStore(STORE_META, { keyPath: 'clave' });
        }
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error || new Error('No se pudo abrir IndexedDB.')); };
    });
  }

  function normalizarEans(articulo) {
    var eans = articulo.ean;
    if (!Array.isArray(eans)) {
      eans = eans ? [String(eans)] : [];
    }
    return eans.map(function (e) { return String(e || '').trim(); }).filter(Boolean);
  }

  async function guardarCatalogo(meta, articulos) {
    var db = await openDB();
    var tx = db.transaction([STORE_CATALOGO, STORE_META], 'readwrite');
    var catStore = tx.objectStore(STORE_CATALOGO);
    catStore.clear();
    (articulos || []).forEach(function (art) {
      var row = Object.assign({}, art);
      row.ean = normalizarEans(row);
      catStore.put(row);
    });
    var metaStore = tx.objectStore(STORE_META);
    metaStore.put({ clave: 'catalogo', valor: meta || {} });
    await txDone(tx);
    db.close();
    return { articulos: (articulos || []).length };
  }

  async function buscarPorEan(ean) {
    /** Coincidencia exacta por EAN (NroCodBarra / NroCodBarraF). Sin código manual ni ID. */
    var codigo = String(ean || '').trim();
    if (!codigo) return null;
    var db = await openDB();
    var tx = db.transaction(STORE_CATALOGO, 'readonly');
    var store = tx.objectStore(STORE_CATALOGO);
    var idx = store.index('ean');
    var hit = await promisifyRequest(idx.get(codigo));
    await txDone(tx);
    db.close();
    return hit || null;
  }

  async function buscarPorEanONombre(consulta, limite) {
    /**
     * Ingreso manual: 1) EAN exacto; 2) nombre de artículo (contiene, sin distinguir mayúsculas).
     * No busca por código manual ni ID de sistema. Devuelve lista (0..N).
     */
    var q = String(consulta || '').trim();
    if (!q) return [];
    var porEan = await buscarPorEan(q);
    if (porEan) return [porEan];

    var qNorm = q.toLowerCase();
    if (qNorm.length < 2) return [];

    var db = await openDB();
    var tx = db.transaction(STORE_CATALOGO, 'readonly');
    var store = tx.objectStore(STORE_CATALOGO);
    var all = await promisifyRequest(store.getAll());
    await txDone(tx);
    db.close();

    var hits = [];
    (all || []).forEach(function (val) {
      var nombre = String((val && val.nombre) || '').toLowerCase();
      if (nombre && nombre.indexOf(qNorm) !== -1) {
        hits.push(val);
      }
    });
    hits.sort(function (a, b) {
      return String(a.nombre || '').localeCompare(String(b.nombre || ''), 'es');
    });
    if (limite != null && limite > 0 && hits.length > limite) {
      hits = hits.slice(0, limite);
    }
    return hits;
  }

  async function contarCatalogo() {
    var db = await openDB();
    var tx = db.transaction(STORE_CATALOGO, 'readonly');
    var store = tx.objectStore(STORE_CATALOGO);
    var count = await promisifyRequest(store.count());
    await txDone(tx);
    db.close();
    return count || 0;
  }

  function claveConteosLocales(idCampana, idDeposito) {
    return 'conteos_local_c' + String(idCampana) + '_d' + String(idDeposito);
  }

  async function listarConteosLocales(idCampana, idDeposito) {
    var db = await openDB();
    var tx = db.transaction(STORE_META, 'readonly');
    var store = tx.objectStore(STORE_META);
    var row = await promisifyRequest(store.get(claveConteosLocales(idCampana, idDeposito)));
    await txDone(tx);
    db.close();
    var mapa = (row && row.valor) || {};
    var lista = Object.keys(mapa).map(function (k) {
      return Object.assign({}, mapa[k], { id_articulo: Number(k) });
    });
    lista.sort(function (a, b) {
      return String(b.ts || '').localeCompare(String(a.ts || ''));
    });
    return lista;
  }

  async function obtenerConteoLocal(idCampana, idDeposito, idArticulo) {
    var db = await openDB();
    var tx = db.transaction(STORE_META, 'readonly');
    var store = tx.objectStore(STORE_META);
    var row = await promisifyRequest(store.get(claveConteosLocales(idCampana, idDeposito)));
    await txDone(tx);
    db.close();
    var mapa = (row && row.valor) || {};
    var key = String(idArticulo);
    return mapa[key] ? Object.assign({}, mapa[key], { id_articulo: Number(idArticulo) }) : null;
  }

  async function guardarConteoLocal(idCampana, idDeposito, registro) {
    if (!registro || registro.id_articulo == null) {
      throw new Error('id_articulo obligatorio para conteo local.');
    }
    var db = await openDB();
    var tx = db.transaction(STORE_META, 'readwrite');
    var store = tx.objectStore(STORE_META);
    var clave = claveConteosLocales(idCampana, idDeposito);
    var prev = await promisifyRequest(store.get(clave));
    var mapa = (prev && prev.valor) ? Object.assign({}, prev.valor) : {};
    var key = String(registro.id_articulo);
    mapa[key] = {
      cantidad: String(registro.cantidad),
      codigo: String(registro.codigo || '-'),
      nombre: String(registro.nombre || '-'),
      ts: registro.ts || new Date().toISOString(),
    };
    store.put({ clave: clave, valor: mapa });
    await txDone(tx);
    db.close();
    return mapa[key];
  }

  async function encolarEvento(evento) {
    if (!evento || !evento.client_event_id) {
      throw new Error('client_event_id obligatorio.');
    }
    var db = await openDB();
    var tx = db.transaction(STORE_COLA, 'readwrite');
    var store = tx.objectStore(STORE_COLA);
    var all = await promisifyRequest(store.getAll());
    var idCampana = Number(evento.id_campana);
    var idDeposito = Number(evento.id_deposito);
    var idArticulo = Number(evento.id_articulo);
    (all || []).forEach(function (ev) {
      if (!ev || ev.estado !== 'pendiente') return;
      if (Number(ev.id_campana) !== idCampana) return;
      if (Number(ev.id_deposito) !== idDeposito) return;
      if (Number(ev.id_articulo) !== idArticulo) return;
      store.delete(ev.client_event_id);
    });
    var row = Object.assign({}, evento, {
      estado: evento.estado || 'pendiente',
      client_ts: evento.client_ts || new Date().toISOString(),
    });
    store.put(row);
    await txDone(tx);
    db.close();
    return row;
  }

  async function listarCola(idCampana) {
    var db = await openDB();
    var tx = db.transaction(STORE_COLA, 'readonly');
    var store = tx.objectStore(STORE_COLA);
    var all = await promisifyRequest(store.getAll());
    await txDone(tx);
    db.close();
    var cid = idCampana != null ? Number(idCampana) : null;
    return (all || []).filter(function (ev) {
      if (cid == null) return true;
      return Number(ev.id_campana) === cid;
    }).sort(function (a, b) {
      return String(a.client_ts || '').localeCompare(String(b.client_ts || ''));
    });
  }

  async function marcarAceptados(clientEventIds) {
    var ids = new Set((clientEventIds || []).map(String));
    if (!ids.size) return 0;
    var db = await openDB();
    var tx = db.transaction(STORE_COLA, 'readwrite');
    var store = tx.objectStore(STORE_COLA);
    var all = await promisifyRequest(store.getAll());
    var removidos = 0;
    (all || []).forEach(function (ev) {
      if (ids.has(String(ev.client_event_id))) {
        store.delete(ev.client_event_id);
        removidos += 1;
      }
    });
    await txDone(tx);
    db.close();
    return removidos;
  }

  async function syncBatch(url, csrf, idCampana) {
    var pendientes = await listarCola(idCampana);
    var aEnviar = pendientes.filter(function (ev) {
      return ev.estado === 'pendiente' || ev.estado === 'conflicto';
    });
    if (!aEnviar.length) {
      return { aceptados: [], conflictos: [], rechazados: [], enviados: 0 };
    }
    var payload = {
      id_campana: idCampana,
      eventos: aEnviar.map(function (ev) {
        return {
          client_event_id: ev.client_event_id,
          id_articulo: ev.id_articulo,
          id_deposito: ev.id_deposito,
          cantidad: ev.cantidad,
          client_ts: ev.client_ts,
        };
      }),
    };
    var resp = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'X-CSRFToken': csrf || '',
      },
      body: JSON.stringify(payload),
    });
    var data = await resp.json().catch(function () { return {}; });
    if (!resp.ok) {
      throw new Error(data.error || 'Error al sincronizar conteos.');
    }
    var aceptados = data.aceptados || [];
    var idsAceptados = aceptados.map(function (a) { return a.client_event_id; });
    await marcarAceptados(idsAceptados);

    var db = await openDB();
    var tx = db.transaction(STORE_COLA, 'readwrite');
    var store = tx.objectStore(STORE_COLA);
    (data.conflictos || []).forEach(function (c) {
      if (!c.client_event_id) return;
      store.put(Object.assign({}, c, {
        client_event_id: c.client_event_id,
        estado: 'conflicto',
        motivo: c.motivo || 'Conflicto de conteo.',
      }));
    });
    (data.rechazados || []).forEach(function (r) {
      if (!r.client_event_id) return;
      store.put(Object.assign({}, r, {
        client_event_id: r.client_event_id,
        estado: 'rechazado',
        motivo: r.motivo || 'Conteo rechazado.',
      }));
    });
    await txDone(tx);
    db.close();

    return {
      aceptados: aceptados,
      conflictos: data.conflictos || [],
      rechazados: data.rechazados || [],
      enviados: aEnviar.length,
    };
  }

  async function contarPendientes(idCampana) {
    var cola = await listarCola(idCampana);
    return cola.filter(function (ev) {
      return ev.estado === 'pendiente';
    }).length;
  }

  global.InvFisicoOffline = {
    DB_NAME: DB_NAME,
    openDB: openDB,
    guardarCatalogo: guardarCatalogo,
    buscarPorEan: buscarPorEan,
    buscarPorEanONombre: buscarPorEanONombre,
    contarCatalogo: contarCatalogo,
    encolarEvento: encolarEvento,
    listarCola: listarCola,
    syncBatch: syncBatch,
    marcarAceptados: marcarAceptados,
    contarPendientes: contarPendientes,
    listarConteosLocales: listarConteosLocales,
    obtenerConteoLocal: obtenerConteoLocal,
    guardarConteoLocal: guardarConteoLocal,
  };
})(typeof window !== 'undefined' ? window : globalThis);
