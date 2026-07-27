# Docenas operativas y clasificación por operario fabricante (MPR)

**Change OpenSpec:** `openspec/changes/mpr-docenas-clasificacion-operario/`  
**Estado:** Implementado en Desarrollo — aplicar migración MySQL en cada base empresa.  
**Fecha:** 08/07/2026

### Prerrequisito esquema MySQL

Control de calidad (clasificación por operario) requiere columnas en `mpr_transicion_lote`: `id_operario`, `operario_nombre`, `fecha_produccion`, `id_mpr_turno`. Si falta alguna:

```bash
docker exec Synap_app python manage.py apply_mpr_core_tables <base_empresa>
```

DDL: `mpr/sql/002_mpr_transicion_lote_operario.sql` (vía `catalog.run_mpr_core_tables_mysql`).

---

## Resumen ejecutivo

Dos mejoras coordinadas para alinear MPR con la planta textil:

1. **Presentación en docenas** por defecto en tablero, envío, parte y clasificación (persistencia en unidades).
2. **Clasificación por operario que fabricó**, con reparto Semi elaborado / 2da selección / Scrap y reporte de rendimiento ampliado.

---

## Decisiones de producto

| Tema | Decisión |
|------|----------|
| Default presentación | Docenas en flujo operativo |
| Toggle | Sesión `mpr_presentacion_cantidad` |
| Divisor componentes | 12 u./docena |
| Filas clasificación | (máquina × artículo × turno × operario), pendiente > 0 o ya clasificadas (roster completo) |
| Alcance pendiente | Fecha obligatoria; turno opcional (vacío = todos los turnos del día) |
| Columnas grilla CC | Máquina, Artículo, Turno, Operario, **Parte** (referencial, fab. del parte), Semi (calculado), 2da, Scrap |
| Semi elaborado | Solo lectura calculado: `base − 2da − desperdicio`; `base` = remanente clasificable de la fila |
| Edición CC | Solo **2da selección** y **Desperdicio**; el servidor recalcula semi |
| Validación CC | `2da + desperdicio ≤ base` (UI Alpine + servidor) |
| Bloqueo parte | Si un turno tiene CC en `mpr_transicion_lote` (fecha+turno), ese turno del parte queda bloqueado |
| Corrección post-CC | No se edita ni se revierte en la grilla CC. Reclasificar Semi/2da/Desperdicio vía **Ingreso de movimiento de stock** → transferencia interna (AdministraNET) |
| Clasificación parcial | Sí |
| Parte sin operario | Bloquear clasificación por rendimiento |
| Reportes | Mismo release que la grilla |
| Ledger | `id_operario` = fabricante; `id_usuario` = quien guardó |

---

## Flujo en planta

```text
Parte (por operario) → Stock Producción agregado
                    → Clasificador revisa bultos por operario
                    → Clasificación (semi / 2da / scrap) con id_operario fabricante
                    → Reporte rendimiento por operario
```

---

## Artefactos SDD

| Documento | Ruta |
|-----------|------|
| Exploración | `openspec/changes/mpr-docenas-clasificacion-operario/exploration.md` |
| Propuesta | `openspec/changes/mpr-docenas-clasificacion-operario/proposal.md` |
| Diseño UX | `openspec/changes/mpr-docenas-clasificacion-operario/design.md` |
| Tasks | `openspec/changes/mpr-docenas-clasificacion-operario/tasks.md` |
| Spec docenas | `specs/mpr-presentacion-docenas-operativa/spec.md` |
| Spec clasificación | `specs/mpr-clasificacion-operario-fabricante/spec.md` |
| Spec reporte | `specs/mpr-reporte-rendimiento-operario/spec.md` |

---

## Cambio de esquema

`mpr_transicion_lote`:

- `id_operario` INT NULL — operario fabricante
- `operario_nombre` VARCHAR — snapshot al guardar

Migración vía `core/services/legacy_mysql_schema/catalog.py`.

---

## P1 completado

- Toggle supervisor **Ver roster completo** en clasificación (filas completadas solo lectura).
- Hub reportes MPR: default **docenas** (GET, sesión operativa o fallback).
- Reporte operario: gráfico apilado **semi · 2da · scrap** (`hbar_stacked`).
- **Bloqueos CC (08/07/2026):** no bloquear fila si ya está 100 % clasificada o sin cantidad sin operario asignado (`construir_grilla_clasificacion_produccion`).
- **Fabricando unificado (08/07/2026):** tablero, parte y reporte pendientes usan `acreditado = max(stock, clasificado CC, partes acumulados)`; componentes sin columna Terminado. Ver [REPORTES_MPR.md](REPORTES_MPR.md), [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md).
- **Guarda física CC corregida (08/07/2026):** al guardar Control de calidad, la validación agregada de stock ahora compara **solo lo que se clasifica ahora** contra el **saldo vivo de Producción** (`total_cls > disponible_real`). Antes sumaba el acumulado ya clasificado del turno (`prev_cls_art + total_cls`), lo que **duplicaba el descuento** y bloqueaba falsamente con "Stock Producción insuficiente" cuando parte del stock clasificado ya había salido del pipeline (p. ej. Semi Elaborado consumido en el armado del pack BOM). El tope por operario (`atribuible = fabricado − ya_clasificado`) se mantiene. Ref: `mpr/views.py::RegistrarClasificacionProduccionView.post`; tests `test_clasificado_previo_consumido_no_bloquea` y `test_bloqueo_si_supera_saldo_vivo_produccion` en `mpr/tests/test_etapa10_clasificacion_produccion.py`.
- **Columna Parte + semi calculado + bloqueo parte (26/07/2026):** la grilla CC muestra **Parte** (cantidad referencial del parte, sin restar clasificado). **Semi elaborado** es solo lectura y se calcula como `base − 2da − desperdicio`, donde `base` es el remanente clasificable de la fila. Solo se editan 2da y desperdicio; el servidor recalcula semi e ignora manipulación. Validación: `2da + desperdicio ≤ base`. Filas 100 % clasificadas se muestran en solo lectura con desglose persistido. Si un turno tiene CC registrada para la fecha, el **parte** bloquea la edición de ese turno (UI + `ValidationError` en registro/ajustes). Para **corregir** Semi/2da/Desperdicio después de guardar: **Ingreso de movimiento de stock** → transferencia interna (no hay reverse en el pipeline MPR). Ref: `mpr/repositories/transicion_lote.py` (`turno_tiene_control_calidad`), `construir_grilla_clasificacion_produccion`, `parte_produccion.html`.
- **Separador visual por máquina (27/07/2026):** en `clasificacion_produccion.html`, la primera fila de cada bloque de máquina (excepto la primera de la grilla) lleva borde superior `2px slate-400` (`clasif-inicio-maquina`). Las celdas Máq./Artículo con `rowspan` usan `align-top` para alinear el chip/nombre con la primera línea de turno del bloque.
