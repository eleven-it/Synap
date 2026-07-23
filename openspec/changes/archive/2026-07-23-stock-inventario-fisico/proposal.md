# Propuesta: Inventario físico / Conteo (Stock)

## Intent

Migrar **Inventario.frm** a Synap: conteo físico mensual ciego en depósitos MPR (Terminado, Semi elaborado, 2da), PWA offline-first, snapshot sin freeze, analizador de diferencias y ajuste masivo MSTOCK auditado. **No** reemplaza `/stock/inventario/` (consulta pivote).

## Scope

### In Scope (MVP)
- Campaña: snapshot `stock_deposito.saldo`, asignación, estados hasta Aplicado/Anulado
- Conteo ciego móvil: EAN + qty; **sin** saldo/diferencia en cliente
- Offline: prefetch catálogo ciego → IndexedDB; cola; sync idempotente (`client_event_id`); conflictos explícitos
- Escritorio: monitor, analizador, autorización → MSTOCK (`administranet_stock.py`)
- Permisos `stock.inventario_fisico.*`; whitelist PWA Nivel A; UI canon reports/MPR

### Out of Scope
- Cycle count, bins, freeze movimientos, ajuste sin autorización, campaña/autorización offline
- Fase 2+: reconteo forzado, fotos, partición prefetch

## Capabilities

### New Capabilities
- `stock-inventario-fisico-campana`: ciclo de vida, snapshot, líneas, estados
- `stock-inventario-fisico-conteo-movil`: PWA ciego, escaneo, progreso
- `stock-inventario-fisico-sync-offline`: IndexedDB, cola, sync batch, conflictos
- `stock-inventario-fisico-ajuste`: analizador, bloqueo sync pendiente, MSTOCK

### Modified Capabilities
- Ninguna (`stock-inventario-tabla` independiente)

## Approach

Patrón captura→aprobación (MPR mi-parte). Rutas `/stock/inventario-fisico/`, `/stock/conteo/`. Servicios en `stock/`; design cierra legacy `inventario*` vs esquema Synap. Reutilizar `articulos-por-codigo` y escáner `alta_movimiento`. Extender SW, `pwa_nivel_a.py`, `MobileLevelAOnlyMiddleware`. Tipos: `administranet_types`; DDL: `legacy_mysql_schema/catalog.py`.

## Roles y permisos

| Rol | Acciones |
|-----|----------|
| Operario | Contar online/offline; progreso/sync; **no** saldo ni diferencias |
| Supervisor | Campañas, analizador, reconteo, autorizar (bloqueado si sync pendiente) |
| Admin stock | Todo + anular, umbrales |

Permisos: `.contar`, `.gestionar`, `.autorizar`.

## Offline (MVP)

Con red (1×): prefetch catálogo ciego sin saldo. Sin red: scan→qty→cola IndexedDB. Al reconectar: batch idempotente; `{aceptados, conflictos, rechazados}`; last-write-wins por contador; conflictos entre contadores explícitos.

## Affected Areas

| Area | Impact |
|------|--------|
| `stock/` | New: views, services, APIs, templates conteo/campaña |
| `core/services/administranet_stock.py` | MSTOCK masivo |
| `core/middleware/mobile_level_a_middleware.py`, `core/pwa_nivel_a.py` | Whitelist PWA |
| `core/services/legacy_mysql_schema/catalog.py` | DDL |
| PWA static/JS | IndexedDB, sync, html5-qrcode |

## Risks

| Riesgo | Mitigación |
|--------|------------|
| Filtración saldo al contador | Contrato API + tests |
| Autorizar con sync pendiente | Bloqueo supervisor |
| Duplicados reintento | `client_event_id` |
| Confusión `/stock/inventario/` | Naming/menú separados |

## Rollback Plan

Deshabilitar URLs y permisos. Borrador/en conteo: anular sin MSTOCK. Aplicadas: compensación manual. Quitar whitelist PWA.

## Dependencies

Plan: `.cursor/plans/inventario_fisico_producto_af44cbbe.plan.md`; tablas `docs/general/tablas/inventario*.md`; patrones MPR parte/aprobación.

## Success Criteria

- [ ] Scan→qty→guardar **< 8 s** (catálogo prefetched)
- [ ] 30+ min offline: 100% sync o conflictos explícitos
- [ ] Contador **nunca** recibe saldo ni diferencia
- [ ] Diferencias supervisor **< 2 clics**; cero ajustes sin autorización
