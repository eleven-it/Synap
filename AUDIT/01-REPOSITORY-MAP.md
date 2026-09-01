# 01 — Mapa Conceptual del Repositorio Synap

**Estado:** COMPLETE (Fase 1)  
**Fecha:** 25/08/2026  
**Metodología:** Inspección directa de estructura de directorios, `INSTALLED_APPS`, `urls.py`, `docker-compose`, `requirements.txt`, y muestreo de código fuente.

---

## 1. Qué es este repositorio

Synap es un **monorepo** que contiene:

1. **Aplicación principal Synap** — monolito Django 4.2 que extiende y complementa AdministraNET (ERP VB6 + MySQL).
2. **Proyecto Support** — backoffice de soporte con RAG/copiloto (Django + React), desplegable de forma independiente.
3. **Referencias legacy** — código VB6, PHP e-commerce, librería AFIP embebida.
4. **Documentación extensa** — `docs/` (~10 MB) y especificaciones formales en `openspec/`.
5. **Infraestructura local** — Docker Compose para desarrollo (Postgres, Redis, MySQL opcional).

**Clasificación:** CONFIRMADO POR CÓDIGO — `django_project/settings.py`, `docker-compose.yml`, estructura de directorios.

---

## 2. Vista conceptual de alto nivel

```
Synap/  (monorepo)
│
├── 🎯 RUNTIME PRINCIPAL — Django Synap
│   ├── django_project/          ← settings, urls raíz, WSGI
│   ├── core/                    ← núcleo transversal (auth sesión, pool MySQL, módulos, backup)
│   ├── login/                   ← autenticación contra MySQL AdministraNET
│   ├── [20 apps de dominio]     ← reports, ecom, mpr, stock, self_checkout, ...
│   ├── theme/                   ← Tailwind CSS + plantillas base UI
│   └── templates/               ← plantillas globales
│
├── 🗄️ CAPA DATOS
│   ├── PostgreSQL (default)     ← datos propios Synap (migraciones Django)
│   ├── MySQL (alias mysql)      ← AdministraNET legacy (pool directo, no ORM mayoritario)
│   └── Redis                    ← cache Django (django-redis)
│
├── 🔌 INTEGRACIONES EMBEBIDAS
│   ├── pyafipws/                ← facturación electrónica AFIP (submódulo/local)
│   ├── administraNET-ecom/      ← PHP legacy e-commerce (relays desde ecom/)
│   └── administranet_vb6/       ← referencia código VB6 (no ejecutable en Synap)
│
├── 🛠️ PROYECTO SEPARADO
│   └── support/                 ← Django+DRF+React+Celery (soporte RAG)
│
├── 📚 DOCUMENTACIÓN Y SPECS
│   ├── docs/                    ← documentación operativa y de dominio
│   └── openspec/                ← especificaciones formales por feature
│
├── 🐳 INFRAESTRUCTURA
│   ├── docker-compose.yml       ← app + Postgres + Redis
│   ├── docker-compose.mysql.yml ← MySQL 5.7 local (solo dev)
│   ├── Dockerfile               ← imagen Python 3.10 + Node 20 + Tesseract
│   └── docker-entrypoint.sh     ← bootstrap migrate + collectstatic
│
└── 🧪 CALIDAD
    ├── */tests/                 ← ~380 archivos test_*.py distribuidos por app
    ├── pytest.ini
    └── scripts/                 ← utilidades operativas (restore MySQL, etc.)
```

---

## 3. Entrypoints y configuración raíz

| Componente | Path | Rol | Evidencia |
|------------|------|-----|-----------|
| **manage.py** | `/manage.py` | CLI Django | CONFIRMADO POR CÓDIGO |
| **Settings** | `django_project/settings.py` | Configuración central (~590 líneas) | CONFIRMADO POR CÓDIGO |
| **URLs raíz** | `django_project/urls.py` | Routing HTTP principal | CONFIRMADO POR CÓDIGO |
| **WSGI** | `django_project/wsgi.py` | Entrypoint producción (Gunicorn) | CONFIRMADO POR CÓDIGO |
| **ASGI** | `django_project/asgi.py` | Presente, sin uso async documentado | CONFIRMADO POR CÓDIGO |
| **Celery** | `django_project/celery.py` | **Comentado/eliminado** en Synap principal | CONFIRMADO POR CÓDIGO |
| **Env template** | `env.example`, `.env.example` | Variables de entorno documentadas | CONFIRMADO POR CÓDIGO |
| **Dependencias** | `requirements.txt` | Stack Python producción | CONFIRMADO POR CÓDIGO |
| **Dev deps** | `requirements-dev.txt` | Herramientas desarrollo | CONFIRMADO POR CÓDIGO |
| **Tests config** | `pytest.ini` | Configuración pytest | CONFIRMADO POR CÓDIGO |

