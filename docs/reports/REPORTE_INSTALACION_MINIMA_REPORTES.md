# 📊 Reporte de Instalación Mínima - Módulo de Reportes

## 🎯 Objetivo
Este documento detalla la configuración mínima necesaria para tener **solo la funcionalidad de Reportes** en Synap, eliminando todos los módulos que no son restrictivos o necesarios.

## Estado actual (instalación mínima vigente)

En el proyecto actual, **INSTALLED_APPS** incluye únicamente: **core**, **login**, **dashboard**, **reports**, **self_checkout** (+ theme y terceros). **No están instalados:** reports_ai, administraNET_integration, sales, inventory, tiendanube, mercadopago, etc. La conexión a MySQL de administraNET se hace desde **login** (AdministraNETAuth) y **reports** (connection_pool), sin la app `administraNET_integration`. Los apartados siguientes que mencionan "Reports AI" y "AdministraNET Integration" son opcionales o de referencia para una instalación ampliada.

---

## ✅ Módulos REQUERIDOS (No se pueden eliminar)

### 1. **Core** (`core`)
**Razón:** Módulo fundamental del sistema
- **Modelos necesarios:**
  - `Empresa` - Usado por `reports.models.ReportDefinition` (y por reports_ai si se instala)
  - `UsuarioExtendido` - Modelo de usuario personalizado (AUTH_USER_MODEL)
  - `Permiso` - Sistema de permisos
  - `Rol` - Sistema de roles
- **Servicios necesarios:**
  - `core.middleware.*` - Middleware de autenticación y permisos
  - `core.context_processors.*` - Context processors para templates
  - `core.services.administranet_permiso_sistema.*` - Servicios de permisos
- **Dependencias:**
  - Conexión a MySQL externo (administraNET) para autenticación
  - Conexión a PostgreSQL (base de datos principal)

### 2. **Login** (`login`)
**Razón:** Sistema de autenticación
- URLs: `/login/`
- Templates de login
- Integración con autenticación de administraNET

### 3. **Dashboard** (`dashboard`)
**Razón:** Redirección inicial y vista principal
- URL: `/core/dashboard/`
- Redirección después del login

### 4. **Reports** (`reports`)
**Razón:** Módulo principal de reportes
- **Modelos:**
  - `ReportDefinition` - Definiciones de reportes
  - `ReportWidget` - Widgets de visualización
  - `ReportDashboard` - Dashboards personalizados
  - `ReportExecutionLog` - Logs de ejecución
  - `ReportWorkspace` - Workspaces de usuarios
- **URLs:** `/reports/`
- **APIs:** `/api/reports/`
- **Dependencias:**
  - `core.models.Empresa`
  - `core.models.UsuarioExtendido`
  - PostgreSQL para almacenar definiciones

### 5. **Reports AI** (`reports_ai`) - NO INSTALADO en mínima actual
**Razón (si se instalara):** Sistema de reportes con IA (CrewAI)
- **Modelos:**
  - `ReportRequest` - Solicitudes de reportes
  - `BusinessRule` - Reglas de negocio
  - `AgentMetrics` - Métricas de agentes
  - `NLUTrainingExample` - Ejemplos de entrenamiento NLU
  - `ChatConversation` - Conversaciones de chat
  - `ChatMessage` - Mensajes de chat
  - Y otros modelos relacionados
- **URLs:** `/reports-ai/`
- **Dependencias:**
  - `core.models.Empresa`
  - `administraNET_integration` (para conexión a MySQL)
  - OpenAI API (para agentes de IA)
  - CrewAI framework

### 6. **AdministraNET Integration** (`administraNET_integration`) - NO INSTALADO en mínima actual
**Razón (si se instalara):** Conexión a base de datos MySQL de administraNET. En la instalación mínima actual la conexión MySQL se hace desde **login** y **reports** (sin esta app).
- **Modelos:**
  - `AdministraNETConfig` - Configuración de conexión
- **Servicios:**
  - `AdministraNETConnectionService` - Servicio de conexión MySQL
- **Nota:** Las validaciones que dependen de `inventory` y `sales` son **opcionales** y no bloquean la funcionalidad básica

### 7. **Theme** (`theme`)
**Razón:** Sistema de UI/Templates
- Templates base
- Assets estáticos (CSS, JS)
- Tailwind CSS

---

## ❌ Módulos ELIMINABLES (No necesarios para Reportes)

