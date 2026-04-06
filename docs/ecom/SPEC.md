# Especificación formal — Migración administraNET-ecom → Synap

**Fuente de verdad:** [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md)  
**Versión:** 1.0 — 2026-03-30  
**Plan mayoristapp (specs por vertical):** [MAYORISTAPP_SPEC_INDICE.md](./MAYORISTAPP_SPEC_INDICE.md)

---

## 2.1 — Arquitectura Django propuesta

### Apps

| App | Rol |
|-----|-----|
| **`ecom`** (nueva) | Punto de entrada web/API para funcionalidades B2B/mayorista migradas desde PHP; metadatos de migración; checkpoints locales en PostgreSQL si aplica |
| **`legacy_db`** (existente) | Lectura/escritura controlada sobre tablas MySQL AdministraNET (`usuarios`, `comp_ped`, `articulo`, …) |
| **`reports`** (existente) | Informes que duplican `relay-ventas-netas*.php` — reutilizar consultas validadas ya presentes en Synap |
| **`core`** | Middleware de módulos, permisos, sesión empresa |

### Estructura de directorios (`ecom`)

```
ecom/
  __init__.py
  apps.py
  models.py          # Checkpoints de migración (PostgreSQL)
  urls.py
  views.py           # API metadatos + futuras vistas
  services/
    migration_info.py   # Datos de paridad con REVERSE_ENGINEERING.md
  tests/
    __init__.py
    conftest.py
    factories.py
    test_models.py
    test_views.py
    test_integration.py
    test_parity.py
```

### Settings por entorno

- Reutilizar `django_project/settings.py` con `decouple` (`ENVIRONMENT`, `DEBUG`, `SECRET_KEY`).
- Sin archivo nuevo obligatorio; variables específicas ecom: prefijo `ECOM_` si en el futuro se requiere feature flag.

### Stack

| Componente | Versión / nota |
|------------|----------------|
| Python | 3.x compatible con Django 4.2 |
| Django | 4.2 |
| DRF | Opcional en fases posteriores; Fase inicial: `JsonResponse` |
| Celery | No requerido hasta inventariar cron PHP |
| MySQL | Compartido AdministraNET vía router legacy |
| PostgreSQL | Tablas Django default (`ecom_ecommigrationcheckpoint`) |

---

## 2.2 — Spec de modelos

### Modelo: EcomMigrationCheckpoint

| Campo | Tipo Django | Opciones | Equivalencia PHP |
|-------|-------------|----------|------------------|
| id | BigAutoField | PK | — |
| module_slug | SlugField | max_length=64, unique=True | nombre lógico del submódulo migrado |
| notes | TextField | blank=True | comentarios internos |
| updated_at | DateTimeField | auto_now=True | auditoría |

**Meta**

- `ordering`: `['-updated_at']`
- `verbose_name`: Checkpoint de migración e-com

**Managers:** default.

**Migraciones:** `python manage.py makemigrations ecom`

---

## 2.3 — Spec de vistas / endpoints

### Endpoint: GET `/ecom/api/migration-info/`

| Campo | Valor |
|-------|-------|
| View | `migration_info` |
| Permisos | `AllowAny` (información no sensible de inventario) |
| Descripción | Devuelve JSON con conteos y etiquetas alineadas a `REVERSE_ENGINEERING.md` para tests de paridad |

**Input:** ninguno.

**Proceso**

1. Construir dict desde `services.migration_info.build_migration_info_dict()`.
2. Devolver `JsonResponse` con `200`.

**Output**

- `200` — cuerpo: `{ "php_file_count": 1287, "mayoristapp_php_file_count": 1276, "relay_endpoint_count": 44, "framework": "procedural_php_mysqli", "source": "administraNET-ecom" }`

**Casos borde**

- N/A (solo lectura de constantes).

### Endpoint: GET `/ecom/api/health/`

