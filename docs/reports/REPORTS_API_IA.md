# API de reportes para integración con IA (`/api/reports/`)

Este documento describe los endpoints HTTP expuestos por el módulo Django `reports` bajo el prefijo **`/api/reports/`** (definidos en `reports/api_urls.py` e incluidos desde `django_project/urls.py`). Sirve de inventario para el **Asistente de Reportes** y otros consumidores; el comportamiento normativo (OpenSpec) está en **`openspec/specs/reports-api-ia-bridge/spec.md`**. El histórico del cambio SDD quedó en **`openspec/changes/archive/2026-04-27-mapeo-endpoints-reportes-ia/`**.

En el despliegue actual, el agente en Synap ejecuta consultas vía **`ReportToolsService` → `QueryRunnerService`** (sin HTTP interno). Las reglas de permisos y payload deben **alinearse** con las descritas aquí para el mismo usuario y sesión.

## Permisos (referencia rápida)

| Clase (DRF) | Código de permiso |
|---------------|---------------------|
| `OperationalReportsPermission` | `reports.view_operational` |
| `ManagerialReportsPermission` | `reports.view_managerial` |
| `BuilderReportsPermission` | `reports.builder` |

Varias vistas combinan permisos operacional **o** gerencial con `OperationalReportsPermission | ManagerialReportsPermission` (el reporte concreto se valida según categoría del `ReportDefinition`).

## Núcleo: consulta, catálogo, filtros, esquema, exportación

| Método | Ruta | Permisos / notas | Parámetros / cuerpo |
|--------|------|------------------|---------------------|
| GET | `/api/reports/catalog/` | **`IsAuthenticated`** (por defecto DRF; la vista no añade permisos por tipo de reporte). Catálogo vía `build_catalog_for_user`. | Sin query. |
| POST | `/api/reports/query/` | Operacional **o** gerencial; además el tipo del reporte debe coincidir | **JSON:** `slug` (obligatorio), `date_from`, `date_to`, `metrics[]`, `dimensions[]`, **`filters`** (objeto libre por reporte), `group_by[]`, `limit` (default 5000). La vista puede inyectar `filters.base_empresa` desde la sesión. |
| GET | `/api/reports/kpi/` | Operacional **o** gerencial | Query: `slug`, opcional `unit`. (Implementación actual devuelve payload simplificado.) |
| POST | `/api/reports/export/` | Igual que `query` | **JSON:** mismo cuerpo que `query`. Query: `?type=` (p. ej. `xlsx`, `pdf`). |
| GET | `/api/reports/filters/` | `IsAuthenticated` | Query obligatorio **`?type=`** con uno de: `puntos_venta`, `sucursales`, `cajas`, `clientes`, `depositos`, `marcas`, `rubros`, `subrubros`, `viajantes`. Requiere **`base_empresa`** en sesión (`user` de sesión); si no, **400**. |
| GET | `/api/reports/<slug>/schema/` | Operacional **o** gerencial | `slug` en path. |
| GET/POST/DELETE/PATCH | `/api/reports/workspace/` | `IsAuthenticated` | **GET:** slots del workspace. **POST:** `slug`, opcional `allow_duplicate`. **DELETE:** `item_key` o `slug`. **PATCH:** lista `items` u `order`. |
| POST | `/api/reports/visibility/` | Autenticado; solo supervisor (`user_has_full_access`) | JSON: `slug`, `is_visible`. |

### Claves dentro de `filters` (POST query / export)

No hay listado fijo en código: dependen de cada **`ReportDefinition`** y del runner declarativo (`execution_engine` / `query_runner`). Para un slug concreto, usar **`GET …/<slug>/schema/`** y la documentación del informe. El spec OpenSpec exige documentar aparte los slugs de **alto tráfico** cuando se formalicen.

## Paneles gerenciales y auxiliares

