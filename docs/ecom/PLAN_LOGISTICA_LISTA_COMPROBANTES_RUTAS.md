# Plan de migración — Lista de comprobantes en rutas (informe legacy en Reports)

**Origen:** `mayoristapp/logistica_lista_comprobantes_rutas.php` + `mayoristapp/relay-logistica-comprobantes.php`.  
**Destino Synap:** módulo **`reports`** como **reporte legacy** (mismo patrón que `pedidos-pendientes`, `ventas_netas`, BO, etc.), no como vista/API de `ecom`.  
**Checkpoint / vertical:** `mayoristapp_logistica` (cierre documentado en `MAYORISTAPP_RELAYS.md`).  
**Fecha:** 2026-04-09.  
**Actualización:** 2026-04-09 — alineación a sesión y permisos de Reports + pool MySQL unificado.  
**Actualización:** 2026-04-09 — **no es migración 1:1** con PHP; es **funcionalidad adaptada a Synap** con lógica de negocio preservada.  
**Actualización:** 2026-04-11 — **Sin KPI de suma total de remitos** en el bloque «Resumen» del dashboard; el importe sigue visible por fila y en subtotales al agrupar.  
**Actualización:** 2026-04-12 — **Estado de entrega** unificado a dos valores en tabla, filtros y agrupación: **Entregado** / **No entregado**; listado solo por **período de fechas** (sin «Buscar por» número).  
**Actualización:** 2026-04-12 — Catálogo de motivos en MySQL (`logi_motivo_no_entrega`, DDL en `docs/general/sql/logi_motivo_no_entrega.sql`); APIs `motivos-no-entrega` devuelven `motivos` + `motivos_catalogo` (`requiere_detalle`, `visible_portal`); respaldo código `MOTIVOS_NO_ENTREGA` si la tabla no existe. Portal cliente: `docs/ecom/PORTAL_CLIENTE_LOGISTICA_PREP.md` + `logistica.portal_compat`.  
**Actualización:** 2026-04-09 — Módulo **Logística → Entregas**: filtros **Ruta** (valor por defecto guardado en sesión Django `logistica_entregas_id_ruta`) y **Chofer** (solo si `permiso_supervisor_venta` ≠ `No`); catálogo `GET …/catalogos/`; sin botón ni modal de detalle en la pantalla (solo «Registrar entrega»).  
**Actualización:** 2026-04-09 — Combo **Ruta** en Entregas: solo rutas asignadas al chofer vía `logi_ruta_chofer` con al menos un remito **no entregado** en el listado operativo; si el usuario es supervisor y filtra por chofer, `GET …/catalogos/?id_chofer=…`; si no es supervisor, se usan los `id_chofer` vinculados al usuario (`logi_abm_chofer.id_usuario`). Si la ruta guardada en sesión deja de figurar en el catálogo, se limpia la sesión.  
**Actualización:** 2026-04-09 — El catálogo de rutas **no** filtra `logi_hoja_ruta.anulado`, para alinear con el SQL del listado principal (si no, el combo podía quedar vacío con remitos visibles en pantalla).  
**Actualización:** 2026-04-09 — Entregas: si el usuario tiene fila en ``logi_abm_chofer`` (vínculo `id_usuario`), no se muestra el combo de chofer y rutas/listado usan siempre esos `id_chofer`; el filtro opcional por chofer queda solo para supervisores de ventas **sin** vínculo en ABM chofer. El listado Entregas envía ``logistica_contexto_entregas`` para no alterar el informe Reports.  
**Actualización:** 2026-04-13 — UI Entregas: selector de ruta como **modal** táctil (no dropdown visible); «Mi ruta» envía siempre ``estado=No`` (solo no entregados); «Hoy» no filtra por estado (todos); etiquetas Entregado / No entregado más grandes en tarjetas.  
**Actualización:** 2026-04-13 — SQL catálogo de rutas (``listar_rutas_catalogo_entregas``): la correlación ``cda.id_ruta = h.id_ruta`` va en el ``WHERE`` del ``EXISTS``, no en el ``ON`` del join a ``cliente_datos_adicionales``; en MySQL 5.7/8.0 la forma anterior producía error 1054 ``Unknown column 'h.id_ruta' in 'on clause'`` y la API ``/catalogos/`` respondía 500.  
**Actualización:** 2026-04-13 — Listado compartido: columnas ``nombre_cliente`` y ``direccion_entrega`` (``cliente_domicilio`` vía ``cliente_datos_adicionales`` **de la factura** ``fact_ruta`` → ``id_cliente_domicilio``, como en VB6 ``Logi_Gestion``/``Remito`` al unir ``cliente_domicilio``; en segundo término pedido y remito, más ``tpv_domicilio_ocasional``); pantalla Entregas muestra nombre sin código y dirección en la misma línea; no muestra chofer ni ruta en la tarjeta.  
**Actualización:** 2026-04-09 — Módulo **Logística → Entregas** (API `/logistica/api/entregas/`): no expone importes (`total_remito`, totales pedido/factura/remito en detalle); la UI no muestra montos en tarjetas ni en trazabilidad del modal (el chofer no debe ver el valor de la carga). El informe Reports **comprobantes-rutas** mantiene importes para uso administrativo.  
**Actualización:** 2026-04-09 — Listado y detalle enriquecidos con datos AdministraNET de **programación de ruta**: `orden_ruta` (secuencia de paradas), `fecha_salida` formateada como salida programada, franja `hora_desde`–`hora_hasta` en `ventana_horaria_ruta`; **choferes** agregados con `GROUP_CONCAT` para evitar filas duplicadas por varios choferes por ruta; filtro por usuario chofer vía `EXISTS`; `ORDER BY` por fecha de salida de ruta, `id_ruta`, `orden_ruta`, luego remito.  
**Actualización:** 2026-04-12 — Filtro **Cliente**: mismo patrón que **Estado entrega** (tags, búsqueda predictiva, desplegable, chips removibles); opciones dinámicas con `GET …/clientes/autocomplete/`; payload `logistica_id_cliente` (uno o varios códigos) y etiquetas para persistencia. **No** hay filtro dedicado por hoja de ruta en esta pantalla; la columna **Hoja de ruta** sigue en **Agrupar por** sobre la tabla.

