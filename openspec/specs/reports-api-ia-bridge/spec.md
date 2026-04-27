# Especificación: API de reportes (puente consumo IA)

> Promovido desde el cambio `mapeo-endpoints-reportes-ia` (archivado el 27/04/2026). Fuente de verdad en `openspec/specs/reports-api-ia-bridge/`.

## Purpose

Contrato observable de las rutas REST bajo `/api/reports/` para acotar filtros, permisos y parámetros frente a agentes y documentación (qué expone la API, no cómo lo implementan los runners).

## Requirements

### Requirement: Prefijo de URL

El sistema **SHALL** publicar los endpoints HTTP del módulo `reports` bajo el prefijo `/api/reports/` (inclusión en `django_project`).

#### Scenario: Base común

- DADO un cliente de la API de reportes
- CUANDO resuelva rutas de este documento
- ENTONCES **SHALL** usar `/api/reports/` como prefijo.

### Requirement: Consulta parametrizada (`POST /api/reports/query/`)

El cuerpo **MUST** incluir `slug`. Opcionales: `date_from`, `date_to`, `metrics`, `dimensions`, `filters`, `group_by`, `limit`. El sistema **MAY** inyectar `filters.base_empresa` desde la sesión del usuario cuando exista. El acceso **MUST** cumplir permisos **Operational** o **Managerial** según el tipo del reporte; sin el permiso adecuado el usuario **SHALL NOT** obtener datos.

#### Scenario: Consulta permitida

- DADO un usuario autenticado con permiso al tipo del reporte y sesión con `base_empresa` si aplica
- CUANDO envíe un cuerpo válido a `POST /api/reports/query/`
- ENTONCES **SHALL** recibir resultado estructurado (meta, datos, totales, notas) o error HTTP si falla la ejecución.

#### Scenario: Sin permiso de tipo

- DADO un usuario sin permiso operacional o gerencial requerido por el reporte
- CUANDO invoque `POST /api/reports/query/`
- ENTONCES **SHALL** responder denegación (p. ej. 403).

### Requirement: Catálogo (`GET /api/reports/catalog/`)

El sistema **SHALL** listar reportes visibles para el usuario autenticado según empresa y reglas de catálogo.

#### Scenario: Listado

- DADO un usuario autenticado
- CUANDO solicite `GET /api/reports/catalog/`
- ENTONCES **SHALL** recibir entradas con metadatos (slug, nombre, categoría, métricas, dimensiones, etc.).

### Requirement: Filtros auxiliares (`GET /api/reports/filters/`)

Parámetro obligatorio `type` con valores **SHALL**: `puntos_venta`, `sucursales`, `cajas`, `clientes`, `depositos`, `marcas`, `rubros`, `subrubros`, `viajantes`. **SHALL** existir `base_empresa` en sesión; si no, **SHALL** responder 400 indicando que no se pudo determinar la base de datos de la empresa.

#### Scenario: Con sesión de empresa

- DADO sesión con `base_empresa`
- CUANDO `GET /api/reports/filters/?type=...` con tipo permitido
- ENTONCES **SHALL** recibirse opciones para ese tipo.

#### Scenario: Sin base_empresa

- DADO sesión sin `base_empresa` utilizable
- CUANDO se llame a `GET /api/reports/filters/`
- ENTONCES **SHALL** aplicarse el 400 descrito.

### Requirement: Esquema (`GET /api/reports/<slug>/schema/`)

El sistema **SHALL** devolver el esquema del reporte (métricas, dimensiones, widgets, opciones) con las mismas reglas de permisos operacional/gerencial que la consulta.

#### Scenario: Lectura

- DADO permisos válidos y `slug` activo
- CUANDO se solicite el esquema
- ENTONCES **SHALL** devolverse el documento o error de servidor si no se puede generar.

### Requirement: Exportación (`POST /api/reports/export/`)

El cuerpo **SHALL** ser el mismo que en `query`. Query param `type` (formato; default según implementación). Permisos **SHALL** coincidir con `query`.

#### Scenario: Export

- DADO usuario y payload de consulta válidos
- CUANDO `POST /api/reports/export/?type=...`
- ENTONCES **SHALL** entregarse fichero de descarga o error.

### Requirement: Claves en `filters`

Las claves de `filters` **SHALL** definirse por cada reporte y runner, no en este spec. **SHOULD** documentarse aparte (seguimiento) slugs de alto tráfico y claves frecuentes.

#### Scenario: No catálogo global

- DADO un consumidor del API
- CUANDO arme `filters` para un slug
- ENTONCES **SHALL** apoyarse en esquema, doc por reporte o convención de ese reporte.

### Requirement: (Opcional) Otras rutas bajo el mismo prefijo

**SHOULD** considerarse para ampliar el agente: resumen ejecutivo, relays ventas netas, reconciliación de movimientos (p. ej. `id_art`, `tipo`, `fecha_desde`, `fecha_hasta`), `builder/reference-values`. Detalle **MAY** diferir; **SHALL** ampliarse en documentación futura.

#### Scenario: Inventario mínimo

- DADO un plan de herramientas del agente
- CUANDO se prioricen integraciones
- ENTONCES estas rutas **SHOULD** listarse brevemente antes de contratos finos.
