# Verify Report: Informe clientes sin ventas por vendedor

**Change:** `informe-clientes-sin-ventas-vendedor` · **Fecha:** 02/07/2026 · **Resultado:** ✅ APROBADO

## Verificación spec → implementación

| Requisito | Cubierto por | Estado |
|---|---|---|
| REQ-CSV-001 (definición sin ventas) | `get_clientes_sin_ventas` (LEFT JOIN período + `IS NULL`, excluye NCA/NCB/anulados, Estado='Activo', Codigo<>1) | ✅ test `test_formato_filas_y_resumen` |
| REQ-CSV-002 (fechas obligatorias/validadas) | `ValueError` en servicio + 400 en relay + `parse_date` | ✅ `test_fechas_obligatorias`, `test_operativo_sin_fechas` |
| REQ-CSV-003 (modo selección) | `listado_vendedores_seleccion` + modo `seleccion` en relay | ✅ `test_seleccion_restringida`, `test_seleccion_devuelve_lista` |
| REQ-CSV-004 (permisos + anti-bypass + anti-SQLi) | `resolver_cod_viajantes` (op/gerencia) + `parse_filtrar_por` + params `%s` | ✅ `test_operativo_anti_bypass_filtro_ajeno`, `test_gerencia_respeta_filtro`, `test_descarta_no_numerico_e_inyeccion`, `test_sql_parametrizado_fechas` |
| REQ-CSV-005 (columnas/última compra/domicilio) | `_armar_filas`, `_fmt_fecha_ddmmaaaa`, `campo_id`, `campo_domicilio` | ✅ `test_formato_filas_y_resumen`, `test_incluir_domicilio_anexa_al_nombre` |
| REQ-CSV-006 (resumen vendedor/global) | `_resumen_por_vendedor`, `modoTodosVendedores` | ✅ `test_formato_filas_y_resumen` |
| REQ-CSV-007 (informe canónico) | ReportDefinition `clientes-sin-ventas-vendedor` + slug en `get_template_names` + template | ✅ rutas resuelven, migración aplicada, template compila |

## Comandos ejecutados

- `docker exec Synap_app python manage.py test reports.tests.test_clientes_sin_ventas_relay` → **Ran 18 tests — OK**
- `docker exec Synap_app python manage.py check` → **0 issues**
- `docker exec Synap_app python manage.py migrate reports` → **0032 applied OK**
- Rutas: `/api/reports/clientes-sin-ventas/relay/`, `.../gerencia/`, `/reports/dashboard/clientes-sin-ventas-vendedor/` resuelven.
- Template `dashboard_clientes_sin_ventas_vendedor.html` compila.

## Pendiente (fuera de este change)

- Paridad numérica fina contra BD real (validación operativa Fase D).
- Verificación visual E2E con sesión real (login + permisos) — recomendada antes de release.

## Constraints cumplidos

- SQL 100% parametrizado (sin concatenar entrada de usuario). ✅
- Tipos AdministraNET (`core.utils.administranet_types`). ✅
- Conexión legacy vía `core.mysql_pool`. ✅
- UI canónica reports (no `ventas/`). ✅
- Español + fechas dd/MM/yyyy. ✅
