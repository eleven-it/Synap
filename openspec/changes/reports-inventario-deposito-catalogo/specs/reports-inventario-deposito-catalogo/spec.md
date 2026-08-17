# Spec: reports-inventario-deposito-catalogo

## Purpose

Publicar Inventario por depósito en el catálogo Reportes con UI propia, menú directo y redirect desde el hub MPR, sin cambiar reglas de negocio del motor MPR.

## Requirements

### Requirement: Alta en catálogo

El sistema MUST registrar `ReportDefinition` global con slug `inventario-deposito-articulo`, `category=operational`, `show_in_catalog=true`, tags `mpr`/`stock`/`listados`.

#### Scenario: Seed idempotente

- GIVEN la migración o `ensure_inventario_deposito_report()`
- WHEN se ejecuta dos veces
- THEN existe una sola definición activa con ese slug

### Requirement: Consulta vía QueryRunner

El sistema MUST ejecutar el informe vía `QueryRunnerService` envolviendo `consultar_inventario_deposito`, preservando fecha_corte, depósitos, marcas, q, incluir_2da (default OFF) y totales SUM(docenas).

#### Scenario: Payload de filtros

- GIVEN filters con `fecha_corte`, `depositos`, `marcas_incluidos`, `q`, `incluir_2da`
- WHEN POST `/api/reports/query/` con slug `inventario-deposito-articulo`
- THEN la respuesta incluye `data` (filas), `totals` (KPIs) y `meta.depositos_jerarquia`

### Requirement: Export Excel

El sistema MUST exportar Excel con columnas Depósito, Marca, Artículo, Talle, Stock, Docenas y fila TOTAL = SUM(docenas) vía `POST /api/reports/export/?type=xlsx`.

### Requirement: UI sin chrome de hub

La pantalla del slug MUST NOT mostrar tabs de grupo MPR, período Desde/Hasta del shell hub ni CTA Tablero de producción. MUST mostrar fecha de corte, filtros propios, KPIs y tabla jerárquica.

### Requirement: Menú y deep-link

El menú Reports MUST incluir ítem «Inventario por depósito» hacia el dashboard del slug. El menú MPR → Reportes MUST ofrecer el mismo deep-link (además del hub mientras exista).

### Requirement: Redirect hub

`GET /mpr/reportes/?grupo=demanda&reporte=inventario_deposito` MUST redirigir (302) a `/reports/dashboard/inventario-deposito-articulo/`.

### Requirement: Permisos OR

Usuarios con `reports.view_operational` OR `mpr.reportes` OR `mpr.ver` MUST poder abrir y consultar este slug. Otros informes del catálogo MUST NOT relajar su permiso por esta excepción.

### Requirement: No confundir con stock-existencias

El slug MUST permanecer distinto de `stock-existencias` (sin reemplazo).
