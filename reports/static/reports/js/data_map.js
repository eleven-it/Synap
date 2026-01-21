/**
 * Data Map V2 - Frontend JavaScript
 * Maneja las 3 vistas: Overview, Cluster, Table Focus
 * Con filtros, búsqueda y inspector mejorado
 */

// Estado global
const state = {
    view: 'overview',  // overview, cluster, table
    clusterId: null,
    clusterLabel: null,  // Nombre/etiqueta del cluster actual
    table: null,
    depth: 1,
    filters: {
        type: 'both',        // fk, learned, both
        status: 'approved',  // approved, proposed, all
        min_conf: 0.8,
        direction: 'both',   // in, out, both
        hide_temp: true
    },
    allTables: [],  // Para búsqueda
    clusters: []    // Para overview
};

// Variables globales
let network = null;
let nodes = null;
let edges = null;
let dataMapApiUrl = '';
let validateApiUrl = '';
let governanceApiUrl = '';

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        try {
            initializeDataMap();
        } catch (error) {
            console.error('Error inicializando mapa de datos:', error);
        }
    }, 100);
});

function initializeDataMap() {
    // Obtener URLs desde el template (se inyectarán)
    dataMapApiUrl = window.DATA_MAP_API_URL || '/api/reports/builder/data-map/';
    validateApiUrl = window.VALIDATE_API_URL || '/api/reports/builder/data-map/validate-relationship/';
    governanceApiUrl = window.GOVERNANCE_API_URL || '/api/reports/builder/data-map/relationships/';
    
    // Cargar filtros desde localStorage
    loadFiltersFromStorage();
    
    // Inicializar UI
    setupEventListeners();
    
    // Cargar vista inicial (overview)
    loadOverview();
}

function setupEventListeners() {
    // Breadcrumbs
    document.getElementById('breadcrumb-overview')?.addEventListener('click', () => navigateToView('overview'));
    
    // Search
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', handleSearch);
        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const value = e.target.value.trim();
                if (value) {
                    hideSearchSuggestions();
                    searchAndFocus(value);
                }
            } else if (e.key === 'Escape') {
                hideSearchSuggestions();
            } else if (e.key === 'ArrowDown' && searchSuggestions.length > 0) {
                e.preventDefault();
                // Navegar por sugerencias (implementación básica)
                const firstSuggestion = document.querySelector('#search-suggestions button');
                if (firstSuggestion) {
                    firstSuggestion.focus();
                }
            }
        });
        
        // Cerrar sugerencias al hacer clic fuera
        document.addEventListener('click', (e) => {
            const suggestionsContainer = document.getElementById('search-suggestions');
            if (searchInput && suggestionsContainer && 
                !searchInput.contains(e.target) && 
                !suggestionsContainer.contains(e.target)) {
                hideSearchSuggestions();
            }
        });
    }
    
    // Cargar todas las tablas disponibles para búsqueda
    loadAllTablesForSearch();
    
    // Filtros
    setupFilterListeners();
    
    // Botón refresh
    document.getElementById('btn-refresh')?.addEventListener('click', () => refreshCurrentView());
}

function setupFilterListeners() {
    const filterType = document.getElementById('filter-type');
    const filterStatus = document.getElementById('filter-status');
    const filterMinConf = document.getElementById('filter-min-conf');
    const filterDirection = document.getElementById('filter-direction');
    const filterDepth = document.getElementById('filter-depth');
    const filterHideTemp = document.getElementById('filter-hide-temp');
    
    if (filterType) filterType.addEventListener('change', (e) => {
        state.filters.type = e.target.value;
        saveFiltersToStorage();
        reloadCurrentView();
    });
    
    if (filterStatus) filterStatus.addEventListener('change', (e) => {
        state.filters.status = e.target.value;
        saveFiltersToStorage();
        reloadCurrentView();
    });
    
    if (filterMinConf) filterMinConf.addEventListener('input', (e) => {
        state.filters.min_conf = parseFloat(e.target.value);
        saveFiltersToStorage();
        reloadCurrentView();
    });
    
    if (filterDirection) filterDirection.addEventListener('change', (e) => {
        state.filters.direction = e.target.value;
        saveFiltersToStorage();
        reloadCurrentView();
    });
    
    if (filterDepth) filterDepth.addEventListener('change', (e) => {
        state.depth = parseInt(e.target.value);
        saveFiltersToStorage();
        reloadCurrentView();
    });
    
    if (filterHideTemp) filterHideTemp.addEventListener('change', (e) => {
        state.filters.hide_temp = e.target.checked;
        saveFiltersToStorage();
        reloadCurrentView();
    });
}

// ========== NAVEGACIÓN ==========

function navigateToView(view, params = {}) {
    state.view = view;
    
    if (view === 'overview') {
        state.clusterId = null;
        state.table = null;
        loadOverview();
    } else if (view === 'cluster') {
        state.clusterId = params.clusterId;
        state.clusterLabel = params.clusterLabel || params.clusterId; // Guardar etiqueta si está disponible
        state.table = null;
        loadCluster(params.clusterId);
    } else if (view === 'table') {
        state.table = params.table;
        state.clusterId = null;
        state.clusterLabel = null;
        loadTable(params.table);
    }
    
    updateBreadcrumbs();
    updateViewVisibility();
}

function updateBreadcrumbs() {
    const breadcrumbOverview = document.getElementById('breadcrumb-overview');
    const breadcrumbCluster = document.getElementById('breadcrumb-cluster');
    const breadcrumbClusterSep = document.getElementById('breadcrumb-cluster-sep');
    const breadcrumbTable = document.getElementById('breadcrumb-table');
    
    if (breadcrumbOverview) {
        breadcrumbOverview.classList.toggle('active', state.view === 'overview');
    }
    
    if (breadcrumbCluster) {
        if (state.view === 'cluster' && state.clusterId) {
            breadcrumbCluster.textContent = state.clusterLabel || state.clusterId;
            breadcrumbCluster.classList.remove('hidden');
            breadcrumbCluster.classList.add('px-3', 'py-1', 'rounded-lg', 'bg-sky-100', 'dark:bg-sky-900', 'text-sky-700', 'dark:text-sky-300');
            if (breadcrumbClusterSep) {
                breadcrumbClusterSep.classList.remove('hidden');
            }
        } else {
            breadcrumbCluster.classList.add('hidden');
            if (breadcrumbClusterSep) {
                breadcrumbClusterSep.classList.add('hidden');
            }
        }
    }
    
    if (breadcrumbTable) {
        if (state.view === 'table' && state.table) {
            breadcrumbTable.textContent = state.table;
            breadcrumbTable.classList.remove('hidden');
            breadcrumbTable.classList.add('px-3', 'py-1', 'rounded-lg', 'bg-sky-100', 'dark:bg-sky-900', 'text-sky-700', 'dark:text-sky-300');
        } else {
            breadcrumbTable.classList.add('hidden');
        }
    }
}

function updateGraphTitle() {
    const titleContainer = document.getElementById('graph-title-container');
    const title = document.getElementById('graph-title');
    const subtitle = document.getElementById('graph-subtitle');
    
    if (!titleContainer || !title || !subtitle) return;
    
    if (state.view === 'cluster' && state.clusterId) {
        title.textContent = `Cluster: ${state.clusterLabel || state.clusterId}`;
        subtitle.textContent = `Visualizando todas las tablas y relaciones dentro de este cluster`;
        titleContainer.classList.remove('hidden');
    } else if (state.view === 'table' && state.table) {
        title.textContent = `Tabla: ${state.table}`;
        subtitle.textContent = `Red de relaciones conectadas a esta tabla (profundidad: ${state.depth})`;
        titleContainer.classList.remove('hidden');
    } else {
        titleContainer.classList.add('hidden');
    }
}

