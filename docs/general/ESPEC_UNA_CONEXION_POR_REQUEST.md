# Especificación: Una conexión MySQL por request (contexto + MPR)

**Estado: Implementado**  
**Prioridad: Alta**  
**Módulos afectados:** core (mysql_pool, middleware, context_processors), core/services (administranet_empresas, administranet_sucursales), mpr (vistas y servicios usan pool sin cambios de firma)

---

## 1. Resumen

Cada request HTTP que use la base AdministraNET (MySQL) debe consumir **una sola** conexión del pool: se obtiene al inicio del request (cuando hay `base_empresa` en sesión) y se reutiliza en context processors (empresa, sucursales, logo) y en toda la vista (incl. MPR), devolviéndola al pool al finalizar el request.

**Enfoque:** variable de contexto (`contextvars`) que el middleware establece al inicio del request; `get_connection` y `mysql_cursor` en `core.mysql_pool` la consultan y reutilizan esa conexión cuando existe y coincide `base_empresa`. No se modifican las firmas de los servicios (p. ej. MPR).

**No incluye:** requests sin sesión o sin `base_empresa` (comportamiento actual: N conexiones según uso); comandos management o workers asíncronos (cada uno su propio contexto).

---

## 2. Requisitos funcionales

| ID | Requisito | Detalle |
|----|-----------|---------|
| RF-1 | Conexión por request | Middleware (después de SessionMiddleware) asigna una conexión por request cuando hay `base_empresa` en sesión y la ruta no está excluida. |
| RF-2 | Reutilización en pool | `get_connection(base_empresa)` y `mysql_cursor(base_empresa)` reutilizan la conexión de request cuando existe y coincide `base_empresa`; no la devuelven al pool al salir del `with`. |
| RF-3 | Liberación al final del request | Al final del request (process_response o process_exception) la conexión se devuelve al pool y el contextvar se limpia. |
| RF-4 | Rutas excluidas | Rutas que no usan MySQL (static, media, PWA: sw.js, manifest.json, offline) no abren conexión de request. |

---

## 3. Criterios de aceptación (CA)

| ID | Criterio | Verificación |
|----|----------|--------------|
| CA-1 | Una adquisición y una devolución por request | Request autenticado a vista que use MySQL (ej. `/mpr/demanda/ventana-pack/`) implica **una única** adquisición al pool y **una única** devolución para ese request. |
| CA-2 | Sin base_empresa | Request sin `base_empresa` en sesión no modifica el contextvar; comportamiento igual que hoy (cada uso pide su conexión al pool). |
| CA-3 | Misma conexión en contexto y vista | Context processors (empresa, sucursales) y vista usan la **misma** conexión (misma referencia) cuando hay conexión de request. |
| CA-4 | Paths excluidos | Request a `/static/...`, `/sw.js`, `/manifest.json`, `/offline/` (con sesión y base_empresa) no asigna conexión de request. |
| CA-5 | Excepción no capturada | Ante excepción no capturada, la conexión de request se libera en process_exception (pool recibe release, contextvar limpiado). |

---

## 4. Diseño

- **Middleware:** `RequestScopedMysqlMiddleware` (o nombre análogo). En `process_request`: si `request.session` tiene `base_empresa` y el path no está en la lista de exclusión, obtiene una conexión del pool (`pool.get_connection(base_empresa).__enter__()`), la guarda en un `contextvars.ContextVar` y una referencia en `request` para liberar después. En `process_response` y `process_exception`: llama `__exit__` del context manager del pool y resetea el contextvar.
- **core/mysql_pool:** Variable de contexto que almacena `(base_empresa, conn)` o equivalente. En `get_connection(base_empresa)`: si el contextvar tiene una conexión para esa `base_empresa`, devuelve un context manager que hace `yield conn` y en `__exit__` no libera (no-op). Si no, comportamiento actual: `pool.get_connection(base_empresa)`. `mysql_cursor` ya usa `get_connection`, por tanto hereda el comportamiento.
- **Servicios empresa/sucursales:** Unificar uso del pool. `AdministraNETSucursalesService` debe usar `core.mysql_pool.get_connection` o `mysql_cursor` en lugar de `_get_connection` (MySQLdb directo). Opcionalmente, los métodos de `AdministraNETEmpresaService` que usan `_get_connection` pasan a usar el pool.

Referencia: plan en `.cursor/plans/` (refactor una conexión por request).

---

## 5. Paths excluidos (configurables)

No se abre conexión de request para:

| Prefijo o ruta | Motivo |
|----------------|--------|
| `/static/` | Archivos estáticos (WhiteNoise u otro). |
| `/media/` | Archivos multimedia. |
| `/sw.js` | Service Worker PWA. |
| `/manifest.json` | Manifest PWA. |
| `/offline/` | Página offline PWA. |

Opcional: `/admin/` si no se usa MySQL de administraNET en el admin de Django.

---

## 6. Consideraciones

- **Timeout:** La conexión permanece abierta durante todo el request; en requests muy largos podría aplicarse timeout del servidor MySQL (p. ej. `wait_timeout`). No se cambia por defecto en esta especificación.
- **Hilos:** La conexión de request no debe usarse desde otro hilo; `contextvars` es por contexto de ejecución, no por hilo.
- **Tests:** Tests unitarios con mock del pool o del contextvar para verificar una adquisición/una devolución; tests de integración opcionales (ej. GET a ventana-pack con sesión) espiando el pool.
