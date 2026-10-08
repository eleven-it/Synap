/**
 * Test Node de la selección por defecto de PV (Ventas Mensuales Licenciatarios).
 * Ejecutar: node reports/tests/js/test_vml_pv_default.mjs
 */
import assert from "node:assert/strict";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const mod = await import(
  pathToFileURL(path.resolve(here, "../../static/reports/js/vml_pv_default.mjs")).href
);
const { resolveVmlPvSelection, pvNro, hasSavedPvSelection, VML_DEFAULT_EXCLUDED_PV_NRO } = mod;

const pvs = [
  { value: 11, label: "PV 1", nro_punto_venta: 1 },
  { value: 12, label: "PV 8", nro_punto_venta: 8 },
  { value: 55, label: "PV 200", nro_punto_venta: 200 },
  { value: 56, label: "PV 201" }, // sin nro en payload: se parsea del label
];

assert.deepEqual(VML_DEFAULT_EXCLUDED_PV_NRO, [200]);
assert.equal(pvNro({ label: "PV 200" }), 200);
assert.equal(pvNro({ nro: "9", label: "x" }), 9);

// Sin guardado: todos menos PV 200 (identificado por nro, no por id).
assert.deepEqual([...resolveVmlPvSelection(pvs, null)].sort(), ["11", "12", "56"]);
assert.deepEqual([...resolveVmlPvSelection(pvs, {})].sort(), ["11", "12", "56"]);
// PV nuevo se incluye automáticamente.
assert.ok(resolveVmlPvSelection([...pvs, { value: 99, label: "PV 300" }], null).has("99"));

// Guardado: gana el usuario (ids numéricos o string).
assert.deepEqual([...resolveVmlPvSelection(pvs, { punto_venta: ["55"] })], ["55"]);
assert.deepEqual([...resolveVmlPvSelection(pvs, { punto_venta: [11] })], ["11"]);
// Guardado vacío (clave presente) = todos, se respeta.
assert.equal(hasSavedPvSelection({ punto_venta: [] }), true);
assert.equal(resolveVmlPvSelection(pvs, { punto_venta: [] }).size, 0);
// Clave ausente = no hay selección guardada.
assert.equal(hasSavedPvSelection({ sucursales: ["1"] }), false);

console.log("OK test_vml_pv_default");
