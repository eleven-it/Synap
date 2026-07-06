/**
 * Inicialización Chart.js para reportes MPR.
 * Payload: #mpr-charts-payload (JSON desde reportes_charts.build_charts_produccion).
 */
(function (global) {
    'use strict';

    var instances = {};

    function isDark() {
        return document.documentElement.classList.contains('dark');
    }

    function theme() {
        var dark = isDark();
        return {
            grid: dark ? 'rgba(148, 163, 184, 0.15)' : 'rgba(148, 163, 184, 0.35)',
            tick: dark ? '#94a3b8' : '#64748b',
        };
    }

    function fmtN(v) {
        return v != null ? Number(v).toLocaleString('es-AR') : '0';
    }

    function destroyAll() {
        Object.keys(instances).forEach(function (id) {
            if (instances[id]) {
                instances[id].destroy();
                delete instances[id];
            }
        });
    }

    function baseOptions(yLabel) {
        var t = theme();
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            return (ctx.dataset.label ? ctx.dataset.label + ': ' : '') + fmtN(ctx.parsed.y != null ? ctx.parsed.y : ctx.parsed.x);
                        },
                    },
                },
            },
            scales: {
                x: {
                    grid: { color: t.grid },
                    ticks: { color: t.tick, font: { size: 11 } },
                },
                y: {
                    beginAtZero: true,
                    grid: { color: t.grid },
                    ticks: { color: t.tick, font: { size: 11 } },
                    title: yLabel ? { display: true, text: yLabel, color: t.tick, font: { size: 11 } } : undefined,
                },
            },
        };
    }

    function renderLineMulti(canvas, block, yLabel) {
        var rows = block.rows || [];
        var t = theme();
        return new global.Chart(canvas, {
            type: 'line',
            data: {
                labels: rows.map(function (r) { return r.label; }),
                datasets: [
                    { label: 'Enviado', data: rows.map(function (r) { return r.enviado; }), borderColor: '#64748b', backgroundColor: 'rgba(100,116,139,0.08)', borderWidth: 2, pointRadius: 3, tension: 0.25, yAxisID: 'y' },
                    { label: 'Parte', data: rows.map(function (r) { return r.parte; }), borderColor: '#059669', backgroundColor: 'rgba(5,150,105,0.08)', borderWidth: 2, pointRadius: 3, tension: 0.25, yAxisID: 'y' },
                    { label: 'Clasificado', data: rows.map(function (r) { return r.clasificado; }), borderColor: '#7c3aed', backgroundColor: 'rgba(124,58,237,0.08)', borderWidth: 2, pointRadius: 3, tension: 0.25, yAxisID: 'y' },
                    { label: 'Scrap', data: rows.map(function (r) { return r.scrap; }), borderColor: '#dc2626', borderDash: [5, 4], borderWidth: 2, pointRadius: 2, tension: 0.25, yAxisID: 'y1' },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: true, position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: { callbacks: { label: function (ctx) { return ctx.dataset.label + ': ' + fmtN(ctx.parsed.y); } } },
                },
                scales: {
                    x: { grid: { color: t.grid }, ticks: { color: t.tick, maxRotation: 45, font: { size: 11 } } },
                    y: { beginAtZero: true, position: 'left', grid: { color: t.grid }, ticks: { color: t.tick }, title: { display: true, text: yLabel || 'unidades', color: t.tick, font: { size: 11 } } },
                    y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { color: '#dc2626' }, title: { display: true, text: 'Scrap', color: '#dc2626', font: { size: 11 } } },
                },
            },
        });
    }

    function renderHbar(canvas, block, yLabel) {
        var opts = baseOptions(yLabel);
        opts.indexAxis = 'y';
        opts.scales.x.title = { display: true, text: yLabel || 'unidades', color: theme().tick, font: { size: 11 } };
        delete opts.scales.y.title;
        return new global.Chart(canvas, {
            type: 'bar',
            data: {
                labels: block.labels || [],
                datasets: [{
                    label: 'Unidades',
                    data: block.values || [],
                    backgroundColor: block.color || '#7c3aed',
                    borderRadius: 4,
                }],
            },
            options: opts,
        });
    }

    function renderHbarColored(canvas, block, yLabel) {
        var opts = baseOptions(yLabel);
        opts.indexAxis = 'y';
        opts.plugins.legend = { display: true, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } };
        opts.scales.x.title = { display: true, text: yLabel || 'unidades', color: theme().tick, font: { size: 11 } };
        delete opts.scales.y.title;
        return new global.Chart(canvas, {
            type: 'bar',
            data: {
                labels: block.labels || [],
                datasets: [{
                    label: 'Pendiente',
                    data: block.values || [],
                    backgroundColor: block.colors || '#d97706',
                    borderRadius: 4,
                }],
            },
            options: opts,
        });
    }

    function renderHbarGrouped(canvas, block, yLabel) {
        var opts = baseOptions(yLabel);
        opts.indexAxis = 'y';
        opts.plugins.legend = { display: true, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } };
        opts.scales.x.title = { display: true, text: yLabel || 'unidades', color: theme().tick, font: { size: 11 } };
        delete opts.scales.y.title;
        var datasets = (block.datasets || []).map(function (ds) {
            return {
                label: ds.label,
                data: ds.values,
                backgroundColor: ds.color,
                borderRadius: 3,
            };
        });
        return new global.Chart(canvas, {
            type: 'bar',
            data: { labels: block.labels || [], datasets: datasets },
            options: opts,
        });
    }

    function renderHbarStacked(canvas, block, yLabel) {
        var opts = baseOptions(yLabel);
        opts.indexAxis = 'y';
        opts.plugins.legend = { display: true, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } };
        opts.scales.x.stacked = true;
        opts.scales.y.stacked = true;
        opts.scales.x.title = { display: true, text: yLabel || 'unidades', color: theme().tick, font: { size: 11 } };
        delete opts.scales.y.title;
        var datasets = (block.datasets || []).map(function (ds) {
            return {
                label: ds.label,
                data: ds.values,
                backgroundColor: ds.color,
                borderRadius: 2,
            };
        });
        return new global.Chart(canvas, {
            type: 'bar',
            data: { labels: block.labels || [], datasets: datasets },
            options: opts,
        });
    }

    function renderGroupedBar(canvas, block, yLabel) {
        var ds0 = (block.datasets || [])[0];
        var colors = (ds0 && ds0.colors) || ['#64748b', '#059669', '#7c3aed'];
        return new global.Chart(canvas, {
            type: 'bar',
            data: {
                labels: block.labels || [],
                datasets: [{
                    label: (ds0 && ds0.label) || 'Unidades',
                    data: (ds0 && ds0.values) || [],
                    backgroundColor: colors,
                    borderRadius: 6,
                }],
            },
            options: baseOptions(yLabel),
        });
    }

    function renderDoughnut(canvas, block) {
        return new global.Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: block.labels || [],
                datasets: [{
                    data: block.values || [],
                    backgroundColor: block.colors || ['#94a3b8', '#d97706', '#7c3aed', '#059669'],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                var pct = total ? Math.round(ctx.parsed / total * 1000) / 10 : 0;
                                return ctx.label + ': ' + ctx.parsed + ' (' + pct + '%)';
                            },
                        },
                    },
                },
            },
        });
    }

    function renderBlock(block, yLabel) {
        var canvas = document.getElementById('mpr-chart-' + block.id);
        if (!canvas || typeof global.Chart === 'undefined') return;
        var chart;
        switch (block.kind) {
            case 'line_multi':
                chart = renderLineMulti(canvas, block, yLabel);
                break;
            case 'hbar':
                chart = renderHbar(canvas, block, yLabel);
                break;
            case 'hbar_colored':
                chart = renderHbarColored(canvas, block, yLabel);
                break;
            case 'hbar_grouped':
                chart = renderHbarGrouped(canvas, block, yLabel);
                break;
            case 'hbar_stacked':
                chart = renderHbarStacked(canvas, block, yLabel);
                break;
            case 'grouped_bar':
                chart = renderGroupedBar(canvas, block, yLabel);
                break;
            case 'doughnut':
                chart = renderDoughnut(canvas, block);
                break;
            default:
                return;
        }
        instances[block.id] = chart;
    }

    function initMprReportesCharts() {
        var el = document.getElementById('mpr-charts-payload');
        if (!el || typeof global.Chart === 'undefined') return;
        var root = document.getElementById('mpr-charts-root');
        var yLabel = (root && root.getAttribute('data-y-label')) || 'unidades';
        var payload;
        try {
            payload = JSON.parse(el.textContent);
        } catch (e) {
            return;
        }
        if (!payload || !payload.blocks || !payload.blocks.length) return;
        destroyAll();
        payload.blocks.forEach(function (block) {
            renderBlock(block, yLabel);
        });
    }

    global.initMprReportesCharts = initMprReportesCharts;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initMprReportesCharts);
    } else {
        initMprReportesCharts();
    }
})(window);
