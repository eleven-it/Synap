# SDD — OPP: entrada docenas y unidades (change cerrado)

**Nombre del change:** `mpr-opp-entrada-docenas-unidades`  
**Estado:** implementado, verificado y archivado (06/05/2026).

## Objetivo

En **Crear OPP** (asistente paso 3) y **Registrar OPP**, cada celda componente × depósito permite **docenas** y **unidades sueltas**. El backend registra solo **unidades totales**: `docenas × 12 + unidades`. En OPP **una docena son siempre 12 unidades** (no `cantidad_promedio_bulto`).

## Especificación resumida

| ID | Requisito |
|----|-----------|
| R1 | POST por celda: `opp_comp_{id_articulo}_dep_{CodDeposito}_docenas` y `_unidades`. |
| R2 | Cantidad en unidades = `max(0,docenas)×12 + max(0,unidades)`; valores no enteros → 0 en cada parte. |
| R3 | Misma lógica en `_post_paso3` (wizard) y `RegistrarOppView.post`. |
| R4 | Validación existente: suma por componente ≤ disponible; operario obligatorio si suma > 0. |
| R5 | Sin cambios a MySQL ni a `ejecutar_opp_por_componentes` (sigue recibiendo unidades). |
| R6 | UI: cabecera por depósito con subcolumnas **Docenas** y **Unidades**. |

### Escenarios de aceptación

| Escenario | Criterio |
|-----------|----------|
| S1 | 9 docenas + 2 unidades → 110 unidades por celda. |
| S2 | 0 docenas + 110 unidades → 110 (equivalente al flujo anterior de un solo campo). |
| S3 | Campos omitidos o inválidos → 0 unidades aportadas por esa celda. |

## Tareas (todas completadas)

- [x] Helper `UNIDADES_POR_DOCENA_OPP` y `_opp_cantidad_unidades_desde_post` en `mpr/views.py`.
- [x] Wizard paso 3 y `registrar_opp.html`: matriz, POST y JS de suma (docenas×12+unidades).
- [x] Cabeceras de tabla en dos filas (nombre depósito + Docenas | Unidades).
- [x] `docs/mpr/MANUAL_USUARIO_MPR.md` actualizado.
- [x] Tests unitarios: `mpr/tests/test_opp_entrada_docenas.py`.

## Código relevante

- `mpr/views.py`: constante, helper, `_post_paso3`, `RegistrarOppView.post`.
- `mpr/templates/mpr/wizard.html`, `mpr/templates/mpr/registrar_opp.html`.

## Trazabilidad Engram (proyecto memoria)

| Artefacto | Observación |
|-----------|-------------|
| explore | #72 |
| proposal | #73 |
| implement / decisión docena 12 | #74 |
| verify-report | #75 |
| archive-report | #76 |

## Verificación

- `manage.py test mpr` incluye `test_opp_entrada_docenas` (escenarios S1–S3 a nivel helper).
