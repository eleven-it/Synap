/**
 * Dashboard SIA con visualizaciones D3.js
 * 
 * Este archivo consume el endpoint /api/sia/dashboard-data/ y renderiza gráficos
 * usando D3.js (reutilizando el vendor de reports).
 * 
 * Estructura:
 * - fetchData(): Obtiene datos del endpoint JSON
 * - renderRatingsChart(): Renderiza gráfico de barras para ratings
 * - renderFodaChart(): Renderiza gráfico de barras para FODA consolidado
 */

// Configuración de colores coherente con el diseño
const SIA_COLORS = {
    strength: '#10b981',      // Verde
    weakness: '#ef4444',      // Rojo
    opportunity: '#3b82f6',   // Azul
    threat: '#f97316',        // Naranja
    default: '#6b7280'        // Gris
};

// Mapeo de dimensiones a nombres legibles
const DIMENSION_LABELS = {
    'area_health': 'Area Health',
    'team_performance': 'Team Performance',
    'strategy_alignment': 'Strategy Alignment',
    'process_maturity': 'Process Maturity',
    'tech_maturity': 'Technology Maturity'
};

// Mapeo de cuadrantes a nombres legibles
const QUADRANT_LABELS = {
    'strength': 'Strengths',
    'weakness': 'Weaknesses',
    'opportunity': 'Opportunities',
    'threat': 'Threats'
};

/**
 * Obtiene el token CSRF desde las cookies
 */
function getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie ? document.cookie.split(';') : [];
    for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.startsWith(`${name}=`)) {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return '';
}

/**
 * Obtiene los parámetros de la URL (empresa_id, cycle_id)
 */
function getUrlParams() {
    const params = new URLSearchParams(window.location.search);
    return {
        empresa_id: params.get('empresa_id') || null,
        cycle_id: params.get('cycle') || params.get('cycle_id') || null
    };
}

/**
 * Obtiene datos del endpoint API del dashboard
 * 
 * @param {string} empresa_id - ID de la empresa (opcional)
 * @param {string} cycle_id - ID del ciclo de evaluación (opcional)
 * @returns {Promise<Object>} Datos consolidados del dashboard
 */
