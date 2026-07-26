# Propuesta — Docenas operativas MPR y clasificación por operario fabricante

**Change:** `mpr-docenas-clasificacion-operario`  
**Fecha:** 08/07/2026  
**Exploración:** [exploration.md](./exploration.md)  
**Diseño UX:** [design.md](./design.md)

---

## 1. Intención

Alinear el módulo MPR con la operación de planta textil en dos ejes:

1. **Cantidades en docenas** como presentación y captura por defecto en tablero, envío, parte, clasificación y flujos afines (persistencia en unidades en MySQL).
2. **Clasificación atribuida al operario que fabricó**, no al clasificador, para medir rendimiento real: cuánto de la producción de cada operario terminó en Semi elaborado, 2da selección o Scrap.

El clasificador registra en Synap el reparto de calidad **por bulto de operario**; el usuario logueado queda solo como auditoría (`id_usuario`).

---

## 2. Problema

| Hoy | Dolor |
|-----|-------|
| Tablero en unidades (6500) | Operadores piensan en docenas (~542) |
| Clasificación por artículo | No hay KPI semi/2da/scrap **por operario** |
| `mpr_transicion_lote` sin operario | Reporte operario solo muestra «fabricado», no calidad |
| Toggle docenas solo en reportes | Default unidades; inconsistente con piso |

---

## 3. Alcance

### Incluido (P0)

| # | Entrega |
|---|---------|
| P0-1 | Toggle sesión **Docenas / Unidades** en shell MPR operativo (default **docenas**) |
| P0-2 | Tablero: columnas y **Enviar** en docenas (con unidades sueltas opcionales) |
| P0-3 | Parte y clasificación alineados al toggle (docenas-first en captura) |
| P0-4 | Esquema: `id_operario` + `operario_nombre` en `mpr_transicion_lote` |
| P0-5 | Grilla clasificación: filas **(artículo × operario)** con semi / 2da / scrap |
| P0-6 | Pendiente por operario = parte(fecha,turno) − clasificado(operario) |
| P0-7 | Validaciones: por fila y global stock Producción |
| P0-8 | Bloqueo si parte sin desglose por operario |
| P0-9 | ~~Sección Pendiente turnos anteriores~~ — **retirada** 26/07/2026 (sin utilidad vs. costo de UI) |
| P0-10 | Reporte **Producción → Por operario** ampliado (semi, 2da, scrap, %) |
| P0-11 | Tests servicio, POST, esquema, reporte |
| P0-12 | Docs `docs/mpr/` |

### Incluido (P1)

| # | Entrega |
|---|---------|
| P1-1 | Toggle supervisor «Ver roster completo» en clasificación |
| P1-2 | Default docenas en hub reportes MPR (alinear con operativa) |
| P1-3 | Gráfico apilado semi/2da/scrap en reporte operario |

### Fuera de alcance v1

- Atribución de operario en **envío tablero** (sigue siendo por componente agregado).
- Fracciones de docena (decimales).
- Divisor distinto por artículo en tablero de componentes (se mantiene 12).
- Registro del clasificador como dimensión analítica.

---

## 4. Capabilities

### New Capabilities

| Capability | Spec | Descripción |
|------------|------|-------------|
| `mpr-presentacion-docenas-operativa` | `specs/mpr-presentacion-docenas-operativa/spec.md` | Toggle sesión y conversión UI |
| `mpr-clasificacion-operario-fabricante` | `specs/mpr-clasificacion-operario-fabricante/spec.md` | Grilla, ledger, validaciones |
| `mpr-reporte-rendimiento-operario` | `specs/mpr-reporte-rendimiento-operario/spec.md` | KPIs calidad por operario |

### Modified Capabilities

| Capability | Cambio |
|------------|--------|
| `mpr-transiciones-lote` (delta en change) | Columna `id_operario` fabricante |
| `mpr-reporte-operario` (delta en change) | Extender métricas; ver spec rendimiento |
| Tablero consolidado | Presentación docenas |
| Parte producción | Toggle global docenas-first |

---

## 5. Enfoque técnico (resumen)

- Reutilizar `descomponer_docenas_unidades`, `texto_docenas_unidades`, `enriquecer_*_presentacion` en `mpr/services.py`.
- Sesión: `mpr_presentacion_cantidad` = `docenas|unidades` (default `docenas`).
- POST envío/clasif: parsear docenas (+ unidades sueltas) → unidades antes de ledger.
- `construir_grilla_clasificacion_operario(base, fecha, turno_id)` nueva o extensión de E10.
- Migración MySQL vía `core/services/legacy_mysql_schema/catalog.py` + `mpr/sql/`.

---

## 6. Criterios de éxito

1. Tablero abre en **docenas** por defecto; Enviar acepta docenas y convierte correctamente.
2. Clasificador ve una fila por cada **(artículo, operario)** con pendiente del turno.
3. Al guardar clasificación, `mpr_transicion_lote.id_operario` = fabricante.
4. Reporte operario muestra fabricado + semi + 2da + scrap + % por operario en el período.
5. Histórico sin `id_operario` sigue legible (NULL → «Sin atribución» en reportes).
