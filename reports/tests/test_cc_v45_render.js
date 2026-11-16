/** Regression checks for the V45 browser rendering without a server or DOM library. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const scriptPath = path.join(__dirname, "..", "static", "reports", "js", "command_center.js");
const source = fs.readFileSync(scriptPath, "utf8");
const marker = '  document.addEventListener("DOMContentLoaded", async () => {';
assert.equal(source.split(marker).length, 2, "The browser bootstrap marker changed");
const instrumented = source.replace(marker,
  '  globalThis.ccTest = { resumenTrend, renderResumenV45Kpis, renderResumenV45Charts, renderV45GroupedChart, renderResumenRanking, areaCard, AREA_DEFS };\n' + marker);
const sandbox = {
  window: { CC_CONFIG: {} },
  document: { addEventListener() {} },
  localStorage: { getItem() { return null; }, setItem() {} },
  Intl,
  console,
};
vm.runInNewContext(instrumented, sandbox, { filename: scriptPath });
const { resumenTrend, renderResumenV45Kpis, renderResumenV45Charts, renderV45GroupedChart, renderResumenRanking, areaCard, AREA_DEFS } = sandbox.ccTest;

assert.equal(resumenTrend("ventas", 70, 100).label, "Baja media");
assert.equal(resumenTrend("ventas", 95, 100).label, "Baja mínima");
assert.equal(resumenTrend("ventas", 100, 100).direction, "flat");
assert.equal(resumenTrend("ventas", 100, 0).direction, "none");
assert.equal(resumenTrend("efectivo_actual", -1, 0).label, "Controlar");
assert.equal(resumenTrend("pedidos", 90, 100), null);

const payload = {
  kpis: { ventas: 70_000_000, compras_netas: 20_000_000, cobranzas: 5_000_000, pagos: 3_000_000,
    pedidos: 4, presupuestos: 2, vencimiento_cobrar: 10, vencimiento_cobrar_cantidad: 1 },
  comparacion: { kpis: { ventas: 100_000_000 } },
  series: { agrupacion: "día", filas: [
    { fecha: "2026-10-01", ventas: 1_000_000, compras: 2_000_000, cobranzas: 500_000, pagos: 400_000 },
    { fecha: "2026-10-02", ventas: -200_000, compras: 0, cobranzas: 300_000, pagos: 500_000 },
  ] },
};
const kpis = renderResumenV45Kpis(payload);
assert.equal((kpis.match(/class="cc-summary-kpi"/g) || []).length, 16);
assert.match(kpis, /Baja media/);
assert.match(kpis, /1 vencimientos dentro del intervalo/);
assert.match(kpis, /data-kpi="ventas"/);
const charts = renderResumenV45Charts(payload);
assert.match(charts, /Gestión comercial · Ventas vs Compras/);
assert.match(charts, /Tesorería · Cobranzas vs Pagos/);
assert.match(charts, /fill="#2563eb"/);
assert.match(charts, /fill="#7c3aed"/);
assert.match(charts, /200,0 %/);
assert.match(charts, />01\/10<\/text>/);
assert.match(charts, /Ver serie completa/);
assert.match(charts, /Comparar con/);
const card = areaCard(AREA_DEFS.find((def) => def.key === "resumen_general"), payload, 0);
assert.match(card, /cc-summary-legend/);
assert.equal((card.match(/class="cc-summary-kpi"/g) || []).length, 16);
const generic = areaCard(AREA_DEFS.find((def) => def.key === "ventas"), { kpis: {} }, 0);
assert.equal((generic.match(/class="cc-summary-kpi"/g) || []).length, 16);
const purchases = areaCard(AREA_DEFS.find((def) => def.key === "compras"),
  { kpis: { compras_netas: 70 }, comparacion: { kpis: { compras_netas: 100 } } }, 0);
assert.match(purchases, /Baja media/, "purchases should follow the VB6 arrow rule");
assert.match(purchases, /data-url-key="compras_v45" data-vista="comprobantes"/, "purchase KPI should open its related data");
for (const key of ["preparacion_pedidos", "inventario", "compras", "financiero", "gestion_contable", "impositivo", "libros_contables", "logistica", "gastos"]) {
  const html = areaCard(AREA_DEFS.find((def) => def.key === key), { kpis: {} }, 0);
  assert.match(html, /cc-summary-kpis/, `${key} should show the compact KPI grid`);
  assert.match(html, /cc-v45-chart-svg/, `${key} should render its chart panel`);
}
const finance = areaCard(AREA_DEFS.find((def) => def.key === "financiero"),
  { kpis: { efectivo: 30, tarjetas: 20, bancos: 80,
    cheques_cartera: 120, cheques_emitidos: 50, cheques_rechazados: 10 } }, 0);
assert.match(finance, /Situación de cheques/);
assert.match(finance, /data-vista="cheques_cartera"/);
assert.match(finance, /data-vista="cheques_emitidos"/);
assert.match(finance, /data-vista="cheques_rechazados"/);
assert.match(finance, /data-vista="efectivo"/);
assert.match(finance, /data-vista="tarjetas"/);
assert.match(finance, /data-vista="bancos"/);
const sharedChart = renderV45GroupedChart([{ fecha: "2026-10-01", actual: -2_000_000, anterior: 1_000_000 }], "actual", "anterior", "Actual", "Anterior");
assert.match(sharedChart, /fill="#2563eb"/);
assert.match(sharedChart, /fill="#7c3aed"/);
assert.match(sharedChart, /-\$&nbsp;|-$|2000000|2\.000\.000/);

const elements = {};
for (const id of ["cc-v45-visual", "cc-detail-table-wrap", "cc-detail-cards", "cc-v45-pagination", "cc-detail-summary", "cc-v45-chart-mode"]) {
  elements[id] = { innerHTML: "", textContent: "", value: "auto", classList: { add() {}, remove() {} } };
}
sandbox.document.getElementById = (id) => elements[id];
renderResumenRanking({
  periodo: { inicio: "2026-10-01", fin: "2026-10-13" },
  nota: "Importes por cabecera.", total_importe: 80, total_cantidad: 2,
  filas: [{ etiqueta: "<Cliente>", importe: 100, cantidad: 1 }, { etiqueta: "Devolución", importe: -20, cantidad: 1 }],
}, { vista: "ventas", mode: "ranking" });
assert.match(elements["cc-v45-visual"].innerHTML, /conic-gradient/);
assert.match(elements["cc-v45-visual"].innerHTML, /&lt;Cliente&gt;/);
assert.match(elements["cc-v45-visual"].innerHTML, /Devolución/);
assert.match(elements["cc-v45-visual"].innerHTML, /negativos permanecen en la tabla/);
renderResumenRanking({
  periodo: { inicio: "2026-10-01", fin: "2026-10-13" },
  comparacion: { inicio: "2026-09-18", fin: "2026-09-30" },
  total_importe: 80, total_anterior: 120,
  filas: [{ etiqueta: "Cliente", importe: 80, anterior: 120, variacion: -40, variacion_pct: -33.33 }],
}, { vista: "ventas", mode: "comparacion" });
assert.match(elements["cc-v45-visual"].innerHTML, /Período 1/);
assert.match(elements["cc-v45-visual"].innerHTML, /↓ Baja/);

console.log("V45 render: KPI, trends, charts and comparison checks passed");