async function fetchDashboardData(empresa_id = null, cycle_id = null) {
    const url = new URL('/api/sia/dashboard-data/', window.location.origin);
    if (empresa_id) {
        url.searchParams.append('empresa_id', empresa_id);
    }
    if (cycle_id) {
        url.searchParams.append('cycle_id', cycle_id);
    }

    try {
        const response = await fetch(url.toString(), {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            credentials: 'same-origin'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        throw error;
    }
}

/**
 * Renderiza gráfico de barras para ratings consolidados
 * 
 * @param {string} containerId - ID del contenedor donde se renderizará el gráfico
 * @param {Array} ratingsData - Array de objetos con {dimension, average, min_value, max_value, count}
 */
function renderRatingsChart(containerId, ratingsData) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn(`Container ${containerId} not found`);
        return;
    }

    // Limpiar contenedor
    container.innerHTML = '';

    if (!ratingsData || ratingsData.length === 0) {
        container.innerHTML = '<p class="text-xs text-gray-500 dark:text-gray-400 text-center py-4">No ratings data available</p>';
        return;
    }

    // Obtener dimensiones del contenedor
    const containerRect = container.getBoundingClientRect();
    const width = containerRect.width || 800;
    const height = 400;
    const margin = { top: 20, right: 30, bottom: 60, left: 80 };

    // Crear SVG
    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'w-full h-auto');

    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Escalas
    const xScale = d3.scaleBand()
        .domain(ratingsData.map(d => d.dimension))
        .range([0, chartWidth])
        .padding(0.2);

    const yScale = d3.scaleLinear()
        .domain([0, 10])  // Ratings van de 1 a 10
        .nice()
        .range([chartHeight, 0]);

    // Ejes
    const xAxis = d3.axisBottom(xScale)
        .tickFormat(d => DIMENSION_LABELS[d] || d);

    const yAxis = d3.axisLeft(yScale)
        .ticks(10)
        .tickFormat(d => d);

    g.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${chartHeight})`)
        .call(xAxis)
        .selectAll('text')
        .style('text-anchor', 'end')
        .attr('dx', '-.8em')
        .attr('dy', '.15em')
        .attr('transform', 'rotate(-45)')
        .style('font-size', '11px')
        .style('fill', 'currentColor');

    g.append('g')
        .attr('class', 'y-axis')
        .call(yAxis)
        .style('font-size', '11px')
        .style('fill', 'currentColor');

    // Barras
    g.selectAll('.bar')
        .data(ratingsData)
        .enter()
        .append('rect')
        .attr('class', 'bar')
        .attr('x', d => xScale(d.dimension))
        .attr('y', d => yScale(d.average))
        .attr('width', xScale.bandwidth())
        .attr('height', d => chartHeight - yScale(d.average))
        .attr('fill', 'url(#ratingsGradient)')
        .attr('rx', 4)
        .on('mouseover', function(event, d) {
            // Tooltip
            const tooltip = d3.select('body').append('div')
                .attr('class', 'absolute bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs px-2 py-1 rounded shadow-lg pointer-events-none')
                .style('opacity', 0);

            tooltip.transition()
                .duration(200)
                .style('opacity', 0.9);

            tooltip.html(`
                <strong>${DIMENSION_LABELS[d.dimension] || d.dimension}</strong><br/>
                Average: ${d.average.toFixed(1)}/10<br/>
                Min: ${d.min_value} | Max: ${d.max_value}<br/>
                Count: ${d.count}
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.tooltip').remove();
        });

    // Etiquetas de valor en las barras
    g.selectAll('.bar-label')
        .data(ratingsData)
        .enter()
        .append('text')
        .attr('class', 'bar-label')
        .attr('x', d => xScale(d.dimension) + xScale.bandwidth() / 2)
        .attr('y', d => yScale(d.average) - 5)
        .attr('text-anchor', 'middle')
        .style('font-size', '11px')
        .style('fill', 'currentColor')
        .text(d => d.average.toFixed(1));

    // Gradiente para las barras
    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
        .attr('id', 'ratingsGradient')
        .attr('x1', '0%')
        .attr('y1', '0%')
        .attr('x2', '0%')
        .attr('y2', '100%');

    gradient.append('stop')
        .attr('offset', '0%')
        .attr('stop-color', '#f97316')
        .attr('stop-opacity', 1);

    gradient.append('stop')
        .attr('offset', '100%')
        .attr('stop-color', '#ea580c')
        .attr('stop-opacity', 1);
}

/**
 * Renderiza gráfico de barras para FODA consolidado
 * 
 * @param {string} containerId - ID del contenedor donde se renderizará el gráfico
 * @param {Object} fodaData - Objeto con {strength: [], weakness: [], opportunity: [], threat: []}
 */
