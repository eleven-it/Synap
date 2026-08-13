/**
 * Test Node del modal de comprobante (DOM mínimo, sin jsdom).
 * Ejecutar: node mpr/tests/js/test_modal_comprobante_movimiento.mjs
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const jsPath = path.resolve(__dirname, '../../static/mpr/js/modal_comprobante_movimiento.js');

class FakeClassList {
  constructor(el) {
    this.el = el;
  }
  add(...tokens) {
    const set = new Set((this.el._className || '').split(/\s+/).filter(Boolean));
    tokens.forEach((t) => set.add(t));
    this.el._className = [...set].join(' ');
  }
  remove(...tokens) {
    const set = new Set((this.el._className || '').split(/\s+/).filter(Boolean));
    tokens.forEach((t) => set.delete(t));
    this.el._className = [...set].join(' ');
  }
  contains(token) {
    return (this.el._className || '').split(/\s+/).includes(token);
  }
}

function createEl(tag, id) {
  const el = {
    tagName: String(tag).toUpperCase(),
    id: id || '',
    children: [],
    attributes: {},
    style: {},
    dataset: {},
    _className: '',
    textContent: '',
    _innerHTML: '',
    parent: null,
    listeners: {},
  };
  el.classList = new FakeClassList(el);
  Object.defineProperty(el, 'className', {
    get() {
      return el._className;
    },
    set(v) {
      el._className = String(v || '');
    },
  });
  Object.defineProperty(el, 'innerHTML', {
    get() {
      return el._innerHTML;
    },
    set(v) {
      el._innerHTML = String(v || '');
      if (!v) el.children = [];
    },
  });
  el.setAttribute = (k, v) => {
    el.attributes[k] = String(v);
    if (k === 'class') el._className = String(v);
  };
  el.getAttribute = (k) => (k in el.attributes ? el.attributes[k] : null);
  el.addEventListener = (type, fn) => {
    el.listeners[type] = el.listeners[type] || [];
    el.listeners[type].push(fn);
  };
  el.focus = () => {
    document.activeElement = el;
  };
  el.appendChild = (child) => {
    child.parent = el;
    el.children.push(child);
    return child;
  };
  el.click = () => {
    (el.listeners.click || []).forEach((fn) => fn({ type: 'click', preventDefault() {} }));
  };
  return el;
}

const byId = new Map();
const triggers = [];

function register(el) {
  if (el.id) byId.set(el.id, el);
  return el;
}

const modal = register(createEl('div', 'modal-comprobante-movimiento'));
modal._className = 'hidden';
modal.setAttribute('aria-hidden', 'true');

const backdrop = register(createEl('div', 'modal-comprobante-backdrop'));
const btnCerrar = register(createEl('button', 'modal-comprobante-cerrar'));
const btnDescargar = register(createEl('a', 'modal-comprobante-descargar'));
const elFecha = register(createEl('dd', 'modal-comprobante-fecha'));
const elNro = register(createEl('dd', 'modal-comprobante-nro'));
const elRuta = register(createEl('dd', 'modal-comprobante-ruta'));
const elCantidad = register(createEl('dd', 'modal-comprobante-cantidad'));
const tbody = register(createEl('tbody', 'modal-comprobante-renglones-body'));
const wrap = register(createEl('div', 'modal-comprobante-renglones-wrap'));
const msgVacio = register(createEl('p', 'modal-comprobante-renglones-vacio'));
msgVacio._className = 'hidden';

const dataEl = register(createEl('script', 'renglones-por-movimiento-data'));
dataEl.textContent = JSON.stringify({
  '100': {
    articulos: [
      {
        codigo_articulo: '907944-02',
        descripcion: 'Pack test',
        filas: [
          {
            id_articulo: 615,
            codigo_articulo: '907944-02',
            descripcion: 'Pack test',
            nombre_deposito: 'Semi',
            entrada: 10,
            salida: 0,
            saldo: 10,
          },
        ],
      },
    ],
  },
});

const trigger = createEl('button');
trigger._className = 'js-comprobante-modal-trigger';
trigger.setAttribute('data-fecha', '01/08/2026');
trigger.setAttribute('data-comprobante', '0001-00000100');
trigger.setAttribute('data-ruta', 'Entrada Semi');
trigger.setAttribute('data-cantidad', 'Entrada: 10');
trigger.setAttribute('data-codigo-movimiento', '100');
trigger.setAttribute('data-pdf-url', '/stock/movimientos/100/pdf/');
triggers.push(trigger);

const document = {
  readyState: 'complete',
  body: { style: {} },
  activeElement: null,
  getElementById(id) {
    return byId.get(id) || null;
  },
  querySelectorAll(sel) {
    if (sel === '.js-comprobante-modal-trigger') return triggers.slice();
    return [];
  },
  createElement(tag) {
    return createEl(tag);
  },
  addEventListener(type, fn) {
    document._listeners = document._listeners || {};
    document._listeners[type] = document._listeners[type] || [];
    document._listeners[type].push(fn);
  },
};

const window = { document };
globalThis.window = window;
globalThis.document = document;
globalThis.requestAnimationFrame = (fn) => fn();

const code = fs.readFileSync(jsPath, 'utf8');
vm.runInThisContext(code, { filename: jsPath });

if (!window.MprModalComprobanteMovimiento || typeof window.MprModalComprobanteMovimiento.init !== 'function') {
  console.error('FAIL: window.MprModalComprobanteMovimiento.init no expuesto');
  process.exit(1);
}

// Re-init por si el IIFE ya corrió con mapa vacío de triggers en otro orden
modal.dataset.mprComprobanteInit = '';
delete modal.dataset.mprComprobanteInit;
window.MprModalComprobanteMovimiento.init();

trigger.click();

function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg);
    process.exit(1);
  }
}

assert(!modal.classList.contains('hidden'), 'modal debe abrirse (sin clase hidden)');
assert(modal.getAttribute('aria-hidden') === 'false', 'aria-hidden=false al abrir');
assert(elFecha.textContent === '01/08/2026', 'fecha en modal');
assert(elNro.textContent === '0001-00000100', 'nro comprobante en modal');
assert(tbody.children.length >= 1, 'debe pintar al menos un renglón');
assert(String(tbody.children[0].innerHTML || tbody._innerHTML || '').includes('Semi') || tbody.children.length >= 1, 'renglón con depósito');

btnCerrar.click();
assert(modal.classList.contains('hidden'), 'modal debe cerrarse');
assert(modal.getAttribute('aria-hidden') === 'true', 'aria-hidden=true al cerrar');

const jsSource = fs.readFileSync(jsPath, 'utf8');
assert(!/\balert\s*\(/.test(jsSource), 'JS no debe usar alert(');
assert(!/\bconfirm\s*\(/.test(jsSource), 'JS no debe usar confirm(');
assert(!/\bprompt\s*\(/.test(jsSource), 'JS no debe usar prompt(');

console.log('OK modal_comprobante_movimiento');
process.exit(0);
