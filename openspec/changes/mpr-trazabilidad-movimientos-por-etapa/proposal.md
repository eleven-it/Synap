# Propuesta: trazabilidad kardex por etapa (pipeline fabricados)

AF: `docs/mpr/AF_TRAZABILIDAD_MOVIMIENTOS_POR_ETAPA.md`.  
Exploración: `openspec/changes/mpr-trazabilidad-movimientos-por-etapa/exploration.md`.

## Intent

El análisis trazabilidad (`kardex_articulo`) para componentes con eje `pipeline_fabricados` expone un **único** saldo consolidado y netea transferencias internas (OPP entre depósitos MPR). El inventario Fabricados sí muestra Producción / Semi elaborado / 2.ª selección / Consolidado. Gerencia no puede auditar cómo evolucionó cada etapa ni conciliar el histórico con el tablero de stock. Este change añade **impacto por depósito/etapa**, **corrido multi-etapa en backend** y **paridad de cierre** con inventario por etapa, sin alterar la semántica de `inventario_tabla`.

## Scope

### In Scope

- Hub MPR: reporte `trazabilidad` / `kardex_articulo` (`construir_analisis_trazabilidad_articulo`).
- Artículos componente con `tipo_eje: pipeline_fabricados` (Producción, Semi elaborado, 2.ª selección).
- Explosión de movimientos por `CodDeposito` (enfoque SQL objetivo de exploración); transferencias pipeline = **dos renglones** (salida origen + entrada destino).
- Payload: `saldos_por_etapa` tras cada movimiento + consolidado derivado (suma etapas); saldo corrido consolidado **visible** en UI.
- UI MVP: columna **Etapa** en grilla; KPIs cabecera con desglose Producción / Semi / 2.ª / Consolidado (canon reportes MPR).
- CSV y presentación Pares/Docenas alineados a nuevos campos.
- Conciliación **estricta por etapa** solo si `Hasta >= hoy` vs `consultar_inventario_tabla(ambito=fabricados)` (lectura; sin cambiar columnas inventario).
- Tests: OPP cross-depósito, cierre vs inventario, regresión golden pack Terminado, columnas CSV.

### Out of Scope

- Timeline OPT (`/mpr/opt/<id>/trazabilidad/`).
- Inventario físico / campañas; rediseño inventario por etapa; cambio reglas OPP/OPA/REM/FA (solo presentación/acumulación).
- **Oleada 1:** packs eje `terminado` — **sin cambio funcional** (oleada 2 opcional multi-eje).
- Snapshot histórico de etapas (paridad estricta fuera de «hoy»).
- Filtro/pestaña por etapa única (SHOULD RF-08; post-MVP si no entra en presupuesto).

## Decisiones de producto (cerradas en propose)

| # | Decisión |
|---|----------|
| 1 | UI MVP: columna **Etapa** + KPIs cabecera por etapa; **saldo corrido consolidado** se mantiene; cada fila muestra `saldos_por_etapa` post-movimiento (backend los calcula). |
| 2 | Transferencias pipeline: **dos renglones** cuando un comprobante impacta dos depósitos del pipeline. |
| 3 | Corrido multi-etapa **siempre en backend** (no derivar en cliente). |
| 4 | Packs Terminado: **fuera de oleada 1**; camino `tipo_eje: terminado` intacto. |
| 5 | Conciliación estricta por etapa solo si **`Hasta >= hoy`**. |

## Capabilities

### New Capabilities

- `mpr-kardex-trazabilidad-por-etapa`: filas por impacto de depósito, corrido `saldo_por_tipo_mpr`, conciliación cierre fabricados, contrato UI/CSV oleada 1.

### Modified Capabilities

- Ninguna en `openspec/specs/` hoy; delta inicial vive en el change hasta archive.

## Approach

Modo **evolution**: patch acotado en `mpr/services_kardex_articulo.py` (consultas `GROUP BY` + `CodDeposito`, normalización dual-fila OPP, acumulador por `tipo_mpr`, saldo inicial pre-período por depósito, advertencia conciliación extendida). Reutilizar `TIPOS_MPR_PIPELINE_FABRICADOS` y orden de etapas alineado a `stock/services/inventario_tabla.py` (**solo lectura** / helper tests — **MUST NOT** cambiar semántica de columnas inventario).

| Capa | Entregable |
|------|------------|
| Backend | Contrato fila + `saldos_por_etapa` / consolidado; bifurcación `pipeline_fabricados` vs resto |
| UI | `kardex_articulo.html`: columna Etapa, KPIs, saldo consolidado corrido |
| Export | `reportes_hub.py`, `export.py`, `reportes_presentacion.py` |
| Tests | `test_analisis_trazabilidad_articulo.py`, `test_kardex_articulo.py` |

Entrega preferida **una oleada** si el presupuesto review lo permite; si no, PR1 backend+tests, PR2 UI+CSV (`ask-on-risk`, ~400–900 líneas estimadas exploración).

## Affected Areas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `mpr/services_kardex_articulo.py` | Modified | SQL por depósito, corrido multi-etapa, conciliación |
| `mpr/services.py` | Modified | Mapeo depósito ↔ `tipo_mpr` (reuso) |
| `mpr/templates/mpr/reportes/partials/kardex_articulo.html` | Modified | Etapa, KPIs, saldos |
| `mpr/reportes_hub.py`, `mpr/export.py` | Modified | Columnas CSV |
| `mpr/reportes_presentacion.py` | Modified | Factores sobre nuevos numéricos |
| `mpr/views.py` | Modified | Contexto export si aplica |
| `stock/services/inventario_tabla.py` | Read-only | Paridad tests / helper cierre |
| `mpr/tests/test_*kardex*`, `test_analisis_trazabilidad*` | Modified | Contratos paridad y regresión pack |
| `docs/mpr/` | Modified | Nota post-diseño (política repo) |

**Sin tocar:** semántica `inventario_tabla`; timeline OPT; reglas de negocio MSTOCK.

## Risks

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| Regresión pack Terminado | Media | Bifurcar por `tipo_eje`; golden existente |
| Truncamiento `limit=2000` con más filas | Media | Advertencia historial; documentar |
| Redondeo docenas ±1 por etapa | Baja | Tolerancia AF; tests |
| FA `afecta_deposito=False` | Baja | Mantener exclusión corrido; definir en design |
| Presupuesto review >400 líneas | Media | PR encadenados; `delivery.strategy` |

## Rollback Plan

Revertir merge del PR (sin DDL). Restaura agregación netea y UI/CSV previos. Tests golden pack deben volver verde tras revert.

## Dependencies

- AF trazabilidad; `FUENTE_VERDAD_UI_REPORTES_MPR.md` (design UI).
- Tablas legacy `stock` / `stock_deposito` / `deposito.tipo_mpr`.

## Success Criteria

- [ ] Pipeline fabricados: columna Etapa y `saldos_por_etapa` post-movimiento en grilla.
- [ ] OPP Producción → Semi: dos renglones; Semi sube / Producción baja; consolidado coherente en transferencia pura.
- [ ] Con `Hasta >= hoy`, cierre 79/28/0/107 (fixture) cuadra con inventario Fabricados (misma presentación).
- [ ] CSV incluye etapa/depósito y saldos auditables.
- [ ] Pack Terminado: sin regresión UI/saldo/CSV golden.
- [ ] `docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo mpr.tests.test_kardex_articulo` verde.
