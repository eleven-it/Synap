# Checklist de implementación: Informe clientes sin ventas por vendedor

**Change:** `informe-clientes-sin-ventas-vendedor`
**Spec:** [specs/reports-clientes-sin-ventas/spec.md](./specs/reports-clientes-sin-ventas/spec.md) · **Design:** [design.md](./design.md)
**Fecha:** 02/07/2026 · **Estado:** implementado (tests 18/18 OK)

---

## Fase 1: Servicio (reports/services/clientes_sin_ventas.py)

- [x] 1.1 Crear módulo e importar `core.mysql_pool` (`get_mysql_pool`) y `core.utils.administranet_types` (`to_int_or_none`, `to_date_or_none`, `str_or_default`). — REQ-CSV-001..006
- [x] 1.2 `parse_filtrar_por(raw) -> list[int]`: extraer pares `vendedor|<id>`, descartar no numéricos, normalizar a `int`, `unique`. — REQ-CSV-004
- [x] 1.3 `listado_vendedores_seleccion(...)`: SQL `viajantes` con `Anulado='No'` + cláusula `IN (%s,...)` por permisos; devolver `[{label, value}]`. — REQ-CSV-003
- [x] 1.4 Helper interno `_clausula_vendedor(...)`: devuelve `(sql_fragment, params)` con placeholders segun permisos/filtro (nunca interpolar). — REQ-CSV-004
- [x] 1.5 `get_clientes_sin_ventas(...)`: consulta principal parametrizada (`BETWEEN %s AND %s`, `IN (...)`), `campoId`/`campoDomicilio`/`UltimaCompra`; armar filas con última compra dd/MM/yyyy y "-" (orden 9999-12-31); anexar domicilio si `incluir_domicilio`. — REQ-CSV-001, 002, 005
- [x] 1.6 Consulta de resumen agregada (`COUNT(DISTINCT CASE ...)`) con misma cláusula vendedor; armar `resumenVendedores`, `resumenGlobal`, `modoTodosVendedores`. — REQ-CSV-006
- [x] 1.7 Devolver dict con `columns`, `datos`, `resumenVendedores`, `resumenGlobal`, `modoTodosVendedores`, `totales`.

## Fase 2: Relay API (reports/clientes_sin_ventas_relay_views.py)

- [x] 2.1 `ClientesSinVentasRelayAPIView` (`OperationalReportsPermission`): scope forzado a vendedor de sesión; helpers de fecha/sesión; 400 si faltan fechas (modo != seleccion). — REQ-CSV-002, 004
- [x] 2.2 `ClientesSinVentasGerenciaRelayAPIView` (`ManagerialReportsPermission`): respeta `filtrarPor` + `vendedor_a_cargo`. — REQ-CSV-003, 004
- [x] 2.3 Mapear claves de sesión con defaults seguros (`inf_gerenciales`, `supervisor_venta`, `vendedor_a_cargo`, `todos_clientes`, `usa_id_manual`, `usa_domicilio_cliente_informes`, `id_vendedor_usr`, `base_empresa`).
- [x] 2.4 Manejo de error 500 controlado (log + mensaje genérico), como `VentasNetasRelay*`.

## Fase 3: Rutas (reports/api_urls.py)

- [x] 3.1 Importar y registrar `clientes-sin-ventas/relay/` y `.../relay/gerencia/` con names `reports-clientes-sin-ventas-relay[-gerencia]`. — REQ-CSV-007

## Fase 4: UI canónica

- [x] 4.1 Añadir rama de slug `clientes-sin-ventas-vendedor` en `DashboardDetailView.get_template_names` (`reports/views.py`). — REQ-CSV-007
- [x] 4.2 Crear `reports/templates/reports/dashboard_clientes_sin_ventas_vendedor.html` (base canónica + includes `reports/includes/`): filtros período, selector vendedor (autocomplete modo `seleccion`), checkbox domicilio, tabla y gráfico segun `modoTodosVendedores`. — REQ-CSV-005, 006, 007
- [x] 4.3 JS `fetch` a la relay API (operativo/gerencial segun permiso); render tabla + Chart.js; textos/fechas en español (dd/MM/yyyy). — REQ-CSV-005, 006
- [x] 4.4 Verificar que NO se usa como referencia visual `ventas/` (canon UI).

## Fase 5: ReportDefinition + checkpoint

- [x] 5.1 Migración `reports/migrations/00XX_add_clientes_sin_ventas_report.py`: `update_or_create` slug `clientes-sin-ventas-vendedor` (guarda de tabla, `reverse` que elimina). — REQ-CSV-007
- [x] 5.2 `EcomMigrationCheckpoint(module_slug="mayoristapp_informe_clientes_sin_ventas")`.

## Fase 6: Tests (reports/tests/test_clientes_sin_ventas_relay.py)

- [x] 6.1 `parse_filtrar_por`: válidos / no numéricos / vacío / inyección textual. — REQ-CSV-004
- [x] 6.2 Cláusula vendedor por permisos (operativo, supervisor con/ sin cargo, gerencial). — REQ-CSV-004
- [x] 6.3 Forma de respuesta del servicio (mock cursor): `datos`, `resumenVendedores`, `resumenGlobal`, `modoTodosVendedores`, columnas, última compra "-"/dd/MM/yyyy. — REQ-CSV-001, 005, 006
- [x] 6.4 Relay: 400 sin fechas; scope operativo no ampliable por `filtrarPor`; gerencial respeta filtro. — REQ-CSV-002, 004
- [x] 6.5 Ejecutar `docker exec Synap_app python manage.py test reports.tests.test_clientes_sin_ventas_relay` (verde).

## Fase 7: Documentación

- [x] 7.1 Marcar en `docs/ecom/DELTA_PHP_2026Q2.md` el informe como migrado (enlazar change + checkpoint).
- [x] 7.2 Nota breve en `docs/ecom/` (índice de informes migrados) si aplica.

---

## Mapeo requisito → tareas

| Requisito | Tareas |
|---|---|
| REQ-CSV-001 | 1.1, 1.5, 6.3 |
| REQ-CSV-002 | 1.5, 2.1, 6.4 |
| REQ-CSV-003 | 1.3, 2.2, 4.2 |
| REQ-CSV-004 | 1.2, 1.4, 2.1, 2.2, 6.1, 6.2, 6.4 |
| REQ-CSV-005 | 1.5, 4.2, 4.3, 6.3 |
| REQ-CSV-006 | 1.6, 4.2, 4.3, 6.3 |
| REQ-CSV-007 | 3.1, 4.1, 4.2, 5.1 |

## Archivos afectados

| Archivo | Cambio |
|---|---|
| `reports/services/clientes_sin_ventas.py` | Crear |
| `reports/clientes_sin_ventas_relay_views.py` | Crear |
| `reports/api_urls.py` | Modificar |
| `reports/views.py` | Modificar (get_template_names) |
| `reports/templates/reports/dashboard_clientes_sin_ventas_vendedor.html` | Crear |
| `reports/migrations/00XX_add_clientes_sin_ventas_report.py` | Crear |
| `reports/tests/test_clientes_sin_ventas_relay.py` | Crear |
| `docs/ecom/DELTA_PHP_2026Q2.md` | Modificar |

## Metadata
- **Próxima fase:** sdd-apply (implementación) — requiere confirmación del usuario.
