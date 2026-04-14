# Spec — Lista de comprobantes en rutas (informe legacy Reports)

## 1. Alcance

| Origen legado | Synap |
|---------------|--------|
| `mayoristapp/logistica_lista_comprobantes_rutas.php` | Vista **Reports:** `/reports/dashboard/comprobantes-rutas/` (`DashboardDetailView`). |
| `mayoristapp/relay-logistica-comprobantes.php` | **Lectura principal:** `POST /api/reports/query/` con `slug: comprobantes-rutas` y `filters` (mismo flujo que otros legacy). **Auxiliares:** endpoints bajo `reports` (autocomplete, detalle, POST entrega). |

En la vista **Reports**, al pulsar **Actualizar**, la UI usa el modal compartido de carga (`#reports-legacy-query-loading-modal` en `dashboard_detail.html`, mismo patrón que stock/BO/ventas netas) hasta completar la petición y el render de la tabla; el cliente aplica **timeout de red de 5 minutos** en este informe (consultas potencialmente pesadas).

**Objetivo de negocio:** listar remitos en contexto de **hoja de ruta** (join vía factura y `cliente_datos_adicionales`), filtrar por **período de fechas** (remito), cliente, ruta y **estado de entrega** (solo **Entregado** / **No entregado** en listado y filtros), ver **trazabilidad** pedido/factura/ruta/chofer, y **registrar o corregir** entrega sincronizando remito y pedido enlazado en `comp_ped`.

### 1.1 Alcance: funcionalidad adaptada, no réplica 1:1

La implementación **no** debe copiar la forma del PHP (HTML en JSON, DataTables, jQuery UI, nombres de query string, ni detalles UX defectuosos). Debe **cumplir el mismo contrato de negocio**:

- Mismas **reglas de inclusión** de remitos en el listado (relaciones y filtros equivalentes).
- Misma **lógica** de columnas `entregado` / `id_usuario_no_entrega` en BD; en UI el listado muestra solo **Entregado** o **No entregado** (sin tercer estado «Sin datos»). La acción de guardar entrega sobre `comp_ped` conserva el contrato de negocio.
- **Libertad:** estructura de `filters` y de filas en `data`, componentes de UI, textos, orden de columnas, agrupación, caché, paginación y formato de export, siempre que no contradigan la lógica anterior.

---

## 2. Sesión, permisos y MySQL (igual que Synap hoy)

### 2.1 Sesión y usuario

- **Vista web:** `ReportsLoginRequiredMixin` (`reports/views.py`): exige `request.session['user']` y usuario autenticado (AdministraNET), redirección a `login:login` si falta.
- **API:** `ReportQueryAPIView` y vistas auxiliares de este informe usan **`OperationalReportsPermission`** y/o **`ManagerialReportsPermission`** según `ReportDefinition.category` (este informe será **operational**).
- **`base_empresa`:** la API de consultas inyecta `payload['filters']['base_empresa']` desde `request.session['user']['base_empresa']` (mismo código que informes actuales en `reports/api_views.py`). El runner debe leer el tenant desde ese filtro / `_get_tenant_id` como el resto de legacy.

### 2.2 Conexión MySQL

- **Única vía** alineada al módulo Reports: `from reports.services.connection_pool import get_mysql_pool` (equivale a `core.mysql_pool.get_mysql_pool`).
- Obtener conexión con el **`base_empresa`** del payload/sesión: `with pool.get_connection(base_empresa) as conn:` (mismo patrón que `ReportExecutionEngine` y ramas legacy de `query_runner`).
- No abrir conexiones MySQL paralelas con otro stack solo para este informe.

### 2.3 ReportDefinition

- **Slug:** `comprobantes-rutas` (kebab-case, coherente con `mayoristapp-estado-pedidos-preparacion` en catálogo).
- **config:** JSON legacy (sin `version: declarative-v1`); puede incluir flags para el builder/schema mínimo o dejarse `{}` si la UI es 100 % custom en template/JS.
- **Catálogo:** incluir en la lista de slugs legacy de `reports/services/catalog_service.py` para sección **comprobantes** (`_LEGACY_COMPROBANTES_SLUGS`).

---

## 3. Reglas de negocio (equivalentes al legado)

Referencia técnica: `relay-logistica-comprobantes.php` / `listadoComprobantes`. En Synap el SQL puede refactorizarse (CTEs, alias claros) si el **resultado conjunto de filas** y las **condiciones de negocio** son equivalentes para los mismos datos.

### 3.1 Restricción por usuario (sesión)

Si en el legado `supervisor_venta == 'No'`, se filtra por `chofer.id_usuario = <usuario sesión>`.

- En Synap: aplicar la **misma regla** leyendo de `request.session['user']` / usuario autenticado. Si en Synap el flag tiene otro nombre, documentar el mapeo; la intención de negocio es «no supervisor de ventas solo ve lo asociado a su usuario en chofer».

### 3.2 Filtros del listado

Criterios que deben comportarse **igual en negocio** que en PHP:

- Rango de fechas sobre `remito.Fecha` cuando **ambas** fechas están informadas (`BETWEEN`).
- `estado` vacío (sin filtro) / `Si` (entregado) / `No` (no entregado: cualquier `entregado = 'No'`).
- Filtros por cliente y por ruta cuando se envían IDs.

