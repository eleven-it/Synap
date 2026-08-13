# Kardex artículo MPR

**Estado SDD:** Fase 1 disponible (MVP archivado 12/08/2026); **Fase 2 NL (tool IA) disponible**; stretch 1.15 (saldo anterior) diferido.

Reporte de trazabilidad por artículo y depósito basado en movimientos MSTOCK (OPP/OPA) de AdministraNET.

## Acceso

- **Ruta hub:** `/mpr/reportes/?grupo=trazabilidad&reporte=kardex_articulo`
- **Permisos:** `mpr.ver` o `mpr.reportes`
- **Export CSV:** mismo URL con `&format=csv` (UTF-8 BOM, fechas `dd/MM/yyyy`)

## Filtros

| Filtro | Parámetro GET | Notas |
|--------|---------------|-------|
| Artículo | `id_articulo` | Autocomplete vía `/mpr/reportes/api/articulos/buscar/` |
| Depósito | `id_deposito` | Opcional; lista desde `listar_depositos_config` |
| Período | `desde`, `hasta` | Default últimos 7 días (hub MPR) |

## Clasificación de movimientos

El servicio `construir_kardex_articulo` (módulo `mpr/services_kardex_articulo.py`) clasifica:

| Tipo | Efecto kardex |
|------|----------------|
| **OPP** | Entrada (+ cantidad) |
| **OPA / ARMADO** | Salida (− cantidad) |
| Motivo legacy «Parte producción» | Entrada |
| OPT, anulados, otros | Ignorados |

Fuente: `movimiento_stock` + `stock`, `tipo_comprobante` MSTOCK.

## Saldo corrido y limitación de ventana

- El **saldo inicial del período es 0**: no se suma stock previo a `fecha_desde`.
- Cada fila muestra `entrada`, `salida` y `saldo_corrido` acumulado en orden cronológico ASC.
- Documentado como limitación MVP; el checkbox «saldo anterior al período» queda diferido (tarea 1.15).

## KPIs y BOM

- **saldo_final:** último saldo corrido del período (o Σ entradas − salidas).
- **max_packs:** solo si el artículo es pack (`id_en_abm`) y hay depósito; delega en `calcular_max_packs_armado_1ra`.
- **Panel BOM:** `get_bom_detalle` cuando el artículo tiene lista de materiales.

## Caso de aceptación UAT — pack 907944-02

| Campo | Valor |
|-------|-------|
| IDArt | 615 |
| Código | 907944-02 |
| BOM | id_en_abm 24 |
| Componente clave | 963 × **2** unidades |
| Depósito auditado | Semi (CodDeposito **3**) |

Validación: `max_packs = floor(saldo_final_semi / 2)` coherente con auditoría AdministraNET.

Tests automatizados: `mpr.tests.test_kardex_articulo.TestKardexPack90794402Semi`.

## UI

- Partial: `mpr/reportes/partials/kardex_articulo.html`
- Modal comprobante reutilizable: `mpr/includes/_modal_comprobante_movimiento.html` + `modal_comprobante_movimiento.js`
- Empty states: sin artículo / sin movimientos en período
- Cross-link: componentes BOM → timeline trazabilidad; comprobante → modal + PDF movimiento

## Servicio y tests

```bash
docker exec Synap_app python manage.py test mpr.tests.test_kardex_articulo --keepdb
```

Cobertura UI (empty states, KPI strip, markup modal + JS Node sin `alert`/`confirm`/`prompt`):
`TestKardexArticuloUIRender` y `mpr/tests/js/test_modal_comprobante_movimiento.mjs`.

## Fase 2 — Asistente IA (disponible)

Tool NL en `ia/services/mpr_kardex_tools.py` (`execute_kardex_articulo`), cableada en `ReportToolsService.interpret_query` y rama temprana de `ReportAgentService.handle_query`.

### Cómo invocar vía asistente

Ejemplos de mensajes que enrutan al kardex (no a stock-existencias):

- «trazabilidad del pack 907944-02 en Semi»
- «kardex artículo 907944-02 este mes»
- «saldo semi del pack 907944-02»

**Permisos:** `mpr.ver` o `mpr.reportes` (mismos que el hub).

**Respuesta del asistente:** saldo final, `max_packs` si es pack, resumen BOM y hasta 20 movimientos recientes (fecha `dd/MM/yyyy`). No se vuelca el ledger completo al LLM; para detalle usar el hub kardex.

**Tests IA:**

```bash
docker exec Synap_app python manage.py test ia.tests.test_mpr_kardex_tools
```
