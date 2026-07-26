# Verify report — contabilidad-auditoria-anulaciones-apply

**Fecha:** 25/07/2026

| Criterio | Resultado |
|----------|-----------|
| Dry-run lista ítems anulación con preview | OK |
| Apply repara marcador / original / contra; no auto-arregla `contra_no_invierte_original` | OK (tests + piloto) |
| Orden regen → repair → concepto → saldos | OK (código + REC-07) |
| Backup `cuentaproveedor` | OK |
| Idempotencia dry-run post-apply ej.1 | OK (0 reparables) |
| Rollback UI (modal Synap, sin `confirm`) | OK (código + tests vistas) |
| Suite tests contenedor | OK (`test_cont_recalculo_anulaciones` + `test_views`, 18 tests) |
| Docs AUDITORIA_* | OK |

**Nota:** check `integridad_anulacion_compra_pago` no filtra por ejercicio; residuales fuera de alcance o sin asiento original quedan visibles en tablero pero no en dry-run `ejercicio_seleccionado`.