**Adaptación Synap:** no se expone búsqueda por número de comprobante en el formulario de filtros; el listado se acota por período de fechas del informe.

### 3.3 Listado SQL, autocomplete, detalle, guardado

- **Listado:** joins y condiciones base equivalentes (`rem_fact`, `comp_ped` remito/pedido, `rem_ped`, factura, ruta, cliente, chofer, usuarios). Orden de presentación puede alinearse al producto (p. ej. por fecha descendente como hoy).
- **Autocomplete:** mismo universo de clientes activos y hojas de ruta no anuladas; límites y texto mostrado pueden mejorarse.
- **Detalle remito:** misma información de negocio (trazabilidad, ruta, totales, estado entrega).
- **Guardar entrega:** misma **persistencia** transaccional en remito y pedido; timestamps y usuario de no entrega según política Synap (p. ej. hora servidor) siempre que el resultado en BD sea coherente con el flujo actual.

### 3.4 Qué no hace falta replicar

- Respuesta JSON con campo `html` de tabla.
- DataTables, jQuery UI, SweetAlert con mismos textos/códigos.
- Logs SQL a archivo en disco.
- Comportamiento de vaciar fechas al hacer focus en el input.
- Selectores o títulos de export basados en nodos DOM inexistentes en el PHP actual.

---

## 4. Contratos API Synap

### 4.1 Listado (estándar Reports)

- **Método / ruta:** `POST /api/reports/query/`  
- **Cuerpo:** `ReportQueryRequestSerializer`: `{ "slug": "comprobantes-rutas", "filters": { ... } }`  
- **Respuesta:** `ReportQueryResponseSerializer` sobre `QueryResult` (`meta`, `data`, `totals`, `notes`). El front del dashboard consumirá `data` como filas para tabla agrupada y export.

### 4.2 Endpoints dedicados (propuesta)

Rutas bajo `reports/api_urls.py` (prefijo según proyecto, típicamente `/api/reports/…`):

| Método | Ruta sugerida | Uso |
|--------|---------------|-----|
| GET | `logistica/lista-comprobantes-rutas/clientes/autocomplete/` | `q` (mín. 2 caracteres) → `{ "results": [ { "id": Codigo, "text": nombre } ] }` — alimenta el filtro **Cliente** (patrón tags como Estado entrega) |
| GET | `logistica/lista-comprobantes-rutas/remito/<cod_mov>/` | Detalle modal |
| POST | `logistica/lista-comprobantes-rutas/entrega/` | JSON cuerpo entrega |

**Permisos:** mismas clases que `ReportQueryAPIView` para informes operativos (lectura/escritura acotada a quien ya puede abrir el dashboard del slug).  
**Sesión:** `base_empresa` e identidad de usuario desde `request.session['user']` para filtros y `id_usuario_no_entrega`.

### 4.3 Tipos AdministraNET

Escritura: `core.utils.administranet_types` (`str_or_default`, `to_int_or_none`, etc.).

---

## 5. UI/UX (diseño Synap, no copia visual PHP)

- **Plantilla:** `dashboard_detail.html` + partial dedicado; filtros y tabla acordes al **design system** de informes (tipografía, espaciado, modo oscuro si aplica).
- **Interacción:** agrupación de filas, búsqueda en tabla, autocompletado accesible, modales nativos del stack Synap; no es requisito imitar modales/CSS del mayoristapp.
- **Look:** coherente con otros informes operativos (cabecera «Foco operativo», Actualizar, Exportar Excel / tiempo real si el producto los habilita para este slug).
- **Modal detalle (trazabilidad):** la sección «Trazabilidad» lista Pedido → Factura → Remito y, como **último paso**, el resultado de **Entrega** en destino: si está entregado, fecha y hora (`fechaHoraEntregaB` / `fecha_hora_entrega`); si no entregado, estado y motivo. La cabecera del modal solo muestra el badge de estado (sin duplicar fecha/motivo bajo el título). En cada documento se muestra **fecha y hora de alta** cuando existe: pedido y remito desde `comp_ped.fecha_control` (parseo en Python a `fechaHoraPedidoB` / `fechaHoraRemitoB`, sin `DATE_FORMAT` con `%` en el SQL del detalle: MySQLdb interpola `%s` con `query % args` y rompe los literales `%d/%m`); factura desde `cuentacliente.FechaControl` en Python (`fechaHoraFacturaB`). Fechas solo día (`Fecha*B`) desde columnas `Fecha` vía `_enriquecer_respuesta_detalle_remito` en `logistica/services/lista_comprobantes_rutas.py`.

---

## 6. Seguridad

- Consultas parametrizadas; mejorar frente al legado donde hubo concatenación insegura.  
- POST entrega: validar permisos operativos y coherencia de `base_empresa`.  
- No exponer datos de otras bases empresas.

---

## 7. Referencias

- Inventario: `docs/general/INVENTARIO_FORMULARIO_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`  
- Plan: `docs/ecom/PLAN_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`  
- Tests: `docs/ecom/TEST_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`  
- Pool: `core/mysql_pool.py`, `reports/services/connection_pool.py`  
- API consulta: `reports/api_views.py` (`ReportQueryAPIView`)  
- Relay índice: `docs/ecom/MAYORISTAPP_RELAYS.md`
