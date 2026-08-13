/**
 * Modal Synap: comprobante de movimiento OPP/OPA.
 * Requiere elemento #renglones-por-movimiento-data (json_script Django).
 */
(function () {
    function initModalComprobanteMovimiento() {
        var modal = document.getElementById('modal-comprobante-movimiento');
        if (!modal || modal.dataset.mprComprobanteInit === '1') {
            return;
        }
        modal.dataset.mprComprobanteInit = '1';

        var backdrop = document.getElementById('modal-comprobante-backdrop');
        var btnCerrar = document.getElementById('modal-comprobante-cerrar');
        var btnDescargar = document.getElementById('modal-comprobante-descargar');
        var elFecha = document.getElementById('modal-comprobante-fecha');
        var elNro = document.getElementById('modal-comprobante-nro');
        var elRuta = document.getElementById('modal-comprobante-ruta');
        var elCantidad = document.getElementById('modal-comprobante-cantidad');
        var tbodyRenglones = document.getElementById('modal-comprobante-renglones-body');
        var wrapRenglones = document.getElementById('modal-comprobante-renglones-wrap');
        var msgRenglonesVacio = document.getElementById('modal-comprobante-renglones-vacio');
        var dataRenglonesEl = document.getElementById('renglones-por-movimiento-data');
        var lastFocus = null;

        function sanitizeFilename(s) {
            var base = (s || 'comprobante').replace(/[\\/:*?"<>|]/g, '-').replace(/\s+/g, '_').trim();
            return base || 'comprobante';
        }

        function fmtNum(n) {
            var x = Number(n);
            if (isNaN(x)) x = 0;
            return x.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        function pluralEs(n, singular, plural) {
            return Math.abs(Number(n)) === 1 ? singular : plural;
        }

        function fmtCantidadDuHtml(docenas, unidades) {
            var d = parseInt(docenas, 10);
            var u = parseInt(unidades, 10);
            if (isNaN(d)) d = 0;
            if (isNaN(u)) u = 0;
            return '<span class="block font-medium text-gray-900 dark:text-white">' + d + ' ' + pluralEs(d, 'docena', 'docenas') + '</span>' +
                '<span class="block text-xs text-gray-600 dark:text-gray-400">' + u + ' ' + pluralEs(u, 'unidad', 'unidades') + '</span>';
        }

        function setCantidadMovimientoCell(td, row, colKey, duKey, oppDu) {
            var qty = Number(row[colKey]) || 0;
            td.className = 'px-2 py-2 text-right align-top tabular-nums text-gray-700 dark:text-gray-300';
            if (qty <= 0 && colKey !== 'saldo') {
                td.innerHTML = '<span class="text-gray-400 dark:text-gray-500">—</span>';
                return;
            }
            if (oppDu && row[duKey]) {
                td.innerHTML = fmtCantidadDuHtml(row[duKey].docenas, row[duKey].unidades);
            } else if (colKey === 'saldo' || qty > 0) {
                td.textContent = fmtNum(qty);
            } else {
                td.innerHTML = '<span class="text-gray-400 dark:text-gray-500">—</span>';
            }
        }

        function parseRenglonesMap() {
            if (!dataRenglonesEl || !dataRenglonesEl.textContent) return {};
            try {
                return JSON.parse(dataRenglonesEl.textContent);
            } catch (e) {
                return {};
            }
        }

        function agruparFilasArticulo(rows) {
            if (!rows || !rows.length) return [];
            var grupos = [];
            var indice = {};
            rows.forEach(function (row) {
                var clave = row.id_articulo != null && row.id_articulo !== ''
                    ? ('id:' + row.id_articulo)
                    : ('cod:' + (row.codigo_articulo || '') + '|' + (row.descripcion || ''));
                if (indice[clave] === undefined) {
                    indice[clave] = grupos.length;
                    grupos.push({
                        codigo_articulo: row.codigo_articulo,
                        descripcion: row.descripcion,
                        filas: []
                    });
                }
                grupos[indice[clave]].filas.push(row);
            });
            return grupos;
        }

        function appendCeldaArticulo(tr, grupo, rowSpan) {
            var tdArt = document.createElement('td');
            tdArt.className = 'max-w-[10rem] border-r border-gray-100 px-3 py-2 align-top text-gray-800 dark:border-gray-700 dark:text-gray-200 sm:max-w-none sm:min-w-[12rem]';
            if (rowSpan > 1) tdArt.rowSpan = rowSpan;
            var cod = document.createElement('div');
            cod.className = 'font-mono text-[11px] text-gray-600 dark:text-gray-400';
            cod.textContent = grupo.codigo_articulo != null ? String(grupo.codigo_articulo) : '—';
            var desc = document.createElement('div');
            desc.className = 'mt-0.5 break-words text-sm leading-snug';
            desc.textContent = grupo.descripcion != null ? String(grupo.descripcion) : '—';
            tdArt.appendChild(cod);
            tdArt.appendChild(desc);
            tr.appendChild(tdArt);
        }

        function renderRenglones(codigoMov) {
            var map = parseRenglonesMap();
            var entry = map[String(codigoMov)] || {};
            var articulos = entry.articulos;
            var oppDu = !!entry.presentacion_opp_du;
            if (!articulos && entry.renglones) {
                articulos = agruparFilasArticulo(entry.renglones);
            }
            if (tbodyRenglones) tbodyRenglones.innerHTML = '';
            if (!articulos || !articulos.length) {
                if (wrapRenglones) wrapRenglones.classList.add('hidden');
                if (msgRenglonesVacio) msgRenglonesVacio.classList.remove('hidden');
                return;
            }
            if (wrapRenglones) wrapRenglones.classList.remove('hidden');
            if (msgRenglonesVacio) msgRenglonesVacio.classList.add('hidden');
            articulos.forEach(function (grupo) {
                var filas = grupo.filas || [];
                filas.forEach(function (row, idx) {
                    var tr = document.createElement('tr');
                    tr.className = 'transition-colors hover:bg-gray-50/80 dark:hover:bg-gray-700/30';
                    if (idx === 0) {
                        appendCeldaArticulo(tr, grupo, filas.length);
                    }
                    var tdDep = document.createElement('td');
                    tdDep.className = 'min-w-[5.5rem] px-2 py-2 align-top text-left text-gray-700 dark:text-gray-300';
                    tdDep.innerHTML = '<span class="block text-xs font-medium leading-snug">' + (row.nombre_deposito != null ? String(row.nombre_deposito) : '—') + '</span>';
                    tr.appendChild(tdDep);
                    [
                        { key: 'entrada', duKey: 'entrada_du' },
                        { key: 'salida', duKey: 'salida_du' },
                        { key: 'saldo', duKey: 'saldo_du' },
                    ].forEach(function (col) {
                        var td = document.createElement('td');
                        setCantidadMovimientoCell(td, row, col.key, col.duKey, oppDu);
                        tr.appendChild(td);
                    });
                    if (tbodyRenglones) tbodyRenglones.appendChild(tr);
                });
            });
        }

        function showModal(trigger) {
            if (!modal || !trigger) return;
            var fecha = trigger.getAttribute('data-fecha') || '-';
            var comprobante = trigger.getAttribute('data-comprobante') || '-';
            var ruta = trigger.getAttribute('data-ruta') || '-';
            var cantidad = trigger.getAttribute('data-cantidad') || '-';
            var pdfUrl = trigger.getAttribute('data-pdf-url') || '';
            var codigoMov = trigger.getAttribute('data-codigo-movimiento') || '';
            var presentacionDu = trigger.getAttribute('data-presentacion-du') === '1';
            if (elFecha) elFecha.textContent = fecha;
            if (elNro) elNro.textContent = comprobante;
            if (elRuta) elRuta.textContent = ruta;
            if (elCantidad) {
                if (presentacionDu) {
                    elCantidad.innerHTML = fmtCantidadDuHtml(
                        trigger.getAttribute('data-docenas'),
                        trigger.getAttribute('data-unidades')
                    );
                } else {
                    elCantidad.textContent = cantidad;
                }
            }
            renderRenglones(codigoMov);
            if (btnDescargar) {
                btnDescargar.setAttribute('href', pdfUrl);
                btnDescargar.setAttribute('download', 'movimiento-' + sanitizeFilename(comprobante) + '.pdf');
            }
            lastFocus = document.activeElement;
            modal.classList.remove('hidden');
            modal.setAttribute('aria-hidden', 'false');
            document.body.style.overflow = 'hidden';
            requestAnimationFrame(function () {
                if (btnDescargar && typeof btnDescargar.focus === 'function') btnDescargar.focus();
            });
        }

        function hideModal() {
            if (!modal) return;
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
            document.body.style.overflow = '';
            if (lastFocus && typeof lastFocus.focus === 'function') {
                try { lastFocus.focus(); } catch (e) { /* noop */ }
            }
            lastFocus = null;
        }

        document.querySelectorAll('.js-comprobante-modal-trigger').forEach(function (btn) {
            btn.addEventListener('click', function () { showModal(btn); });
        });
        if (btnCerrar) btnCerrar.addEventListener('click', hideModal);
        if (backdrop) backdrop.addEventListener('click', hideModal);
        document.addEventListener('keydown', function (ev) {
            if (ev.key !== 'Escape' || !modal || modal.classList.contains('hidden')) return;
            ev.preventDefault();
            hideModal();
        });
    }

    // Hook de prueba / re-init (p. ej. tests Node con DOM mínimo).
    if (typeof window !== 'undefined') {
        window.MprModalComprobanteMovimiento = {
            init: initModalComprobanteMovimiento,
        };
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initModalComprobanteMovimiento);
    } else {
        initModalComprobanteMovimiento();
    }
})();