| Campo | Valor |
|-------|-------|
| View | `health` |
| Permisos | `AllowAny` |
| Descripción | Smoke check |

**Output:** `{ "status": "ok", "app": "ecom" }`

### Endpoint: GET `/ecom/api/mayoristapp/relay-inventory/`

| Campo | Valor |
|-------|-------|
| View | `mayoristapp_relay_inventory` |
| Permisos | `AllowAny` (inventario técnico de nombres de archivo) |
| Descripción | Lista canónica de rutas relay bajo `mayoristapp/`; Fase A del plan mayorista |

**Output:** `{ "mayoristapp_relay_count": 44, "relays": [ "jcart/relay.php", ... ] }` — orden y cantidad alineados a `ecom.services.mayoristapp_relays.MAYORISTAPP_RELAY_PATHS`.

### Endpoints relay catálogo (mayoristapp)

Ver [SPEC_CATALOGO_RUBRO.md](./SPEC_CATALOGO_RUBRO.md).

| Ruta | Permiso |
|------|---------|
| GET `/ecom/api/mayoristapp/catalogo/rubros/` | `EcomMayoristappSessionPermission` |
| GET `/ecom/api/mayoristapp/catalogo/subrubros/` | `EcomMayoristappSessionPermission` |
| POST `/ecom/api/mayoristapp/catalogo/filtro-rubro-catalogo/` | `EcomMayoristappSessionPermission` |
| POST `/ecom/api/mayoristapp/catalogo/articulos/autocomplete/` | `EcomMayoristappSessionPermission` |
| GET `/ecom/api/mayoristapp/catalogo/subrubros-tipo-cliente/` | `EcomMayoristappSessionPermission` |

---

## 2.4 — Autenticación y permisos

- **Sistema:** `django.contrib.auth` para usuarios Synap; para paridad con vendedores PHP, autenticación contra MySQL vía flujo documentado en `login`/`core` (fuera del alcance mínimo de este módulo).
- **Login PHP:** AES en SQL → **no** replicar; **[DECISIÓN-1]** mapear `usuarios.cod_usuario` a usuario Django o token de sesión legacy tras validación única.

---

## 2.5 — Serializers

- Fase inicial: sin DRF serializers; respuestas dict → JSON.
- **[DECISION PENDIENTE]** Introducir `Ecom*` serializers cuando se expongan recursos REST de negocio.

---

## 2.6 — Tareas asíncronas

- Ninguna en alcance inicial.
- Sustitutos de `sincroniza.php` / cron: **[DECISION PENDIENTE]** Celery beat vs management command programado.

---

## 2.7 — Decisiones de diseño

**[DECISIÓN-1] Metadatos sin datos de negocio**  
*Contexto:* Paridad testeable sin BD MySQL en CI.  
*Opciones:* A) Solo constantes en código, B) Leer árbol PHP en runtime.  
*Decisión:* A) Constantes en `migration_info.py` alineadas al documento de ingeniería inversa.  
*Consecuencias:* Si el clon PHP cambia, actualizar constantes + doc.

**[DECISIÓN-2] Checkpoints en PostgreSQL**  
*Contexto:* TDD requiere modelos persistibles.  
*Opciones:* A) Tabla `EcomMigrationCheckpoint`, B) solo tests en memoria.  
*Decisión:* A).  
*Consecuencias:* Migración Django adicional pequeña.

**[DECISIÓN-3] Informes ventas netas**  
*Contexto:* Duplicación con `reports`.  
*Opciones:* A) Extender `reports`, B) duplicar SQL en `ecom`.  
*Decisión:* A) cuando se migre el relay.  
*Consecuencias:* Coordinación de releases con módulo reportes.

---

## Tags [DECISION PENDIENTE] (seguimiento)

- FK exactas y dump MySQL de producción.
- Fórmulas completas en `util-calculaprecio.inc.php`.
- Inventario cron en servidor PHP.
