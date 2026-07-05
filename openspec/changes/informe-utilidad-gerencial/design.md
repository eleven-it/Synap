# Design: Informe utilidad gerencial

**Change:** `informe-utilidad-gerencial`
**Spec:** [specs/reports-utilidad-gerencial/spec.md](./specs/reports-utilidad-gerencial/spec.md)
**Decisión:** servicio **dedicado** `reports/services/utilidad_gerencial.py` (la lógica de costo/NC/% e inflación difiere de `ventas_netas`; no se modifica el relay de ventas netas existente).

## Componentes

### 1. Servicio `reports/services/utilidad_gerencial.py` (nuevo)
- `get_utilidad_gerencial(base_empresa, *, fecha_desde, fecha_hasta, listar_por="cliente", filtros=None, punto_venta_id=None, vendedor_id=None, vendedor_a_cargo=None, con_inflacion=False, tipo_inflacion=None) -> dict`.
- **Config de dimensiones** (`_DIMENSIONES`): por cada `listar_por` → `cod_expr`, `nom_expr`, `group_col`, `order_col`, `filter_col`, `nc_col` (solo cliente/tipocliente/vendedor/zona), `article_level` bool.
- **Query principal** (FROM `stock st` + JOINs cuentacliente/articulo/rubro/categoria/subrubro/marca/proveedor/cliente/viajantes/zona/tipo_cliente):
  - Sumas con signo por `st.TipoComp`: Venta=`±PrecioVentaxR`, Neto=`±PrecioNetoxR`, Costo=`±PrecioCostoxR`, Utilidad=`±(PrecioNetoxR-PrecioCostoxR)`. En inflación cada suma se envuelve con guarda de fecha rango1 y se agrega `Neto2` (rango2).
  - WHERE: `Anulado='No'`, `visualiza_ensamble='No'`, `TipoComp IN (...)`, rango(s) de fecha, filtros por dimensión, punto de venta, scope de vendedor. `GROUP BY group_col`.
- **NC/Desc** (`_consultar_nc`): solo si `nc_col` definido y sin filtros de nivel artículo. SQL sobre `cuentacliente` (+cliente/viajantes/zona/tipo_cliente) con el `CASE` de devolución/ND/NC/factura y `concepto_nd<>'Anulacion NC - Mercaderia'`, `GROUP BY nc_col` → dict `cod→importe`.
- **Índice inflación** (`_consultar_indice`): `AVG(PrecioCostoxU rango1)/AVG(PrecioCostoxU rango2)` `GROUP BY group_col` → dict `cod→indice` (default 1.0).
- **Post-proceso** por fila: `desc`, `venta_neta=Neto+desc`, `utilidad=Utilidad+desc`, `utilidad_pct=(Neto+desc)/Costo|0`; en inflación `venta_ant`, `desc_ant`, `indice`, `venta_esp`, `resultado`.
- Devuelve `{columns, filas, totales, meta}` (montos `float`).
- `tipo_inflacion`: `mensual` desplaza el mismo lapso; `anual` resta 1 año (helpers de fecha con `dateutil`/`timedelta`).

### 2. Relay `reports/utilidad_gerencial_relay_views.py` (nuevo)
- `UtilidadGerencialRelayAPIView` (`OperationalReportsPermission`): fuerza `vendedor_id` de sesión (anti-bypass).
- `UtilidadGerencialGerenciaRelayAPIView` (`ManagerialReportsPermission`): sin forzar; `vendedor_a_cargo` si supervisor.
- Ambas: `queInforme=seleccion` → reutiliza `listado_seleccion_ventas_netas`/`listado_filtros_estadisticas` para poblar filtros. Parseo de `filtrarPor`/`pvSelec`, fechas obligatorias (400), `con_inflacion` desde `queInforme=uti` o `modo=inflacion`.

### 3. Rutas `reports/api_urls.py`
- `utilidad-gerencial/relay/` y `utilidad-gerencial/relay/gerencia/`.

### 4. UI canónica
- Slug `utilidad-gerencial` en `DashboardDetailView` → `reports/dashboard_utilidad_gerencial.html`.
- Filtros: período, dimensión (Listar), punto de venta, filtro por tipo+valor, toggle inflación (tipo mensual/anual). Tabla con columnas dinámicas (Venta/Desc/Venta Neta/Costo/Utilidad/Utilidad %, + inflación), pie de totales, montos es-AR, Utilidad % como porcentaje.

### 5. Migración `reports/migrations/0035_add_utilidad_gerencial_report.py`
- `ReportDefinition` slug `utilidad-gerencial`, `category=managerial`, metadata `catalog_legacy_section=gerenciales`, `catalog_legacy_order=10` + checkpoint `mayoristapp_informe_utilidad_gerencial`.

## Decisiones
- **cod de cliente**: usar `cli.Codigo` como clave (aunque `usa_id_manual`), para que el match con NC (keyed por `cc.Codigo`) sea correcto; el id manual va en el nombre.
- **Período**: v1 agrega sobre el rango (sin pivote por mes), coherente con `controlarFechas` (~1 mes).
- **Solo lectura**: sin hooks de commit.

## Test plan
- Servicio (mock cursor): signo por TipoComp (devolución resta), Costo=PrecioCostoxR, Utilidad %, NC aplica cliente / no aplica artículo, dimensiones, inflación (índice, venta_esp, resultado, Costo/denominador 0).
- Relay: 400 sin fechas; operativo fuerza vendedor propio; gerencial ve todos; 403 operativo sin CodViajante.
- `docker exec Synap_app python manage.py test reports.tests.test_utilidad_gerencial_relay`.