function updateViewVisibility() {
    const overviewContainer = document.getElementById('overview-container');
    const graphContainer = document.getElementById('graph-container');
    
    if (overviewContainer) {
        overviewContainer.classList.toggle('hidden', state.view !== 'overview');
    }
    if (graphContainer) {
        graphContainer.classList.toggle('hidden', state.view !== 'cluster' && state.view !== 'table');
    }
}

// ========== CARGA DE VISTAS ==========

async function loadOverview() {
    try {
        showProgressModal();
        updateProgress(10, 'Cargando overview...', 'Obteniendo clusters...');
        
        const url = `${dataMapApiUrl}?view=overview`;
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        state.clusters = data.clusters || [];
        
        // Guardar todas las tablas para búsqueda desde los clusters
        state.allTables = [];
        state.clusters.forEach(cluster => {
            if (cluster.table_names) {
                state.allTables.push(...cluster.table_names);
            }
        });
        
        // También cargar todas las tablas disponibles para el selector y búsqueda
        if (allAvailableTables.length === 0) {
            await loadAllTablesForSearch();
        }
        
        updateProgress(90, 'Renderizando...', 'Creando vista de clusters...');
        
        renderOverview(data);
        
        updateStats(data.stats);
        
        hideProgressModal();
        
    } catch (error) {
        console.error('Error cargando overview:', error);
        showError('Error cargando overview: ' + error.message);
        hideProgressModal();
    }
}

async function loadCluster(clusterId) {
    try {
        showProgressModal();
        updateProgress(10, 'Cargando cluster...', `Obteniendo datos del cluster ${clusterId}...`);
        
        const filtersHash = getFiltersHash();
        const url = `${dataMapApiUrl}?view=cluster&cluster_id=${clusterId}&${buildFiltersQuery()}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Guardar información del cluster si está disponible
        if (data.cluster_id) {
            state.clusterId = data.cluster_id;
            // Buscar el label del cluster desde los clusters cargados
            const cluster = state.clusters.find(c => c.id === data.cluster_id);
            if (cluster) {
                state.clusterLabel = cluster.label || cluster.id;
            } else {
                // Si no está en el estado, usar el cluster_id como fallback
                state.clusterLabel = data.cluster_id;
            }
        }
        
        updateProgress(90, 'Renderizando...', 'Creando grafo del cluster...');
        
        renderGraph(data.nodes, data.edges);
        
        updateStats(data.stats);
        
        // Actualizar breadcrumbs para mostrar el cluster
        updateBreadcrumbs();
        
        hideProgressModal();
        
    } catch (error) {
        console.error('Error cargando cluster:', error);
        showError('Error cargando cluster: ' + error.message);
        hideProgressModal();
    }
}

async function loadTable(tableName) {
    try {
        showProgressModal();
        updateProgress(10, 'Cargando tabla...', `Obteniendo red de ${tableName}...`);
        
        const url = `${dataMapApiUrl}?view=table&table=${tableName}&depth=${state.depth}&${buildFiltersQuery()}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        updateProgress(90, 'Renderizando...', 'Creando grafo de la tabla...');
        
        renderGraph(data.nodes, data.edges);
        
        updateStats(data.stats);
        
        // Actualizar breadcrumbs para mostrar la tabla
        updateBreadcrumbs();
        
        hideProgressModal();
        
    } catch (error) {
        console.error('Error cargando tabla:', error);
        showError('Error cargando tabla: ' + error.message);
        hideProgressModal();
    }
}

function reloadCurrentView() {
    if (state.view === 'overview') {
        loadOverview();
    } else if (state.view === 'cluster' && state.clusterId) {
        loadCluster(state.clusterId);
    } else if (state.view === 'table' && state.table) {
        loadTable(state.table);
    }
}

function refreshCurrentView() {
    // Forzar refresh agregando force_refresh=true
    const currentUrl = window.location.href;
    if (state.view === 'overview') {
        loadOverview();
    } else if (state.view === 'cluster' && state.clusterId) {
        loadCluster(state.clusterId);
    } else if (state.view === 'table' && state.table) {
        loadTable(state.table);
    }
}

// ========== RENDERIZADO ==========