---

## 0. Principio de migración (negocio sí, forma no)

| Se preserva (lógica de negocio) | Se adapta libremente (Synap) |
|----------------------------------|------------------------------|
| Qué datos entran en el listado (joins, tablas, condiciones de anulación, vínculo remito–pedido–factura–ruta). | Forma del API (JSON estándar Reports, no HTML embebido ni mismos nombres de parámetros GET que PHP). |
| Significado de filtros (fechas, nº comprobante, cliente, ruta, estado entrega) y regla supervisor/viajante. | UX: componentes Tailwind, tabla agrupada, autocompletes sin jQuery UI, flujo de modales accesible. |
| Efecto de **registrar entrega** (UPDATE en `comp_ped` remito + pedido, transacción, campos relevantes). | Validaciones UX (mensajes, orden de pasos, eliminar campos muertos del PHP como chofer obligatorio si no aplica). |
| Motivos de no entrega como conjunto de opciones de negocio (misma lista salvo decisión explícita de negocio). | Exportación: un solo mecanismo coherente con reportes (p. ej. Excel/CSV Synap), sin replicar DataTables+PDF si el producto no lo exige. |

**No se busca:** misma pantalla, mismos endpoints, mismo SQL byte a byte ni reproducir bugs del legado (p. ej. fechas que se vacían al focus).  
**Sí se busca:** un usuario de logística obtiene el **mismo resultado operativo** que en mayoristapp para los mismos datos y filtros.

---

## 1. Objetivo

Reemplazar la pantalla PHP por un informe Synap que:

