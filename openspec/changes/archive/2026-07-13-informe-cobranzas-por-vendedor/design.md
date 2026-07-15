# Design: Informe cobranzas por vendedor

**Change:** `informe-cobranzas-por-vendedor`
**Spec:** [specs/reports-cobranzas-vendedor/spec.md](./specs/reports-cobranzas-vendedor/spec.md)
**Patrón de referencia:** `informe-clientes-sin-ventas-vendedor` (servicio + relay + ReportDefinition + template dedicado).

## Componentes

### 1. Servicio `reports/services/cobranzas_vendedor.py` (nuevo)
- `get_cobranzas_vendedor(base_empresa, *, fecha_desde, fecha_hasta, cod_viajante, modo="mes") -> dict`
  - `cod_viajante`: `int` (restringe) o `None` (todos). La vista resuelve permisos.
  - `modo`: `"mes"` | `"totalizado"`.
  - SQL parametrizado sobre `cuentacliente`:
    - `WHERE TipoComprobante IN ('REC','FA','FB','FM','FE','FC') AND Fecha BETWEEN %s AND %s AND CodigoMovimiento<>0 AND Anulado='No' AND CondVenta IN ('Contado','-')` + (`AND CodViajante=%s` si `cod_viajante`).
    - Agregados: efectivo/dolar/cheque/transferencia/percepcion/total (ver REQ-COB-003), con `SUM(CASE WHEN TipoComprobante='REC' THEN ... ELSE ... END)`.
    - `modo=mes`: `SELECT YEAR(Fecha) AS aaaa, MONTH(Fecha) AS m, CONCAT(YEAR,LPAD(MONTH,2,'0')) AS periodo, ... GROUP BY aaaa, m ORDER BY aaaa, m`.
    - `modo=totalizado`: sin dimensión de mes, `GROUP BY CodViajante` (una fila agregada); etiqueta `"dd/MM/yyyy al dd/MM/yyyy"`.
  - Devuelve `{columns, filas, totales, modo}` donde:
    - `columns`: `["Período","Efectivo","Dólares","Cheques","Transferencias","Percepciones","Total"]`.
    - `filas`: lista de dicts `{periodo, ordenPeriodo, efectivo, dolar, cheque, transferencia, percepcion, total}` (montos `float` para JSON).
    - `totales`: dict con la suma por columna (pie).
  - Meses en español vía diccionario 1..12 (no depende de locale del contenedor).

### 2. Relay `reports/cobranzas_vendedor_relay_views.py` (nuevo)
- `CobranzasVendedorRelayAPIView` (`OperationalReportsPermission`): fuerza `cod_viajante = id_vendedor_usr` de sesión; ignora `codViajante` entrante (anti-bypass). 403 si no hay `id_vendedor_usr`.
- `CobranzasVendedorGerenciaRelayAPIView` (`ManagerialReportsPermission`): `codViajante=<int>` restringe; `todos`/ausente → `None`.
- Ambas: 400 si faltan fechas; `modo` desde `tipo`/`modo` (`0`→mes, `1`→totalizado, o `mes`/`totalizado`). Helpers de sesión/fecha reutilizados del patrón (se pueden duplicar mínimamente o extraer).

### 3. Rutas `reports/api_urls.py`
- `cobranzas-vendedor/relay/` → operativo (`reports-cobranzas-vendedor-relay`).
- `cobranzas-vendedor/relay/gerencia/` → gerencial (`reports-cobranzas-vendedor-relay-gerencia`).

### 4. UI canónica
- Slug `cobranzas-por-vendedor` en `DashboardDetailView.get_template_names` → `reports/dashboard_cobranzas_por_vendedor.html`.
- Contexto: `cobranzas_api_url` (gerencia si permiso managerial, si no operativo) y `cobranzas_scope`.
- Template extends `base_app.html`: filtros período (`filters_period.html`), selector vendedor (solo visible/efectivo para gerencial; operativo fijo), tabla con pie de totales, gráfico de barras por período (CSS/Chart) y buscador. Fetch a la relay API. Montos es-AR.

### 5. `ReportDefinition` `reports/migrations/0034_add_cobranzas_vendedor_report.py`
- `update_or_create(slug="cobranzas-por-vendedor", empresa=None, category="operational", metadata{catalog_legacy_section:"listados", catalog_legacy_order:60}, config{filters})`, guarda de tabla + `reverse`.
- `EcomMigrationCheckpoint(module_slug="mayoristapp_informe_cobranzas_vendedor")` (cross-app, dependency a ecom).

## Decisiones

- **Operativo vs gerencial:** dos endpoints (igual que clientes-sin-ventas) para evitar bypass.
- **Selector de vendedor:** el operativo no necesita autocomplete (scope fijo); el gerencial lista vendedores. Para simplicidad se reutiliza `listado_vendedores_seleccion` de `clientes_sin_ventas` (misma consulta `viajantes` `Anulado='No'`) o se agrega un modo `seleccion`. Se opta por reutilizar el helper existente para no duplicar SQL.
- **Solo lectura:** sin hooks de commit.

## Test plan

- Servicio (mock cursor): SQL parametrizado (fechas, IN comprobantes, CondVenta), agregados REC vs factura, modo mes vs totalizado, totales del pie, meses en español.
- Relay: 400 sin fechas; operativo fuerza scope propio (ignora codViajante); gerencial filtra/ve todos; 403 sin id_vendedor_usr.
- `docker exec Synap_app python manage.py test reports.tests.test_cobranzas_vendedor_relay`.