function renderOverview(data) {
    const container = document.getElementById('overview-container');
    if (!container) return;
    
    const clusters = data.clusters || [];
    
    let html = '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">';
    
    clusters.forEach(cluster => {
        html += `
            <div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 hover:shadow-lg transition-shadow">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-sm font-semibold text-slate-900 dark:text-white">
                        ${cluster.label || cluster.id}
                    </h3>
                    <div class="flex items-center gap-2">
                        <button onclick="event.stopPropagation(); editCluster('${cluster.id}', '${(cluster.label || cluster.id).replace(/'/g, "\\'")}')" 
                                class="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                                title="Editar cluster">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                            </svg>
                        </button>
                        <button onclick="navigateToView('cluster', {clusterId: '${cluster.id}', clusterLabel: '${(cluster.label || cluster.id).replace(/'/g, "\\'")}'})" 
                                class="text-xs px-2 py-1 bg-sky-100 dark:bg-sky-900 text-sky-700 dark:text-sky-300 rounded hover:bg-sky-200 dark:hover:bg-sky-800">
                            Explorar →
                        </button>
                    </div>
                </div>
                <div class="grid grid-cols-3 gap-2 text-xs">
                    <div>
                        <div class="text-slate-500 dark:text-slate-400">Tablas</div>
                        <div class="text-lg font-bold text-slate-900 dark:text-white">${cluster.tables_count || 0}</div>
                    </div>
                    <div>
                        <div class="text-slate-500 dark:text-slate-400">FK</div>
                        <div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">${cluster.fk_edges || 0}</div>
                    </div>
                    <div>
                        <div class="text-slate-500 dark:text-slate-400">Aprendidas</div>
                        <div class="text-lg font-bold text-amber-600 dark:text-amber-400">${cluster.learned_edges || 0}</div>
                    </div>
                </div>
                ${cluster.density ? `
                    <div class="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Densidad: ${(cluster.density * 100).toFixed(1)}%
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    html += '</div>';
    
    container.innerHTML = html;
}

function renderGraph(nodesData, edgesData) {
    // Actualizar título según la vista
    updateGraphTitle();
    
    const container = document.getElementById('network-container');
    if (!container) return;
    
    // Limpiar red anterior
    if (network) {
        network.destroy();
    }
    
    // Crear datasets
    nodes = new vis.DataSet(nodesData);
    edges = new vis.DataSet(edgesData);
    
    const data_vis = { nodes: nodes, edges: edges };
    
    const options = {
        nodes: {
            shape: 'box',
            font: {
                size: 14,
                face: 'Inter, system-ui, sans-serif',
                color: '#1e293b'
            },
            borderWidth: 2,
            shadow: {
                enabled: true,
                color: 'rgba(0,0,0,0.1)',
                size: 5,
                x: 2,
                y: 2
            },
            margin: 10,
            widthConstraint: {
                maximum: 200
            }
        },
        edges: {
            font: {
                size: 11,
                align: 'middle',
                color: '#64748b'
            },
            arrows: {
                to: {
                    enabled: true,
                    scaleFactor: 0.8
                }
            },
            smooth: {
                type: 'continuous',
                roundness: 0.5
            },
            color: {
                inherit: 'from'
            }
        },
        physics: {
            enabled: true,
            stabilization: {
                enabled: true,
                iterations: 200,
                fit: true
            },
            barnesHut: {
                gravitationalConstant: -2000,
                centralGravity: 0.1,
                springLength: 200,
                springConstant: 0.04,
                damping: 0.09
            }
        },
        interaction: {
            hover: true,
            tooltipDelay: 100,
            zoomView: true,
            dragView: true
        },
        layout: {
            improvedLayout: true,
            hierarchical: {
                enabled: false
            }
        }
    };
    
    network = new vis.Network(container, data_vis, options);
    
    // Eventos
    network.on("click", function (params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            showNodeInspector(node);
        } else if (params.edges.length > 0) {
            const edgeId = params.edges[0];
            const edge = edges.get(edgeId);
            showEdgeInspector(edge);
        } else {
            closeInspector();
        }
    });
}

// ========== INSPECTOR ==========

function showNodeInspector(node) {
    const inspector = document.getElementById('inspector-panel');
    const inspectorContent = document.getElementById('inspector-content');
    if (!inspector || !inspectorContent) return;
    
    let html = `
        <div class="space-y-3">
            <div class="flex items-center justify-between">
                <h3 class="text-sm font-semibold text-slate-900 dark:text-white">${node.label || node.id}</h3>
                <button onclick="closeInspector()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="text-xs text-slate-600 dark:text-slate-400">
                ${node.title || `Tabla ${node.id}`}
            </div>
            <button onclick="navigateToView('table', {table: '${node.id}'})"
                    class="w-full px-3 py-2 bg-sky-600 text-white text-xs rounded-lg hover:bg-sky-700 transition-colors">
                🔍 Focus en esta tabla
            </button>
        </div>
    `;
    
    inspectorContent.innerHTML = html;
    inspector.classList.remove('hidden');
}

function showEdgeInspector(edge) {
    const inspector = document.getElementById('inspector-panel');
    const inspectorContent = document.getElementById('inspector-content');
    if (!inspector || !inspectorContent) return;
    
    const typeLabel = edge.type === 'foreign_key' ? 
        '<span class="px-2 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200">FK</span>' :
        '<span class="px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">Aprendida</span>';
    
    let html = `
        <div class="space-y-3">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                    ${typeLabel}
                </div>
                <button onclick="closeInspector()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="text-xs space-y-1">
                <div><span class="font-semibold">Desde:</span> <span class="font-mono">${edge.from}</span></div>
                <div><span class="font-semibold">Hacia:</span> <span class="font-mono">${edge.to}</span></div>
                <div><span class="font-semibold">Relación:</span> ${edge.label}</div>
            </div>
    `;
    
    if (edge.type === 'foreign_key') {
        html += `
            <div class="text-xs space-y-1 pt-2 border-t border-slate-200 dark:border-slate-700">
                ${edge.update_rule && edge.update_rule !== 'RESTRICT' ? `
                    <div><span class="font-semibold">UPDATE:</span> ${edge.update_rule}</div>
                ` : ''}
                ${edge.delete_rule && edge.delete_rule !== 'RESTRICT' ? `
                    <div><span class="font-semibold">DELETE:</span> ${edge.delete_rule}</div>
                ` : ''}
            </div>
        `;
    } else if (edge.type === 'learned') {
        html += `
            <div class="text-xs space-y-1 pt-2 border-t border-slate-200 dark:border-slate-700">
                <div><span class="font-semibold">Confianza:</span> ${(edge.confidence * 100).toFixed(1)}%</div>
                <div><span class="font-semibold">Status:</span> ${edge.status || 'proposed'}</div>
                <div><span class="font-semibold">Usos:</span> ${edge.usage_count || 0}</div>
            </div>
            <div class="flex gap-2 pt-2">
                ${edge.status === 'proposed' ? `
                    <button onclick="approveRelationship(${edge.id || 'null'})"
                            class="flex-1 px-3 py-2 bg-emerald-600 text-white text-xs rounded-lg hover:bg-emerald-700">
                        ✓ Aprobar
                    </button>
                ` : ''}
                <button onclick="deprecateRelationship(${edge.id || 'null'})"
                        class="flex-1 px-3 py-2 bg-red-600 text-white text-xs rounded-lg hover:bg-red-700">
                    ✗ Deprecar
                </button>
                <button onclick="editRelationship(${edge.id || 'null'})"
                        class="flex-1 px-3 py-2 bg-sky-600 text-white text-xs rounded-lg hover:bg-sky-700">
                    ✏️ Editar
                </button>
            </div>
        `;
    }
    
    html += '</div>';
    
    inspectorContent.innerHTML = html;
    inspector.classList.remove('hidden');
}

function closeInspector() {
    const inspector = document.getElementById('inspector-panel');
    if (inspector) {
        inspector.classList.add('hidden');
    }
}

// ========== BÚSQUEDA ==========

let searchSuggestions = [];
let searchTimeout = null;

function handleSearch(e) {
    const query = e.target.value.trim();
    
    // Limpiar timeout anterior
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    // Si está vacío, limpiar sugerencias
    if (!query) {
        hideSearchSuggestions();
        return;
    }
    
    // Debounce: esperar 300ms antes de buscar
    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300);
}

function performSearch(query) {
    const queryLower = query.toLowerCase();
    
    // Buscar en todas las tablas disponibles
    const matches = allAvailableTables.filter(table => 
        table.toLowerCase().includes(queryLower)
    ).slice(0, 10); // Limitar a 10 resultados
    
    searchSuggestions = matches;
    showSearchSuggestions(matches, query);
}

function showSearchSuggestions(suggestions, query) {
    // Eliminar sugerencias anteriores si existen
    let suggestionsContainer = document.getElementById('search-suggestions');
    if (!suggestionsContainer) {
        const searchInput = document.getElementById('search-input');
        if (!searchInput) return;
        
        suggestionsContainer = document.createElement('div');
        suggestionsContainer.id = 'search-suggestions';
        suggestionsContainer.className = 'absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-lg shadow-lg max-h-60 overflow-y-auto';
        searchInput.parentElement.appendChild(suggestionsContainer);
    }
    
    if (suggestions.length === 0) {
        suggestionsContainer.innerHTML = `
            <div class="px-4 py-2 text-sm text-slate-500 dark:text-slate-400">
                No se encontraron tablas que coincidan con "${query}"
            </div>
        `;
        suggestionsContainer.classList.remove('hidden');
        return;
    }
    
    let html = '';
    suggestions.forEach((table, index) => {
        const highlighted = table.replace(
            new RegExp(`(${query})`, 'gi'),
            '<strong class="text-sky-600 dark:text-sky-400">$1</strong>'
        );
        html += `
            <button onclick="selectSearchSuggestion('${table}')" 
                    class="w-full text-left px-4 py-2 text-sm text-slate-900 dark:text-white hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors ${index === 0 ? 'bg-slate-50 dark:bg-slate-700' : ''}">
                ${highlighted}
            </button>
        `;
    });
    
    suggestionsContainer.innerHTML = html;
    suggestionsContainer.classList.remove('hidden');
}

function hideSearchSuggestions() {
    const suggestionsContainer = document.getElementById('search-suggestions');
    if (suggestionsContainer) {
        suggestionsContainer.classList.add('hidden');
    }
}

function selectSearchSuggestion(tableName) {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = tableName;
    }
    hideSearchSuggestions();
    searchAndFocus(tableName);
}