**Nota producción:** `Dockerfile` usa `runserver` por defecto; `gunicorn` está en `requirements.txt` pero no es el CMD del contenedor. DOCUMENTADO en `docs/general/DOCKER_OPTIMIZATIONS.md` — INFERIDO CON ALTA CONFIANZA que producción usa Gunicorn detrás de reverse proxy externo (no hay `nginx/` en repo).

---

## 4. Aplicaciones Django — mapa funcional

### 4.1 Apps activas (`INSTALLED_APPS`)

Fuente: `django_project/settings.py` líneas 36–90.

| App | Path | Dominio funcional | Modelos Django | Acceso MySQL legacy |
|-----|------|-------------------|:--------------:|:-------------------:|
| **theme** | `theme/` | UI Tailwind, estáticos | No | No |
| **core** | `core/` | Núcleo: usuarios, permisos, empresas, módulos, backup, pool MySQL | Sí (`models/`) | Sí (extenso) |
| **login** | `login/` | Autenticación AdministraNET, WebAuthn | Sí | Sí |
| **dashboard** | `dashboard/` | Stub Firebase legacy (sustituido por `core/`) | No (vacío) | No |
| **logistica** | `logistica/` | Operación entregas | No | Sí |
| **reports** | `reports/` | Motor de informes y dashboards | Sí | Sí (principal consumidor) |
| **ia** | `ia/` | Asistentes IA persistentes | Sí | Parcial |
| **self_checkout** | `self_checkout/` | TPV / autoservicio | No | Sí (intenso) |
| **fe_afip** | `fe_afip/` | Facturación electrónica AFIP/ARCA | Sí | Sí |
| **stock** | `stock/` | Movimientos e inventario AdministraNET | No | Sí |
| **ventas** | `ventas/` | Objetivos de venta, presupuestos | No | Sí |
| **compras** | `compras/` | Remitos de compra (hub comprobantes) | No | Sí |
| **factura_compra_posting** | `factura_compra_posting/` | Contrato posting factura compra (stub) | No | Stub |
| **factura_compra_captura** | `factura_compra_captura/` | Workflow captura factura (PG) | Sí | Validación fiscal |
| **legacy_db** | `legacy_db/` | Escritura compatible VB6 en MySQL | No* | Sí (repositorios) |
| **contabilidad_audit** | `contabilidad_audit/` | Auditoría imputación contable (lectura) | Sí | Sí |
| **mpr** | `mpr/` | Manufacturing / Producción | Sí | Sí (muy intenso) |
| **odoo_migracion** | `odoo_migracion/` | Migración AdministraNET → Odoo 19 | Sí | Sí |
| **ecom** | `ecom/` | E-commerce mayorista B2B, relays PHP | Sí | Sí (intenso) |
| **tiendanube_administranet** | `tiendanube_administranet/` | Integración Tienda Nube ↔ AdministraNET | Sí | Sí |

\* `legacy_db/models_legacy.py` existe pero no hay `models.py`; modelos ORM no auto-descubiertos. CONFIRMADO POR CÓDIGO.

### 4.2 Apps presentes pero NO activas

| App | Path | Estado | Evidencia |
|-----|------|--------|-----------|
| **sia** | `sia/` | Código completo, no en `INSTALLED_APPS`, URLs no montadas | CONFIRMADO POR CÓDIGO |
| **mercadopago** | `mercadopago/` | Comentada en settings; carga dinámica vía `url_registry` si activa | CONFIRMADO POR CÓDIGO |
| **mtrix** | `mtrix/` | Solo `__pycache__`, fuentes eliminadas | CONFIRMADO POR CÓDIGO |
| **support** | `support/` | Proyecto Django independiente, no parte del runtime Synap | CONFIRMADO POR CÓDIGO |