### Módulos de Negocio
- ❌ `sales` - Ventas
- ❌ `inventory` - Inventario
- ❌ `purchases` - Compras
- ❌ `accounting` - Contabilidad
- ❌ `finance` - Finanzas
- ❌ `logistics` - Logística
- ❌ `mercadopago` - Integración MercadoPago
- ❌ `clover` - Integración Clover
- ❌ `tiendanube` - Integración TiendaNube
- ❌ `tiendanube_administranet` - Sincronización TiendaNube-AdministraNET
- ❌ `support_ai` - Soporte AI

**Nota:** Estos módulos pueden tener validaciones en `administraNET_integration`, pero son opcionales y no afectan la funcionalidad básica de conexión MySQL.

---

## 📦 Dependencias de Python (requirements.txt)

### REQUERIDAS (Core)
```python
Django==4.2
djangorestframework
psycopg2-binary==2.9.9
gunicorn==21.2.0
whitenoise==6.9.0
dj-database-url==0.5.0
django-tailwind
requests
PyJWT==2.8.0
cryptography
python-decouple
mysqlclient==2.2.7  # Para conexión a MySQL de administraNET
django-allauth
django-redis
django-crispy-forms==2.4
crispy-tailwind==1.0.3
Pillow==10.1.0
six==1.16.0
django-widget-tweaks==1.5.0
django-filter
PyYAML
django-cors-headers
mysql-connector-python
defusedxml
bleach
geopy
openpyxl  # Para exportación de reportes
reportlab  # Para exportación PDF
```

### OPCIONALES (Solo si se usa Reports AI)
```python
celery>=5.2  # Solo si se usan tareas asíncronas
django-celery-beat>=2.8.1  # Solo si se usan tareas programadas
openai>=1.10.0  # Para Reports AI
crewai>=0.28.0  # Para Reports AI
langchain>=0.1.0  # Para Reports AI
langchain-openai>=0.0.5  # Para Reports AI
```

### ELIMINABLES (No necesarios)
```python
fastapi  # Solo si se usa API FastAPI separada
firebase-admin  # Firebase deshabilitado
uvicorn  # Solo para FastAPI
```

---

## 🐳 Servicios Docker (docker-compose.yml)

### REQUERIDOS
```yaml
services:
  app:
    # Aplicación Django
    build: .
    container_name: Synap_app
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      - db
      - redis  # Opcional, solo si se usa cache
    command: python manage.py runserver 0.0.0.0:8002
    restart: unless-stopped

  db:
    # PostgreSQL - Base de datos principal
    image: postgres:13
    container_name: Synap_db
    env_file:
      - .env
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5435:5432"
    restart: unless-stopped

  redis:
    # Redis - Cache (opcional pero recomendado)
    image: redis:6-alpine
    container_name: Synap_redis
    ports:
      - "6381:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --stop-writes-on-bgsave-error no
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### ELIMINABLES
```yaml
  celery_worker:  # Solo si se usan tareas asíncronas
  celery_beat:    # Solo si se usan tareas programadas
  qdrant:         # Solo si se usa vector database para AI
```

---

## ⚙️ Configuración Django (settings.py)

### INSTALLED_APPS - Mínimo Requerido
```python
INSTALLED_APPS = [
    # Terceros
    'theme',
    'tailwind',
    'rest_framework',
    'widget_tweaks',
    
    # Django Core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'corsheaders',
    'crispy_forms',
    'crispy_tailwind',
    
    # Apps propias - Mínimo para Reportes
    'core',
    'login',
    'dashboard',
    'reports',
    # 'reports_ai',  # Opcional - Solo si se usa Reports AI
    # 'administraNET_integration',  # Requerido solo si se usa Reports AI
]
```

### MIDDLEWARE - Mínimo Requerido
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.RequestUserMiddleware',
    'core.middleware.AdminAccessMiddleware',
    'core.middleware.DeviceDetectionMiddleware',
    'core.middleware.module_middleware.ModuleMiddleware',
    'core.middleware.module_middleware.ModulePermissionMiddleware',
    'core.middleware.module_middleware.ModuleContextMiddleware',
    'core.middleware.module_middleware.ModuleCacheMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_project.settings.custom_ajax_login_required',
]
```

