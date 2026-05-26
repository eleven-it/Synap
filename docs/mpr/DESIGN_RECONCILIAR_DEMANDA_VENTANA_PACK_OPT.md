# Diseño técnico: reconciliar demanda al Actualizar (ventana Pack)

**Especificación:** `SPEC_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md`  
**Código actual:** `mpr/services.py` — `actualizar_pedidos_produccion` (aprox. líneas 2413–2607).

---

## Enfoque técnico

Mantener una única transacción como hoy: después de construir `filas_origen` con el mismo SQL de origen:

1. **Fase A — Upsert de líneas PED en detalle**  
   Para cada fila `(cod_ped, id_art, qty)` del origen con qty &gt; 0:
   - Si **no** existe detalle: **INSERT** (comportamiento actual).
   - Si existe y `en_proceso_produccion` normalizado es **'No'**: **UPDATE** `cantidad_pedida` y `cantidad_pendiente_prod` (ver fórmula abajo).
   - Si existe y **'Si'**: **no modificar** (omitir actualización desde este flujo).

2. **Fase B — Eliminar huérfanos de pedido**  
   Identificar filas en `lista_produccion_detalle` donde:
   - `COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'`
   - `codigo_movimiento_pedido <> 0`
   - La pareja `(codigo_movimiento_pedido, id_articulo)` **no** está en el conjunto de claves devuelto por el mismo SELECT origen **en esta ejecución** (mismo alcance de filtros).

   Acción: **DELETE** de esas filas (preferido frente a cantidad 0 para evitar filas basura y simplificar SUM).

   **Exclusión explícita:** nunca DELETE donde `codigo_movimiento_pedido = 0` (demanda reserva).

3. **Fase C — Reserva**  
   Invocar `_sincronizar_demanda_reserva_lista_detalle` **después** de A y B (orden actual puede mantenerse si la reserva no depende de las líneas PED eliminadas; si hay acoplamiento, validar en implementación).

4. **Fase D — Agrupada desde SUM**  
   Conservar el bloque actual que hace `GROUP BY id_articulo` sobre detalle con `en_proceso = 'No'` y **UPDATE/INSERT** en `lista_produccion_agrupada`.

5. **Fase E — Agrupada obsoleta sin filas en SUM**  
   El GROUP BY actual **no** produce fila para un `id_articulo` que solo tenía líneas PED eliminadas y **no** tiene reserva ni otras líneas. Esas filas en `lista_produccion_agrupada` con `en_proceso = 'No'` pueden quedar con cantidades viejas.

   **Decisión:** ejecutar un **paso adicional** (misma transacción):  
   - Obtener `id_articulo` presentes en agrupada pendientes que **no** aparecen en el resultado del SUM **o** cuyo SUM da 0 **solo** por haber eliminado PED (cuidado con artículos que siguen teniendo solo demanda reserva).  
   - Implementación pragmática: tras el bucle actual de SUM, **SELECT** ids de agrupada `en_proceso = 'No'` y comparar con el conjunto de ids del SUM; para ids **solo** en agrupada pero no en SUM: **UPDATE** `cantidad_pedida = 0`, `cantidad_pendiente_prod = 0` **o** **DELETE** según política de huérfanos del proyecto (preferencia: **UPDATE a 0** si hay FKs desde detalle a `id_lista_produccion`; si no, evaluar DELETE de agrupada vacía).

   Ajuste fino: si un artículo tiene demanda **solo** por reserva, el SUM del detalle **sí** lo incluye tras `_sincronizar_demanda_reserva_*`; no limpiar esas filas.

---

## Decisión: fórmula `cantidad_pedida` / `cantidad_pendiente_prod` al UPDATE

**Datos:**  
- `qty_origen`: cantidad desde `stockp` / pedido (nueva verdad).  
- `ped_old`, `pend_old`: valores actuales en detalle antes del UPDATE.  
- Fabricado implícito en la línea: `fab = max(0, ped_old - pend_old)` (lo ya cubierto por OPP / diferencia pedida−pendiente).

**Propuesta:**

- `ped_new = qty_origen`  
- `pend_new = max(0, qty_origen - fab)`  

Así se preserva lo ya «consumido» por producción parcial y solo el resto queda pendiente. Si `qty_origen < fab` (pedido bajó por debajo de lo ya producido), `pend_new = 0` y conviene **documentar** si en AdministraNET es escenario válido o requiere mensaje (opcional fase 2).

**Validación:** si `pend_old == ped_old` (sin parcial), entonces `fab = 0` → `pend_new = qty_origen`, coherente con pedido nuevo.

---

## Decisiones de arquitectura

| Decisión | Elección | Alternativa rechazada | Motivo |
|----------|----------|------------------------|--------|
| Fuente de verdad para demanda PED | `stockp` + `comp_ped` como hoy | Leer solo agrupada en UI | Duplicaría inconsistencias |
| Huérfanos | DELETE detalle pendiente no en origen | Marcar anulado si columna existe | Menos columnas; modelo actual sin flag |
| Reserva | Tras reconciliar PED | Antes de PED | Mantener orden cercano al actual; validar en PR |
| Agrupada huérfana | Paso E explícito | Confiar solo en SUM | SUM no lista artículos con 0 líneas |

---

## Archivos a tocar

| Archivo | Cambio |
|---------|--------|
| `mpr/services.py` | Implementar fases A–E dentro de `actualizar_pedidos_produccion` |
| `mpr/tests/test_actualizar_pedidos.py` | Tests de UPDATE/DELETE reconciliación (mock cursor o fixtures) |
| Docstring de `actualizar_pedidos_produccion` | Describir reconciliación |

**Vistas:** `VentanaPackView` / `VentanaPackActualizarView` — **sin cambio** si los filtros ya pasan igual; revisar que **búsqueda** y fechas estén alineadas al SELECT origen para que la reconciliación use el mismo alcance.

---

## Riesgos y mitigación

| Riesgo | Mitigación |
|--------|------------|
| Pedido baja por debajo de lo ya producido | `pend_new = max(0, qty - fab)`; log opcional |
| OPT liberada en otra sesión entre lecturas | Solo tocar `en_proceso = 'No'` |
| Performance en muchas líneas | Misma transacción; índices `(codigo_movimiento_pedido, id_articulo)` en detalle si no existen (catálogo schema) |

---

## Rollback

Revertir commit en `mpr/services.py` + tests: vuelve el comportamiento solo-INSERT documentado en versión anterior.

---

## Próximo paso SDD

Lista de tareas: `TASKS_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md`. Siguiente: `sdd-apply` / implementación por fases A→E y tests.