| Método | Ruta | Permisos | Parámetros |
|--------|------|----------|------------|
| GET | `/api/reports/executive-summary/` | `ManagerialReportsPermission` | Query opcional `fecha` (`YYYY-MM-DD`); por defecto fecha local del servidor. |
| GET, PUT | `/api/reports/pv-canal-ejecutivo/` | `ManagerialReportsPermission` | GET: lista PV + canal asignado. PUT: reemplazo de asignaciones mayorista/minorista (ver vista). |
| GET | `/api/reports/reconciliacion-movimiento-detalle/` | Operacional **o** gerencial | Query: **`id_art`** (int, obligatorio), **`tipo`**: `oc` \| `rem` \| `factoc` \| `anul`, `fecha_desde`, `fecha_hasta` opcionales. `base_empresa` desde sesión o usuario. |

## Relay ventas netas (paridad legacy)

| Método | Ruta | Permisos | Query (resumen) |
|--------|------|----------|-----------------|
| GET | `/api/reports/ventas-netas/relay/` | `OperationalReportsPermission` | `queInforme` / `que_informe`; si no es `seleccion`, **`fechaDesde`** y **`fechaHasta`** obligatorias (`YYYY-MM-DD`). También: `listarPor`, `tipo`, `filtrarPor` / `filtrar_por`, segundo rango (`rangoDoble`, `fechaDesdeDos`, `fechaHastaDos`, `opRango`), `grafico`, `ajax`. Sesión con `id_vendedor_usr` para filtro vendedor. |
| GET | `/api/reports/ventas-netas/relay/gerencia/` | `ManagerialReportsPermission` | Similar; admite **`puntoVenta`** / `punto_venta` (entero). |

## Logística — lista comprobantes en rutas

| Método | Ruta | Permisos | Parámetros / cuerpo |
|--------|------|----------|---------------------|
| GET | `/api/reports/logistica/lista-comprobantes-rutas/clientes/autocomplete/` | Operacional **o** gerencial | `?q=` mínimo 2 caracteres. |
| GET | `/api/reports/logistica/lista-comprobantes-rutas/remito/<cod_mov>/` | Idem | `cod_mov` en path (entero). |
| POST | `/api/reports/logistica/lista-comprobantes-rutas/entrega/` | Idem | JSON: `cod_mov_remito`, `cod_mov_pedido`, `entregado` (`Si`\|`No`), `motivo_no_entrega`, `detalle_no_entrega`. Sesión: `base_empresa`, `id_usuario`. |
| GET | `/api/reports/logistica/lista-comprobantes-rutas/motivos-no-entrega/` | Idem | Sin parámetros obligatorios (catálogo). |

## Builder, data-map y valores de referencia

Rutas bajo `/api/reports/builder/…` y `/api/reports/<slug>/builder/…` están orientadas al **Report Builder** (permiso **`reports.builder`** en la mayoría). Incluyen: configuración, preview, widgets, historial, rollback, datasources semánticos, joins, plantillas, export/import, `data-map`, validación y gobernanza de relaciones, clusters, etc.

Casos frecuentes para **opciones de filtro dinámico** en UI:

| Método | Ruta | Permisos | Query |
|--------|------|----------|--------|
| GET | `/api/reports/builder/reference-values/` | Operacional **o** gerencial **o** builder | **`table`** (obligatorio), `value_field` (default `id`), `display_field` (default `nombre`), `search`, opcional `base_empresa`. |
| GET | `/api/reports/builder/data-map/` | `BuilderReportsPermission` | `base_empresa`; filtros internos: `type`, `direction`, `depth`, `min_conf`, `status`, `hide_temp` (ver `DataMapAPIView`). |

Para el detalle de cada vista builder, inspeccionar **`reports/api_views.py`** (clases `ReportBuilder*`, `Builder*`, `DataMapAPIView`, etc.).

## Rutas HTML (no API)

Las vistas web bajo **`/reports/`** (`reports/urls.py`: catálogo, workspace, dashboards, builder) **no** forman parte de la API JSON descrita aquí.

## Pruebas manuales sugeridas

1. Sesión con `base_empresa` establecida: `GET /api/reports/filters/?type=puntos_venta` → lista de opciones.
2. Sin `base_empresa` en sesión: mismo GET → **400** con mensaje de empresa.
3. `POST /api/reports/query/` con `slug` autorizado y cuerpo mínimo → **200** o error de ejecución según datos.
4. Usuario sin `reports.view_managerial`: `GET /api/reports/executive-summary/` → **403**.

Comando de tests del proyecto (según `openspec/config.yaml`): `docker exec Synap_app pytest`.