### DATABASES - Requerido
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('POSTGRES_DB', default='synap_db'),
        'USER': config('POSTGRES_USER', default='synap_user'),
        'PASSWORD': config('POSTGRES_PASSWORD', default='mypassword'),
        'HOST': config('POSTGRES_HOST', default='db'),
        'PORT': config('POSTGRES_PORT', default='5432'),
    },
    'mysql': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', default='administranet'),
        'USER': config('DB_USER', default='administranet'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='mysql'),
        'PORT': config('DB_PORT', default='3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'latin1',
        },
    }
}
```

### CACHES - Opcional pero Recomendado
```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://redis:6379/0'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'decode_responses': False,
            }
        }
    }
}
```

### CELERY - Solo si se usa Reports AI con tareas asíncronas
```python
# Comentar si no se usa Reports AI o tareas asíncronas
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
```

---

## 🔗 URLs (urls.py)

### URLs Mínimas Requeridas
```python
urlpatterns = [
    path('', lambda request: redirect('/core/dashboard/')),
    path("__/auth/handler", TemplateView.as_view(template_name="login/auth_handler.html")),
    path("admin/", admin.site.urls),
    path("login/", include("login.urls")),
    path("core/", include("core.urls", namespace="core")),
    path('core/api/', include('core.api.urls', namespace='core_api')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('api/reports/', include('reports.api_urls', namespace='reports-api')),
    # path('reports-ai/', include('reports_ai.urls', namespace='reports_ai')),  # Opcional
]
```

---

## 📋 Variables de Entorno (.env)

### REQUERIDAS
```bash
# Django
DEBUG=False
SECRET_KEY=tu_clave_secreta_aqui
ALLOWED_HOSTS=synap.administranet.com.ar,localhost,127.0.0.1
SITE_URL=https://synap.administranet.com.ar

# PostgreSQL
POSTGRES_DB=synap_db
POSTGRES_USER=synap_user
POSTGRES_PASSWORD=tu_password_seguro
POSTGRES_HOST=db
POSTGRES_PORT=5432

# MySQL (administraNET)
DB_NAME=administranet
DB_USER=administranet
DB_PASSWORD=tu_password_mysql
DB_HOST=tu_host_mysql
DB_PORT=3306

# Redis (opcional pero recomendado)
REDIS_URL=redis://redis:6379/0
```

### OPCIONALES (Solo si se usa Reports AI)
```bash
# OpenAI (para Reports AI)
OPENAI_API_KEY=tu_api_key_openai

# Celery (solo si se usan tareas asíncronas)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### ELIMINABLES
```bash
# TiendaNube
TIENDANUBE_ACCESS_TOKEN=
TIENDANUBE_STORE_ID=
TIENDANUBE_WEBHOOK_SECRET=

# Firebase
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

---

## 🗄️ Base de Datos

### PostgreSQL (default)
**Tablas necesarias:**
- Todas las tablas de `core` (usuarios, empresas, permisos, roles)
- Todas las tablas de `reports` (report_definitions, report_widgets, etc.)
- Todas las tablas de `reports_ai` (si se usa)
- Tablas de Django (auth, sessions, admin, etc.)

### MySQL (mysql)
**Conexión externa a administraNET:**
- Base de datos de administraNET Gestión
- Tablas: `usuarios`, `puestos`, `permiso_sistema_puesto`, `empresas`, etc.
- **No se crean tablas en esta BD**, solo se lee

---

## 🚀 Pasos de Instalación Mínima

### 1. Limpiar INSTALLED_APPS
```python
# En settings.py, comentar módulos no necesarios:
INSTALLED_APPS = [
    # ... apps de Django y terceros ...
    'core',
    'login',
    'dashboard',
    'reports',
    # 'reports_ai',  # Opcional
    # 'administraNET_integration',  # Solo si se usa Reports AI
]
```

### 2. Limpiar URLs
```python
# En urls.py, comentar URLs de módulos eliminados
# Mantener solo:
# - login
# - core
# - reports
# - reports_ai (opcional)
```

### 3. Limpiar requirements.txt
```bash
# Eliminar dependencias no necesarias:
# - fastapi
# - uvicorn
# - firebase-admin (ya está comentado)
```

### 4. Limpiar docker-compose.yml
```yaml
# Eliminar servicios:
# - celery_worker
# - celery_beat
# - qdrant (si no se usa Reports AI)
```

### 5. Aplicar Migraciones
```bash
# Solo migraciones de módulos activos
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear Usuario Superusuario (si es necesario)
```bash
python manage.py createsuperuser
```

---

## ⚠️ Consideraciones Importantes

### 1. **administraNET_integration y Validaciones**
- El módulo `administraNET_integration` tiene validaciones que importan `inventory` y `sales`
- **Estas validaciones son opcionales** y no bloquean la funcionalidad básica
- Si se eliminan `inventory` y `sales`, las validaciones fallarán al importar, pero:
  - La conexión MySQL funciona correctamente
  - `reports_ai` puede usar `AdministraNETConnectionService` sin problemas
  - **Solución:** Comentar o eliminar las validaciones que dependen de módulos eliminados

### 2. **Celery y Tareas Asíncronas**
- Si se elimina Celery, asegurarse de que:
  - No hay tareas programadas en `CELERY_BEAT_SCHEDULE`
  - No se importan tareas de Celery en el código activo
  - `reports_ai` puede funcionar sin Celery (síncrono)

### 3. **Redis**
- Redis es **opcional** pero **altamente recomendado** para:
  - Cache de reportes
  - Cache de permisos
  - Sesiones (si se configura)
- Si se elimina Redis, cambiar `CACHES` a `django.core.cache.backends.locmem.LocMemCache`

### 4. **Reports AI**
- `reports_ai` es **completamente opcional**
- Si no se usa, se puede eliminar completamente
- Si se usa, requiere:
  - `administraNET_integration`
  - OpenAI API key
  - CrewAI y LangChain

### 5. **Middleware de Módulos**
- Los middlewares de módulos (`ModuleMiddleware`, `ModulePermissionMiddleware`, etc.) son **necesarios**
- Gestionan el acceso a módulos basado en permisos
- Sin ellos, el sistema de permisos no funcionará correctamente

---

## 📊 Resumen de Módulos

| Módulo | Estado | Razón |
|--------|--------|-------|
| `core` | ✅ REQUERIDO | Base del sistema |
| `login` | ✅ REQUERIDO | Autenticación |
| `dashboard` | ✅ REQUERIDO | Redirección inicial |
| `reports` | ✅ REQUERIDO | Funcionalidad principal |
| `reports_ai` | ⚠️ OPCIONAL | Solo si se usa IA |
| `administraNET_integration` | ⚠️ OPCIONAL | Solo si se usa Reports AI |
| `theme` | ✅ REQUERIDO | UI/Templates |
| `sales` | ❌ ELIMINABLE | No necesario |
| `inventory` | ❌ ELIMINABLE | No necesario |
| `purchases` | ❌ ELIMINABLE | No necesario |
| `accounting` | ❌ ELIMINABLE | No necesario |
| `finance` | ❌ ELIMINABLE | No necesario |
| `logistics` | ❌ ELIMINABLE | No necesario |
| `mercadopago` | ❌ ELIMINABLE | No necesario |
| `clover` | ❌ ELIMINABLE | No necesario |
| `tiendanube` | ❌ ELIMINABLE | No necesario |
| `tiendanube_administranet` | ❌ ELIMINABLE | No necesario |
| `support_ai` | ❌ ELIMINABLE | No necesario |

---

## 🔍 Verificación Post-Instalación

### 1. Verificar que el servidor inicia
```bash
python manage.py runserver
```

### 2. Verificar que las URLs funcionan
- `/login/` - Debe mostrar login
- `/core/dashboard/` - Debe mostrar dashboard
- `/reports/` - Debe mostrar catálogo de reportes
- `/reports-ai/` - Solo si se instaló Reports AI

### 3. Verificar que no hay imports rotos
```bash
python manage.py check
```

### 4. Verificar migraciones
```bash
python manage.py showmigrations
# Debe mostrar solo migraciones de módulos activos
```

---

## 📝 Notas Finales

1. **Este es un reporte de instalación mínima**. Para producción, se recomienda mantener Redis y considerar Reports AI si se necesita funcionalidad avanzada.

2. **Las validaciones de administraNET_integration** que dependen de módulos eliminados deben ser comentadas o eliminadas para evitar errores de importación.

3. **El sistema de permisos** funciona completamente con solo los módulos requeridos, ya que los permisos se gestionan desde la base de datos MySQL de administraNET.

4. **La autenticación** funciona completamente con solo `core` y `login`, ya que se conecta directamente a MySQL de administraNET.

---

**Fecha de creación:** 2025-12-01  
**Versión:** 1.0  
**Autor:** Análisis automatizado del proyecto Synap

