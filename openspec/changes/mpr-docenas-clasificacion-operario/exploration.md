# Exploración — Presentación docenas y clasificación por operario fabricante (MPR)

**Change:** `mpr-docenas-clasificacion-operario`  
**Fecha:** 08/07/2026

---

## 1. Contexto de negocio

### Planta textil MPR

- El **tablero consolidado** muestra hoy cantidades en **unidades** (ej. 6500 pendiente); en piso se razona en **docenas** (~542 doc.).
- **Parte de producción** ya captura docenas + unidades por **operario** (`mpr_parte_linea`: `id_articulo`, `id_operario`, `cantidad`).
- **Clasificación** mueve stock Producción → {Semi elaborado | 2da selección | Scrap} **solo por artículo**; no atribuye al **operario que fabricó**.
- El **clasificador** (control de calidad) revisa bultos **separados por operario** en línea y define la condición de cada pieza; no se busca medir quién clasificó, sino **rendimiento del operario fabricante**.

### Objetivo de producto acordado

1. **Presentación docenas-first** en todo el flujo operativo MPR (default docenas; captura principal en docenas).
2. **Clasificación por (artículo × operario fabricante)** con reparto semi / 2da / scrap.
3. **Reporte de rendimiento** por operario (semi, 2da, scrap, % apto, % scrap) en el mismo release.

---

## 2. Estado técnico actual

| Área | Comportamiento | Gap |
|------|----------------|-----|
| `listar_tablero_por_articulo` | Devuelve unidades en columnas numéricas | Sin `*_docenas` ni toggle sesión |
| `tablero_produccion.html` | `floatformat` unidades; Enviar en unidades | No docenas |
| `construir_grilla_parte` | Operarios × componentes; docenas+unidades | OK; falta alinear toggle global |
| `construir_grilla_clasificacion_produccion` | 1 fila/artículo; `disponible` agregado | Sin dimensión operario |
| `mpr_transicion_lote` | `id_articulo`, tipos, `cantidad`, `id_usuario` (quien cargó) | **Sin `id_operario` fabricante** |
| `reporte_mpr_operario_parte` | Suma `mpr_parte_linea.cantidad` | Sin desglose semi/2da/scrap |
| Reportes hub | Toggle `presentacion` default **unidades** | Inconsistente con operativa |
| `descomponer_docenas_unidades` / `texto_docenas_unidades` | Divisor 12 componentes; bulto packs | Reutilizable |

### Stock físico vs ledger operario

- Depósito **Producción**: saldo **agregado** por `id_articulo` en `stock_deposito`.
- Parte: ledger **desglosado** por operario.
- Clasificación futura: ledger **desglosado** por operario fabricante; validación cruzada con stock agregado.

---

## 3. Decisiones de producto (cerradas)

| # | Tema | Decisión |
|---|------|----------|
| D1 | Alcance pendiente clasificación | **Fecha + turno** del clasificador; arrastre turnos anteriores en sección separada |
| D2 | Filas en grilla | **Solo (artículo, operario) con pendiente > 0**; toggle supervisor «ver roster» off por defecto |
| D3 | Clasificación parcial | **Sí**; pendiente decremental por guardado |
| D4 | Parte sin operario | **Bloquear** clasificación por rendimiento; corregir en Parte |
| D5 | Reportes | **Mismo release** que grilla; ampliar reporte Por operario |
| D6 | Default presentación | **Docenas** en MPR operativo; toggle por **sesión** |
| D7 | Divisor componentes | **12 u./docena** fijo (como OPP/parte/clasificación hoy) |
| D8 | Campo Enviar tablero | Docenas enteras + unidades sueltas opcionales si resto ≠ 0 |

---

## 4. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Desfase parte vs stock agregado | Validación global: Σ clasificado(art) ≤ saldo Producción |
| Desfase operarios vs total parte | Bloqueo si parte sin operario o suma operarios < saldo |
| Migración esquema `mpr_transicion_lote` | `catalog.py` + `mpr/sql` ALTER; backfill opcional NULL en histórico |
| Regresión reportes cadena/pipeline | Mantener agregados por artículo; nuevos KPIs solo en reporte operario |

---

## 5. Archivos probables (implementación futura)

- `mpr/services.py` — grilla clasificación, enriquecimiento docenas tablero, pendiente por operario
- `mpr/repositories/transicion_lote.py` — `id_operario` en INSERT
- `mpr/sql/` — migración columna `id_operario`, `operario_nombre`
- `mpr/templates/mpr/tablero_produccion.html`, `clasificacion_produccion.html`, `parte_produccion.html`
- `mpr/templates/mpr/includes/` — toggle presentación MPR
- `mpr/views.py` — sesión presentación; POST clasificación con operario
- `mpr/reportes_presentacion.py` — default docenas operativo
- `docs/mpr/CLASIFICACION_PRODUCCION.md`, `TABLERO_CONSOLIDADO.md`
