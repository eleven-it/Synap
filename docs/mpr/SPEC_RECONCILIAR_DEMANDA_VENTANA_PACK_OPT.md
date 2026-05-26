# Especificación (delta): reconciliar demanda al Actualizar (ventana Pack / OPT)

**Estado:** implementación núcleo en `actualizar_pedidos_produccion` (synopsis en `TASKS_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md`).  
**Ámbito:** Módulo MPR — `actualizar_pedidos_produccion`, ventana demanda para crear OPT (`ventana_pack`).  
**Relacionado:** propuesta SDD «demanda OPT reconciliar», exploración código `mpr/services.py` (solo INSERT de detalle hoy).

---

## Contexto

Hoy, al pulsar **Actualizar**, Synap ejecuta `actualizar_pedidos_produccion`, que lee pedidos PED desde `stockp` + `comp_ped` y:

- En **`lista_produccion_detalle`**: si ya existe la pareja `(codigo_movimiento_pedido, id_articulo)`, **no modifica** la fila (solo **INSERT** si no existe).
- Luego recalcula **`lista_produccion_agrupada`** con **SUM** sobre el detalle con `en_proceso_produccion` tratado como pendiente.

Si en AdministraNET/VB6 cambia la cantidad de una línea de pedido (o desaparece la línea), el detalle Synap **no se actualiza** y la agrupada puede quedar **incoherente** con el pedido real.

---

## Capacidad modificada

### `mpr-ventana-pack-demanda` (sincronización desde PED)

**Comportamiento actual (a preservar donde aplique):**

- Filtros de origen: PED, no anulado, `estado_pedido_opt` Pendiente/Parcial si existe columna, fechas, búsqueda, `tipo_art_fab = Terminado`.
- Inserción de líneas nuevas en detalle con `en_proceso_produccion = 'No'`.
- Sincronización de demanda por **reserva** (`_sincronizar_demanda_reserva_lista_detalle`, `codigo_movimiento_pedido = 0`).
- Recálculo **SUM → lista_produccion_agrupada** para artículos que tienen filas en detalle pendientes.

**Comportamiento nuevo (requerido):**

1. **Actualización de cantidades (UPSERT lógico)**  
   Para cada fila del **origen** `(codigo_movimiento_pedido, id_articulo, cantidad)` con cantidad &gt; 0:  
   si existe en `lista_produccion_detalle` la misma pareja y **`en_proceso_produccion = 'No'`**, **actualizar** `cantidad_pedida` y `cantidad_pendiente_prod` según las reglas del diseño (no pisar trabajo ya registrado por OPP sin criterio).

2. **Reconciliación de líneas obsoletas**  
   Filas de `lista_produccion_detalle` con **`en_proceso_produccion = 'No'`**, `codigo_movimiento_pedido ≠ 0`, que **no** aparecen en el conjunto origen **para el mismo alcance de filtros** que usa el SELECT actual: deben **eliminarse** o quedar en cantidad cero de forma consistente con el modelo (definido en diseño).  
   **No** aplicar esta eliminación a la fila sintética de demanda por **reserva** (`codigo_movimiento_pedido = 0`).

3. **Agrupada y artículos sin líneas PED**  
   Tras SUM, si un artículo ya **no** tiene líneas pendientes de pedido que aporten demanda pero **`lista_produccion_agrupada`** aún muestra cantidades solo por datos viejos: la agrupada debe **reflejar** el SUM real (incluido **cero** o ausencia de fila según reglas acordadas en diseño).

4. **Fuera de alcance**  
   - Modificar filas con **`en_proceso_produccion = 'Si'`** (OPT en curso).  
   - Modificar líneas ya asociadas a OPT liberada / trazabilidad que el diseño declare intocable.  
   - Cambiar comportamiento de liberación OPT u OPP.

---

## Requisitos funcionales

### RF1 — Reflejar cambio de cantidad en pedido

**Dado** una línea `(cod_ped, id_art)` ya presente en `lista_produccion_detalle` con `en_proceso_produccion = 'No'` y el mismo par en el origen con cantidad **distinta** desde `stockp`,  
**cuando** el usuario ejecuta **Actualizar** con filtros que **incluyen** ese pedido,  
**entonces** las cantidades en detalle deben alinearse al pedido según reglas de pendiente (ver diseño), y la vista **ventana_pack** (tras `listar_ventana_pack`) debe mostrar totales coherentes.

### RF2 — Reflejar línea de pedido eliminada o fuera de filtro

**Dado** una línea de detalle pendiente `(cod_ped, id_art)` que **ya no** está en el resultado del SELECT origen (pedido anulado, línea borrada, estado fuera de Pendiente/Parcial, o fecha fuera del rango si el usuario acotó fechas),  
**cuando** se ejecuta Actualizar,  
**entonces** esa línea no debe seguir contando como demanda pendiente **si** las reglas de reconciliación la marcan como eliminable (solo `en_proceso = 'No'`, no reserva).

### RF3 — Parcial / OPP ya registrado

**Dado** una línea con `cantidad_pedida` &gt; `cantidad_pendiente_prod` (producción parcial ya registrada),  
**cuando** el pedido aumenta o disminuye la cantidad,  
**entonces** el sistema debe ajustar **sin** volver a pedir como pendiente lo ya cubierto por OPP (fórmula en diseño).

### RF4 — Mensaje al usuario

**Cuando** la ejecución termina con éxito, el mensaje puede indicar que se **sincronizaron** líneas existentes además de incorporar nuevas (texto a definir en implementación, sin romper tests que validan presencia de «demanda por reserva»).

---

## Escenarios de prueba (aceptación)

| ID | Escenario | Resultado esperado |
|----|-----------|-------------------|
| A1 | Detalle tiene (pedido P, art A) pedida 10; origen pasa a 15 | Tras Actualizar, pedida y pendiente coherentes con regla de diseño; agrupada SUM correcta |
| A2 | Origen ya no incluye (P, A); fila detalle solo pendiente | Fila eliminada o cantidades cero según diseño; agrupada sin demanda fantasma |
| A3 | Línea `codigo_movimiento_pedido = 0` (reserva) | No se borra por reconciliación PED |
| A4 | `en_proceso_produccion = 'Si'` | Fila no modificada por este flujo |
| A5 | Parcial: pedida 10, pendiente 4 | Cambio pedido a 12 → pendiente según fórmula diseño |

---

## Dependencias

- Diseño técnico: `DESIGN_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md`.
- Implementación principal: `mpr/services.py` — función `actualizar_pedidos_produccion`.
- Tests: ampliar `mpr/tests/test_actualizar_pedidos.py` (mocks o BD de prueba según patrón del proyecto).

---

## Seguimiento SDD

| Fase | Artefacto |
|------|-----------|
| Propuesta | Engram `sdd/mpr-opt-demanda-reconciliar-proposal/proposal` |
| Especificación | Este documento |
| Diseño | `DESIGN_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md` |
| Tareas | `TASKS_RECONCILIAR_DEMANDA_VENTANA_PACK_OPT.md` |