1. **Preserve la lógica de negocio** del dominio: criterio de listado, filtros, restricción por supervisor/viajante, actualización de entrega en `comp_ped` (remito y pedido vinculado) y consulta de detalle.
2. **Integre el módulo Reports:** catálogo, `DashboardDetailView`, API `POST /api/reports/query/`, permisos `reports.view_operational`, y conexión MySQL vía **`get_mysql_pool()`** / `core.mysql_pool` (igual que el resto de informes existentes).
3. **Adapte la experiencia** a patrones Synap: agrupación en tabla, búsqueda predictiva, textos y exportación en español, coherente con `dashboard_detail.html` y `dashboard.js` (cabecera «Foco operativo», filtros colapsables, exportar Excel donde corresponda).

---

## 2. Arquitectura Synap (obligatoria)

| Aspecto | Implementación |
|---------|----------------|
| **Entrada usuario** | `ReportsLoginRequiredMixin`: sesión `request.session['user']` + `request.user` (AdministraNET), igual que hoy en reportes. |
| **Permisos API lectura** | `ReportQueryAPIView`: `OperationalReportsPermission \| ManagerialReportsPermission` según categoría del `ReportDefinition`; el payload recibe `filters.base_empresa` desde sesión (mismo mecanismo que líneas 95–101 de `reports/api_views.py`). |
| **Ejecución SQL lectura** | `QueryRunnerService(request.user).run(report, payload)` con rama `_run_logistica_lista_comprobantes_rutas` usando **`reports.services.connection_pool.get_mysql_pool()`** y lógica en **`logistica.services.lista_comprobantes_rutas`** (import compatible vía `reports.services.logistica_lista_comprobantes_rutas`). |
| **Definición del reporte** | `ReportDefinition` en migración de datos: categoría **operational**, `config` **sin** `version: declarative-v1` (legacy). Slug propuesto: **`comprobantes-rutas`**. |
| **UI** | `reports/dashboard/<slug>/` → `dashboard_detail.html` con rama por `report.slug` (includes de filtros + bloque de resultados / JS dedicado), mismo patrón que otros legacy con filtros custom. |
| **Escritura (entrega)** | Vista API en **`reports`** (p. ej. `POST /api/reports/logistica/lista-comprobantes-rutas/entrega/`) con **los mismos** `permission_classes` que los informes operativos y `base_empresa` desde sesión; transacciones con `get_connection(base_empresa)` del pool (no conexión ad-hoc). |
| **Autocomplete / detalle** | Endpoints GET bajo `reports/api_urls.py` (o servicio interno llamado desde vistas API), mismas clases de permiso y sesión; sin `EcomMayoristappSessionPermission`. |

---

## 3. Fases

### Fase A — ReportDefinition + runner legacy + lectura

- Migración: crear `ReportDefinition` (`comprobantes-rutas`), metadata para catálogo legacy (`catalog_legacy_section`, `catalog_legacy_order` en `reports/services/catalog_service.py` lista de slugs mayoristapp).
- `query_runner.py`: implementar `_run_logistica_lista_comprobantes_rutas` devolviendo `QueryResult` con `data` en filas dict (**campos acordes a la UI y export**, no copia literal de nombres de columnas PHP si se normalizan en Synap).
- Mapear `filters` del front a los **mismos criterios de negocio** que el relay (fechas, nº comprobante, estado, cliente, ruta); aplicar filtro `chofer.id_usuario` según `session['user']` (mapeo `supervisor_venta` / `idusuario` documentado en código).
- Tests: `reports/tests/…` mockeando pool o cursor (ver documento de tests).

### Fase B — APIs auxiliares (autocomplete, detalle)

- GET autocomplete clientes / rutas y GET detalle remito: vistas en `reports/api_views.py`, permisos operativos, SQL parametrizado, `base_empresa` desde sesión.

### Fase C — Escritura entrega

- POST entrega: transacción `comp_ped` remito + pedido; tipos AdministraNET (`core.utils.administranet_types`).

### Fase D — UI en `dashboard_detail`

- Partial de filtros + ampliar `dashboard.js` / template para slug (botón exportar Excel si aplica, tabla agrupada, modales).
- Opcional: slug en lista de `dashboard_detail.html` para mostrar botón «Exportar Excel» como otros legacy.

### Fase E — Documentación relay