### 4.3 Apps comentadas/eliminadas en settings

Listadas en `django_project/settings.py` líneas 75–89:

`reports_ai`, `administraNET_integration`, `sales`, `inventory`, `tiendanube`, `django_celery_beat`, `celery`, `accounting`, `purchases`, `mercadopago`, `clover`, `logistics`, `finance`

**Clasificación:** OBSOLETO en runtime actual; código residual puede existir en repo.

---

## 5. Estructura por capas (no por carpetas)

### 5.1 Capa de presentación

| Tecnología | Ubicación | Uso |
|------------|-----------|-----|
| **Django Templates** | `*/templates/`, `theme/templates/` | SSR principal (~977 archivos HTML) |
| **Tailwind CSS** | `theme/static/`, `theme/static_src/` | Sistema de diseño |
| **Alpine.js** | Embebido en templates (MPR, ecom, reports) | Interactividad cliente |
| **JavaScript ES modules** | `ecom/static/ecom/js/*.mjs`, `mpr/static/` | Flujos complejos (pedidos, TPV) |
| **PWA** | `core/views/pwa_views.py`, `sw.js`, `manifest.json` | Service worker, offline, Nivel A móvil |
| **DRF** | `*/api/`, `*/api_urls.py` | APIs JSON autenticadas |

**Clasificación:** CONFIRMADO POR CÓDIGO — no hay React/Vue en la app principal (solo en `support/frontend/`).

### 5.2 Capa de aplicación (servicios)

Patrón dominante: **views → services → mysql_pool / ORM**

| Patrón | Ejemplo | Apps |
|--------|---------|------|
| Servicios con SQL crudo | `core/mysql_pool.py` → `get_connection(base_empresa)` | core, reports, ecom, mpr, self_checkout, stock |
| Repositorios legacy | `legacy_db/repositories.py` | legacy_db, contabilidad_audit |
| Servicios de dominio | `ecom/services/`, `mpr/services/` | ecom, mpr |
| Runners de reportes | `reports/services/query_runner.py` | reports |
| Relays PHP | `ecom/services/*_relay.py` | ecom → administraNET-ecom |

### 5.3 Capa de datos

| Store | Alias/config | Propietario | Migraciones Django |
|-------|-------------|-------------|:------------------:|
| **PostgreSQL** | `DATABASES['default']` | Synap | Sí |
| **MySQL AdministraNET** | `DATABASES['mysql']` + pool | AdministraNET (VB6) | No (router bloquea) |
| **Redis** | `CACHES['default']` | Synap (cache) | N/A |
| **Filesystem** | `MEDIA_ROOT`, `BACKUP_LOCAL_ROOT`, `SYNAP_AFIP_STORAGE` | Synap | N/A |

### 5.4 Capa de infraestructura

| Componente | Archivo | Notas |
|------------|---------|-------|
| Contenedor app | `Dockerfile`, `docker-compose.yml` | Python 3.10, Node 20, Tesseract OCR |
| PostgreSQL 13 | `docker-compose.yml` service `db` | WAL archiving habilitado |
| Redis 6 | `docker-compose.yml` service `redis` | AOF persistence |
| MySQL 5.7 (dev) | `docker-compose.mysql.yml` | Red `synap_net` compartida |
| E-com PHP (dev) | `docker-compose.administranet-ecom.yml` | Stack PHP separado |
| Support stack | `support/docker/docker-compose.yml` | Puerto 8250, Celery propio |

---

## 6. Directorios especiales (no son apps Django)

### 6.1 `core/` — Núcleo transversal (~5.5 MB)

El directorio más importante del sistema. Subsistemas internos:

