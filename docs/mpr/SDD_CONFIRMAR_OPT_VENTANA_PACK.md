# SDD — Confirmar OPT: precarga desde ventana-pack y sin operario

**Nombre del change:** `mpr-ventana-pack-agrupar-prefill-sin-operario`  
**Estado:** implementado (06/05/2026).

## Objetivo

1. Al pulsar **Continuar** en Pedido producción trabajo (OPT), la pantalla **Confirmar OPT** (`/mpr/demanda/ventana-pack/agrupar/`) debe mostrar **Cantidad a fabricar** por componente coherente con la selección y la explosión BOM (sin depender del saldo neto en Semi para el valor editable inicial que quedaba en 0).
2. En esa pantalla **no** se muestra la columna **Operario** (sigue en OPP y Armado/OPA).

## Requisitos

| ID | Descripción |
|----|-------------|
| R1 | POST desde ventana-pack guarda en sesión packs con `cantidad_a_fabricar` > 0. |
| R2 | `listar_unidades_desde_seleccion` usa demanda bruta de componentes para la columna editable (`restar_saldo_semi_en_cant_fabricar=False` en `_listar_unidades_por_demanda`). |
| R3 | Columnas **Urgente** siguen usando brecha vs saldo Semi elaborado. |
| R4 | Plantilla `ventana_pack_agrupar.html` sin Operario; `lineas_opt_desde_formulario_unidades` admite operario `None`. |
| R5 | Manual de usuario actualizado (§3.1.1 y wizard §4.0). |
| R6 | En Pedido producción trabajo (OPT), pestaña **Packs**, **Cantidad a fabricar** es editable (unidades y docenas sincronizadas como en Confirmar OPT); el POST envía `cant_{id_articulo}` con el valor indicado y la sesión incluye `cantidad_pedida_pedido` para la explosión BOM. |
| R7 | El formulario `#form-crear-opt` envuelve **Packs**, **Unidades** y el botón **Continuar**. Continuar no debe quedar solo dentro de `#panel-packs` (si no, al cambiar de pestaña queda oculto y el usuario no puede confirmar desde Unidades con los mismos campos POST). |

## Tareas

- [x] Parámetro `restar_saldo_semi_en_cant_fabricar` en `_listar_unidades_por_demanda`.
- [x] `listar_unidades_desde_seleccion` con `False` para Confirmar OPT.
- [x] Ajuste UI agrupar (inputs `min`, sincronización docenas, validación submit).
- [x] Eliminación columna Operario solo en agrupar.
- [x] Documentación `MANUAL_USUARIO_MPR.md`.
- [x] Test de regresión del flag (`test_listar_unidades_desde_seleccion_flag.py`).
- [x] Cant. a fabricar editable en `ventana_pack.html` (Packs); sesión con `cantidad_pedida_pedido`; POST parsea cantidades numéricas.

## Código

- `mpr/services.py`: `_listar_unidades_por_demanda`, `listar_unidades_desde_seleccion`.
- `mpr/templates/mpr/ventana_pack_agrupar.html`.
- `mpr/templates/mpr/ventana_pack.html` (inputs Cant. a fabricar + sincronización docenas).
- `mpr/views.py`: `VentanaPackAgruparView.post` (parseo robusto de cantidades, `cantidad_pedida_pedido` en sesión).

## Engram

- Propuesta: **#77** (`…/proposal`).
- Verify-report: **#78** (`…/verify-report`).
- Archive-report: **#79** (`…/archive-report`).
