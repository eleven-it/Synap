/**
 * Controlador específico para el reporte BO vs Stock vs Facturación.
 * Maneja tabs, KPIs clickeables y renderizado de tablas estilo Excel.
 */

(function() {
    'use strict';
    
    // Verificar que estamos en el reporte correcto
    const dashboardRoot = document.querySelector('#dashboard-root');
    const reportSlug = dashboardRoot?.dataset?.reportSlug || '';
    
    if (reportSlug !== 'bo-stock-facturacion') {
        return; // No ejecutar en otros reportes
    }
    
    console.log('📊 [BO-Stock-Facturacion] Inicializando controlador...');
    
    // =========================================================
    // CONSTANTES Y CONFIGURACIÓN
    // =========================================================
    
    const CURRENCY_FORMAT = new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    
    const NUMBER_FORMAT = new Intl.NumberFormat('es-AR', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    });
    
    // =========================================================
    // UTILIDADES DE FORMATO
    // =========================================================
    
    /**
     * Formatea un valor como moneda argentina
     */
    function formatCurrency(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return '$0,00';
        }
        return CURRENCY_FORMAT.format(value);
    }
    
    /**
     * Formatea un valor numérico con separadores de miles
     */
    function formatNumber(value) {
        if (value === null || value === undefined || isNaN(value)) {
            return '0';
        }
        return NUMBER_FORMAT.format(value);
    }

    function escHtml(s) {
        if (s == null || s === undefined) return '';
        var t = String(s);
        return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /**
     * Filtra filas por búsqueda predictiva (mín. 2 caracteres). keys = array de nombres de propiedades a buscar.
     */
    function filterBoDataBySearch(data, query, keys) {
        if (!data || !Array.isArray(data)) return data;
        var q = (query && String(query).trim()) || '';
        if (q.length < 2) return data;
        q = q.toLowerCase();
        return data.filter(function (row) {
            return keys.some(function (k) {
                var val = row[k];
                if (val == null) return false;
                return String(val).toLowerCase().indexOf(q) !== -1;
            });
        });
    }

    /** Escapa string para uso en atributo HTML value. */
    function boSearchEscAttr(s) {
        if (s == null || s === '') return '';
        return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    /** HTML del input de búsqueda para un tab (id, placeholder, valor actual opcional). Misma estructura que Agrupar por: label arriba, campo abajo; altura coherente con el campo de agrupación. */
    function boSearchInputHtml(id, placeholder, currentValue) {
        var valAttr = (currentValue != null && currentValue !== '') ? ' value="' + boSearchEscAttr(currentValue) + '"' : '';
        return '<div class="w-full min-w-0">' +
            '<label for="' + id + '" class="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-2">Buscar</label>' +
            '<input type="text" id="' + id + '" placeholder="' + (placeholder || 'Escriba al menos 2 caracteres...') + '"' + valAttr + ' ' +
            'class="w-full min-w-0 min-h-[2.5rem] py-2 px-3 text-xs border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-sky-400 focus:border-sky-400" autocomplete="off">' +
            '</div>';
    }

    var boSearchTimeout = null;
    /** Debounce en ms para no re-renderizar en cada tecla y no perder foco. */
    var BO_SEARCH_DEBOUNCE_MS = 400;
    function attachBoSearchListener(inputId, onFilter) {
        var el = document.getElementById(inputId);
        if (!el || !onFilter) return;
        el.removeEventListener('input', el._boSearchHandler);
        el._boSearchHandler = function () {
            if (boSearchTimeout) clearTimeout(boSearchTimeout);
            boSearchTimeout = setTimeout(function () { onFilter(); }, BO_SEARCH_DEBOUNCE_MS);
        };
        el.addEventListener('input', el._boSearchHandler);
    }

    /**
     * Escribe el HTML del buscador en el slot (70/30) y el contenido de la tabla en el container.
     * Usar cuando se hace render completo (primera carga o sin content-only).
     */
    function boSetSearchAndContent(container, searchInputId, placeholder, searchQuery, tablePartHtml) {
        var searchSlot = document.getElementById(container.id.replace('-content', '-search-slot'));
        if (searchSlot) searchSlot.innerHTML = boSearchInputHtml(searchInputId, placeholder, searchQuery);
        container.innerHTML = '<div class="bo-tab-content-area">' + tablePartHtml + '</div>';
    }

    /**
     * Actualiza solo el área de contenido del tab (tabla/leyenda), sin tocar el input de búsqueda,
     * para no destruir el input y no perder el foco al filtrar.
     * Si el input ya existe (en el slot) y hay .bo-tab-content-area, pone tablePartHtml ahí y ejecuta onUpdated(container).
     * Retorna true si se hizo solo actualización de contenido; false si hay que hacer innerHTML completo.
     */
    function boUpdateContentOnly(container, searchInputId, tablePartHtml, onUpdated) {
        var inputEl = document.getElementById(searchInputId);
        var contentArea = container.querySelector('.bo-tab-content-area');
        if (inputEl && contentArea) {
            contentArea.innerHTML = tablePartHtml;
            if (onUpdated) onUpdated(container);
            return true;
        }
        return false;
    }

    /**
     * Construye HTML para tooltip de OC pendientes (estilo ventas-netas).
     * Estructura: header (OC pendientes / N órdenes), separador, filas Fecha / Nro / Vto / Proveedor / Qty por OC.
     */
    function buildBoDetalleTooltipHtml(bo_detalle) {
        if (!bo_detalle || bo_detalle.length === 0) {
            return '<div class="font-bold text-sm text-white mb-0.5">BO por comprobante</div>' +
                '<div class="text-sky-300 text-[10px] font-medium">Sin datos</div>';
        }
        var n = bo_detalle.length;
        var header = '<div class="font-bold text-sm text-white mb-1">BO por comprobante</div>' +
            '<div class="text-sky-300 text-[10px] font-medium mb-1">' + n + ' comprobante' + (n !== 1 ? 's' : '') + '</div>';
        var lines = bo_detalle.map(function (d) {
            var fecha = escHtml(d.fecha || '-');
            var nro = escHtml(d.nro_comprobante || '-');
            var cliente = escHtml(d.cliente || '-');
            var qty = formatNumber(d.cantidad);
            var nroRaw = (d.nro_comprobante || '').replace(/"/g, '&quot;');
            return '<div class="py-1 border-b border-slate-700/50 last:border-0">' +
                '<div class="flex items-center justify-between gap-2 text-xs">' +
                '<span class="text-slate-400 shrink-0">' + fecha + '</span>' +
                '<span class="bo-comp-link text-sky-300 truncate min-w-0 cursor-pointer hover:text-sky-200 hover:underline" data-nro-comprobante="' + nroRaw + '" title="Ir al comprobante (próximamente)">' + nro + '</span>' +
                '<span class="text-emerald-300 font-semibold shrink-0">' + qty + '</span></div>' +
                '<div class="text-slate-300 text-[10px] mt-0.5 truncate" title="' + (d.cliente || '') + '">' + cliente + '</div>' +
                '</div>';
        });
        return header + '<div class="border-t border-slate-700 pt-1 mt-1" style="max-height: 260px; overflow-y: auto; overflow-x: hidden;">' + lines.join('') + '</div>';
    }

    function buildReservadoDetalleTooltipHtml(reservado_detalle) {
        if (!reservado_detalle || reservado_detalle.length === 0) {
            return '<div class="font-bold text-sm text-white mb-0.5">Reservado (PED En preparación/Preparado/Parcial)</div>' +
                '<div class="text-sky-300 text-[10px] font-medium">Sin datos</div>';
        }
        var n = reservado_detalle.length;
        var header = '<div class="font-bold text-sm text-white mb-1">Reservado por comprobante</div>' +
            '<div class="text-sky-300 text-[10px] font-medium mb-1">' + n + ' comprobante' + (n !== 1 ? 's' : '') + ' (PED En preparación/Preparado/Parcial)</div>';
        var lines = reservado_detalle.map(function (d) {
            var fecha = escHtml(d.fecha || '-');
            var nro = escHtml(d.nro_comprobante || '-');
            var cliente = escHtml(d.cliente || '-');
            var estado = escHtml(d.estado || '-');
            var qty = formatNumber(d.cantidad);
            return '<div class="py-1 border-b border-slate-700/50 last:border-0">' +
                '<div class="flex items-center justify-between gap-2 text-xs">' +
                '<span class="text-slate-400 shrink-0">' + fecha + '</span>' +
                '<span class="text-sky-300 truncate min-w-0" title="' + nro + '">' + nro + '</span>' +
                '<span class="text-amber-400 text-[9px] shrink-0">' + estado + '</span>' +
                '<span class="text-amber-300 font-semibold shrink-0">' + qty + '</span></div>' +
                '<div class="text-slate-300 text-[10px] mt-0.5 truncate" title="' + (d.cliente || '') + '">' + cliente + '</div>' +
                '</div>';
        });
        return header + '<div class="border-t border-slate-700 pt-1 mt-1" style="max-height: 260px; overflow-y: auto; overflow-x: hidden;">' + lines.join('') + '</div>';
    }

    function buildStockPorDepositoTooltipHtml(stock_por_deposito) {
        if (!stock_por_deposito || stock_por_deposito.length === 0) {
            return '<div class="font-bold text-sm text-white mb-0.5">Stock por depósito</div>' +
                '<div class="text-sky-300 text-[10px] font-medium">Sin datos</div>';
        }
        var lines = stock_por_deposito.map(function (d) {
            var qty = formatNumber(d.saldo);
            var nom = escHtml(d.deposito || 'Sin nombre');
            return '<div class="flex items-center justify-between gap-3 py-0.5"><span class="text-slate-300 text-xs">' + nom + '</span><span class="text-emerald-300 font-semibold text-xs">' + qty + '</span></div>';
        });
        return '<div class="font-bold text-sm text-white mb-1">Stock por depósito</div>' +
            '<div class="space-y-0.5 border-t border-slate-700 pt-1 mt-1">' + lines.join('') + '</div>';
    }

    function buildOcTooltipHtml(oc_detalle) {
        if (!oc_detalle || oc_detalle.length === 0) {
            return '<div class="font-bold text-sm text-white mb-0.5">OC pendientes</div>' +
                '<div class="text-sky-300 text-[10px] font-medium">Sin órdenes pendientes</div>';
        }
        var max = 10;
        var list = oc_detalle.slice(0, max);
        var extra = oc_detalle.length > max ? oc_detalle.length - max : 0;
        var header = '<div class="mb-2">' +
            '<div class="font-bold text-sm text-white mb-0.5">OC pendientes</div>' +
            '<div class="text-sky-300 text-[10px] font-medium">' + escHtml(oc_detalle.length) + ' orden' + (oc_detalle.length !== 1 ? 'es' : '') + '</div>' +
            '</div>';
        var body = '';
        list.forEach(function(o, i) {
            var nro = escHtml(o.nro_comprobante || o.nro_comp_busq || '');
            var fecha = escHtml(o.fecha || '');
            var vto = escHtml(o.vencimiento || '-');
            var prov = escHtml(o.proveedor || '');
            var qty = formatNumber(o.qty_pend);
            var sep = i > 0 ? '<div class="mt-2 pt-2 border-t border-slate-700"></div>' : '';
            body += sep + '<div class="py-1.5">' +
                '<div class="flex items-center justify-between gap-3 mt-1"><div class="text-slate-400 text-[9px]">Fecha:</div><div class="text-white font-semibold text-xs">' + fecha + '</div></div>' +
                '<div class="flex items-center justify-between gap-3 mt-1"><div class="text-slate-400 text-[9px]">Nro:</div><div class="text-sky-300 font-semibold text-xs">' + nro + '</div></div>' +
                '<div class="flex items-center justify-between gap-3 mt-1"><div class="text-slate-400 text-[9px]">Vto:</div><div class="text-white font-semibold text-xs">' + vto + '</div></div>' +
                '<div class="flex items-center justify-between gap-3 mt-1"><div class="text-slate-400 text-[9px] shrink-0">Proveedor:</div><div class="text-white font-semibold text-xs truncate min-w-0 max-w-[140px]" title="' + prov + '">' + prov + '</div></div>' +
                '<div class="flex items-center justify-between gap-3 mt-1"><div class="text-slate-400 text-[9px]">Qty pend.:</div><div class="text-emerald-300 font-semibold text-xs">' + qty + ' u</div></div>' +
                '</div>';
        });
        if (extra > 0) {
            body += '<div class="mt-2 pt-2 border-t border-slate-700"><div class="text-slate-400 text-[9px]">… y ' + extra + ' más</div></div>';
        }
        return header + '<div class="py-2 border-t border-slate-700">' +
            '<div class="text-slate-400 text-[9px] uppercase tracking-wide mb-1.5">Detalle</div>' +
            body + '</div>';
    }

    var _ocTooltipEl = null;
    var _stickyHideTimeout = null;

    function getOcTooltipEl() {
        if (_ocTooltipEl) return _ocTooltipEl;
        _ocTooltipEl = document.createElement('div');
        _ocTooltipEl.setAttribute('class', 'absolute bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-2xl opacity-0 z-[9999] border border-slate-700 overflow-y-auto');
        _ocTooltipEl.style.fontFamily = 'system-ui, sans-serif';
        _ocTooltipEl.style.minWidth = '180px';
        _ocTooltipEl.style.maxWidth = '280px';
        _ocTooltipEl.style.maxHeight = '400px';
        _ocTooltipEl.style.transition = 'opacity 0.2s ease-in-out';
        _ocTooltipEl.style.pointerEvents = 'none';
        _ocTooltipEl._mouseInside = false;
        _ocTooltipEl._showingBo = false;
        document.body.appendChild(_ocTooltipEl);
        return _ocTooltipEl;
    }

    function hideStickyTooltip() {
        if (_stickyHideTimeout) clearTimeout(_stickyHideTimeout);
        _stickyHideTimeout = null;
        var t = getOcTooltipEl();
        t._showingBo = false;
        t._mouseInside = false;
        t.style.opacity = '0';
        t.style.pointerEvents = 'none';
    }
    function scheduleHideSticky() {
        if (_stickyHideTimeout) clearTimeout(_stickyHideTimeout);
        _stickyHideTimeout = setTimeout(hideStickyTooltip, 350);
    }
    function cancelHideSticky() {
        if (_stickyHideTimeout) { clearTimeout(_stickyHideTimeout); _stickyHideTimeout = null; }
    }

    function setupBoDetalleTooltips(container) {
        if (!container) return;
        var cells = container.querySelectorAll('.bo-qty-cell');
        var tooltip = getOcTooltipEl();
        var padding = 10;

        if (!tooltip._boDetalleListeners) {
            tooltip._boDetalleListeners = true;
            tooltip.addEventListener('mouseenter', function () {
                tooltip._mouseInside = true;
                cancelHideSticky();
            });
            tooltip.addEventListener('mouseleave', function () {
                hideStickyTooltip();
            });
        }

        cells.forEach(function (cell) {
            cell.addEventListener('mouseover', function (e) {
                cancelHideSticky();
                tooltip._showingBo = true;
                tooltip._mouseInside = false;
                var raw = cell.getAttribute('data-bo-detalle');
                var data = [];
                try { data = raw ? JSON.parse(raw) : []; } catch (_) { }
                tooltip.innerHTML = buildBoDetalleTooltipHtml(data);
                tooltip.style.opacity = '1';
                tooltip.style.pointerEvents = 'auto';
                var left = e.pageX + padding;
                var top = e.pageY - padding;
                if (left + 280 > window.innerWidth) left = e.pageX - 280 - padding;
                if (top + 200 > window.innerHeight) top = e.pageY - 200 - padding;
                if (top < padding) top = padding;
                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
            });
            cell.addEventListener('mouseout', function (e) {
                var to = e.relatedTarget;
                if (to && tooltip.contains && tooltip.contains(to)) {
                    cancelHideSticky();
                    return;
                }
                scheduleHideSticky();
            });
        });
    }

    function setupReservadoDetalleTooltips(container) {
        if (!container) return;
        var cells = container.querySelectorAll('.reservado-cell');
        var tooltip = getOcTooltipEl();
        var padding = 10;

        if (!tooltip._boDetalleListeners) {
            tooltip._boDetalleListeners = true;
            tooltip.addEventListener('mouseenter', function () {
                tooltip._mouseInside = true;
                cancelHideSticky();
            });
            tooltip.addEventListener('mouseleave', function () {
                hideStickyTooltip();
            });
        }

        cells.forEach(function (cell) {
            cell.addEventListener('mouseover', function (e) {
                cancelHideSticky();
                tooltip._showingBo = true;
                tooltip._mouseInside = false;
                var raw = cell.getAttribute('data-reservado-detalle');
                var data = [];
                try { data = raw ? JSON.parse(raw) : []; } catch (_) { }
                tooltip.innerHTML = buildReservadoDetalleTooltipHtml(data);
                tooltip.style.opacity = '1';
                tooltip.style.pointerEvents = 'auto';
                var left = e.pageX + padding;
                var top = e.pageY - padding;
                if (left + 280 > window.innerWidth) left = e.pageX - 280 - padding;
                if (top + 200 > window.innerHeight) top = e.pageY - 200 - padding;
                if (top < padding) top = padding;
                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
            });
            cell.addEventListener('mouseout', function (e) {
                var to = e.relatedTarget;
                if (to && tooltip.contains && tooltip.contains(to)) {
                    cancelHideSticky();
                    return;
                }
                scheduleHideSticky();
            });
        });
    }

    function setupStockPorDepositoTooltips(container) {
        if (!container) return;
        var cells = container.querySelectorAll('.stock-cell');
        var tooltip = getOcTooltipEl();
        var padding = 10;
        cells.forEach(function (cell) {
            cell.addEventListener('mouseover', function (e) {
                if (tooltip._showingBo) return;
                var raw = cell.getAttribute('data-stock-deposito');
                var data = [];
                try { data = raw ? JSON.parse(raw) : []; } catch (_) { }
                tooltip.innerHTML = buildStockPorDepositoTooltipHtml(data);
                tooltip.style.opacity = '1';
                tooltip.style.pointerEvents = 'none';
                var left = e.pageX + padding;
                var top = e.pageY - padding;
                if (left + 280 > window.innerWidth) left = e.pageX - 280 - padding;
                if (top + 200 > window.innerHeight) top = e.pageY - 200 - padding;
                if (top < padding) top = padding;
                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
            });
            cell.addEventListener('mousemove', function (e) {
                var left = e.pageX + padding;
                var top = e.pageY - padding;
                if (left + 280 > window.innerWidth) left = e.pageX - 280 - padding;
                if (top + 200 > window.innerHeight) top = e.pageY - 200 - padding;
                if (top < padding) top = padding;
                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
            });
            cell.addEventListener('mouseout', function () {
                tooltip.style.opacity = '0';
            });
        });
    }

    function setupOcPendTooltips(container) {
        if (!container) return;
        var cells = container.querySelectorAll('.oc-pend-cell');
        var tooltip = getOcTooltipEl();
        var padding = 10;

        if (!tooltip._boDetalleListeners) {
            tooltip._boDetalleListeners = true;
            tooltip.addEventListener('mouseenter', function () {
                tooltip._mouseInside = true;
                cancelHideSticky();
            });
            tooltip.addEventListener('mouseleave', function () {
                hideStickyTooltip();
            });
        }

        cells.forEach(function (cell) {
            cell.addEventListener('mouseover', function (e) {
                cancelHideSticky();
                tooltip._showingBo = true;
                tooltip._mouseInside = false;
                var raw = cell.getAttribute('data-oc-detalle');
                var oc = [];
                try { oc = raw ? JSON.parse(raw) : []; } catch (_) { }
                tooltip.innerHTML = buildOcTooltipHtml(oc);
                tooltip.style.opacity = '1';
                tooltip.style.pointerEvents = 'auto';
                var left = e.pageX + padding;
                var top = e.pageY - padding;
                if (left + 280 > window.innerWidth) left = e.pageX - 280 - padding;
                if (top + 300 > window.innerHeight) top = e.pageY - 300 - padding;
                if (top < padding) top = padding;
                tooltip.style.left = left + 'px';
                tooltip.style.top = top + 'px';
            });
            cell.addEventListener('mouseout', function (e) {
                var to = e.relatedTarget;
                if (to && tooltip.contains && tooltip.contains(to)) {
                    cancelHideSticky();
                    return;
                }
                scheduleHideSticky();
            });
        });
    }
    
    // =========================================================
    // MANEJO DE TABS
    // =========================================================
    
    let currentTab = 'resumen';
    
    /**
     * Inicializa el sistema de tabs
     */
    function initializeTabs() {
        const tabButtons = document.querySelectorAll('[data-bo-tab]');
        
        tabButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const tabId = this.dataset.boTab;
                switchToTab(tabId);
            });
        });
        
        console.log('📊 [BO-Stock-Facturacion] Tabs inicializados:', tabButtons.length);
    }
    
    /**
     * Cambia a un tab específico
     */
    function switchToTab(tabId) {
        // Actualizar botones de navegación
        const tabButtons = document.querySelectorAll('[data-bo-tab]');
        tabButtons.forEach(btn => {
            const isActive = btn.dataset.boTab === tabId;
            btn.classList.toggle('active', isActive);
            btn.classList.toggle('border-sky-500', isActive);
            btn.classList.toggle('text-sky-600', isActive);
            btn.classList.toggle('dark:text-sky-400', isActive);
            btn.classList.toggle('bg-slate-50', isActive);
            btn.classList.toggle('dark:bg-slate-900/50', isActive);
            btn.classList.toggle('border-transparent', !isActive);
            btn.classList.toggle('text-slate-500', !isActive);
            btn.classList.toggle('dark:text-slate-400', !isActive);
        });
        
        // Mostrar/ocultar contenido de tabs
        const tabContents = document.querySelectorAll('.bo-tab-content');
        tabContents.forEach(content => {
            const contentId = content.id.replace('bo-tab-', '');
            content.classList.toggle('hidden', contentId !== tabId);
        });
        
        currentTab = tabId;
        console.log('📊 [BO-Stock-Facturacion] Tab activo:', tabId);
        
        // Scroll al contenido si es necesario
        const targetContent = document.getElementById(`bo-tab-${tabId}`);
        if (targetContent) {
            targetContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
    
    // =========================================================
    // KPIs CLICKEABLES
    // =========================================================
    
    /**
     * Inicializa los KPIs clickeables
     */
    function initializeKPIs() {
        const kpiCards = document.querySelectorAll('[data-kpi-card]');
        
        kpiCards.forEach(card => {
            card.addEventListener('click', function() {
                const targetTab = this.dataset.targetTab;
                if (targetTab) {
                    switchToTab(targetTab);
                    
                    // Scroll suave a la sección de tabs
                    const tabsSection = document.getElementById('bo-tabs-section');
                    if (tabsSection) {
                        setTimeout(() => {
                            tabsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }, 100);
                    }
                }
            });
        });
        
        console.log('📊 [BO-Stock-Facturacion] KPIs clickeables inicializados:', kpiCards.length);
    }
    
    /**
     * Inicializa drilldown desde Resumen: click en fila → cambiar a tab
     */
    function initializeResumenDrill() {
        const tabResumen = document.getElementById('bo-tab-resumen');
        if (!tabResumen) return;
        tabResumen.addEventListener('click', function(e) {
            const row = e.target.closest('[data-resumen-drill]');
            if (!row || !row.dataset.targetTab) return;
            const tabId = row.dataset.targetTab;
            switchToTab(tabId);
            const tabsSection = document.getElementById('bo-tabs-section');
            if (tabsSection) {
                setTimeout(function() { tabsSection.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 100);
            }
        });
        console.log('📊 [BO-Stock-Facturacion] Drilldown Resumen inicializado');
    }
    
    /**
     * Actualiza los valores de los KPIs
     */
    function updateKPIs(totals) {
        totals = totals || {};
        // KPI: Total Importe — siempre actualizar (aunque sea $0,00) para quitar "Cargando..."
        const kpiTotalImporte = document.getElementById('kpi-total-importe');
        if (kpiTotalImporte) {
            kpiTotalImporte.textContent = formatCurrency(totals.total_importe ?? 0);
        }
        
        // KPI: Sin Stock Total
        const kpiSinStockTotal = document.getElementById('kpi-sin-stock-total');
        if (kpiSinStockTotal) {
            kpiSinStockTotal.textContent = formatCurrency(totals.sin_stock_total ?? 0);
        }
        
        console.log('📊 [BO-Stock-Facturacion] KPIs actualizados');
    }
    
    // =========================================================
    // RENDERIZADO DE TABLAS
    // =========================================================
    
    /**
     * Renderiza la tabla de resumen estilo Excel
     */
    function renderResumenTable(data, totals) {
        const container = document.getElementById('bo-resumen-content');
        if (!container) return;
        
        // Crear estructura estilo Excel
        const html = `
            <div class="overflow-x-auto">
                <table class="w-full border-collapse text-sm">
                    <thead>
                        <tr>
                            <th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                                Concepto
                            </th>
                            <th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">
                                Importe
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Bloque Facturación -->
                        <tr class="bg-slate-100 dark:bg-slate-800/50">
                            <td colspan="2" class="px-4 py-2 text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                                Facturación
                            </td>
                        </tr>
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30">
                            <td class="px-4 py-3 text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800">
                                FACTURACIÓN (neto)
                            </td>
                            <td class="px-4 py-3 text-right font-mono text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800">
                                ${formatCurrency(totals.facturacion_neta)}
                            </td>
                        </tr>
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30">
                            <td class="px-4 py-3 text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800">
                                REMITO (no facturados)
                            </td>
                            <td class="px-4 py-3 text-right font-mono text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800">
                                ${formatCurrency(totals.remitos_no_facturados_total)}
                            </td>
                        </tr>
                        <tr class="bg-sky-50 dark:bg-sky-900/20 font-semibold">
                            <td class="px-4 py-3 text-sky-700 dark:text-sky-300 border-b-2 border-sky-200 dark:border-sky-800">
                                TOTAL (Facturación + Remitos)
                            </td>
                            <td class="px-4 py-3 text-right font-mono text-sky-700 dark:text-sky-300 border-b-2 border-sky-200 dark:border-sky-800">
                                ${formatCurrency(totals.total_importe)}
                            </td>
                        </tr>
                        
                        <!-- Espacio -->
                        <tr><td colspan="2" class="h-4"></td></tr>
                        
                        <!-- Bloque Backorder -->
                        <tr class="bg-slate-100 dark:bg-slate-800/50">
                            <td colspan="2" class="px-4 py-2 text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                                Backorder
                            </td>
                        </tr>
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30 cursor-pointer bo-resumen-drill" data-resumen-drill data-target-tab="backorder_detalle" title="Ver Backorder detalle">
                            <td class="px-4 py-3 text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800">
                                BACKORDER TOTAL
                            </td>
                            <td class="px-4 py-3 text-right font-mono text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800">
                                ${formatCurrency(totals.bo_total_importe)}
                            </td>
                        </tr>
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30 cursor-pointer bo-resumen-drill" data-resumen-drill data-target-tab="detalle_con_stock" title="Ver Detalle con stock">
                            <td class="px-4 py-3 text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800 pl-8">
                                → CON STOCK
                            </td>
                            <td class="px-4 py-3 text-right font-mono text-green-600 dark:text-green-400 border-b border-slate-100 dark:border-slate-800">
                                ${formatCurrency(totals.con_stock_total)}
                            </td>
                        </tr>
                        <tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30 cursor-pointer bo-resumen-drill" data-resumen-drill data-target-tab="detalle_con_ingreso" title="Ver Detalle con ingreso">
                            <td class="px-4 py-3 text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800 pl-8">
                                → CON INGRESO
                            </td>
                            <td class="px-4 py-3 text-right font-mono text-amber-600 dark:text-amber-400 border-b border-slate-100 dark:border-slate-800">
                                ${formatCurrency(totals.con_ingreso_total)}
                            </td>
                        </tr>
                        <tr class="bg-rose-50 dark:bg-rose-900/20 font-semibold cursor-pointer bo-resumen-drill" data-resumen-drill data-target-tab="detalle_sin_stock" title="Ver Detalle sin stock">
                            <td class="px-4 py-3 text-rose-700 dark:text-rose-300 border-b-2 border-rose-200 dark:border-rose-800 pl-8">
                                → SIN STOCK
                            </td>
                            <td class="px-4 py-3 text-right font-mono text-rose-700 dark:text-rose-300 border-b-2 border-rose-200 dark:border-rose-800">
                                ${formatCurrency(totals.sin_stock_total)}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
        
        container.innerHTML = html;
        console.log('📊 [BO-Stock-Facturacion] Tabla de resumen renderizada');
    }
    
    /**
     * Renderiza la tabla Detalle con stock (producto). Con agrupación opcional (ej. por categoría).
     */
    function renderDetalleConStockTable(data, groupByFieldsOptional) {
        var container = document.getElementById('bo-con-stock-content');
        if (!container) return;
        BO_LAST_CON_STOCK_DATA = data || [];
        data = BO_LAST_CON_STOCK_DATA;
        var searchQuery = (document.getElementById('bo-con-stock-search') && document.getElementById('bo-con-stock-search').value) || '';
        data = filterBoDataBySearch(data, searchQuery, ['codigo', 'articulo', 'categoria']);
        var config = BO_TAB_CONFIGS.con_stock;
        var groupByFields = groupByFieldsOptional;
        if (groupByFields === undefined) {
            groupByFields = getGroupByFieldsInSelectionOrder('bo-con-stock-group-by');
        }
        var tablePartHtml;
        var contentOnly = function (html, onUpdated) {
            return boUpdateContentOnly(container, 'bo-con-stock-search', html, onUpdated);
        };
        function setupConStockTooltips() {
            setupStockPorDepositoTooltips(container);
            setupBoDetalleTooltips(container);
            setupReservadoDetalleTooltips(container);
        }
        if (!data || data.length === 0) {
            tablePartHtml = '<div class="flex items-center justify-center py-8"><div class="text-xs text-slate-500 dark:text-slate-400">' + (searchQuery.length >= 2 ? 'No hay coincidencias para la búsqueda.' : 'No hay datos de con stock para mostrar.') + '</div></div>';
            if (contentOnly(tablePartHtml)) return;
            boSetSearchAndContent(container, 'bo-con-stock-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-con-stock-search', function () { renderDetalleConStockTable(BO_LAST_CON_STOCK_DATA); });
            return;
        }
        if (!container.dataset.boConStockGroupByInit) {
            container.dataset.boConStockGroupByInit = '1';
            initializeBoGroupByUI('bo-con-stock-group-by', config, function () { return BO_LAST_CON_STOCK_DATA; }, function (d, g) { renderDetalleConStockTable(d, g); });
        }
        if (groupByFields && groupByFields.length > 0) {
            var grouped = groupTableDataGeneric(data, groupByFields, config.metricKeys);
            var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
            var headerCells = config.columns.map(function (colKey) {
                var col = (config.dimensions || []).find(function (d) { return d.key === colKey; }) || (config.metrics || []).find(function (m) { return m.key === colKey; });
                var label = col ? col.label : colKey;
                var align = (config.metrics || []).some(function (m) { return m.key === colKey; }) ? ' text-right' : ' text-left';
                return '<th class="' + th + align + '">' + label + '</th>';
            }).join('');
            var bodyRows = renderGroupedTableRowsBO(grouped, config, 0, true);
            var total = data.reduce(function (s, r) { return s + (r.con_stock_importe || 0); }, 0);
            var numAgrupaciones = grouped.length;
            var totalRows = BO_LAST_CON_STOCK_DATA ? BO_LAST_CON_STOCK_DATA.length : data.length;
            var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' ítems. ' : '';
            var pieAgrupado = 'Con stock. Agrupado por: ' + groupByFields.join(' → ') + '. ' + numAgrupaciones + ' agrupación' + (numAgrupaciones !== 1 ? 'es' : '') + (leyendaFilas ? ' · ' + leyendaFilas : '') + ' · Total: ' + formatCurrency(total);
            tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr>' + headerCells + '</tr></thead><tbody>' + bodyRows + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + pieAgrupado + '</p>';
            if (contentOnly(tablePartHtml, function () { attachGroupToggleListenersBO(container); setupConStockTooltips(); })) return;
            boSetSearchAndContent(container, 'bo-con-stock-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-con-stock-search', function () { renderDetalleConStockTable(BO_LAST_CON_STOCK_DATA); });
            attachGroupToggleListenersBO(container);
            setupConStockTooltips();
            return;
        }
        var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
        var td = 'px-3 py-2 text-xs border-b border-slate-100 dark:border-slate-800';
        function attrEsc(s) {
            if (s == null) return '';
            return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        var sortedData = sortByArticulo(data);
        var rows = sortedData.map(function (r) {
            var stockDepJson = attrEsc(JSON.stringify(r.stock_por_deposito || []));
            var boDetalleJson = attrEsc(JSON.stringify(r.bo_detalle || []));
            return '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30">' +
                '<td class="' + td + ' font-mono text-slate-600 dark:text-slate-400">' + (r.codigo || '') + '</td>' +
                '<td class="' + td + ' text-slate-700 dark:text-slate-300">' + (r.articulo || '').toString().substring(0, 50) + '</td>' +
                '<td class="' + td + ' text-slate-600 dark:text-slate-400">' + (r.categoria || '') + '</td>' +
                '<td class="' + td + ' bo-qty-cell cursor-help text-right font-mono text-slate-900 dark:text-white" data-bo-detalle="' + boDetalleJson + '">' + formatNumber(r.bo_qty) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-slate-900 dark:text-white">' + formatCurrency(r.bo_importe) + '</td>' +
                '<td class="' + td + ' stock-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-stock-deposito="' + stockDepJson + '">' + formatNumber(r.stock_actual) + '</td>' +
                (r.stock_reservado > 0 ? '<td class="' + td + ' reservado-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-reservado-detalle="' + attrEsc(JSON.stringify(r.reservado_detalle || [])) + '">' + formatNumber(r.stock_reservado) + '</td>' : '<td class="' + td + ' text-right font-mono text-slate-600 dark:text-slate-400">' + formatNumber(r.stock_reservado) + '</td>') +
                '<td class="' + td + ' stock-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-stock-deposito="' + stockDepJson + '">' + formatNumber(r.disponible) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-green-600 dark:text-green-400">' + formatNumber(r.con_stock_qty) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-green-600 dark:text-green-400">' + formatCurrency(r.con_stock_importe) + '</td>' +
                '</tr>';
        }).join('');
        var total = data.reduce(function (s, r) { return s + (r.con_stock_importe || 0); }, 0);
        var totalRows = BO_LAST_CON_STOCK_DATA ? BO_LAST_CON_STOCK_DATA.length : data.length;
        var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' ítems' : data.length + ' ítems';
        tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm">' +
            '<thead class="sticky top-0"><tr>' +
            '<th class="' + th + ' text-left">Código</th><th class="' + th + ' text-left">Artículo</th><th class="' + th + ' text-left">Categoría</th>' +
            '<th class="' + th + ' text-right">BO qty</th><th class="' + th + ' text-right">BO importe</th>' +
            '<th class="' + th + ' text-right">Stock</th><th class="' + th + ' text-right">Reservado</th><th class="' + th + ' text-right">Disponible</th>' +
            '<th class="' + th + ' text-right">Con stock qty</th><th class="' + th + ' text-right">Con stock importe</th>' +
            '</tr></thead><tbody>' + rows + '</tbody></table></div>' +
            '<p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + leyendaFilas + ' · Total con stock: ' + formatCurrency(total) + '</p>';
        if (contentOnly(tablePartHtml, setupConStockTooltips)) return;
        boSetSearchAndContent(container, 'bo-con-stock-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
        attachBoSearchListener('bo-con-stock-search', function () { renderDetalleConStockTable(BO_LAST_CON_STOCK_DATA); });
        setupConStockTooltips();
    }

    /**
     * Renderiza la tabla Detalle con ingreso (producto). Con agrupación opcional (ej. por categoría).
     * CON INGRESO = cantidades en OC aprobadas y pendientes de entrega (saldo_pedido_proveedor).
     */
    function renderDetalleConIngresoTable(data, groupByFieldsOptional) {
        var container = document.getElementById('bo-con-ingreso-content');
        if (!container) return;
        BO_LAST_CON_INGRESO_DATA = data || [];
        data = BO_LAST_CON_INGRESO_DATA;
        var searchQuery = (document.getElementById('bo-con-ingreso-search') && document.getElementById('bo-con-ingreso-search').value) || '';
        data = filterBoDataBySearch(data, searchQuery, ['codigo', 'articulo', 'categoria']);
        var config = BO_TAB_CONFIGS.con_ingreso;
        var groupByFields = groupByFieldsOptional;
        if (groupByFields === undefined) {
            groupByFields = getGroupByFieldsInSelectionOrder('bo-con-ingreso-group-by');
        }
        var tablePartHtml;
        var contentOnlyIngreso = function (html, onUpdated) {
            return boUpdateContentOnly(container, 'bo-con-ingreso-search', html, onUpdated);
        };
        function setupConIngresoTooltips() {
            setupOcPendTooltips(container);
            setupStockPorDepositoTooltips(container);
            setupBoDetalleTooltips(container);
            setupReservadoDetalleTooltips(container);
        }
        if (!data || data.length === 0) {
            tablePartHtml = '<div class="flex items-center justify-center py-8"><div class="text-xs text-slate-500 dark:text-slate-400">' + (searchQuery.length >= 2 ? 'No hay coincidencias para la búsqueda.' : 'No hay datos de con ingreso para mostrar.') + '</div></div>';
            if (contentOnlyIngreso(tablePartHtml)) return;
            boSetSearchAndContent(container, 'bo-con-ingreso-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-con-ingreso-search', function () { renderDetalleConIngresoTable(BO_LAST_CON_INGRESO_DATA); });
            return;
        }
        if (!container.dataset.boConIngresoGroupByInit) {
            container.dataset.boConIngresoGroupByInit = '1';
            initializeBoGroupByUI('bo-con-ingreso-group-by', config, function () { return BO_LAST_CON_INGRESO_DATA; }, function (d, g) { renderDetalleConIngresoTable(d, g); });
        }
        if (groupByFields && groupByFields.length > 0) {
            var grouped = groupTableDataGeneric(data, groupByFields, config.metricKeys);
            var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
            var headerCells = config.columns.map(function (colKey) {
                var col = (config.dimensions || []).find(function (d) { return d.key === colKey; }) || (config.metrics || []).find(function (m) { return m.key === colKey; });
                var label = col ? col.label : colKey;
                var align = (config.metrics || []).some(function (m) { return m.key === colKey; }) ? ' text-right' : ' text-left';
                return '<th class="' + th + align + '">' + label + '</th>';
            }).join('');
            var bodyRows = renderGroupedTableRowsBO(grouped, config, 0, true);
            var total = data.reduce(function (s, r) { return s + (r.con_ingreso_importe || 0); }, 0);
            var numAgrupaciones = grouped.length;
            var totalRows = BO_LAST_CON_INGRESO_DATA ? BO_LAST_CON_INGRESO_DATA.length : data.length;
            var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' ítems. ' : '';
            var pieAgrupado = 'Con ingreso (OC pend.). Agrupado por: ' + groupByFields.join(' → ') + '. ' + numAgrupaciones + ' agrupación' + (numAgrupaciones !== 1 ? 'es' : '') + (leyendaFilas ? ' · ' + leyendaFilas : '') + ' · Total: ' + formatCurrency(total);
            tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr>' + headerCells + '</tr></thead><tbody>' + bodyRows + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + pieAgrupado + '</p>';
            if (contentOnlyIngreso(tablePartHtml, function () { attachGroupToggleListenersBO(container); setupConIngresoTooltips(); })) return;
            boSetSearchAndContent(container, 'bo-con-ingreso-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-con-ingreso-search', function () { renderDetalleConIngresoTable(BO_LAST_CON_INGRESO_DATA); });
            attachGroupToggleListenersBO(container);
            setupConIngresoTooltips();
            return;
        }
        var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
        var td = 'px-3 py-2 text-xs border-b border-slate-100 dark:border-slate-800';
        function attrEsc(s) {
            if (s == null) return '';
            return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        var sortedData = sortByArticulo(data);
        var rows = sortedData.map(function (r) {
            var ocJson = attrEsc(JSON.stringify(r.oc_detalle || []));
            var stockDepJson = attrEsc(JSON.stringify(r.stock_por_deposito || []));
            var boDetalleJson = attrEsc(JSON.stringify(r.bo_detalle || []));
            return '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30">' +
                '<td class="' + td + ' font-mono text-slate-600 dark:text-slate-400">' + (r.codigo || '') + '</td>' +
                '<td class="' + td + ' text-slate-700 dark:text-slate-300">' + (r.articulo || '').toString().substring(0, 50) + '</td>' +
                '<td class="' + td + ' text-slate-600 dark:text-slate-400">' + (r.categoria || '') + '</td>' +
                '<td class="' + td + ' bo-qty-cell cursor-help text-right font-mono text-slate-900 dark:text-white" data-bo-detalle="' + boDetalleJson + '">' + formatNumber(r.bo_qty) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-slate-900 dark:text-white">' + formatCurrency(r.bo_importe) + '</td>' +
                '<td class="' + td + ' stock-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-stock-deposito="' + stockDepJson + '">' + formatNumber(r.stock_actual) + '</td>' +
                (r.stock_reservado > 0 ? '<td class="' + td + ' reservado-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-reservado-detalle="' + attrEsc(JSON.stringify(r.reservado_detalle || [])) + '">' + formatNumber(r.stock_reservado) + '</td>' : '<td class="' + td + ' text-right font-mono text-slate-600 dark:text-slate-400">' + formatNumber(r.stock_reservado) + '</td>') +
                '<td class="' + td + ' stock-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-stock-deposito="' + stockDepJson + '">' + formatNumber(r.disponible) + '</td>' +
                '<td class="' + td + ' oc-pend-cell text-right font-mono text-slate-500 dark:text-slate-400 cursor-help" data-oc-detalle="' + ocJson + '">' + formatNumber(r.oc_pendiente) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-amber-600 dark:text-amber-400">' + formatNumber(r.con_ingreso_qty) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-amber-600 dark:text-amber-400">' + formatCurrency(r.con_ingreso_importe) + '</td>' +
                '</tr>';
        }).join('');
        var total = data.reduce(function (s, r) { return s + (r.con_ingreso_importe || 0); }, 0);
        var totalRows = BO_LAST_CON_INGRESO_DATA ? BO_LAST_CON_INGRESO_DATA.length : data.length;
        var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' ítems' : data.length + ' ítems';
        tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto bo-con-ingreso-scroll">' +
            '<table class="w-full border-collapse text-sm">' +
            '<thead class="sticky top-0"><tr>' +
            '<th class="' + th + ' text-left">Código</th><th class="' + th + ' text-left">Artículo</th><th class="' + th + ' text-left">Categoría</th>' +
            '<th class="' + th + ' text-right">BO qty</th><th class="' + th + ' text-right">BO importe</th>' +
            '<th class="' + th + ' text-right">Stock</th><th class="' + th + ' text-right">Reservado</th><th class="' + th + ' text-right">Disponible</th>' +
            '<th class="' + th + ' text-right" title="OC aprobadas pend. entrega">OC pend. qty</th>' +
            '<th class="' + th + ' text-right">Con ingreso qty</th><th class="' + th + ' text-right">Con ingreso importe</th>' +
            '</tr></thead><tbody>' + rows + '</tbody></table></div>' +
            '<p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + leyendaFilas + ' · Total con ingreso (OC pend.): ' + formatCurrency(total) + '</p>';
        if (contentOnlyIngreso(tablePartHtml, setupConIngresoTooltips)) return;
        boSetSearchAndContent(container, 'bo-con-ingreso-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
        attachBoSearchListener('bo-con-ingreso-search', function () { renderDetalleConIngresoTable(BO_LAST_CON_INGRESO_DATA); });
        setupConIngresoTooltips();
    }

    /**
     * Renderiza la tabla Detalle sin stock (producto). Con agrupación opcional (ej. por categoría).
     * Misma funcionalidad que Facturación, Remitos y Backorder detalle.
     */
    function renderDetalleSinStockTable(data, groupByFieldsOptional) {
        var container = document.getElementById('bo-sin-stock-content');
        if (!container) return;
        BO_LAST_SIN_STOCK_DATA = data || [];
        data = BO_LAST_SIN_STOCK_DATA;
        var searchQuery = (document.getElementById('bo-sin-stock-search') && document.getElementById('bo-sin-stock-search').value) || '';
        data = filterBoDataBySearch(data, searchQuery, ['codigo', 'articulo', 'categoria']);
        var config = BO_TAB_CONFIGS.sin_stock;
        var groupByFields = groupByFieldsOptional;
        if (groupByFields === undefined) {
            groupByFields = getGroupByFieldsInSelectionOrder('bo-sin-stock-group-by');
        }
        var tablePartHtml;
        var contentOnlySinStock = function (html, onUpdated) {
            return boUpdateContentOnly(container, 'bo-sin-stock-search', html, onUpdated);
        };
        function setupSinStockTooltips() {
            setupStockPorDepositoTooltips(container);
            setupBoDetalleTooltips(container);
            setupReservadoDetalleTooltips(container);
        }
        if (!data || data.length === 0) {
            tablePartHtml = '<div class="flex items-center justify-center py-8"><div class="text-xs text-slate-500 dark:text-slate-400">' + (searchQuery.length >= 2 ? 'No hay coincidencias para la búsqueda.' : 'No hay datos de sin stock para mostrar.') + '</div></div>';
            if (contentOnlySinStock(tablePartHtml)) return;
            boSetSearchAndContent(container, 'bo-sin-stock-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-sin-stock-search', function () { renderDetalleSinStockTable(BO_LAST_SIN_STOCK_DATA); });
            return;
        }
        if (!container.dataset.boSinStockGroupByInit) {
            container.dataset.boSinStockGroupByInit = '1';
            initializeBoGroupByUI('bo-sin-stock-group-by', config, function () { return BO_LAST_SIN_STOCK_DATA; }, function (d, g) { renderDetalleSinStockTable(d, g); });
        }
        if (groupByFields && groupByFields.length > 0) {
            var grouped = groupTableDataGeneric(data, groupByFields, config.metricKeys);
            var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
            var headerCells = config.columns.map(function (colKey) {
                var col = (config.dimensions || []).find(function (d) { return d.key === colKey; }) || (config.metrics || []).find(function (m) { return m.key === colKey; });
                var label = col ? col.label : colKey;
                var align = (config.metrics || []).some(function (m) { return m.key === colKey; }) ? ' text-right' : ' text-left';
                return '<th class="' + th + align + '">' + label + '</th>';
            }).join('');
            var bodyRows = renderGroupedTableRowsBO(grouped, config, 0, true);
            var total = data.reduce(function (s, r) { return s + (r.sin_stock_importe || 0); }, 0);
            var numAgrupaciones = grouped.length;
            var totalRows = BO_LAST_SIN_STOCK_DATA ? BO_LAST_SIN_STOCK_DATA.length : data.length;
            var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' ítems. ' : '';
            var pieAgrupado = 'Sin stock. Agrupado por: ' + groupByFields.join(' → ') + '. ' + numAgrupaciones + ' agrupación' + (numAgrupaciones !== 1 ? 'es' : '') + (leyendaFilas ? ' · ' + leyendaFilas : '') + ' · Total: ' + formatCurrency(total);
            tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr>' + headerCells + '</tr></thead><tbody>' + bodyRows + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + pieAgrupado + '</p>';
            if (contentOnlySinStock(tablePartHtml, function () { attachGroupToggleListenersBO(container); setupSinStockTooltips(); })) return;
            boSetSearchAndContent(container, 'bo-sin-stock-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-sin-stock-search', function () { renderDetalleSinStockTable(BO_LAST_SIN_STOCK_DATA); });
            attachGroupToggleListenersBO(container);
            setupSinStockTooltips();
            return;
        }
        var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
        var td = 'px-3 py-2 text-xs border-b border-slate-100 dark:border-slate-800';
        function attrEsc(s) {
            if (s == null) return '';
            return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        }
        var sortedData = sortByArticulo(data);
        var rows = sortedData.map(function (r) {
            var stockDepJson = attrEsc(JSON.stringify(r.stock_por_deposito || []));
            var boDetalleJson = attrEsc(JSON.stringify(r.bo_detalle || []));
            return '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30">' +
                '<td class="' + td + ' font-mono text-slate-600 dark:text-slate-400">' + (r.codigo || '') + '</td>' +
                '<td class="' + td + ' text-slate-700 dark:text-slate-300">' + (r.articulo || '').toString().substring(0, 50) + '</td>' +
                '<td class="' + td + ' text-slate-600 dark:text-slate-400">' + (r.categoria || '') + '</td>' +
                '<td class="' + td + ' bo-qty-cell cursor-help text-right font-mono text-slate-900 dark:text-white" data-bo-detalle="' + boDetalleJson + '">' + formatNumber(r.bo_qty) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-slate-900 dark:text-white">' + formatCurrency(r.bo_importe) + '</td>' +
                '<td class="' + td + ' stock-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-stock-deposito="' + stockDepJson + '">' + formatNumber(r.stock_actual) + '</td>' +
                (r.stock_reservado > 0 ? '<td class="' + td + ' reservado-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-reservado-detalle="' + attrEsc(JSON.stringify(r.reservado_detalle || [])) + '">' + formatNumber(r.stock_reservado) + '</td>' : '<td class="' + td + ' text-right font-mono text-slate-600 dark:text-slate-400">' + formatNumber(r.stock_reservado) + '</td>') +
                '<td class="' + td + ' stock-cell cursor-help text-right font-mono text-slate-600 dark:text-slate-400" data-stock-deposito="' + stockDepJson + '">' + formatNumber(r.disponible) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-slate-500 dark:text-slate-400">' + formatNumber(r.oc_pendiente) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-rose-600 dark:text-rose-400">' + formatNumber(r.sin_stock_qty) + '</td>' +
                '<td class="' + td + ' text-right font-mono text-rose-600 dark:text-rose-400">' + formatCurrency(r.sin_stock_importe) + '</td>' +
                '</tr>';
        }).join('');
        var total = data.reduce(function (s, r) { return s + (r.sin_stock_importe || 0); }, 0);
        var totalRows = BO_LAST_SIN_STOCK_DATA ? BO_LAST_SIN_STOCK_DATA.length : data.length;
        var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' ítems' : data.length + ' ítems';
        tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm">' +
            '<thead class="sticky top-0"><tr>' +
            '<th class="' + th + ' text-left">Código</th><th class="' + th + ' text-left">Artículo</th><th class="' + th + ' text-left">Categoría</th>' +
            '<th class="' + th + ' text-right">BO qty</th><th class="' + th + ' text-right">BO importe</th>' +
            '<th class="' + th + ' text-right">Stock</th><th class="' + th + ' text-right">Reservado</th><th class="' + th + ' text-right">Disponible</th><th class="' + th + ' text-right">OC pend. qty</th>' +
            '<th class="' + th + ' text-right">Sin stock qty</th><th class="' + th + ' text-right">Sin stock importe</th>' +
            '</tr></thead><tbody>' + rows + '</tbody></table></div>' +
            '<p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + leyendaFilas + ' · Total sin stock: ' + formatCurrency(total) + '</p>';
        if (contentOnlySinStock(tablePartHtml, setupSinStockTooltips)) return;
        boSetSearchAndContent(container, 'bo-sin-stock-search', 'Buscar por código, artículo, categoría...', searchQuery, tablePartHtml);
        attachBoSearchListener('bo-sin-stock-search', function () { renderDetalleSinStockTable(BO_LAST_SIN_STOCK_DATA); });
        setupSinStockTooltips();
    }
    
    /**
     * Formatea fecha YYYY-MM-DD a dd/mm/yy
     */
    function formatDateShort(val) {
        if (!val) return '';
        var s = String(val);
        var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (m) return m[3] + '/' + m[2] + '/' + m[1].slice(-2);
        return s;
    }

    // =========================================================
    // AGRUPACIÓN DINÁMICA (tipo ventas-netas / Excel)
    // =========================================================

    var BO_LAST_FACTURACION_DATA = [];
    var BO_LAST_REMITOS_DATA = [];
    var BO_LAST_BACKORDER_DATA = [];
    var BO_LAST_SIN_STOCK_DATA = [];
    var BO_LAST_CON_STOCK_DATA = [];
    var BO_LAST_CON_INGRESO_DATA = [];

    var BO_TAB_CONFIGS = {
        con_stock: {
            dimensions: [
                { key: 'categoria', label: 'Categoría' },
                { key: 'codigo', label: 'Código' },
                { key: 'articulo', label: 'Artículo' }
            ],
            metrics: [
                { key: 'con_stock_qty', label: 'Con stock qty', format: 'number' },
                { key: 'con_stock_importe', label: 'Con stock importe', format: 'currency' }
            ],
            metricKeys: ['con_stock_qty', 'con_stock_importe'],
            columns: ['codigo', 'articulo', 'categoria', 'bo_qty', 'bo_importe', 'stock_actual', 'stock_reservado', 'disponible', 'con_stock_qty', 'con_stock_importe']
        },
        con_ingreso: {
            dimensions: [
                { key: 'categoria', label: 'Categoría' },
                { key: 'codigo', label: 'Código' },
                { key: 'articulo', label: 'Artículo' }
            ],
            metrics: [
                { key: 'oc_pendiente', label: 'OC pend. qty', format: 'number' },
                { key: 'con_ingreso_qty', label: 'Con ingreso qty', format: 'number' },
                { key: 'con_ingreso_importe', label: 'Con ingreso importe', format: 'currency' }
            ],
            metricKeys: ['oc_pendiente', 'con_ingreso_qty', 'con_ingreso_importe'],
            columns: ['codigo', 'articulo', 'categoria', 'bo_qty', 'bo_importe', 'stock_actual', 'stock_reservado', 'disponible', 'oc_pendiente', 'con_ingreso_qty', 'con_ingreso_importe']
        },
        sin_stock: {
            dimensions: [
                { key: 'categoria', label: 'Categoría' },
                { key: 'codigo', label: 'Código' },
                { key: 'articulo', label: 'Artículo' }
            ],
            metrics: [
                { key: 'sin_stock_qty', label: 'Sin stock qty', format: 'number' },
                { key: 'sin_stock_importe', label: 'Sin stock importe', format: 'currency' }
            ],
            metricKeys: ['sin_stock_qty', 'sin_stock_importe'],
            columns: ['codigo', 'articulo', 'categoria', 'bo_qty', 'bo_importe', 'stock_actual', 'stock_reservado', 'disponible', 'oc_pendiente', 'sin_stock_qty', 'sin_stock_importe']
        },
        facturacion: {
            dimensions: [
                { key: 'vendedor', label: 'Vendedor' },
                { key: 'zona', label: 'Zona' },
                { key: 'cliente', label: 'Cliente' }
            ],
            metrics: [
                { key: 'sub_total', label: 'Sub Total', format: 'currency' },
                { key: 'porc_ventas', label: '% ventas', format: 'percent' }
            ],
            metricKeys: ['sub_total'],
            columns: ['nro', 'cliente', 'sub_total', 'porc_ventas', 'ultima_compra', 'vendedor', 'zona', 'telefono', 'email', 'cuit']
        },
        remitos: {
            dimensions: [
                { key: 'sucursal', label: 'Sucursal' },
                { key: 'punto_venta', label: 'Punto de venta' },
                { key: 'fecha', label: 'Fecha' },
                { key: 'nro_comprobante', label: 'Nro. Comprobante' }
            ],
            metrics: [
                { key: 'subtotal_desc', label: 'Subtotal', format: 'currency' }
            ],
            metricKeys: ['subtotal_desc'],
            columns: ['fecha', 'nro_comprobante', 'sucursal', 'punto_venta', 'subtotal_desc']
        },
        backorder: {
            dimensions: [
                { key: 'descripcion', label: 'Descripción' },
                { key: 'cliente', label: 'Cliente' },
                { key: 'nro_comp', label: 'Nro. comp' },
                { key: 'nombre_rubro', label: 'Rubro' },
                { key: 'nombre_vendedor', label: 'Vendedor' },
                { key: 'fecha', label: 'Fecha' }
            ],
            metrics: [
                { key: 'precio_x_renglon', label: 'Precio x renglón', format: 'currency' },
                { key: 'cant_pend', label: 'Cant. pend', format: 'number' }
            ],
            metricKeys: ['precio_x_renglon', 'cant_pend'],
            columns: ['fecha', 'nro_comp', 'descripcion', 'cod_manual', 'cant_pend', 'cliente', 'precio_x_renglon', 'nombre_rubro', 'nombre_sub_rubro', 'nombre_vendedor']
        }
    };

    /**
     * Ordena filas por nombre de artículo (articulo o descripcion).
     */
    function sortByArticulo(items) {
        if (!items || !items.length) return items;
        return items.slice().sort(function (a, b) {
            var va = (a.articulo != null ? a.articulo : a.descripcion || '').toString().toLowerCase();
            var vb = (b.articulo != null ? b.articulo : b.descripcion || '').toString().toLowerCase();
            return va.localeCompare(vb, 'es');
        });
    }

    /**
     * Obtiene los campos de agrupación en orden de selección del usuario (chips = orden de selección).
     * El primer elemento seleccionado es el nivel más externo, el último el más interno.
     */
    function getGroupByFieldsInSelectionOrder(selectId) {
        var tagsContainer = document.getElementById(selectId + '_tags_container');
        var chipsContainer = tagsContainer && tagsContainer.querySelector('.tags-chips');
        if (chipsContainer) {
            var chips = chipsContainer.querySelectorAll('[data-group-value]');
            if (chips.length > 0) {
                return Array.from(chips).map(function (c) { return c.getAttribute('data-group-value'); });
            }
        }
        var sel = document.getElementById(selectId);
        return sel ? Array.from(sel.selectedOptions).map(function (o) { return o.value; }) : [];
    }

    /**
     * Agrupa datos recursivamente por múltiples campos. Retorna árbol { type: 'group'|'item', data, children }.
     * groupByFields[0] = nivel más externo, groupByFields[n] = nivel más interno.
     */
    function groupTableDataGeneric(data, groupByFields, metricKeys) {
        if (!groupByFields || !groupByFields.length || !data || !data.length) return data;
        var level = 0;
        function groupByLevels(items, fields, lev) {
            if (lev >= fields.length) {
                var sorted = sortByArticulo(items);
                return sorted.map(function (item) { return { type: 'item', data: item, children: [] }; });
            }
            var currentField = fields[lev];
            var grouped = {};
            items.forEach(function (row) {
                var groupKey = (row[currentField] !== undefined && row[currentField] !== null && row[currentField] !== '') ? String(row[currentField]) : 'Sin especificar';
                if (!grouped[groupKey]) {
                    grouped[groupKey] = { groupKey: groupKey, groupValue: groupKey, groupField: currentField, items: [], totals: {} };
                    metricKeys.forEach(function (k) { grouped[groupKey].totals[k] = 0; });
                }
                grouped[groupKey].items.push(row);
                metricKeys.forEach(function (k) {
                    var v = parseFloat(row[k]);
                    if (!isNaN(v)) grouped[groupKey].totals[k] += v;
                });
            });
            var result = [];
            Object.keys(grouped).sort().forEach(function (key) {
                var g = grouped[key];
                var nested = groupByLevels(g.items, fields, lev + 1);
                result.push({ type: 'group', data: g, children: nested });
            });
            return result;
        }
        return groupByLevels(data, groupByFields, 0);
    }

    function formatCellValueBO(value, colKey, config) {
        if (value === undefined || value === null) return '';
        if (colKey === 'ultima_compra' || (colKey && colKey.indexOf('fecha') !== -1)) return formatDateShort(value);
        var col = (config.metrics || []).concat(config.dimensions || []).find(function (c) { return c.key === colKey; });
        var fmt = col && col.format ? col.format : '';
        if (fmt === 'currency') return formatCurrency(value);
        if (fmt === 'percent') return (typeof value === 'number' ? value.toFixed(2).replace('.', ',') : value) + '%';
        if (fmt === 'number') return formatNumber(value);
        return String(value);
    }

    /**
     * Renderiza filas de tabla con grupos (expandir/colapsar, subtotales).
     */
    function renderGroupedTableRowsBO(groupedData, config, level, collapsedDefault) {
        level = level || 0;
        collapsedDefault = collapsedDefault !== false;
        var dimensions = config.dimensions || [];
        var metrics = config.metrics || [];
        var metricKeys = config.metricKeys || [];
        var allCols = config.columns || [];
        var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
        var td = 'px-3 py-2 text-xs border-b border-slate-100 dark:border-slate-800';
        var rowsHTML = '';
        var groupIdPrefix = 'bo-g-' + Math.random().toString(36).substr(2, 6) + '-';
        groupedData.forEach(function (item, idx) {
            if (item.type === 'group') {
                var g = item.data;
                var groupId = groupIdPrefix + level + '-' + idx;
                var dimLabel = (dimensions.find(function (d) { return d.key === g.groupField; }) || { label: g.groupField }).label;
                var bgClass = level === 0 ? 'bg-slate-100 dark:bg-slate-800' : (level === 1 ? 'bg-slate-50 dark:bg-slate-900' : 'bg-slate-50/50 dark:bg-slate-800/50');
                var padLeft = (level * 20) + 8;
                var expandIcon = '<svg class="w-4 h-4 inline-block mr-2 align-middle group-toggle-icon cursor-pointer" data-bo-group-toggle="' + groupId + '" style="transform: ' + (collapsedDefault ? 'rotate(0deg)' : 'rotate(90deg)') + ';" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M9 18l6-6-6-6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
                rowsHTML += '<tr class="' + bgClass + ' bo-group-row" data-bo-group-id="' + groupId + '">';
                rowsHTML += '<td class="' + td + '" style="padding-left: ' + padLeft + 'px;">' + expandIcon + '<span class="font-medium text-slate-700 dark:text-slate-300">' + dimLabel + ': ' + (g.groupValue || '').toString().substring(0, 50) + '</span></td>';
                allCols.slice(1).forEach(function (colKey) {
                    if (metricKeys.indexOf(colKey) !== -1 && g.totals && g.totals[colKey] !== undefined) {
                        rowsHTML += '<td class="' + td + ' text-right font-semibold text-sky-600 dark:text-sky-400">' + formatCellValueBO(g.totals[colKey], colKey, config) + '</td>';
                    } else {
                        rowsHTML += '<td class="' + td + '"></td>';
                    }
                });
                rowsHTML += '</tr>';
                rowsHTML += '<tr class="bo-group-children" data-bo-group-parent="' + groupId + '" style="' + (collapsedDefault ? 'display:none;' : '') + '"><td colspan="' + allCols.length + '" class="p-0 border-0"><table class="w-full border-collapse text-sm"><tbody>';
                rowsHTML += renderGroupedTableRowsBO(item.children, config, level + 1, collapsedDefault);
                rowsHTML += '</tbody></table></td></tr>';
            } else {
                var row = item.data;
                rowsHTML += '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30 bo-detail-row">';
                allCols.forEach(function (colKey) {
                    var val = row[colKey];
                    var formatted = formatCellValueBO(val, colKey, config);
                    if (formatted === '' && (val === 0 || val === '0')) formatted = formatCellValueBO(0, colKey, config);
                    if (formatted === '' && val !== undefined && val !== null) formatted = String(val).substring(0, 60);
                    var align = metrics.some(function (m) { return m.key === colKey; }) ? ' text-right font-mono' : '';
                    var cellClass = td + ' text-slate-700 dark:text-slate-300' + align;
                    var dataAttr = '';
                    if (colKey === 'stock_actual' && row.stock_por_deposito) {
                        cellClass += ' stock-cell cursor-help';
                        var stockDepJson = String(JSON.stringify(row.stock_por_deposito)).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        dataAttr = ' data-stock-deposito="' + stockDepJson + '"';
                    } else if (colKey === 'bo_qty' && row.bo_detalle) {
                        cellClass += ' bo-qty-cell cursor-help';
                        var boDepJson = String(JSON.stringify(row.bo_detalle)).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        dataAttr = ' data-bo-detalle="' + boDepJson + '"';
                    } else if (colKey === 'stock_reservado' && (row.stock_reservado > 0)) {
                        cellClass += ' reservado-cell cursor-help';
                        var resDepJson = String(JSON.stringify(row.reservado_detalle || [])).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        dataAttr = ' data-reservado-detalle="' + resDepJson + '"';
                    } else if ((colKey === 'disponible') && row.stock_por_deposito) {
                        cellClass += ' stock-cell cursor-help';
                        var dispDepJson = String(JSON.stringify(row.stock_por_deposito)).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        dataAttr = ' data-stock-deposito="' + dispDepJson + '"';
                    } else if (colKey === 'oc_pendiente' && row.oc_detalle) {
                        cellClass += ' oc-pend-cell cursor-help';
                        var ocDetJson = String(JSON.stringify(row.oc_detalle || [])).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                        dataAttr = ' data-oc-detalle="' + ocDetJson + '"';
                    }
                    rowsHTML += '<td class="' + cellClass + '"' + dataAttr + '>' + formatted + '</td>';
                });
                rowsHTML += '</tr>';
            }
        });
        return rowsHTML;
    }

    function attachGroupToggleListenersBO(container) {
        if (!container) return;
        container.querySelectorAll('[data-bo-group-toggle]').forEach(function (el) {
            if (el._boToggleAttached) return;
            el._boToggleAttached = true;
            el.addEventListener('click', function () {
                var groupId = this.getAttribute('data-bo-group-toggle');
                var childrenRow = container.querySelector('tr[data-bo-group-parent="' + groupId + '"]');
                if (!childrenRow) return;
                var isHidden = childrenRow.style.display === 'none';
                childrenRow.style.display = isHidden ? 'table-row' : 'none';
                this.style.transform = isHidden ? 'rotate(90deg)' : 'rotate(0deg)';
            });
        });
    }

    /**
     * Inicializa UI "Agrupar por" (opciones, chips, búsqueda) y re-render al cambiar.
     */
    function initializeBoGroupByUI(selectId, config, getDataFn, renderTableFn) {
        var select = document.getElementById(selectId);
        var tagsContainer = document.getElementById(selectId + '_tags_container');
        var chipsContainer = tagsContainer && tagsContainer.querySelector('.tags-chips');
        var input = document.getElementById(selectId + '_search');
        var dropdown = document.getElementById(selectId + '_dropdown');
        if (!select || !tagsContainer || !chipsContainer || !input || !dropdown) return;
        if (tagsContainer.dataset.boGroupByInit === 'true') return;
        tagsContainer.dataset.boGroupByInit = 'true';

        var dimensions = config.dimensions || [];
        dimensions.forEach(function (d) {
            var opt = document.createElement('option');
            opt.value = d.key;
            opt.textContent = d.label;
            select.appendChild(opt);
        });

        var selectedValues = [];
        function getSelected() {
            return Array.from(select.selectedOptions).map(function (o) { return o.value; });
        }
        function renderChips() {
            chipsContainer.innerHTML = '';
            selectedValues.forEach(function (value) {
                var dim = dimensions.find(function (d) { return d.key === value; });
                var label = dim ? dim.label : value;
                var chip = document.createElement('div');
                chip.className = 'inline-flex items-center gap-1 px-2 py-1 bg-sky-100 dark:bg-sky-900 text-sky-800 dark:text-sky-200 rounded-full text-xs font-medium';
                chip.setAttribute('data-group-value', value);
                chip.innerHTML = '<span>' + label + '</span><button type="button" class="ml-1 hover:text-sky-600 dark:hover:text-sky-300 focus:outline-none" data-remove="' + value + '">×</button>';
                chipsContainer.appendChild(chip);
                chip.querySelector('button').addEventListener('click', function () {
                    var v = this.getAttribute('data-remove');
                    selectedValues = selectedValues.filter(function (x) { return x !== v; });
                    Array.from(select.options).forEach(function (o) { o.selected = selectedValues.indexOf(o.value) !== -1; });
                    renderChips();
                    renderTableFn(getDataFn(), selectedValues.slice());
                });
            });
        }
        function addTag(value) {
            if (selectedValues.indexOf(value) === -1) {
                selectedValues.push(value);
                var opt = select.querySelector('option[value="' + value + '"]');
                if (opt) opt.selected = true;
                renderChips();
                dropdown.classList.add('hidden');
                dropdown.style.display = '';
                input.value = '';
                renderTableFn(getDataFn(), selectedValues.slice());
            }
        }
        function showDropdown() {
            var available = dimensions.filter(function (d) { return selectedValues.indexOf(d.key) === -1; });
            var q = (input.value || '').toLowerCase();
            var toShow = q ? available.filter(function (d) { return d.label.toLowerCase().indexOf(q) !== -1; }) : available;
            dropdown.innerHTML = toShow.map(function (d) {
                return '<div class="px-3 py-2 text-xs cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200" data-value="' + d.key + '">' + d.label + '</div>';
            }).join('') || '<div class="px-3 py-2 text-xs text-slate-500 dark:text-slate-400">' + (q ? 'Sin resultados' : 'Sin más campos') + '</div>';
            dropdown.querySelectorAll('[data-value]').forEach(function (el) {
                el.addEventListener('click', function () { addTag(this.getAttribute('data-value')); });
            });
            dropdown.classList.remove('hidden');
            dropdown.style.display = 'block';
        }
        function hideDropdown() {
            dropdown.classList.add('hidden');
            dropdown.style.display = '';
        }
        input.addEventListener('focus', showDropdown);
        input.addEventListener('click', function (e) {
            e.stopPropagation();
            showDropdown();
        });
        input.addEventListener('input', function () {
            showDropdown();
        });
        document.addEventListener('click', function (e) {
            if (!tagsContainer.contains(e.target) && !dropdown.contains(e.target)) hideDropdown();
        }, true);
        select.addEventListener('change', function () {
            selectedValues = getSelected();
            renderChips();
            renderTableFn(getDataFn(), selectedValues.slice());
        });
    }

    /**
     * Renderiza la tabla Facturación por cliente (con agrupación dinámica opcional).
     */
    function renderFacturacionTable(data, groupByFieldsOptional) {
        var container = document.getElementById('bo-facturacion-content');
        if (!container) return;
        BO_LAST_FACTURACION_DATA = data || [];
        data = BO_LAST_FACTURACION_DATA;
        var searchQuery = (document.getElementById('bo-facturacion-search') && document.getElementById('bo-facturacion-search').value) || '';
        data = filterBoDataBySearch(data, searchQuery, ['cliente', 'vendedor', 'zona', 'telefono', 'email', 'cuit']);
        var config = BO_TAB_CONFIGS.facturacion;
        var groupByFields = groupByFieldsOptional;
        if (groupByFields === undefined) {
            groupByFields = getGroupByFieldsInSelectionOrder('bo-facturacion-group-by');
        }
        var tablePartHtml;
        var contentOnlyFac = function (html, onUpdated) {
            return boUpdateContentOnly(container, 'bo-facturacion-search', html, onUpdated);
        };
        if (!data || data.length === 0) {
            tablePartHtml = '<div class="flex items-center justify-center py-8"><div class="text-xs text-slate-500 dark:text-slate-400">' + (searchQuery.length >= 2 ? 'No hay coincidencias para la búsqueda.' : 'No hay datos de facturación por cliente para mostrar.') + '</div></div>';
            if (contentOnlyFac(tablePartHtml)) return;
            boSetSearchAndContent(container, 'bo-facturacion-search', 'Buscar por cliente, vendedor, zona...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-facturacion-search', function () { renderFacturacionTable(BO_LAST_FACTURACION_DATA); });
            return;
        }
        if (!container.dataset.boFacGroupByInit) {
            container.dataset.boFacGroupByInit = '1';
            initializeBoGroupByUI('bo-facturacion-group-by', config, function () { return BO_LAST_FACTURACION_DATA; }, function (d, g) { renderFacturacionTable(d, g); });
        }
        if (groupByFields && groupByFields.length > 0) {
            var grouped = groupTableDataGeneric(data, groupByFields, config.metricKeys);
            var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
            var headerCells = config.columns.map(function (colKey) {
                var col = config.dimensions.find(function (d) { return d.key === colKey; }) || config.metrics.find(function (m) { return m.key === colKey; });
                var label = col ? col.label : colKey;
                var align = config.metrics.some(function (m) { return m.key === colKey; }) ? ' text-right' : ' text-left';
                return '<th class="' + th + align + '">' + label + '</th>';
            }).join('');
            var bodyRows = renderGroupedTableRowsBO(grouped, config, 0, true);
            var numAgrupaciones = grouped.length;
            var totalRows = BO_LAST_FACTURACION_DATA ? BO_LAST_FACTURACION_DATA.length : data.length;
            var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' clientes. ' : '';
            var pieAgrupado = 'Facturación por cliente. Agrupado por: ' + groupByFields.join(' → ') + '. ' + numAgrupaciones + ' agrupación' + (numAgrupaciones !== 1 ? 'es' : '') + (leyendaFilas ? ' · ' + leyendaFilas : '') + '.';
            tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr>' + headerCells + '</tr></thead><tbody>' + bodyRows + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + pieAgrupado + '</p>';
            if (contentOnlyFac(tablePartHtml, function () { attachGroupToggleListenersBO(container); })) return;
            boSetSearchAndContent(container, 'bo-facturacion-search', 'Buscar por cliente, vendedor, zona...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-facturacion-search', function () { renderFacturacionTable(BO_LAST_FACTURACION_DATA); });
            attachGroupToggleListenersBO(container);
            return;
        }
        var PAGE_SIZE = 50;
        var currentPage = 1;
        var totalPages = Math.max(1, Math.ceil(data.length / PAGE_SIZE));
        function buildTable(page) {
            var start = (page - 1) * PAGE_SIZE;
            var pageData = data.slice(start, start + PAGE_SIZE);
            var td = 'px-3 py-2 text-xs border-b border-slate-100 dark:border-slate-800';
            var rowsHtml = pageData.map(function (row) {
                return '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30">' +
                    '<td class="' + td + ' text-slate-600 dark:text-slate-400 text-center font-mono">' + (row.nro || '') + '</td>' +
                    '<td class="' + td + ' text-slate-700 dark:text-slate-300">' + (row.cliente || '').toString().substring(0, 60) + '</td>' +
                    '<td class="' + td + ' text-right font-mono text-slate-900 dark:text-white">' + formatCurrency(row.sub_total) + '</td>' +
                    '<td class="' + td + ' text-right font-mono text-slate-600 dark:text-slate-400">' + (row.porc_ventas != null ? Number(row.porc_ventas).toFixed(2).replace('.', ',') + '%' : '') + '</td>' +
                    '<td class="' + td + ' text-slate-600 dark:text-slate-400 text-center">' + formatDateShort(row.ultima_compra) + '</td>' +
                    '<td class="' + td + ' text-slate-600 dark:text-slate-400">' + (row.vendedor || '').toString().substring(0, 30) + '</td>' +
                    '<td class="' + td + ' text-slate-500 dark:text-slate-500">' + (row.zona || '') + '</td>' +
                    '<td class="' + td + ' text-slate-500 dark:text-slate-500 font-mono">' + (row.telefono || '') + '</td>' +
                    '<td class="' + td + ' text-slate-500 dark:text-slate-500">' + (row.email || '').toString().substring(0, 30) + '</td>' +
                    '<td class="' + td + ' text-slate-500 dark:text-slate-500 font-mono">' + (row.cuit || '') + '</td></tr>';
            }).join('');
            var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
            return '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr><th class="' + th + ' text-center">Nro</th><th class="' + th + ' text-left">Cliente</th><th class="' + th + ' text-right">Sub Total</th><th class="' + th + ' text-right">% ventas</th><th class="' + th + ' text-center">Última compra</th><th class="' + th + ' text-left">Vendedor</th><th class="' + th + ' text-left">Zona</th><th class="' + th + ' text-left">Teléfono</th><th class="' + th + ' text-left">Email</th><th class="' + th + ' text-left">CUIT</th></tr></thead><tbody>' + rowsHtml + '</tbody></table></div>';
        }
        function buildPagination() {
            var prevDisabled = currentPage <= 1;
            var nextDisabled = currentPage >= totalPages;
            var prevClass = 'px-3 py-1.5 rounded text-xs font-medium ' + (prevDisabled ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600');
            var nextClass = 'px-3 py-1.5 rounded text-xs font-medium ' + (nextDisabled ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-300 dark:hover:bg-slate-600');
            return '<div class="flex flex-wrap items-center gap-3 mt-3"><span class="text-xs text-slate-500 dark:text-slate-400">Página ' + currentPage + ' de ' + totalPages + ' · ' + data.length + ' clientes</span><button type="button" data-fac-prev class="' + prevClass + '"' + (prevDisabled ? ' disabled' : '') + '>Anterior</button><button type="button" data-fac-next class="' + nextClass + '"' + (nextDisabled ? ' disabled' : '') + '>Siguiente</button></div>';
        }
        function render() {
            var tbl = container.querySelector('[data-fac-table]');
            var pag = container.querySelector('[data-fac-pagination]');
            if (tbl) tbl.innerHTML = buildTable(currentPage);
            if (pag) pag.innerHTML = buildPagination();
            var prevBtn = container.querySelector('[data-fac-prev]');
            var nextBtn = container.querySelector('[data-fac-next]');
            if (prevBtn) prevBtn.addEventListener('click', function () { if (currentPage > 1) { currentPage--; render(); } });
            if (nextBtn) nextBtn.addEventListener('click', function () { if (currentPage < totalPages) { currentPage++; render(); } });
        }
        var totalRows = BO_LAST_FACTURACION_DATA ? BO_LAST_FACTURACION_DATA.length : data.length;
        var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' clientes. ' : '';
        tablePartHtml = '<div data-fac-table>' + buildTable(1) + '</div><div data-fac-pagination class="fac-pagination">' + buildPagination() + '</div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + leyendaFilas + 'Facturación por cliente (ordenado por Sub Total DESC). % ventas = (sub_total / facturacion_neta_total) × 100.</p>';
        function attachFacPagination() {
            var prevBtn = container.querySelector('[data-fac-prev]');
            var nextBtn = container.querySelector('[data-fac-next]');
            if (prevBtn) prevBtn.addEventListener('click', function () { if (currentPage > 1) { currentPage--; render(); } });
            if (nextBtn) nextBtn.addEventListener('click', function () { if (currentPage < totalPages) { currentPage++; render(); } });
        }
        if (contentOnlyFac(tablePartHtml, attachFacPagination)) return;
        boSetSearchAndContent(container, 'bo-facturacion-search', 'Buscar por cliente, vendedor, zona...', searchQuery, tablePartHtml);
        attachBoSearchListener('bo-facturacion-search', function () { renderFacturacionTable(BO_LAST_FACTURACION_DATA); });
        attachFacPagination();
    }
    
    /**
     * Renderiza la tabla de remitos no facturados (con agrupación dinámica opcional).
     */
    function renderRemitosTable(data, groupByFieldsOptional) {
        var container = document.getElementById('bo-remitos-content');
        if (!container) return;
        BO_LAST_REMITOS_DATA = data || [];
        data = BO_LAST_REMITOS_DATA;
        var searchQuery = (document.getElementById('bo-remitos-search') && document.getElementById('bo-remitos-search').value) || '';
        data = filterBoDataBySearch(data, searchQuery, ['fecha', 'nro_comprobante', 'sucursal', 'punto_venta']);
        var config = BO_TAB_CONFIGS.remitos;
        var groupByFields = groupByFieldsOptional;
        if (groupByFields === undefined) {
            groupByFields = getGroupByFieldsInSelectionOrder('bo-remitos-group-by');
        }
        var tablePartHtml;
        var contentOnlyRem = function (html, onUpdated) {
            return boUpdateContentOnly(container, 'bo-remitos-search', html, onUpdated);
        };
        if (!data || data.length === 0) {
            tablePartHtml = '<div class="flex items-center justify-center py-8"><div class="text-xs text-slate-500 dark:text-slate-400">' + (searchQuery.length >= 2 ? 'No hay coincidencias para la búsqueda.' : 'No hay remitos no facturados para mostrar.') + '</div></div>';
            if (contentOnlyRem(tablePartHtml)) return;
            boSetSearchAndContent(container, 'bo-remitos-search', 'Buscar por fecha, nro comprobante, sucursal...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-remitos-search', function () { renderRemitosTable(BO_LAST_REMITOS_DATA); });
            return;
        }
        if (!container.dataset.boRemGroupByInit) {
            container.dataset.boRemGroupByInit = '1';
            initializeBoGroupByUI('bo-remitos-group-by', config, function () { return BO_LAST_REMITOS_DATA; }, function (d, g) { renderRemitosTable(d, g); });
        }
        if (groupByFields && groupByFields.length > 0) {
            var grouped = groupTableDataGeneric(data, groupByFields, config.metricKeys);
            var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
            var headerCells = config.columns.map(function (colKey) {
                var col = config.dimensions.find(function (d) { return d.key === colKey; }) || config.metrics.find(function (m) { return m.key === colKey; });
                var label = col ? col.label : colKey;
                var align = config.metrics.some(function (m) { return m.key === colKey; }) ? ' text-right' : ' text-left';
                return '<th class="' + th + align + '">' + label + '</th>';
            }).join('');
            var bodyRows = renderGroupedTableRowsBO(grouped, config, 0, true);
            var numAgrupaciones = grouped.length;
            var totalRows = BO_LAST_REMITOS_DATA ? BO_LAST_REMITOS_DATA.length : data.length;
            var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' remitos. ' : '';
            var pieAgrupado = 'Remitos no facturados. Agrupado por: ' + groupByFields.join(' → ') + '. ' + numAgrupaciones + ' agrupación' + (numAgrupaciones !== 1 ? 'es' : '') + (leyendaFilas ? ' · ' + leyendaFilas : '') + '.';
            tablePartHtml = '<div class="overflow-x-auto max-h-[420px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr>' + headerCells + '</tr></thead><tbody>' + bodyRows + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + pieAgrupado + '</p>';
            if (contentOnlyRem(tablePartHtml, function () { attachGroupToggleListenersBO(container); })) return;
            boSetSearchAndContent(container, 'bo-remitos-search', 'Buscar por fecha, nro comprobante, sucursal...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-remitos-search', function () { renderRemitosTable(BO_LAST_REMITOS_DATA); });
            attachGroupToggleListenersBO(container);
            return;
        }
        var td = 'px-4 py-3 text-slate-700 dark:text-slate-300 border-b border-slate-100 dark:border-slate-800';
        var rowsHtml = data.map(function (row) {
            return '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30"><td class="' + td + ' text-center">' + (row.fecha || '') + '</td><td class="' + td + ' font-mono">' + (row.nro_comprobante || '') + '</td><td class="' + td + '">' + (row.sucursal || '') + '</td><td class="' + td + ' text-center">' + (row.punto_venta || '') + '</td><td class="' + td + ' text-right font-mono text-slate-900 dark:text-white">' + formatCurrency(row.subtotal_desc) + '</td></tr>';
        }).join('');
        var totalRows = BO_LAST_REMITOS_DATA ? BO_LAST_REMITOS_DATA.length : data.length;
        var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' remitos' : 'Mostrando ' + data.length + ' remitos no facturados';
        tablePartHtml = '<div class="overflow-x-auto max-h-96 overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr><th class="px-4 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">Fecha</th><th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">Nro. Comprobante</th><th class="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">Sucursal</th><th class="px-4 py-3 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">Punto Venta</th><th class="px-4 py-3 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50">Subtotal</th></tr></thead><tbody>' + rowsHtml + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + leyendaFilas + '</p>';
        if (contentOnlyRem(tablePartHtml)) return;
        boSetSearchAndContent(container, 'bo-remitos-search', 'Buscar por fecha, nro comprobante, sucursal...', searchQuery, tablePartHtml);
        attachBoSearchListener('bo-remitos-search', function () { renderRemitosTable(BO_LAST_REMITOS_DATA); });
    }
    
    /**
     * Renderiza la tabla de detalle de backorder por renglón (con agrupación dinámica opcional).
     */
    function renderBackorderDetalleTable(data, groupByFieldsOptional) {
        var container = document.getElementById('bo-backorder-content');
        if (!container) return;
        BO_LAST_BACKORDER_DATA = data || [];
        data = BO_LAST_BACKORDER_DATA;
        var searchQuery = (document.getElementById('bo-backorder-search') && document.getElementById('bo-backorder-search').value) || '';
        data = filterBoDataBySearch(data, searchQuery, ['descripcion', 'cod_manual', 'cliente', 'nombre_rubro', 'nombre_sub_rubro', 'nombre_vendedor', 'nro_comp', 'estado']);
        var config = BO_TAB_CONFIGS.backorder;
        var groupByFields = groupByFieldsOptional;
        if (groupByFields === undefined) {
            groupByFields = getGroupByFieldsInSelectionOrder('bo-backorder-group-by');
        }
        var tablePartHtml;
        var contentOnlyBo = function (html, onUpdated) {
            return boUpdateContentOnly(container, 'bo-backorder-search', html, onUpdated);
        };
        if (!data || data.length === 0) {
            tablePartHtml = '<div class="flex items-center justify-center py-8"><div class="text-xs text-slate-500 dark:text-slate-400">' + (searchQuery.length >= 2 ? 'No hay coincidencias para la búsqueda.' : 'No hay backorder para mostrar.') + '</div></div>';
            if (contentOnlyBo(tablePartHtml)) return;
            boSetSearchAndContent(container, 'bo-backorder-search', 'Buscar por descripción, código, cliente, rubro, vendedor...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-backorder-search', function () { renderBackorderDetalleTable(BO_LAST_BACKORDER_DATA); });
            return;
        }
        if (!container.dataset.boBoGroupByInit) {
            container.dataset.boBoGroupByInit = '1';
            initializeBoGroupByUI('bo-backorder-group-by', config, function () { return BO_LAST_BACKORDER_DATA; }, function (d, g) { renderBackorderDetalleTable(d, g); });
        }
        if (groupByFields && groupByFields.length > 0) {
            var grouped = groupTableDataGeneric(data, groupByFields, config.metricKeys);
            var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
            var headerCells = config.columns.map(function (colKey) {
                var col = config.dimensions.find(function (d) { return d.key === colKey; }) || config.metrics.find(function (m) { return m.key === colKey; });
                var label = col ? col.label : colKey;
                var align = config.metrics.some(function (m) { return m.key === colKey; }) ? ' text-right' : ' text-left';
                return '<th class="' + th + align + '">' + label + '</th>';
            }).join('');
            var bodyRows = renderGroupedTableRowsBO(grouped, config, 0, true);
            var numAgrupaciones = grouped.length;
            var totalRows = BO_LAST_BACKORDER_DATA ? BO_LAST_BACKORDER_DATA.length : data.length;
            var leyendaFilas = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' renglones. ' : '';
            var pieAgrupado = 'Backorder detalle. Agrupado por: ' + groupByFields.join(' → ') + '. ' + numAgrupaciones + ' agrupación' + (numAgrupaciones !== 1 ? 'es' : '') + (leyendaFilas ? ' · ' + leyendaFilas : '') + '.';
            tablePartHtml = '<div class="overflow-x-auto max-h-[500px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr>' + headerCells + '</tr></thead><tbody>' + bodyRows + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + pieAgrupado + '</p>';
            if (contentOnlyBo(tablePartHtml, function () { attachGroupToggleListenersBO(container); })) return;
            boSetSearchAndContent(container, 'bo-backorder-search', 'Buscar por descripción, código, cliente, rubro, vendedor...', searchQuery, tablePartHtml);
            attachBoSearchListener('bo-backorder-search', function () { renderBackorderDetalleTable(BO_LAST_BACKORDER_DATA); });
            attachGroupToggleListenersBO(container);
            return;
        }
        var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
        var td = 'px-3 py-2 text-xs border-b border-slate-100 dark:border-slate-800';
        var sortedData = sortByArticulo(data);
        var rowsHtml = sortedData.map(function (row) {
            return '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30"><td class="' + td + ' text-slate-700 dark:text-slate-300 text-center">' + (row.fecha || '') + '</td><td class="' + td + ' text-slate-600 dark:text-slate-400 font-mono">' + (row.nro_comp || '') + '</td><td class="' + td + ' text-slate-700 dark:text-slate-300">' + (row.descripcion || '').toString().substring(0, 80) + '</td><td class="' + td + ' text-slate-600 dark:text-slate-400 font-mono">' + (row.cod_manual || '') + '</td><td class="' + td + ' text-right font-mono text-slate-900 dark:text-white">' + formatNumber(row.cant_pend) + '</td><td class="' + td + ' text-slate-700 dark:text-slate-300">' + (row.cliente || '').toString().substring(0, 40) + '</td><td class="' + td + ' text-right font-mono text-slate-900 dark:text-white">' + formatCurrency(row.precio_x_renglon) + '</td><td class="' + td + ' text-slate-600 dark:text-slate-400">' + (row.nombre_rubro || '') + '</td><td class="' + td + ' text-slate-500 dark:text-slate-500">' + (row.nombre_sub_rubro || '') + '</td><td class="' + td + ' text-slate-500 dark:text-slate-500">' + (row.nombre_vendedor || '') + '</td></tr>';
        }).join('');
        var totalRows = BO_LAST_BACKORDER_DATA ? BO_LAST_BACKORDER_DATA.length : data.length;
        var leyenda = searchQuery.length >= 2 ? 'Mostrando ' + data.length + ' de ' + totalRows + ' renglones de backorder' : 'Mostrando ' + data.length + ' renglones de backorder';
        tablePartHtml = '<div class="overflow-x-auto max-h-[500px] overflow-y-auto"><table class="w-full border-collapse text-sm"><thead class="sticky top-0"><tr><th class="' + th + ' text-center">Fecha</th><th class="' + th + ' text-left">Nro comp</th><th class="' + th + ' text-left">Descripción</th><th class="' + th + ' text-left">Cod. manual</th><th class="' + th + ' text-right">Cant. pend</th><th class="' + th + ' text-left">Cliente</th><th class="' + th + ' text-right">Precio x renglón</th><th class="' + th + ' text-left">Rubro</th><th class="' + th + ' text-left">Subrubro</th><th class="' + th + ' text-left">Vendedor</th></tr></thead><tbody>' + rowsHtml + '</tbody></table></div><p class="text-xs text-slate-400 dark:text-slate-500 mt-3">' + leyenda + '</p>';
        if (contentOnlyBo(tablePartHtml)) return;
        boSetSearchAndContent(container, 'bo-backorder-search', 'Buscar por descripción, código, cliente, rubro, vendedor...', searchQuery, tablePartHtml);
        attachBoSearchListener('bo-backorder-search', function () { renderBackorderDetalleTable(BO_LAST_BACKORDER_DATA); });
    }
    
    // =========================================================
    // MANEJO DE DATOS
    // =========================================================
    
    /**
     * Procesa la respuesta del API y renderiza todas las tablas
     */
    function processReportData(response) {
        console.log('📊 [BO-Stock-Facturacion] Procesando datos del reporte...');
        
        const data = response.data || [];
        const totals = response.totals || {};
        const extra = response.meta?.extra || {};
        const tabs = extra.tabs || {};
        
        // Actualizar KPIs
        updateKPIs(totals);
        
        // Renderizar todas las tablas
        renderResumenTable(data, totals);
        renderDetalleSinStockTable(tabs.detalle_sin_stock || []);
        renderDetalleConStockTable(tabs.detalle_con_stock || []);
        renderDetalleConIngresoTable(tabs.detalle_con_ingreso || []);
        renderFacturacionTable(tabs.facturacion || []);
        renderRemitosTable(tabs.remitos || []);
        renderBackorderDetalleTable(tabs.backorder_detalle_rows || []);
        
        // Mostrar notas si las hay
        if (response.notes && response.notes.length > 0) {
            console.log('📊 [BO-Stock-Facturacion] Notas:', response.notes);
        }
        
        console.log('📊 [BO-Stock-Facturacion] Datos procesados exitosamente');
    }
    
    // =========================================================
    // INTEGRACIÓN CON DASHBOARD.JS
    // =========================================================
    
    /**
     * Hook para interceptar respuestas del API
     * Se llama cuando dashboard.js recibe datos del reporte
     */
    window.boStockFacturacionHandler = {
        processData: processReportData,
        switchTab: switchToTab,
        updateKPIs: updateKPIs
    };
    
    // Escuchar evento personalizado cuando dashboard.js carga datos
    document.addEventListener('reportDataLoaded', function(event) {
        if (event.detail && event.detail.slug === 'bo-stock-facturacion') {
            processReportData(event.detail.response);
        }
    });
    
    // =========================================================
    // INICIALIZACIÓN
    // =========================================================
    
        document.addEventListener('DOMContentLoaded', function() {
        console.log('📊 [BO-Stock-Facturacion] DOM cargado, inicializando componentes...');
        
        initializeTabs();
        initializeKPIs();
        initializeResumenDrill();
        
        console.log('📊 [BO-Stock-Facturacion] Controlador listo');
    });
    
})();