- `MAYORISTAPP_RELAYS.md`: `relay-logistica-comprobantes.php` → v1 con rutas Reports + slug.

---

## 4. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Confundir permisos ecom vs reports | Solo permisos de reportes + sesión login Synap; no usar `ecom.permissions`. |
| `supervisor_venta` / `idusuario` en sesión | Leer de `session['user']` alineado a lo que ya pobla `login`/middleware; si falta clave, comportamiento documentado (ej. no filtrar chofer). |
| SQL mayúsculas `Anulado` / `anulado` | Mantener **equivalencia** con el legado en condiciones WHERE (mismas tablas y criterios de inclusión/exclusión); los nombres de alias pueden adaptarse. |
| Mutaciones vía `POST …/query/` | No mezclar escritura en el runner de solo lectura; endpoint dedicado en `reports`. |

---

## 5. Dependencias

- Pool MySQL y credenciales ya configurados para informes (`settings` + `core.mysql_pool`).
- Permiso `reports.view_operational` para usuarios que deben ver el informe.

---

## 6. Documentos relacionados

- `docs/general/INVENTARIO_FORMULARIO_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`  
- `docs/ecom/SPEC_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`  
- `docs/ecom/TEST_LOGISTICA_LISTA_COMPROBANTES_RUTAS.md`

---

## 7. Estado de implementación (Synap Reports)

- **UI legacy:** `dashboard_detail.html` incluye filtros extra, botón Excel, modales y `logistica_lista_comprobantes_rutas.js` (autocompletado, detalle, entrega). Modal detalle: shell Synap (cabecera en gradiente slate/indigo/púrpura, botón Cerrar con gradiente como el informe, `max-w-6xl`, backdrop con blur, entrada animada respetando `prefers-reduced-motion`); sin fila duplicada fecha/nº remito bajo el título (datos en Trazabilidad); **cliente** en bloque destacado **antes** de Trazabilidad; sin sección “Preparación”; trazabilidad en orden **pedido → factura → remito** (filas en una línea con scroll horizontal si hiciera falta). Iconos: **Material Icons** (`base_app.html`) con color semántico (pedido ámbar, factura esmeralda, remito azul, ruta cian/rosa/violeta, cliente fucsia; cabeceras de sección con degradados sky/violeta e índigo/púrpura). Modal **Registrar entrega** comparte el mismo estilo de cabecera y botones.
- **`dashboard.js`:** slug en `legacyReports`, `getFilters`, `setupPeriodoTipo`, `applyFilters` / `loadFilterOptions`, `renderTable` (columnas, traducciones, acciones), exportación Excel y workspace (`reportsWithDateFilters`). La tabla es la vista principal (sin alternancia gráfico/tabla); **barra tipo BO** en `logistica_lista_comprobantes_rutas_tabla_toolbar.html` — mismos textos/ proporción 70–30 que Backorder BO; **siempre visible** bajo el título del widget; agrupación local (orden de chips = niveles anidados) y búsqueda (≥2 caracteres); **opciones de agrupación** acotadas en `logistica_lista_comprobantes_rutas.js`: solo `fecha_remito`, `estado_entrega`, `cliente`, `nombre_chofer`; **con chips de agrupación**, misma lógica que BO: árbol `groupLogisticaListaData`, filas de grupo con chevron expandir/colapsar, subtotales en columnas monetarias (`total_remito`), tabla anidada por nivel, leyenda “Agrupado por: … · N agrupaciones”; Detalle/Entrega por delegación en el widget (`data-logistica-*`). Caché (`WeakMap`) y `refreshLogisticaListaComprobantesTabla`. **Estética** alineada a Backorder BO: cabeceras compactas, cebra solo en vista plana sin agrupación, scroll `max-h-[500px]`, thead sticky.
- **Catálogo:** `comprobantes-rutas` en `_LEGACY_COMPROBANTES_SLUGS`; caché de consulta con TTL 5 min (`status_reports` en `query_runner`).
- **Tests:** `reports/tests/test_logistica_lista_comprobantes_rutas.py` (sección catálogo, TTL, enrutado del runner).
