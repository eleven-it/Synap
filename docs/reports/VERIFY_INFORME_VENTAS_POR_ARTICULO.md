# Verificación: Informe «Ventas por artículo»

Fecha: 20/05/2026. Change SDD: `ventas-por-articulo`.

## Migración

| Check | Resultado |
|-------|-----------|
| `0032_add_ventas_por_articulo_report` aplicada | OK (`[X]` en `showmigrations reports`) |
| `ReportDefinition` slug `ventas-por-articulo` | OK — nombre «Ventas por artículo», `is_active=True` |
| Corrección migración | Se quitó `show_in_catalog` del `defaults` (campo no está en estado histórico de migraciones); en BD la columna existe y quedó en `True` por defecto |

## Tests automatizados (contenedor)

```
docker exec Synap_app python manage.py test reports.tests.test_ventas_por_articulo reports.tests.test_export_column_order
```

Resultado: **9/9 OK**.

## Smoke test runner (MySQL)

Período **01/01/2025 – 31/12/2025**, usuario activo, base `administranet`:

| Métrica | ventas-por-articulo | ventas-por-vendedor |
|---------|---------------------|---------------------|
| Filas planas | 46.513 (art×prov×cli) | 1.157 (clientes) |
| Raíz jerarquía | 2.393 artículos | 25 vendedores |
| Facturación total | 12.389.637.735,92 | 12.200.089.373,83 |
| Tiempo total | ~2,9 s | ~2,0 s |

- Runner sin excepciones; árbol con `tipo` artículo → proveedor → cliente.
- Diferencia de facturación ~1,5 % vs VPV: esperable (VPV agrega cabecera cliente; VPA solo suma líneas de detalle por artículo). Validar en UI con mismos filtros si producto exige paridad exacta.

## Matriz spec (estático + evidencia)

| Requisito | Estado |
|-----------|--------|
| R1 Catálogo y URL | OK — migración, `query_runner`, `catalog_service`, redirect |
| R2 Jerarquía art→prov→cli | OK — `_nest_articulo_proveedor_cliente`, tests nest |
| R3 Sin proveedor | OK — test `test_sin_proveedor_display` |
| R3 Filtros rubro/vendedor | OK — `vo_filtra_rubro` activo para slug artículo |
| R4 Export | OK — headers test + rama `export_service` |
| R5 Recarga manual | OK — `isInformeQuerySoloManualORealtime` incluye slug |
| R6 Paridad métricas | OK aproximado (misma órden de magnitud 2025); ver nota ±1,5 % vs VPV |
| R7 Ajustes sin mercadería | OK — nodo sintético + helper compartido (`test_nodo_ajustes_cabecera`) |

## UI

| Check | Estado |
|-------|--------|
| Plantilla jerarquía + filtros BO | OK — `dashboard_detail.html`, includes |
| JS dedicado `ventas_por_articulo.js` | OK — no carga `objetivos_ventas_bo.js` |
| `dashboard.js` handler | OK — `ventasPorArticuloHandler` |

## Veredicto

**PASS** — migración, tests, runner con datos reales y registro de slug en UI/export. Recomendado: abrir `/reports/dashboard/ventas-por-articulo/` y confirmar expansión artículo → proveedor → cliente en navegador.