function searchAndFocus(query) {
    if (!query || !query.trim()) {
        return;
    }
    
    const queryLower = query.trim().toLowerCase();
    
    // Buscar en todas las tablas disponibles
    const matches = allAvailableTables.filter(table => 
        table.toLowerCase().includes(queryLower)
    );
    
    if (matches.length > 0) {
        // Enfocar en la primera coincidencia exacta o la primera parcial
        const exactMatch = matches.find(t => t.toLowerCase() === queryLower);
        const tableToFocus = exactMatch || matches[0];
        
        navigateToView('table', { table: tableToFocus });
    } else {
        showToast(`No se encontraron tablas que coincidan con "${query}"`, 'warning');
    }
}

// ========== FILTROS ==========

function buildFiltersQuery() {
    const params = new URLSearchParams();
    params.append('type', state.filters.type);
    params.append('status', state.filters.status);
    params.append('min_conf', state.filters.min_conf.toString());
    params.append('direction', state.filters.direction);
    params.append('hide_temp', state.filters.hide_temp.toString());
    return params.toString();
}

function getFiltersHash() {
    // Hash simple para cache keys
    return btoa(JSON.stringify(state.filters)).substring(0, 8);
}

function saveFiltersToStorage() {
    try {
        localStorage.setItem('dataMapFilters', JSON.stringify(state.filters));
        localStorage.setItem('dataMapDepth', state.depth.toString());
    } catch (e) {
        console.warn('Error guardando filtros:', e);
    }
}

function loadFiltersFromStorage() {
    try {
        const savedFilters = localStorage.getItem('dataMapFilters');
        if (savedFilters) {
            state.filters = { ...state.filters, ...JSON.parse(savedFilters) };
        }
        const savedDepth = localStorage.getItem('dataMapDepth');
        if (savedDepth) {
            state.depth = parseInt(savedDepth);
        }
        
        // Aplicar filtros a los controles
        applyFiltersToUI();
    } catch (e) {
        console.warn('Error cargando filtros:', e);
    }
}

function applyFiltersToUI() {
    const filterType = document.getElementById('filter-type');
    const filterStatus = document.getElementById('filter-status');
    const filterMinConf = document.getElementById('filter-min-conf');
    const filterDirection = document.getElementById('filter-direction');
    const filterDepth = document.getElementById('filter-depth');
    const filterHideTemp = document.getElementById('filter-hide-temp');
    
    if (filterType) filterType.value = state.filters.type;
    if (filterStatus) filterStatus.value = state.filters.status;
    if (filterMinConf) filterMinConf.value = state.filters.min_conf;
    if (filterDirection) filterDirection.value = state.filters.direction;
    if (filterDepth) filterDepth.value = state.depth;
    if (filterHideTemp) filterHideTemp.checked = state.filters.hide_temp;
}

// ========== ACCIONES DE GOBERNANZA ==========

