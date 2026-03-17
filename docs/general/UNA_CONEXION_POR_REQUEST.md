# Una conexión MySQL por request — Nota operativa

**Referencia:** [ESPEC_UNA_CONEXION_POR_REQUEST.md](ESPEC_UNA_CONEXION_POR_REQUEST.md)

## Resumen

Cada request HTTP con `base_empresa` en sesión usa **una sola** conexión del pool MySQL: el middleware `RequestScopedMysqlMiddleware` la asigna al inicio y la libera al final (response o excepción). Context processors (empresa, sucursales) y vistas (p. ej. MPR ventana-pack) reutilizan esa conexión vía `get_connection` / `mysql_cursor` sin cambiar firmas de servicios.

## Componentes

- **Middleware:** `core.middleware.request_scoped_mysql.RequestScopedMysqlMiddleware` (registrado en `settings.MIDDLEWARE` tras `SessionMiddleware`).
- **Pool:** `core.mysql_pool.request_mysql_conn_var` (contextvar) y lógica en `get_connection()` para reutilizar la conexión de request cuando coincide `base_empresa`.
- **Paths excluidos:** `/static/`, `/media/`, `/sw.js`, `/manifest.json`, `/offline/` (no se abre conexión de request).

## Verificación

- Tests: `docker exec Synap_app python manage.py test core.tests.test_request_mysql_middleware`
- En logs, para un request a una vista que use MySQL (ej. `/mpr/demanda/ventana-pack/`), debe verse una única adquisición y una única devolución al pool por request.
