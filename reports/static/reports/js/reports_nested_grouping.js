/**
 * Agrupación anidada reutilizable ("Agrupar por" multi-select + "Buscar") para reportes.
 * Extraído de bo_stock_facturacion.js (comportamiento idéntico) para compartirlo con
 * pedidos-pendientes-produccion. Expone window.ReportsNestedGrouping.
 */
(function (global) {
    'use strict';
    if (global.ReportsNestedGrouping) return;

    function defaultFormatCell(value) {
        if (value === undefined || value === null) return '';
        return String(value);
    }

    /**
     * Filtra filas por búsqueda predictiva (mín. 2 caracteres). keys = array de nombres de propiedades a buscar.
     */
    function filterBySearch(data, query, keys) {
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
    function searchEscAttr(s) {
        if (s == null || s === '') return '';
        return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    /** HTML del input de búsqueda para un tab (id, placeholder, valor actual opcional). Misma estructura que Agrupar por: label arriba, campo abajo; altura coherente con el campo de agrupación. */
    function searchInputHtml(id, placeholder, currentValue) {
        var valAttr = (currentValue != null && currentValue !== '') ? ' value="' + searchEscAttr(currentValue) + '"' : '';
        return '<div class="w-full min-w-0">' +
            '<label for="' + id + '" class="text-xs font-semibold text-slate-500 dark:text-slate-400 block mb-2">Buscar</label>' +
            '<input type="text" id="' + id + '" placeholder="' + (placeholder || 'Escriba al menos 2 caracteres...') + '"' + valAttr + ' ' +
            'class="w-full min-w-0 min-h-[2.5rem] py-2 px-3 text-xs border border-slate-300 dark:border-slate-600 rounded-md bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-sky-400 focus:border-sky-400" autocomplete="off">' +
            '</div>';
    }

    var boSearchTimeout = null;
    /** Debounce en ms para no re-renderizar en cada tecla y no perder foco. */
    var BO_SEARCH_DEBOUNCE_MS = 400;
    function attachSearchListener(inputId, onFilter) {
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
    function setSearchAndContent(container, searchInputId, placeholder, searchQuery, tablePartHtml) {
        var searchSlot = document.getElementById(container.id.replace('-content', '-search-slot'));
        if (searchSlot) searchSlot.innerHTML = searchInputHtml(searchInputId, placeholder, searchQuery);
        container.innerHTML = '<div class="bo-tab-content-area">' + tablePartHtml + '</div>';
    }

    /**
     * Actualiza solo el área de contenido del tab (tabla/leyenda), sin tocar el input de búsqueda,
     * para no destruir el input y no perder el foco al filtrar.
     * Si el input ya existe (en el slot) y hay .bo-tab-content-area, pone tablePartHtml ahí y ejecuta onUpdated(container).
     * Retorna true si se hizo solo actualización de contenido; false si hay que hacer innerHTML completo.
     */
    function updateContentOnly(container, searchInputId, tablePartHtml, onUpdated) {
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
    function groupTableDataGeneric(data, groupByFields, metricKeys, sortItemsFn) {
        if (!groupByFields || !groupByFields.length || !data || !data.length) return data;
        var level = 0;
        function groupByLevels(items, fields, lev) {
            if (lev >= fields.length) {
                var sorted = (sortItemsFn || sortByArticulo)(items);
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

    /**
     * Renderiza filas de tabla con grupos (expandir/colapsar, subtotales).
     */
    function renderGroupedTableRows(groupedData, config, level, collapsedDefault) {
        level = level || 0;
        collapsedDefault = collapsedDefault !== false;
        var dimensions = config.dimensions || [];
        var metrics = config.metrics || [];
        var metricKeys = config.metricKeys || [];
        var allCols = config.columns || [];
        var th = 'px-3 py-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50';
        var td = 'px-3 py-2 text-xs border-b border-slate-100 dark:border-slate-800';
        var fmtCell = config.formatCell || defaultFormatCell;
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
                        rowsHTML += '<td class="' + td + ' text-right font-semibold text-sky-600 dark:text-sky-400">' + fmtCell(g.totals[colKey], colKey, config) + '</td>';
                    } else {
                        rowsHTML += '<td class="' + td + '"></td>';
                    }
                });
                rowsHTML += '</tr>';
                rowsHTML += '<tr class="bo-group-children" data-bo-group-parent="' + groupId + '" style="' + (collapsedDefault ? 'display:none;' : '') + '"><td colspan="' + allCols.length + '" class="p-0 border-0"><table class="w-full border-collapse text-sm"><tbody>';
                rowsHTML += renderGroupedTableRows(item.children, config, level + 1, collapsedDefault);
                rowsHTML += '</tbody></table></td></tr>';
            } else {
                var row = item.data;
                rowsHTML += '<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/30 bo-detail-row">';
                allCols.forEach(function (colKey) {
                    var val = row[colKey];
                    var formatted = fmtCell(val, colKey, config);
                    if (formatted === '' && (val === 0 || val === '0')) formatted = fmtCell(0, colKey, config);
                    if (formatted === '' && val !== undefined && val !== null) formatted = String(val).substring(0, 60);
                    var align = metrics.some(function (m) { return m.key === colKey; }) ? ' text-right font-mono' : '';
                    var cellClass = td + ' text-slate-700 dark:text-slate-300' + align;
                    var dataAttr = '';
                    if (typeof config.decorateCell === 'function') {
                        var deco = config.decorateCell(colKey, row) || {};
                        if (deco.cellClass) cellClass += ' ' + deco.cellClass;
                        if (deco.dataAttr) dataAttr = deco.dataAttr;
                    }
                    rowsHTML += '<td class="' + cellClass + '"' + dataAttr + '>' + formatted + '</td>';
                });
                rowsHTML += '</tr>';
            }
        });
        return rowsHTML;
    }


    function attachGroupToggleListeners(container) {
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
    function initializeGroupByUI(selectId, config, getDataFn, renderTableFn) {
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

    global.ReportsNestedGrouping = {
        filterBySearch: filterBySearch,
        searchInputHtml: searchInputHtml,
        attachSearchListener: attachSearchListener,
        setSearchAndContent: setSearchAndContent,
        updateContentOnly: updateContentOnly,
        sortByArticulo: sortByArticulo,
        getGroupByFieldsInSelectionOrder: getGroupByFieldsInSelectionOrder,
        groupTableDataGeneric: groupTableDataGeneric,
        renderGroupedTableRows: renderGroupedTableRows,
        attachGroupToggleListeners: attachGroupToggleListeners,
        initializeGroupByUI: initializeGroupByUI
    };
})(window);