```
core/
├── middleware/           ← RequestScopedMysql, permisos módulos, PWA Nivel A
├── mysql_pool.py         ← Pool thread-safe MySQL (origen único legacy)
├── module_registry.py    ← Catálogo estático MODULE_CONFIGS
├── module_manager.py     ← Activación runtime vía ModuleConfig (Postgres)
├── url_registry.py       ← Montaje dinámico URLs por módulo activo
├── plugin_registry.py    ← Sistema de plugins
├── hook_registry.py      ← Sistema de hooks/extensibilidad
├── event_dispatcher.py   ← Eventos asíncronos in-process
├── backup/               ← DR: BackupSettings, jobs, SFTP, restore
├── services/
│   ├── legacy_mysql_schema/  ← Catálogo DDL MySQL (~3200 líneas catalog.py)
│   ├── administranet_permisos_usuario.py
│   └── administranet_stock.py, ...
├── management/commands/  ← 57 comandos operativos
├── api/                  ← APIs búsqueda (artículos, clientes, geo)
├── models/               ← Empresa, UsuarioExtendido, Rol, ModuleConfig, ...
└── views/                ← Dashboard, backup UI, usuarios, permisos, ...
```

**Clasificación:** CONFIRMADO POR CÓDIGO.

### 6.2 `reports/` — Motor de informes (~11 MB)

```
reports/
├── models.py             ← ReportDefinition, ReportDashboard, ReportWidget, ...
├── services/
│   ├── query_runner.py   ← Ejecución SQL contra MySQL
│   ├── connection_pool.py
│   └── [runners por informe]
├── migrations/           ← Solo Postgres (metadatos reportes)
├── templates/reports/      ← UI dashboards
├── api_urls.py           ← API REST reportes
└── tests/                ← 38 archivos de test
```

### 6.3 `administraNET-ecom/` — PHP legacy

Aplicación PHP separada (mayorista B2B) con la que `ecom/` se comunica vía HTTP relays. No es parte del runtime Django pero es dependencia funcional del módulo ecom.

**Clasificación:** CONFIRMADO POR CÓDIGO — `docker-compose.administranet-ecom.yml`, `ecom/services/*_relay.py`.

### 6.4 `administranet_vb6/` — Referencia VB6 (~1.7 MB)

Código fuente VB6 de AdministraNET incluido como referencia para migración/reverse engineering. **No se ejecuta** en Synap.

**Clasificación:** CONFIRMADO POR CÓDIGO — `docs/administranet_vb6/`.

### 6.5 `pyafipws/` — Librería AFIP (~20 MB)