function renderFodaChart(containerId, fodaData) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn(`Container ${containerId} not found`);
        return;
    }

    // Limpiar contenedor
    container.innerHTML = '';

    // Preparar datos: agrupar por cuadrante y sumar counts
    const quadrantData = [];
    for (const [quadrant, items] of Object.entries(fodaData)) {
        const totalCount = items.reduce((sum, item) => sum + item.count, 0);
        if (totalCount > 0) {
            quadrantData.push({
                quadrant: quadrant,
                count: totalCount,
                items: items.length
            });
        }
    }

    if (quadrantData.length === 0) {
        container.innerHTML = '<p class="text-xs text-gray-500 dark:text-gray-400 text-center py-4">No FODA data available</p>';
        return;
    }

    // Obtener dimensiones del contenedor
    const containerRect = container.getBoundingClientRect();
    const width = containerRect.width || 800;
    const height = 300;
    const margin = { top: 20, right: 30, bottom: 40, left: 80 };

    // Crear SVG
    const svg = d3.select(`#${containerId}`)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('class', 'w-full h-auto');

    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    const chartWidth = width - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    // Escalas
    const xScale = d3.scaleBand()
        .domain(quadrantData.map(d => d.quadrant))
        .range([0, chartWidth])
        .padding(0.2);

    const maxCount = d3.max(quadrantData, d => d.count);
    const yScale = d3.scaleLinear()
        .domain([0, maxCount])
        .nice()
        .range([chartHeight, 0]);

    // Ejes
    const xAxis = d3.axisBottom(xScale)
        .tickFormat(d => QUADRANT_LABELS[d] || d);

    const yAxis = d3.axisLeft(yScale)
        .ticks(Math.min(10, maxCount));

    g.append('g')
        .attr('class', 'x-axis')
        .attr('transform', `translate(0,${chartHeight})`)
        .call(xAxis)
        .style('font-size', '11px')
        .style('fill', 'currentColor');

    g.append('g')
        .attr('class', 'y-axis')
        .call(yAxis)
        .style('font-size', '11px')
        .style('fill', 'currentColor');

    // Barras con colores por cuadrante
    g.selectAll('.bar')
        .data(quadrantData)
        .enter()
        .append('rect')
        .attr('class', 'bar')
        .attr('x', d => xScale(d.quadrant))
        .attr('y', d => yScale(d.count))
        .attr('width', xScale.bandwidth())
        .attr('height', d => chartHeight - yScale(d.count))
        .attr('fill', d => SIA_COLORS[d.quadrant] || SIA_COLORS.default)
        .attr('rx', 4)
        .on('mouseover', function(event, d) {
            // Tooltip
            const tooltip = d3.select('body').append('div')
                .attr('class', 'absolute bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs px-2 py-1 rounded shadow-lg pointer-events-none')
                .style('opacity', 0);

            tooltip.transition()
                .duration(200)
                .style('opacity', 0.9);

            tooltip.html(`
                <strong>${QUADRANT_LABELS[d.quadrant] || d.quadrant}</strong><br/>
                Total Items: ${d.count}<br/>
                Unique Items: ${d.items}
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', function() {
            d3.selectAll('.tooltip').remove();
        });

    // Etiquetas de valor en las barras
    g.selectAll('.bar-label')
        .data(quadrantData)
        .enter()
        .append('text')
        .attr('class', 'bar-label')
        .attr('x', d => xScale(d.quadrant) + xScale.bandwidth() / 2)
        .attr('y', d => yScale(d.count) - 5)
        .attr('text-anchor', 'middle')
        .style('font-size', '11px')
        .style('fill', 'currentColor')
        .text(d => d.count);
}

/**
 * Inicializa el dashboard cuando el DOM está listo
 */
function initSIADashboard() {
    // Verificar que D3 esté disponible
    if (typeof d3 === 'undefined') {
        console.error('D3.js is not loaded. Please include d3.min.js before this script.');
        return;
    }

    // Obtener parámetros de la URL
    const params = getUrlParams();

    // Obtener datos y renderizar gráficos
    fetchDashboardData(params.empresa_id, params.cycle_id)
        .then(data => {
            console.log('Dashboard data loaded:', data);

            // Renderizar gráfico de ratings
            renderRatingsChart('sia-ratings-chart', data.ratings || []);

            // Renderizar gráfico de FODA
            renderFodaChart('sia-foda-chart', data.foda || {});

            // Actualizar información del ciclo si está disponible
            if (data.cycle_info) {
                const cycleInfoElement = document.getElementById('sia-cycle-info');
                if (cycleInfoElement) {
                    cycleInfoElement.textContent = `Cycle: ${data.cycle_info.name} (${data.total_responses} responses)`;
                }
            }
        })
        .catch(error => {
            console.error('Error initializing SIA dashboard:', error);
            // Mostrar mensaje de error en los contenedores
            const ratingsContainer = document.getElementById('sia-ratings-chart');
            const fodaContainer = document.getElementById('sia-foda-chart');
            
            if (ratingsContainer) {
                ratingsContainer.innerHTML = '<p class="text-xs text-red-500 text-center py-4">Error loading ratings data</p>';
            }
            if (fodaContainer) {
                fodaContainer.innerHTML = '<p class="text-xs text-red-500 text-center py-4">Error loading FODA data</p>';
            }
        });
}

// Inicializar cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSIADashboard);
} else {
    initSIADashboard();
}