async function approveRelationship(relationshipId) {
    if (!relationshipId) {
        showToast('ID de relación no disponible', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${governanceApiUrl}${relationshipId}/approve/`, {
            method: 'PATCH',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            showToast('Relación aprobada exitosamente', 'success');
            reloadCurrentView();
            closeInspector();
        } else {
            const data = await response.json();
            throw new Error(data.detail || 'Error al aprobar relación');
        }
    } catch (error) {
        console.error('Error aprobando relación:', error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function deprecateRelationship(relationshipId) {
    if (!relationshipId) {
        showToast('ID de relación no disponible', 'error');
        return;
    }
    
    const reason = prompt('Ingrese el motivo de deprecación:');
    if (!reason) return;
    
    try {
        const response = await fetch(`${governanceApiUrl}${relationshipId}/deprecate/`, {
            method: 'PATCH',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                deprecated_reason: reason
            })
        });
        
        if (response.ok) {
            showToast('Relación deprecada exitosamente', 'success');
            reloadCurrentView();
            closeInspector();
        } else {
            const data = await response.json();
            throw new Error(data.detail || 'Error al deprecar relación');
        }
    } catch (error) {
        console.error('Error deprecando relación:', error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function editRelationship(relationshipId) {
    // TODO: Abrir wizard de edición (PR4)
    showToast('Funcionalidad de edición en desarrollo', 'info');
}

// Funciones wrapper para llamar desde el inspector de edges
function approveRelationshipFromEdge(relationshipId) {
    return approveRelationship(relationshipId);
}

function deprecateRelationshipFromEdge(relationshipId) {
    return deprecateRelationship(relationshipId);
}

function editRelationshipFromEdge(relationshipId) {
    return editRelationship(relationshipId);
}

// ========== UTILIDADES ==========

function updateStats(stats) {
    const statTables = document.getElementById('stat-tables');
    const statFk = document.getElementById('stat-fk');
    const statLearned = document.getElementById('stat-learned');
    const statTotal = document.getElementById('stat-total');
    
    if (statTables && stats.total_tables !== undefined) statTables.textContent = stats.total_tables;
    if (statFk && stats.fk_edges !== undefined) statFk.textContent = stats.fk_edges;
    if (statLearned && stats.learned_edges !== undefined) statLearned.textContent = stats.learned_edges;
    if (statTotal && stats.total_edges !== undefined) statTotal.textContent = stats.total_edges;
}

function showProgressModal() {
    const modal = document.getElementById('progress-modal');
    if (modal) {
        modal.classList.remove('hidden');
        updateProgress(0, 'Preparando...', 'Obteniendo información...');
    }
}

function hideProgressModal() {
    const modal = document.getElementById('progress-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function updateProgress(percent, status, detail) {
    const progressBar = document.getElementById('progress-bar');
    const progressStatus = document.getElementById('progress-status');
    const progressDetail = document.getElementById('progress-detail');
    
    if (progressBar) progressBar.style.width = `${Math.min(100, Math.max(0, percent))}%`;
    if (progressStatus) progressStatus.textContent = status || '';
    if (progressDetail) progressDetail.textContent = detail || '';
}

function showError(message) {
    showToast(message, 'error', 5000);
}

function showToast(message, type = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-emerald-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        type === 'warning' ? 'bg-amber-500 text-white' :
        'bg-sky-500 text-white'
    }`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ========== WIZARD PARA CREAR RELACIONES APRENDIDAS ==========

// Estado del wizard
const wizardState = {
    currentTab: 'manual',  // 'suggested' o 'manual'
    currentStep: 1,        // 1-4
    fromTable: '',
    fromColumn: '',
    toTable: '',
    toColumn: '',
    matchRule: {
        from_column_rule: {},
        to_column_rule: {}
    },
    validationResults: null,
    confidence: 0.7,
    status: 'proposed',
    notes: '',
    allTables: [],
    tableFieldsCache: {}
};

// Abrir wizard
function showCreateRelationshipWizard() {
    const modal = document.getElementById('create-relationship-modal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    wizardState.currentTab = 'manual';
    wizardState.currentStep = 1;
    wizardState.fromTable = '';
    wizardState.fromColumn = '';
    wizardState.toTable = '';
    wizardState.toColumn = '';
    wizardState.matchRule = { from_column_rule: {}, to_column_rule: {} };
    wizardState.validationResults = null;
    wizardState.confidence = 0.7;
    wizardState.status = 'proposed';
    wizardState.notes = '';
    
    // Cargar tablas si no están cargadas
    if (wizardState.allTables.length === 0) {
        loadWizardTables();
    } else {
        populateWizardTableSelects();
    }
    
    // Inicializar UI
    switchWizardTab('manual');
    updateWizardStep(1);
}

// Cerrar wizard
function closeCreateRelationshipWizard() {
    const modal = document.getElementById('create-relationship-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

// Cambiar tab (Sugeridas/Manual)
function switchWizardTab(tab) {
    wizardState.currentTab = tab;
    
    // Actualizar botones de tabs
    const tabSuggested = document.getElementById('wizard-tab-suggested');
    const tabManual = document.getElementById('wizard-tab-manual');
    const contentSuggested = document.getElementById('wizard-content-suggested');
    const contentManual = document.getElementById('wizard-content-manual');
    
    if (tab === 'suggested') {
        if (tabSuggested) {
            tabSuggested.classList.add('border-sky-600', 'text-sky-600', 'dark:text-sky-400');
            tabSuggested.classList.remove('border-transparent', 'text-slate-500', 'dark:text-slate-400');
        }
        if (tabManual) {
            tabManual.classList.remove('border-sky-600', 'text-sky-600', 'dark:text-sky-400');
            tabManual.classList.add('border-transparent', 'text-slate-500', 'dark:text-slate-400');
        }
        if (contentSuggested) contentSuggested.classList.remove('hidden');
        if (contentManual) contentManual.classList.add('hidden');
        
        loadSuggestedRelationships();
    } else {
        if (tabManual) {
            tabManual.classList.add('border-sky-600', 'text-sky-600', 'dark:text-sky-400');
            tabManual.classList.remove('border-transparent', 'text-slate-500', 'dark:text-slate-400');
        }
        if (tabSuggested) {
            tabSuggested.classList.remove('border-sky-600', 'text-sky-600', 'dark:text-sky-400');
            tabSuggested.classList.add('border-transparent', 'text-slate-500', 'dark:text-slate-400');
        }
        if (contentManual) contentManual.classList.remove('hidden');
        if (contentSuggested) contentSuggested.classList.add('hidden');
        
        updateWizardStep(1);
    }
}

// Actualizar paso del wizard
function updateWizardStep(step) {
    wizardState.currentStep = step;
    
    // Ocultar todos los pasos
    for (let i = 1; i <= 4; i++) {
        const stepContent = document.getElementById(`wizard-step-content-${i}`);
        if (stepContent) stepContent.classList.add('hidden');
    }
    
    // Mostrar paso actual
    const currentStepContent = document.getElementById(`wizard-step-content-${step}`);
    if (currentStepContent) currentStepContent.classList.remove('hidden');
    
    // Actualizar indicadores de progreso
    for (let i = 1; i <= 4; i++) {
        const stepIndicator = document.getElementById(`wizard-step-${i}`);
        const progressBar = document.getElementById(`wizard-progress-${i}`);
        
        if (i < step) {
            // Pasos completados
            if (stepIndicator) {
                stepIndicator.classList.remove('bg-slate-300', 'dark:bg-slate-600', 'text-slate-600', 'dark:text-slate-300');
                stepIndicator.classList.add('bg-emerald-600', 'text-white');
            }
            if (progressBar) {
                progressBar.classList.remove('bg-slate-300', 'dark:bg-slate-600');
                progressBar.classList.add('bg-emerald-600');
            }
        } else if (i === step) {
            // Paso actual
            if (stepIndicator) {
                stepIndicator.classList.remove('bg-slate-300', 'dark:bg-slate-600', 'text-slate-600', 'dark:text-slate-300', 'bg-emerald-600', 'text-white');
                stepIndicator.classList.add('bg-sky-600', 'text-white');
            }
        } else {
            // Pasos futuros
            if (stepIndicator) {
                stepIndicator.classList.remove('bg-sky-600', 'bg-emerald-600', 'text-white');
                stepIndicator.classList.add('bg-slate-300', 'dark:bg-slate-600', 'text-slate-600', 'dark:text-slate-300');
            }
            if (progressBar) {
                progressBar.classList.remove('bg-emerald-600');
                progressBar.classList.add('bg-slate-300', 'dark:bg-slate-600');
            }
        }
    }
    
    // Actualizar etiqueta del paso
    const stepLabels = {
        1: 'Selección',
        2: 'Reglas',
        3: 'Validación',
        4: 'Gobernanza'
    };
    const stepLabel = document.getElementById('wizard-step-label');
    if (stepLabel) stepLabel.textContent = stepLabels[step] || '';
    
    // Actualizar botones de navegación
    const btnPrev = document.getElementById('wizard-btn-prev');
    const btnNext = document.getElementById('wizard-btn-next');
    const btnSave = document.getElementById('wizard-btn-save');
    
    if (btnPrev) {
        if (step > 1) {
            btnPrev.classList.remove('hidden');
        } else {
            btnPrev.classList.add('hidden');
        }
    }
    
    if (btnNext) {
        if (step < 4) {
            btnNext.classList.remove('hidden');
        } else {
            btnNext.classList.add('hidden');
        }
    }
    
    if (btnSave) {
        if (step === 4) {
            btnSave.classList.remove('hidden');
        } else {
            btnSave.classList.add('hidden');
        }
    }
    
    // Sincronizar valores del estado con los campos del formulario cuando se muestra el paso 4
    if (step === 4) {
        const statusSelect = document.getElementById('wizard-status');
        const confidenceInput = document.getElementById('wizard-confidence');
        const notesInput = document.getElementById('wizard-notes');
        
        if (statusSelect) {
            statusSelect.value = wizardState.status || 'proposed';
        }
        
        if (confidenceInput) {
            confidenceInput.value = wizardState.confidence || 0.7;
        }
        
        if (notesInput) {
            notesInput.value = wizardState.notes || '';
        }
    }
}

// Navegar al siguiente paso
function wizardNextStep() {
    // Validar paso actual antes de avanzar
    if (wizardState.currentStep === 1) {
        const fromTable = document.getElementById('wizard-from-table')?.value;
        const fromColumn = document.getElementById('wizard-from-column')?.value;
        const toTable = document.getElementById('wizard-to-table')?.value;
        const toColumn = document.getElementById('wizard-to-column')?.value;
        
        if (!fromTable || !fromColumn || !toTable || !toColumn) {
            showToast('Por favor completa todos los campos de selección', 'error');
            return;
        }
        
        wizardState.fromTable = fromTable;
        wizardState.fromColumn = fromColumn;
        wizardState.toTable = toTable;
        wizardState.toColumn = toColumn;
    } else if (wizardState.currentStep === 3) {
        // En el paso de validación, ejecutar validación automáticamente si no se ha hecho
        if (!wizardState.validationResults) {
            wizardRunValidation();
            return; // No avanzar hasta que se complete la validación
        }
    }
    
    if (wizardState.currentStep < 4) {
        updateWizardStep(wizardState.currentStep + 1);
    }
}

// Navegar al paso anterior
function wizardPreviousStep() {
    if (wizardState.currentStep > 1) {
        updateWizardStep(wizardState.currentStep - 1);
    }
}

// Cargar tablas para el wizard
async function loadWizardTables() {
    try {
        const response = await fetch(`${dataMapApiUrl}?count_only=true`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            // Obtener todas las tablas desde el overview
            const overviewResponse = await fetch(`${dataMapApiUrl}?view=overview`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (overviewResponse.ok) {
                const overviewData = await overviewResponse.json();
                wizardState.allTables = [];
                if (overviewData.clusters) {
                    overviewData.clusters.forEach(cluster => {
                        if (cluster.table_names) {
                            wizardState.allTables.push(...cluster.table_names);
                        }
                    });
                }
                wizardState.allTables = [...new Set(wizardState.allTables)].sort();
                populateWizardTableSelects();
            }
        }
    } catch (error) {
        console.error('Error cargando tablas:', error);
        showToast('Error cargando lista de tablas', 'error');
    }
}

// Poblar selects de tablas
function populateWizardTableSelects() {
    const fromTableSelect = document.getElementById('wizard-from-table');
    const toTableSelect = document.getElementById('wizard-to-table');
    
    if (fromTableSelect) {
        fromTableSelect.innerHTML = '<option value="">Seleccionar tabla...</option>';
        wizardState.allTables.forEach(table => {
            const option = document.createElement('option');
            option.value = table;
            option.textContent = table;
            fromTableSelect.appendChild(option);
        });
    }
    
    if (toTableSelect) {
        toTableSelect.innerHTML = '<option value="">Seleccionar tabla...</option>';
        wizardState.allTables.forEach(table => {
            const option = document.createElement('option');
            option.value = table;
            option.textContent = table;
            toTableSelect.appendChild(option);
        });
    }
}

// Cargar campos de una tabla
async function wizardLoadTableFields(tableSelectId, columnSelectId) {
    const tableSelect = document.getElementById(`wizard-${tableSelectId}`);
    const columnSelect = document.getElementById(`wizard-${columnSelectId}`);
    const tableName = tableSelect?.value;
    
    if (!tableName) {
        if (columnSelect) {
            columnSelect.innerHTML = '<option value="">Primero selecciona una tabla</option>';
        }
        return;
    }
    
    // Verificar cache
    if (wizardState.tableFieldsCache[tableName]) {
        populateWizardColumnSelect(columnSelect, wizardState.tableFieldsCache[tableName]);
        return;
    }
    
    // Cargar desde API
    try {
        if (columnSelect) {
            columnSelect.innerHTML = '<option value="">Cargando campos...</option>';
            columnSelect.disabled = true;
        }
        
        // Construir URL de la API de campos
        const fieldsUrl = `/api/reports/builder/datasources/${tableName}/fields/`;
        const response = await fetch(fieldsUrl, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            const fields = data.fields || [];
            
            wizardState.tableFieldsCache[tableName] = fields;
            populateWizardColumnSelect(columnSelect, fields);
        } else {
            throw new Error(`Error ${response.status}`);
        }
    } catch (error) {
        console.error('Error cargando campos:', error);
        if (columnSelect) {
            columnSelect.innerHTML = '<option value="">Error al cargar campos</option>';
        }
        showToast('Error cargando campos de la tabla', 'error');
    } finally {
        if (columnSelect) {
            columnSelect.disabled = false;
        }
    }
}

// Poblar select de columnas
function populateWizardColumnSelect(select, fields) {
    if (!select) return;
    select.innerHTML = '<option value="">Seleccionar campo...</option>';
    fields.forEach(field => {
        const option = document.createElement('option');
        option.value = field.name;
        option.textContent = `${field.name} (${field.data_type || 'N/A'})`;
        select.appendChild(option);
    });
}

// Cargar relaciones sugeridas
async function loadSuggestedRelationships() {
    const suggestedList = document.getElementById('wizard-suggested-list');
    if (!suggestedList) return;
    
    suggestedList.innerHTML = '<p class="text-sm text-slate-500 dark:text-slate-500 italic">Cargando sugerencias...</p>';
    
    try {
        // Obtener relaciones aprendidas propuestas con alta confianza
        const learnedRelationshipsUrl = window.LEARNED_RELATIONSHIPS_API_URL || '/api/reports/builder/learned-relationships/';
        const response = await fetch(learnedRelationshipsUrl, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            const relationships = data.relationships || [];
            
            // Filtrar: solo propuestas con confianza >= 0.7
            const suggested = relationships.filter(rel => 
                rel.status === 'proposed' && rel.confidence >= 0.7
            );
            
            if (suggested.length === 0) {
                suggestedList.innerHTML = '<p class="text-sm text-slate-500 dark:text-slate-500 italic">No hay relaciones sugeridas disponibles.</p>';
                return;
            }
            
            suggestedList.innerHTML = suggested.map(rel => `
                <div class="p-3 border border-slate-200 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer"
                     onclick="wizardSelectSuggested(${rel.id})">
                    <div class="flex items-center justify-between">
                        <div>
                            <div class="font-medium text-slate-900 dark:text-white">
                                ${rel.from_table}.${rel.from_column} → ${rel.to_table}.${rel.to_column}
                            </div>
                            <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                Confianza: ${(rel.confidence * 100).toFixed(1)}%
                            </div>
                        </div>
                        <button class="px-3 py-1 bg-sky-600 text-white text-xs rounded hover:bg-sky-700">
                            Usar
                        </button>
                    </div>
                </div>
            `).join('');
        } else {
            suggestedList.innerHTML = '<p class="text-sm text-red-500">Error cargando sugerencias</p>';
        }
    } catch (error) {
        console.error('Error cargando relaciones sugeridas:', error);
        suggestedList.innerHTML = '<p class="text-sm text-red-500">Error cargando sugerencias</p>';
    }
}

// Seleccionar una relación sugerida
function wizardSelectSuggested(relationshipId) {
    // TODO: Cargar datos de la relación y pre-llenar el wizard
    showToast('Funcionalidad de selección de sugerida en desarrollo', 'info');
    // Por ahora, cambiar a tab manual
    switchWizardTab('manual');
}

// Ejecutar validación
async function wizardRunValidation() {
    const validationContent = document.getElementById('wizard-validation-content');
    const validationResults = document.getElementById('wizard-validation-results');
    
    if (!validationContent || !validationResults) return;
    
    // Recopilar reglas de matching
    const matchRule = {
        from_column_rule: {
            trim: document.getElementById('wizard-match-trim-from')?.checked || false,
            upper: document.getElementById('wizard-match-upper-from')?.checked || false,
            lower: document.getElementById('wizard-match-lower-from')?.checked || false,
            cast_as: document.getElementById('wizard-match-cast-from')?.value || null
        },
        to_column_rule: {
            trim: document.getElementById('wizard-match-trim-to')?.checked || false,
            upper: document.getElementById('wizard-match-upper-to')?.checked || false,
            lower: document.getElementById('wizard-match-lower-to')?.checked || false,
            cast_as: document.getElementById('wizard-match-cast-to')?.value || null
        }
    };
    
    wizardState.matchRule = matchRule;
    
    // Mostrar loading
    validationContent.innerHTML = '<p class="text-sm text-slate-600 dark:text-slate-400">Ejecutando validación...</p>';
    validationResults.classList.add('hidden');
    
    try {
        const response = await fetch(validateApiUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                from_table: wizardState.fromTable,
                from_column: wizardState.fromColumn,
                to_table: wizardState.toTable,
                to_column: wizardState.toColumn,
                match_rule: matchRule
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            wizardState.validationResults = data;
            
            // Actualizar confianza sugerida
            if (data.suggested_confidence !== undefined) {
                wizardState.confidence = data.suggested_confidence;
                const confidenceInput = document.getElementById('wizard-confidence');
                if (confidenceInput) {
                    confidenceInput.value = data.suggested_confidence;
                }
            }
            
            // Mostrar resultados
            displayValidationResults(data);
            validationResults.classList.remove('hidden');
            validationContent.innerHTML = '<button onclick="wizardRunValidation()" class="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors">Re-ejecutar Validación</button>';
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error en la validación');
        }
    } catch (error) {
        console.error('Error ejecutando validación:', error);
        validationContent.innerHTML = `
            <button onclick="wizardRunValidation()" class="px-4 py-2 bg-sky-600 text-white rounded-lg hover:bg-sky-700 transition-colors">Reintentar</button>
            <p class="text-sm text-red-500 mt-2">Error: ${error.message}</p>
        `;
    }
}

// Mostrar resultados de validación
function displayValidationResults(data) {
    const validationResults = document.getElementById('wizard-validation-results');
    if (!validationResults) return;
    
    const metrics = data.metrics || {};
    const samples = data.samples || {};
    const warnings = data.warnings || [];
    
    let html = `
        <div class="space-y-4">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <div class="text-xs text-slate-500 dark:text-slate-400">Match Rate</div>
                    <div class="text-lg font-semibold text-slate-900 dark:text-white">
                        ${((metrics.match_rate || 0) * 100).toFixed(1)}%
                    </div>
                </div>
                <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <div class="text-xs text-slate-500 dark:text-slate-400">Null Rate (Origen)</div>
                    <div class="text-lg font-semibold text-slate-900 dark:text-white">
                        ${((metrics.null_rate_from || 0) * 100).toFixed(1)}%
                    </div>
                </div>
                <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <div class="text-xs text-slate-500 dark:text-slate-400">Duplicados (Destino)</div>
                    <div class="text-lg font-semibold text-slate-900 dark:text-white">
                        ${metrics.duplicates_in_to || 0}
                    </div>
                </div>
                <div class="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                    <div class="text-xs text-slate-500 dark:text-slate-400">Cardinalidad</div>
                    <div class="text-lg font-semibold text-slate-900 dark:text-white">
                        ${metrics.cardinality_est || 'N-N'}
                    </div>
                </div>
            </div>
    `;
    
    if (warnings.length > 0) {
        html += `
            <div class="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg">
                <div class="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-2">⚠️ Advertencias:</div>
                <ul class="text-xs text-amber-700 dark:text-amber-300 space-y-1">
                    ${warnings.map(w => `<li>• ${w}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    if (samples.matches && samples.matches.length > 0) {
        html += `
            <div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white mb-2">Muestras de Matches:</div>
                <div class="text-xs text-slate-600 dark:text-slate-400 space-y-1">
                    ${samples.matches.slice(0, 5).map(m => 
                        `<div>${m.from} → ${m.to}</div>`
                    ).join('')}
                </div>
            </div>
        `;
    }
    
    html += `</div>`;
    validationResults.innerHTML = html;
}

// Guardar relación aprendida
async function wizardSaveRelationship() {
    const statusSelect = document.getElementById('wizard-status');
    const confidenceInput = document.getElementById('wizard-confidence');
    const notesInput = document.getElementById('wizard-notes');
    
    if (!statusSelect || !confidenceInput) return;
    
    wizardState.status = statusSelect.value;
    wizardState.confidence = parseFloat(confidenceInput.value) || 0.7;
    wizardState.notes = notesInput?.value || '';
    
    try {
        const response = await fetch(dataMapApiUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                from_table: wizardState.fromTable,
                from_column: wizardState.fromColumn,
                to_table: wizardState.toTable,
                to_column: wizardState.toColumn,
                confidence: wizardState.confidence,
                status: wizardState.status,
                match_rule_json: wizardState.matchRule,
                validation_metrics_json: wizardState.validationResults?.metrics || {}
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast('Relación aprendida creada exitosamente', 'success');
            closeCreateRelationshipWizard();
            refreshCurrentView();
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al guardar relación');
        }
    } catch (error) {
        console.error('Error guardando relación:', error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ========== GESTIÓN DE CLUSTERS ==========

let clusterEditState = {
    clusterId: null,
    clusterLabel: null,
    tables: [] // Array de {table_name, order}
};

async function editCluster(clusterId, clusterLabel) {
    clusterEditState.clusterId = clusterId;
    clusterEditState.clusterLabel = clusterLabel;
    clusterEditState.tables = [];
    
    // Cargar tablas del cluster desde la API
    try {
        // Construir URL correctamente
        let clustersUrl;
        if (dataMapApiUrl && dataMapApiUrl.includes('/builder/data-map/')) {
            clustersUrl = dataMapApiUrl.replace('/builder/data-map/', '/builder/data-map/clusters/');
        } else {
            clustersUrl = '/api/reports/builder/data-map/clusters/';
        }
        const response = await fetch(clustersUrl, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            const cluster = data.clusters.find(c => c.id === clusterId);
            if (cluster) {
                clusterEditState.tables = cluster.tables.map(t => ({
                    table_name: t.table_name,
                    order: t.order || 0
                })).sort((a, b) => a.order - b.order);
            }
        }
    } catch (error) {
        console.error('Error cargando cluster:', error);
    }
    
    // Cargar todas las tablas disponibles para el selector
    await loadAllTablesForSelector();
    
    // Mostrar modal
    showEditClusterModal();
}

function showEditClusterModal() {
    const modal = document.getElementById('edit-cluster-modal');
    if (!modal) return;
    
    // Llenar formulario
    document.getElementById('edit-cluster-id').value = clusterEditState.clusterId || '';
    document.getElementById('edit-cluster-label').value = clusterEditState.clusterLabel || '';
    
    // Renderizar lista de tablas
    renderClusterTablesList();
    
    // Actualizar selector para excluir tablas ya en el cluster
    updateTablesSelector();
    
    modal.classList.remove('hidden');
}

function closeEditClusterModal() {
    const modal = document.getElementById('edit-cluster-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    clusterEditState = {
        clusterId: null,
        clusterLabel: null,
        tables: []
    };
}

function renderClusterTablesList() {
    const container = document.getElementById('edit-cluster-tables-list');
    const countSpan = document.getElementById('edit-cluster-tables-count');
    
    if (!container) return;
    
    if (countSpan) {
        countSpan.textContent = clusterEditState.tables.length;
    }
    
    if (clusterEditState.tables.length === 0) {
        container.innerHTML = '<p class="text-sm text-slate-500 dark:text-slate-400 italic">No hay tablas en este cluster</p>';
        return;
    }
    
    let html = '<div class="space-y-2">';
    clusterEditState.tables.forEach((table, index) => {
        html += `
            <div class="flex items-center justify-between p-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg">
                <div class="flex items-center gap-2">
                    <span class="text-xs text-slate-500 dark:text-slate-400">${index + 1}.</span>
                    <span class="text-sm font-medium text-slate-900 dark:text-white">${table.table_name}</span>
                </div>
                <div class="flex items-center gap-1">
                    ${index > 0 ? `
                        <button onclick="moveTableInCluster(${index}, -1)" 
                                class="p-1 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300" title="Mover arriba">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"/>
                            </svg>
                        </button>
                    ` : ''}
                    ${index < clusterEditState.tables.length - 1 ? `
                        <button onclick="moveTableInCluster(${index}, 1)" 
                                class="p-1 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300" title="Mover abajo">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                            </svg>
                        </button>
                    ` : ''}
                    <button onclick="removeTableFromCluster(${index})" 
                            class="p-1 text-red-500 hover:text-red-700 dark:hover:text-red-400" title="Eliminar">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

function addSelectedTablesToCluster() {
    const select = document.getElementById('edit-cluster-add-tables');
    if (!select) return;
    
    const selectedOptions = Array.from(select.selectedOptions);
    if (selectedOptions.length === 0) {
        showToast('Por favor selecciona al menos una tabla', 'error');
        return;
    }
    
    let addedCount = 0;
    let skippedCount = 0;
    
    selectedOptions.forEach(option => {
        const tableName = option.value.trim();
        if (!tableName) return;
        
        // Verificar que no esté ya en el cluster
        if (clusterEditState.tables.some(t => t.table_name === tableName)) {
            skippedCount++;
            return;
        }
        
        // Agregar tabla
        clusterEditState.tables.push({
            table_name: tableName,
            order: clusterEditState.tables.length
        });
        addedCount++;
        
        // Desmarcar la opción
        option.selected = false;
    });
    
    if (addedCount > 0) {
        showToast(`${addedCount} tabla(s) agregada(s)${skippedCount > 0 ? `, ${skippedCount} ya estaban en el cluster` : ''}`, 'success');
    } else if (skippedCount > 0) {
        showToast('Las tablas seleccionadas ya están en el cluster', 'info');
    }
    
    // Re-renderizar lista y actualizar selector
    renderClusterTablesList();
    updateTablesSelector();
}

function removeTableFromCluster(index) {
    clusterEditState.tables.splice(index, 1);
    // Reordenar
    clusterEditState.tables.forEach((table, idx) => {
        table.order = idx;
    });
    renderClusterTablesList();
    // Actualizar selector para que la tabla eliminada vuelva a aparecer
    updateTablesSelector();
}

function moveTableInCluster(index, direction) {
    if (index + direction < 0 || index + direction >= clusterEditState.tables.length) {
        return;
    }
    
    const temp = clusterEditState.tables[index];
    clusterEditState.tables[index] = clusterEditState.tables[index + direction];
    clusterEditState.tables[index + direction] = temp;
    
    // Actualizar orden
    clusterEditState.tables.forEach((table, idx) => {
        table.order = idx;
    });
    
    renderClusterTablesList();
}

let allAvailableTables = []; // Cache de todas las tablas disponibles

async function loadAllTablesForSearch() {
    try {
        // Obtener todas las tablas desde la API de datasources
        let datasourcesUrl;
        if (dataMapApiUrl && dataMapApiUrl.includes('/builder/data-map/')) {
            datasourcesUrl = dataMapApiUrl.replace('/builder/data-map/', '/builder/datasources/');
        } else {
            datasourcesUrl = '/api/reports/builder/datasources/';
        }
        
        const dsResponse = await fetch(datasourcesUrl, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (dsResponse.ok) {
            const dsData = await dsResponse.json();
            // La API devuelve { datasources: [...], total: ..., base_empresa: ... }
            if (dsData && Array.isArray(dsData.datasources)) {
                allAvailableTables = dsData.datasources.map(ds => ds.name || ds).sort();
            } else if (Array.isArray(dsData)) {
                // Fallback: si es un array directo
                allAvailableTables = dsData.map(ds => ds.name || ds).sort();
            } else {
                console.warn('Formato inesperado de respuesta de datasources:', dsData);
                allAvailableTables = [];
            }
        }
    } catch (error) {
        console.error('Error cargando tablas para búsqueda:', error);
    }
}

async function loadAllTablesForSelector() {
    try {
        // Obtener todas las tablas desde la API de datasources
        // dataMapApiUrl es algo como /api/reports/builder/data-map/
        // Necesitamos /api/reports/builder/datasources/
        // Construir la URL correctamente
        let datasourcesUrl;
        if (dataMapApiUrl && dataMapApiUrl.includes('/builder/data-map/')) {
            datasourcesUrl = dataMapApiUrl.replace('/builder/data-map/', '/builder/datasources/');
        } else {
            // Fallback: construir desde cero
            datasourcesUrl = '/api/reports/builder/datasources/';
        }
        const dsResponse = await fetch(datasourcesUrl, {
            method: 'GET',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin'
        });
        
        if (dsResponse.ok) {
            const dsData = await dsResponse.json();
            // La API devuelve { datasources: [...], total: ..., base_empresa: ... }
            if (dsData && Array.isArray(dsData.datasources)) {
                allAvailableTables = dsData.datasources.map(ds => ds.name || ds).sort();
            } else if (Array.isArray(dsData)) {
                // Fallback: si es un array directo
                allAvailableTables = dsData.map(ds => ds.name || ds).sort();
            } else {
                console.warn('Formato inesperado de respuesta de datasources:', dsData);
                allAvailableTables = [];
            }
            
            // Actualizar selector
            updateTablesSelector();
        }
    } catch (error) {
        console.error('Error cargando tablas para selector:', error);
        showToast('Error cargando tablas disponibles', 'error');
    }
}

function updateTablesSelector() {
    const select = document.getElementById('edit-cluster-add-tables');
    if (!select) return;
    
    // Obtener tablas ya en el cluster
    const clusterTableNames = new Set(clusterEditState.tables.map(t => t.table_name));
    
    // Limpiar selector
    select.innerHTML = '';
    
    // Agregar opciones solo para tablas que NO están en el cluster
    allAvailableTables.forEach(tableName => {
        if (!clusterTableNames.has(tableName)) {
            const option = document.createElement('option');
            option.value = tableName;
            option.textContent = tableName;
            select.appendChild(option);
        }
    });
    
    if (select.options.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Todas las tablas ya están en este cluster';
        option.disabled = true;
        select.appendChild(option);
    }
}

async function saveClusterChanges() {
    const clusterId = document.getElementById('edit-cluster-id').value.trim();
    const clusterLabel = document.getElementById('edit-cluster-label').value.trim();
    
    if (!clusterId || !clusterLabel) {
        showToast('ID y Etiqueta del cluster son requeridos', 'error');
        return;
    }
    
    if (clusterEditState.tables.length === 0) {
        showToast('El cluster debe tener al menos una tabla', 'error');
        return;
    }
    
    try {
        // Primero, eliminar las tablas de sus clusters anteriores si estaban en otro cluster
        // Esto se hace automáticamente en el backend porque el POST elimina las asignaciones
        // existentes para esas tablas antes de crear las nuevas
        
        // Construir URL correctamente
        let clustersUrl;
        if (dataMapApiUrl && dataMapApiUrl.includes('/builder/data-map/')) {
            clustersUrl = dataMapApiUrl.replace('/builder/data-map/', '/builder/data-map/clusters/');
        } else {
            clustersUrl = '/api/reports/builder/data-map/clusters/';
        }
        const response = await fetch(clustersUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                cluster_id: clusterId,
                cluster_label: clusterLabel,
                tables: clusterEditState.tables
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            showToast(data.detail || 'Cluster guardado exitosamente', 'success');
            closeEditClusterModal();
            // Recargar overview
            refreshCurrentView();
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Error al guardar cluster');
        }
    } catch (error) {
        console.error('Error guardando cluster:', error);
        showToast(`Error: ${error.message}`, 'error');
    }
}

// Exportar funciones globales necesarias
window.navigateToView = navigateToView;
window.closeInspector = closeInspector;
window.approveRelationship = approveRelationship;
window.deprecateRelationship = deprecateRelationship;
window.editRelationship = editRelationship;
window.approveRelationshipFromEdge = approveRelationshipFromEdge;
window.deprecateRelationshipFromEdge = deprecateRelationshipFromEdge;
window.editRelationshipFromEdge = editRelationshipFromEdge;
window.refreshCurrentView = refreshCurrentView;
window.showCreateRelationshipWizard = showCreateRelationshipWizard;
window.closeCreateRelationshipWizard = closeCreateRelationshipWizard;
window.switchWizardTab = switchWizardTab;
window.editCluster = editCluster;
window.closeEditClusterModal = closeEditClusterModal;
window.addSelectedTablesToCluster = addSelectedTablesToCluster;
window.removeTableFromCluster = removeTableFromCluster;
window.moveTableInCluster = moveTableInCluster;
window.saveClusterChanges = saveClusterChanges;
window.selectSearchSuggestion = selectSearchSuggestion;
window.wizardNextStep = wizardNextStep;
window.wizardPreviousStep = wizardPreviousStep;
window.wizardLoadTableFields = wizardLoadTableFields;
window.wizardSelectSuggested = wizardSelectSuggested;
window.wizardRunValidation = wizardRunValidation;
window.wizardSaveRelationship = wizardSaveRelationship;

