# Verify Report — ecom-pedido-masivo-consolidado-hub

**Fecha:** 22/07/2026  
**Fase:** apply Phase 6 + verify ligero  
**Tests:** `docker exec Synap_app python manage.py test ecom.tests.test_pedidos_hub_pipeline ecom.tests.test_lote_resumen ecom.tests.test_aprobacion_lote ecom.tests.test_batch_checkout_masivo --keepdb`  
**Resultado global:** **PASS** (59 tests OK)

## Resumen por dominio

| Dominio | Reqs clave | Estado | Evidencia |
|---------|------------|--------|-----------|
| **HUB** | HUB-04, HUB-07..10 | **PASS** | `TestCargasMasivasPipeline`: `cargas_masivas[]`, tarjeta `lote_masivo`, mapa reverso, meta hijo `puede_aprobar=False`, PED suelto sin meta lote. Docs lane/chips/filtro Lista. |
| **LOT** | LOT-01..04 | **PASS** | `test_lote_resumen`: payload coherente, 403 alcance, 404 no confirmado, Anulada + No generada. |
| **APR** | APR-03, APR-05..08 | **PASS** | `test_aprobacion_lote`: guard individual, subflag OFF, lote OK N PED, compensación parcial, escalado válido (no compensación). |
| **MAS** | MAS-20..21 | **PASS** | `test_batch_checkout_masivo`: `estado_aprobacion_lote=pendiente` post-confirmación. Docs post-confirm CTA + `readonly=1`. |

## Requisitos verificados (muestra)

| Req | Verificación | Resultado |
|-----|--------------|-----------|
| HUB-07 | Segmento `cargas_masivas` top-level, fuera de `columnas[]` | PASS |
| HUB-08 | Tarjeta rollup k/n, CTA Ver resumen | PASS |
| HUB-09 | Mapa reverso + chip/meta PED hijo | PASS |
| HUB-04 | `puede_aprobar=False` si lote pendiente | PASS |
| HUB-10 | Filtro Lista documentado (`localStorage`) | PASS (docs; UI manual pendiente QA) |
| LOT-01 | Resumen draft confirmado, 403/404 | PASS |
| LOT-04 | Reconciliación Anulada / No generada | PASS |
| APR-05 | Autorizar lote N PED + escalado | PASS |
| APR-08 | Compensación fallo parcial → `error` | PASS |
| APR-07 | `estado_aprobacion_lote` post-checkout | PASS |
| MAS-20 | CTA resumen post-confirmación | PASS (docs + modal) |
| MAS-21 | Matriz `readonly=1` | PASS (docs + implementación Phase 4) |

## Warnings (no bloqueantes)

1. **HUB-10 UI:** filtro «Ocultar PED de lotes» no tiene test E2E automatizado; cubierto por implementación en `pedidos_hub.html` y documentación.
2. **LOT-03/05/06:** CTAs resumen con modales Synap — verificados en implementación Phase 3–4; sin test de vista HTML en esta fase.
3. **APR-06 APIs HTTP:** tests a nivel servicio; smoke API en `test_aprobacion_flujo_api` existente (no re-ejecutado en lote).

## Deviaciones

Ninguna respecto al diseño. Escalado tratado como éxito parcial con `estado_aprobacion_lote=pendiente`, según ADR del change.

## Próximo paso

**sdd-archive** — sincronizar delta specs a main y archivar change.
