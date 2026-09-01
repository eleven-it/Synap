# SYNAP-TECHNICAL-REFERENCE

**Estado:** COMPLETE  
**Fecha:** 25/08/2026  
**Audiencia:** Arquitecto nuevo en el proyecto

---

## 1. Inicio rápido

```bash
# Desarrollo
docker compose up -d
docker exec Synap_app python manage.py test <app>

# URLs
http://localhost:8000/core/dashboard/  # Dashboard principal
http://localhost:8000/login/           # Login
```

## 2. Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Django 4.2, Python 3.10 |
| Frontend | Templates + Tailwind + Alpine.js |
| DB Synap | PostgreSQL 13 |
| DB ERP | MySQL 5.7+ (AdministraNET) |
| Cache | Redis 6 |
| Container | Docker Compose |

## 3. Estructura del repo

```
Synap/
├── django_project/     # Settings, URLs, WSGI
├── core/               # NÚCLEO — empezar aquí
├── login/              # Autenticación
├── reports/            # Motor informes
├── ecom/               # E-commerce B2B
├── mpr/                # Producción
├── self_checkout/      # TPV
├── [15 apps más]
├── theme/              # UI Tailwind
├── docs/               # Documentación operativa
├── AUDIT/              # Esta auditoría
└── support/            # Proyecto separado
```

## 4. Flujo de un request

1. HTTP → Middleware stack (12 middlewares)
2. `RequestScopedMysqlMiddleware` abre conn MySQL con `session["user"]["base_empresa"]`
3. `RequestUserMiddleware` crea `AdministraNETUser` desde sesión
4. `ModulePermissionMiddleware` verifica módulo activo + permisos
5. URL routing → View → Service → mysql_pool/ORM → Response

## 5. Autenticación

- Login: `POST /login/` con cod_usuario, password, base_empresa
- Fuente: MySQL tabla `usuarios` en database seleccionada
- Sesión: `session["user"]` con campos AdministraNET
- Superuser: `cod_usuario == 'supervisor'`

## 6. Acceso a datos

```python
# MySQL (canónico)
from core.mysql_pool import get_connection, mysql_cursor

with get_connection(base_empresa) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT ... FROM articulo WHERE ...", [params])

# PostgreSQL (ORM)
from reports.models import ReportDefinition
ReportDefinition.objects.filter(...)
```

## 7. Módulos

Activación: `core.models.ModuleConfig` (PostgreSQL) + `core/module_registry.py` (estático).

Verificar módulo activo: `module_manager.is_module_active('reports')`

## 8. Permisos

```python
from core.decorators import administranet_login_required, tiene_permiso

@administranet_login_required
@tiene_permiso('reports.view_dashboard')
def my_view(request): ...
```

Fuente: `SYNAP_PERMISOS_SOURCE` (legacy/synap/dual)

## 9. Tests

```bash
docker exec Synap_app python manage.py test ecom
docker exec Synap_app python manage.py test reports.tests.test_query_runner
```

## 10. Management commands clave

```bash
docker exec Synap_app python manage.py backup_tick
docker exec Synap_app python manage.py setup_modules --sync
docker exec Synap_app python manage.py bootstrap_instalacion
```

## 11. Variables de entorno críticas

Ver `env.example` y `20-CONFIGURATION.md`.

## 12. Documentación existente

| Doc | Contenido |
|-----|-----------|
| `docs/general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md` | Plan migración VB6 |
| `docs/general/TIPOS_DATOS_ADMINISTRANET.md` | Normalización tipos |
| `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` | Canon UI |
| `AUDIT/` | Esta auditoría técnica |

## 13. Gotchas

1. **base_empresa** es el tenant key — siempre de sesión
2. **No usar ORM para MySQL legacy** — usar pool
3. **Migraciones solo Postgres** — SYNAP_MIGRATIONS_POSTGRES_ONLY
4. **Celery no activo** — usar management commands
5. **administranet_types** obligatorio para writes MySQL
6. **No alert/confirm nativos** — usar modales Synap
7. **core es hub** — cambios en core afectan todo

## 14. Diagrama de referencia

Ver `SYNAP-SYSTEM-MAP.md` y `02-CURRENT-ARCHITECTURE.md`.

---

*Manual técnico generado por auditoría READ ONLY.*
