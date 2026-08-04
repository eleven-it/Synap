# Plan — Ajuste post-snapshot (inventario físico)

**Estado:** **implementado** (04/08/2026).  
**Relacionado:** [`INVENTARIO_FISICO.md`](INVENTARIO_FISICO.md), analizador `/stock/inventario-fisico/<id>/analizador/`.

## Problema

Best Sox produce en 3 turnos; la carga de parte, control de calidad y armado suele ingresar al sistema **después** del conteo físico. El snapshot (`saldo_snapshot`) queda bajo respecto de la realidad contada y el analizador muestra **sobrantes ficticios**. Autorizar MSTOCK con `Contado − Snapshot` puede **duplicar** stock cuando luego se cargan los partes.

## Objetivo

Antes de autorizar, el supervisor ve y puede ajustar el **gap de movimientos posteriores al snapshot**, y MSTOCK se aplica sobre la **diferencia real**.

## Decisiones de producto

| # | Tema | Decisión |
|---|------|----------|
| 1 | Referencia temporal | Desde el **momento del snapshot** (alta/creación de campaña). |
| 2 | Qué mueve el ajuste | **Todo movimiento de stock** (entradas y salidas) en depósitos de la campaña que genere gap. |
| 3 | Alcance | Solo **depósitos elegidos** en la campaña; cálculo por **artículo × depósito**. |
| 4 | Autorización MSTOCK | Usa **Diferencia real** = Contado − (Snapshot + Ajuste post-snapshot). |
| 5 | Override | Supervisor puede **editar / cargar** un ajuste manual por línea antes de autorizar. |
| 6 | Recálculo | Al **abrir el analizador** (fresco) **y** botón **Actualizar ajustes post-snapshot**. |
| 7 | Flujo operativo | Conteo inicia a la mañana → durante el día se cargan partes/QA/armado → cierre el mismo día o después → analizador → ajustar y/o aprobar. |
| 8 | Multi-día | El ajuste **acumula** desde el snapshot hasta el momento del recálculo / autorización. |
| 9 | Permisos y auditoría | Solo roles de **supervisor de inventario** (`gestionar` / `autorizar` según acción). Auditoría de ajustes. Visualizar **quién contó** (contador que registró la cantidad). |
| 10 | Nombres UI | **Cargado después**, **Disponible ajustado**, **Diferencia real**. |

## Fórmulas (UI y MSTOCK)

```
Cargado después (sistema)  = Σ movimientos netos al depósito de campaña
                             desde timestamp_snapshot hasta ahora
                             (entradas − salidas; signo neto por artículo×depósito)

Ajuste efectivo            = override manual si existe, si no = Cargado después (sistema)

Disponible ajustado        = Snapshot + Ajuste efectivo

Diferencia real            = Contado − Disponible ajustado
```

- Si Contado es `NULL` (no contado): sin diferencia real para MSTOCK (igual que hoy).
- MSTOCK Faltante/Sobrante se deriva del signo de **Diferencia real** (no de la diferencia cruda snapshot).

## Implementación técnica (cerrada)

| Aspecto | Decisión |
|---------|----------|
| Fuente movimientos | Tabla legacy `stock` (renglones), `CodDeposito` + `FechaControl >= fecha_snapshot`, `Anulado <> 'Si'` |
| Campo temporal | `stock.FechaControl` (TIMESTAMP inserción); desempate `id_stock` |
| Persistencia | Columnas en `inv_fisico_linea` + `inv_fisico_ajuste_auditoria` |
| DDL | `stock/sql/002_inv_fisico_ajuste_post_snapshot.sql` vía `run_stock_inv_fisico_tables_mysql` |
| Índice performance | `stock_indice_fechacontrol` → `idx_stock_dep_fechactrl (CodDeposito, FechaControl)` |
| Refresh default | `pisar_overrides=False` (conserva override manual) |
| Contador ciego | Campos nuevos en `CAMPOS_PROHIBIDOS_CONTEO`; APIs móviles sin cambio |

## Columnas del analizador

| Columna | Origen |
|---------|--------|
| Código / Artículo | Como hoy |
| Disponible | `saldo_snapshot` (congelado) |
| Cargado después | Cálculo sistema (editable vía override) |
| Disponible ajustado | Snapshot + ajuste efectivo |
| Contado | `cantidad_contada` |
| Diferencia real | Contado − Disponible ajustado |
| Contador | Usuario/código que proyectó la línea |
| Detalle | Ver conteos + origen del ajuste (movimientos) |

Filtros (Todas / Faltante / Sobrante / Con diferencia) basados en **Diferencia real**.

## Comportamiento UX (implementado)

1. Supervisor abre analizador → recalc automático (`pisar_overrides=False`).
2. Botón **Actualizar ajustes post-snapshot** → modal Synap si hay overrides (Conservar / Reemplazar).
3. Override por línea → modal Synap numérico; auditoría.
4. **Autorizar y aplicar MSTOCK** usa solo **Diferencia real** ≠ 0.
5. Bloqueos sync pendiente / conflictos sin cambio.

## Auditoría

Tabla `inv_fisico_ajuste_auditoria`: override guardado/quitado/pisado; autorización con `codigo_movimiento` y `diferencia_real`.

## Permisos

| Acción | Permiso |
|--------|---------|
| Ver analizador + columnas de ajuste | `stock.inventario_fisico.gestionar` |
| Editar override de ajuste | `stock.inventario_fisico.gestionar` |
| Autorizar MSTOCK con diferencia real | `stock.inventario_fisico.autorizar` |

## Fuera de alcance (esta fase)

- Recalcular o pisar `saldo_snapshot` histórico.
- Ajustes fuera de los depósitos de la campaña.
- Cambio del flujo móvil del contador (sigue ciego; no ve snapshot ni diferencias).
- Auto-autorización.

## Criterios de aceptación

- [x] Analizador muestra **Cargado después**, **Disponible ajustado**, **Diferencia real** y **contador**.
- [x] Cargado después = neto de movimientos en depósitos de campaña desde `fecha_snapshot` (`stock.FechaControl`).
- [x] Botón actualizar refresca cálculo sistema; por defecto **no** pisa override (`pisar_overrides=False`); modal para reemplazar.
- [x] Override editable con modal Synap + auditoría.
- [x] Autorizar genera MSTOCK según **Diferencia real**.
- [x] Contador no ve estas columnas (APIs ciegas intactas).
- [x] Docs y tests de servicio/UI actualizados.

## Tests

- `stock/tests/test_inv_fisico_ajuste_post_snapshot.py` — funciones puras y recalc con mocks.
- Extensiones en `test_inv_fisico_ajuste.py`, `test_inv_fisico_no_filtracion.py`, `test_inv_fisico_urls.py`.

## Referencias SDD

- Change: `ajuste-post-snapshot-inventario-fisico` (engram)
- Design/spec: tasks T1–T30 completadas 04/08/2026
