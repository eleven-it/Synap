/**
 * Selección por defecto del filtro "Punto de venta" en Ventas Mensuales Licenciatarios.
 * Lógica pura (sin DOM) para poder testearla con node.
 */

/** PV (nro_punto_venta) excluidos por defecto: el 200 no forma parte del reporte. */
export const VML_DEFAULT_EXCLUDED_PV_NRO = [200];

/** Número de PV de una opción: payload `nro_punto_venta`/`nro`, o dígitos de "PV 200". */
export function pvNro(pv) {
  const direct = pv?.nro_punto_venta ?? pv?.nro;
  if (direct !== undefined && direct !== null && direct !== "") {
    const n = Number(direct);
    if (Number.isFinite(n)) return n;
  }
  const m = String(pv?.label ?? "").match(/(\d+)\s*$/);
  return m ? Number(m[1]) : null;
}

/**
 * ¿Hay una selección guardada por el usuario? Solo si el objeto guardado tiene la clave
 * `punto_venta` (aunque esté vacía: "todos los PV" elegido a propósito).
 */
export function hasSavedPvSelection(saved) {
  return Boolean(saved) && Array.isArray(saved.punto_venta);
}

/**
 * Valores (string) de PV a marcar como seleccionados.
 * - Guardado: se respeta tal cual (incluida la selección vacía).
 * - Sin guardado: todos los PV cuyo nro no esté en `excludedNro` (dinámico).
 */
export function resolveVmlPvSelection(pvList, saved, excludedNro = VML_DEFAULT_EXCLUDED_PV_NRO) {
  const list = Array.isArray(pvList) ? pvList : [];
  if (hasSavedPvSelection(saved)) {
    const wanted = new Set(saved.punto_venta.map((v) => String(v)));
    return new Set(list.map((pv) => String(pv.value)).filter((v) => wanted.has(v)));
  }
  const excluded = new Set(excludedNro);
  return new Set(
    list.filter((pv) => !excluded.has(pvNro(pv))).map((pv) => String(pv.value)),
  );
}
