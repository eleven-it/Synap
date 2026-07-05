# Verify Report: Informe cobranzas por vendedor

**Change:** `informe-cobranzas-por-vendedor`
**Fecha:** 02/07/2026
**Estado:** ✅ Implementado y verificado

## Resumen

Migrado el informe "Cobranzas por vendedor" del PHP `administraNET-ecom`
(`listado-cobranzas-vendedor.php` + `informes-json/cobranza_lista_vendedor_resumen.php`)
al módulo `reports/` de Synap, con el patrón validado en `informe-clientes-sin-ventas-vendedor`.

## Cobertura de spec

| Requisito | Estado | Evidencia |
|---|---|---|
| REQ-COB-001 Universo comprobantes | ✅ | `where_comun` en `cobranzas_vendedor.py` (IN tipos, Anulado, CodigoMovimiento, CondVenta) + test `test_sql_parametrizado_y_comprobantes` |
| REQ-COB-002 Fechas obligatorias/parametrizadas | ✅ | `get_cobranzas_vendedor` ValueError; relay 400; tests `test_operativo_sin_fechas`, `test_fechas_obligatorias` |
| REQ-COB-003 Agregados por medio de pago | ✅ | `sumas` (CASE REC vs factura) + `Decimal`; test `test_modo_mes_formato_y_totales` |
| REQ-COB-004 Modos mes/totalizado | ✅ | `_normalizar_modo` + SQL condicional; tests `test_modo_mes_*`, `test_modo_totalizado_una_fila` |
| REQ-COB-005 Totales generales (pie) | ✅ | `_armar_totales`; test `test_modo_mes_formato_y_totales` |
| REQ-COB-006 Control de acceso | ✅ | Relays operativo/gerencial; tests scope propio / anti-bypass / 403 / gerencia |
| REQ-COB-007 Acceso canónico | ✅ | ReportDefinition slug `cobranzas-por-vendedor`, sección `listados`, template dedicado |

## Pruebas

```
docker exec Synap_app python manage.py test reports.tests.test_cobranzas_vendedor_relay
Ran 14 tests ... OK
```

## Migración / rutas

```
Applying reports.0034_add_cobranzas_vendedor_report... OK
op:   /api/reports/cobranzas-vendedor/relay/
ger:  /api/reports/cobranzas-vendedor/relay/gerencia/
dash: /reports/dashboard/cobranzas-por-vendedor/
ReportDefinition: cobranzas-por-vendedor · operational · legacy_section=listados · order=60 · activo
```

## Notas / pendientes

- Validación E2E con login real y datos de MySQL legacy (paridad de sumas contra el PHP) queda como verificación operativa.
- El modo `totalizado` se implementa como fila única agregada del rango (la UI PHP solo exponía "Mensual").