Fork/local de [pyafipws](https://github.com/reingart/pyafipws) instalado editable en Docker (`pip install -e ./pyafipws`). Usado por `fe_afip/` para WSAA, WSFE, padrón.

**Clasificación:** CONFIRMADO POR CÓDIGO — `Dockerfile` líneas 67–74.

### 6.6 `docs/` — Documentación (~10 MB)

Estructura por dominio:

| Subdirectorio | Contenido |
|---------------|-----------|
| `docs/general/` | Arquitectura, permisos, migración formularios, tablas legacy, planes FODA |
| `docs/reports/` | Motor de reportes, diseño columnas, análisis ventas |
| `docs/ecom/` | E-commerce mayorista, pedidos, relays |
| `docs/mpr/` | Manufacturing, SQL operativo, E2E |
| `docs/self_checkout/` | TPV, SQL, CAE/ARCA |
| `docs/compras/` | Factura compra, OCR, posting |
| `docs/general/tablas/` | Esquema tablas AdministraNET |
| `docs/contabilidad/` | Auditoría contable |

**Advertencia:** La documentación puede divergir del código. Esta auditoría prioriza código; divergencias se marcarán explícitamente.

### 6.7 `openspec/` — Especificaciones formales (~3.1 MB)

Specs por feature en `openspec/specs/` (contabilidad, ecom, mpr, reports, stock, permisos, UI). Complementan `docs/` con contratos formales.

### 6.8 `support/` — Proyecto separado (~51 MB)

```
support/
├── backend/          ← Django + DRF + Celery + pgvector (RAG)
│   ├── apps/
│   │   ├── api/          ← Casos, copilot, knowledge
│   │   ├── knowledge/    ← RAG con langchain
│   │   ├── integrations/ ← SynapClient (HTTP+JWT)
│   │   └── sla/
│   └── config/       ← settings, celery.py
├── frontend/         ← React/Vite (node_modules masivo)
└── docker/           ← docker-compose independiente
```

**No comparte runtime con Synap principal.** Se integra vía HTTP (`SUPPORT_SYNAP_API_URL`, JWT).

**Clasificación:** CONFIRMADO POR CÓDIGO.

### 6.9 `scripts/` — Utilidades operativas

Scripts bash/Python para restore MySQL local, importaciones, operaciones batch. No son parte del runtime web.

### 6.10 `tmp/`, `tmp_exports/`, `backups/`

Directorios operativos/temporales. `backups/` contiene dumps históricos. No forman parte de la arquitectura lógica.

---

## 7. Sistema de módulos dinámicos

Synap implementa un **sistema de módulos plugables** más allá de `INSTALLED_APPS`:

| Componente | Archivo | Función |
|----------|---------|---------|
| `MODULE_CONFIGS` | `core/module_registry.py` | Definición estática: nombre, dependencias, permisos, hooks |
| `ModuleManager` | `core/module_manager.py` | Estado activo/inactivo en `ModuleConfig` (Postgres) |
| `URLRegistry` | `core/url_registry.py` | Monta URLs de módulos activos dinámicamente |
| `PluginRegistry` | `core/plugin_registry.py` | Plugins opcionales |
| `HookRegistry` | `core/hook_registry.py` | Hooks de extensibilidad |
| Middleware | `core/middleware/module_middleware.py` | Bloquea acceso a módulos inactivos |

Módulos registrados en `MODULE_CONFIGS`: `core`, `login`, `dashboard`, `mercadopago`, `clover`, `reports`, `ia`, `tiendanube_administranet`, `logistica`, `fe_afip`, `mpr`, `odoo_migracion`, `ecom`.

**Clasificación:** CONFIRMADO POR CÓDIGO.

**Nota:** No todos los módulos en `MODULE_CONFIGS` están en `INSTALLED_APPS` (ej. `mercadopago`, `clover`).

---

## 8. Tests y calidad

| Métrica | Valor | Distribución destacada |
|---------|------:|------------------------|
| Archivos `test_*.py` | ~380 | ecom: 80, mpr: 73, reports: 38, factura_compra_captura: 36, core: 27 |
| Management commands | ~160 | core: 57, distribuidos en otras apps |
| `urls.py` | 27 | Por app + APIs |
| Modelos (`models.py` o `models/`) | 43 | — |

Framework: Django TestCase + pytest (`pytest.ini`). Tests se ejecutan en contenedor `Synap_app` según `.cursorrules`.

**Clasificación:** CONFIRMADO POR CÓDIGO.

---

## 9. Dependencias externas clave

### Python (`requirements.txt`)

| Paquete | Uso en Synap |
|---------|-------------|
| Django 4.2 | Framework principal |
| djangorestframework | APIs JSON |
| psycopg2-binary | PostgreSQL |
| mysqlclient | MySQL AdministraNET |
| django-redis | Cache Redis |
| gunicorn | WSGI producción |
| whitenoise | Estáticos |
| celery (≥5.3) | **Instalado** pero worker **no configurado** en compose principal |
| openpyxl, reportlab, pyxlsb | Exportación reportes |
| pytesseract, opencv-python-headless | OCR factura compra |
| pyafipws (local) | Facturación electrónica |
| pymssql | Azure SQL BEST (MPR migración, solo lectura) |
| webauthn | Passkeys PWA |
| paramiko | SFTP backups |

**Paquetes IA eliminados del requirements principal:** `openai`, `crewai`, `langchain` (solo en `support/backend/` e `ia/` vía requests directos).

### JavaScript

Node 20 en Docker para build Tailwind (`theme/`). Alpine.js y módulos ES en templates. No hay `package.json` en raíz del monorepo principal (solo en `theme/` y `support/frontend/`).

### Docker images

| Imagen | Versión | Servicio |
|--------|---------|----------|
| python:3.10-slim | build | Synap_app |
| postgres:13 | pin | Synap_db |
| redis:6-alpine | pin | Synap_redis |
| mysql:5.7 | pin (dev) | Synap_mysql57 |

---

## 10. Artefactos históricos y código muerto detectado

| Artefacto | Ubicación | Estado |
|-----------|-----------|--------|
| Firebase auth | `login/`, `dashboard/` | OBSOLETO — comentado/deshabilitado (`FIREBASE_DESHABILITADO.md`) |
| Celery worker/beat | `django_project/celery.py` | OBSOLETO — comentado en Synap principal |
| Apps sales/inventory/accounting | Comentadas en settings | OBSOLETO — código residual posible |
| `mtrix/` | Solo `__pycache__` | ORPHAN — fuentes eliminadas |
| `sia/` | Completo pero no instalado | LEGACY — Strategic Insights |
| Duplicados `* 2.py` | Varios módulos (fe_afip, factura_compra_captura, self_checkout) | REQUIERE VALIDACIÓN — posible copia accidental |
| `mercadopago/` | Código presente, no en INSTALLED_APPS | LEGACY — activable vía ModuleConfig |

---

## 11. Mapa de rutas HTTP (resumen)

Montaje en `django_project/urls.py`:

| Prefijo | App | Tipo |
|---------|-----|------|
| `/` | redirect → `/core/dashboard/` | — |
| `/login/` | login | Auth |
| `/core/` | core | Núcleo + dashboard |
| `/reports/` | reports | Informes |
| `/ia/` | ia | Asistentes IA |
| `/ecom/` | ecom | E-commerce mayorista |
| `/mpr/` | mpr | Producción |
| `/stock/` | stock | Inventario |
| `/ventas/` | ventas | Objetivos venta |
| `/compras/` | compras | Remitos compra |
| `/compras/captura/` | factura_compra_captura | Workflow factura |
| `/self_checkout/` | self_checkout | TPV |
| `/contabilidad/` | contabilidad_audit | Auditoría contable |
| `/odoo-migracion/` | odoo_migracion | Migración Odoo |
| `/logistica/` | logistica | Entregas |
| `/tiendanube_administranet/` | tiendanube_administranet | Tienda Nube |
| `/api/reports/` | reports API | REST |
| `/api/ia/` | ia API | REST |
| `/api/self-checkout/` | self_checkout API | REST |
| `/api/compras/` | factura_compra_captura API | REST |
| `/api/legacy-hub/` | legacy_db | REST hub compras |
| `/core/api/` | core API | REST búsquedas |
| `/admin/` | Django admin | Admin |
| `/sw.js`, `/manifest.json` | PWA | Service worker |

Módulos dinámicos (`fe_afip`, `mercadopago`, `dashboard`) se montan vía `url_registry` cuando activos en `ModuleConfig`.

**Clasificación:** CONFIRMADO POR CÓDIGO.

---

## 12. Relación con repositorios externos

| Referencia | Tipo | Ubicación |
|------------|------|-----------|
| AdministraNET VB6 | ERP legacy (referencia) | `administranet_vb6/`, MySQL remoto |
| administraNET-ecom | PHP e-commerce | `administraNET-ecom/`, submódulo git (`.gitmodules`) |
| pyafipws | Librería AFIP | `pyafipws/`, git clone local |
| Odoo 19 | ERP destino migración | `odoo_migracion/` (conexión externa) |
| Tienda Nube | E-commerce SaaS | `tiendanube_administranet/` (API REST) |
| Azure SQL BEST | Data warehouse MPR | `mpr/best_migration/` (pymssql) |

---

## 13. Preguntas respondidas en esta fase

| # | Pregunta | Respuesta breve |
|---|----------|-----------------|
| 1 | ¿Qué es Synap? | Monolito Django modular complementario a AdministraNET |
| 2 | ¿Cuántos módulos? | 20 apps activas + 4 legacy/huérfanas + support separado |
| 3 | ¿Es monolito o microservicios? | Monolito con un proyecto satellite (`support/`) |
| 4 | ¿Dónde vive el core? | `core/` + `login/` + `django_project/` |
| 5 | ¿Hay FastAPI? | No en Synap principal; no en support (Django+DRF) |

---

## 14. Próximos pasos (Fase 2+)

- Profundizar arquitectura runtime → `02-CURRENT-ARCHITECTURE.md` ✅
- Catalogar cada módulo con modelos/tablas/APIs → `03-MODULE-CATALOG.md`
- Construir grafo de dependencias → `04-MODULE-DEPENDENCY-GRAPH.md`
- Mapear acceso a datos y tablas → `05`–`08`

---

*Generado por auditoría técnica READ ONLY. Sin modificaciones al código fuente.*
