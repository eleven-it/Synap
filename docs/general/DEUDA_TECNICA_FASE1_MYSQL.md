# Deuda técnica Fase 1: MySQL – estrategia de conexión

**Contexto:** Fase 1 utiliza MySQL "como se encuentra" (administraNET). En una versión 2 se prevé migrar a PostgreSQL.

## Pool vs conexión directa

| Criterio | Conexión directa | Pool de conexiones |
|----------|------------------|--------------------|
| **Uso** | Una conexión nueva por operación (open → query → close) | Reutilización de conexiones; se obtienen y devuelven al pool |
| **Ventaja** | Implementación simple | Límite controlado de conexiones, menor overhead, adecuado para múltiples workers |
| **Riesgo** | Muchos workers/requests pueden agotar `max_connections` de MySQL | Configuración (tamaño del pool) debe ser coherente con workers |
| **Recomendación** | Solo para scripts one-off o migraciones | **Recomendado para la aplicación web** (Django con varios workers, reportes, API) |

**Decisión:** Usar **pool de conexiones** como patrón único para todo acceso MySQL desde Synap (login, core, reports, self_checkout). Así se controla el número de conexiones y se reutilizan, alineado con buenas prácticas para aplicaciones multiworker.

## Implementación adoptada

- **Ubicación del pool:** `core/mysql_pool.py` (origen único). Consumen: **login** (administranet_auth, logout en views), **reports** (connection_pool reexporta desde core), **self_checkout** (db.py).
- **API:** `get_mysql_pool()`, `get_connection(base_empresa)` (context manager), `mysql_cursor(base_empresa, dict_cursor=False)` (context manager).
- **Transacciones largas:** Usar `with get_connection(base_empresa) as conn:` y no cerrar la conexión manualmente; al salir del `with` la conexión vuelve al pool.
- **Login:** `login/administranet_auth.py` usa `pool_get_connection` en `get_empresas`, `validate_user`, `create_session` y en `get_connection()` (para logout en views).

## Fase 2 (PostgreSQL)

Cuando se migre a PostgreSQL, el pool y las consultas se reemplazarán por el backend Django (PostgreSQL); este documento y `core/mysql_pool.py` quedarán solo para compatibilidad temporal o lectura legacy si se mantiene MySQL en paralelo.
