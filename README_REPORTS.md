# 📊 Synap - Instalación Mínima para Reportes

Esta rama contiene una instalación mínima de Synap configurada **únicamente para el módulo de Reportes**.

## 🎯 Características

- ✅ Módulo de Reportes completo (`reports`)
- ✅ Autenticación con administraNET (`core`, `login`)
- ✅ Dashboard básico (`dashboard`)
- ✅ Sistema de permisos y roles (`core`)
- ❌ Reports AI eliminado
- ❌ administraNET_integration eliminado
- ❌ Todos los módulos de negocio eliminados (sales, inventory, purchases, etc.)
- ❌ Celery eliminado (sin tareas asíncronas)
- ❌ Qdrant eliminado (sin vector database)

## 📦 Módulos Incluidos

### Apps Django
- `core` - Base del sistema (usuarios, empresas, permisos)
- `login` - Autenticación
- `dashboard` - Dashboard principal
- `reports` - Módulo de reportes

### Apps de Terceros
- `theme` - Sistema de UI/Templates
- `tailwind` - Framework CSS
- `rest_framework` - API REST
- `widget_tweaks` - Mejoras de widgets
- `crispy_forms` - Formularios mejorados
- `corsheaders` - CORS

## 🐳 Servicios Docker

### Requeridos
- `app` - Aplicación Django
- `db` - PostgreSQL (base de datos principal)
- `redis` - Cache (opcional pero recomendado)

### Eliminados
- `celery_worker` - No necesario
- `celery_beat` - No necesario
- `qdrant` - No necesario

## 📋 Dependencias Python

Ver `requirements.txt` para la lista completa. Las dependencias eliminadas incluyen:
- Celery y django-celery-beat
- OpenAI, CrewAI, LangChain (para Reports AI)
- FastAPI y Uvicorn
- Firebase Admin
- Geopy

## ⚙️ Configuración

### Variables de Entorno (.env)

```bash
# Django
DEBUG=False
SECRET_KEY=tu_clave_secreta
ALLOWED_HOSTS=synap.administranet.com.ar,localhost
SITE_URL=https://synap.administranet.com.ar

# PostgreSQL
POSTGRES_DB=synap_db
POSTGRES_USER=synap_user
POSTGRES_PASSWORD=tu_password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# MySQL (administraNET) - Para autenticación
DB_NAME=administranet
DB_USER=administranet
DB_PASSWORD=tu_password_mysql
DB_HOST=tu_host_mysql
DB_PORT=3306

# Redis (opcional)
REDIS_URL=redis://redis:6379/0
```

## 🚀 Instalación

1. **Clonar y cambiar a la rama Reports:**
```bash
git clone <repo>
git checkout Reports
```

2. **Configurar variables de entorno:**
```bash
cp env.example .env
# Editar .env con tus configuraciones
```

3. **Construir e iniciar servicios:**
```bash
docker-compose build
docker-compose up -d
```

4. **Aplicar migraciones:**
```bash
docker exec Synap_app python manage.py migrate
```

5. **Crear superusuario (opcional):**
```bash
docker exec -it Synap_app python manage.py createsuperuser
```

## 🔗 URLs Disponibles

- `/login/` - Login
- `/core/dashboard/` - Dashboard principal
- `/reports/` - Catálogo de reportes
- `/api/reports/` - API REST de reportes
- `/admin/` - Panel de administración Django

## 📝 Notas

- La conexión a MySQL de administraNET se mantiene para autenticación, pero el módulo `administraNET_integration` no está instalado.
- Redis es opcional pero recomendado para cache de reportes y permisos.
- Si no se usa Redis, cambiar `CACHES` en `settings.py` a `django.core.cache.backends.locmem.LocMemCache`.

## 🔄 Diferencias con la rama principal

| Característica | Rama Principal | Rama Reports |
|----------------|---------------|--------------|
| Reports | ✅ | ✅ |
| Reports AI | ✅ | ❌ |
| administraNET_integration | ✅ | ❌ |
| Módulos de negocio | ✅ | ❌ |
| Celery | ✅ | ❌ |
| Qdrant | ✅ | ❌ |

## 📊 Reducción de Tamaño

Esta rama ha sido optimizada para ocupar el menor espacio posible:
- ✅ **1066 archivos eliminados** del repositorio
- ✅ Solo se mantienen los módulos esenciales: `core`, `login`, `dashboard`, `reports`, `theme`
- ✅ Eliminados todos los módulos de negocio, Reports AI, y dependencias no necesarias
- ✅ Eliminados archivos de prueba, scripts de desarrollo y documentación innecesaria

### Archivos Mantenidos
- Módulos Django: `core/`, `login/`, `dashboard/`, `reports/`, `theme/`, `django_project/`
- Configuración: `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `env.example`
- Archivos raíz: `manage.py`, `.gitignore`, `README_REPORTS.md`

---

**Rama:** Reports  
**Última actualización:** 2025-12-01  
**Archivos eliminados:** 1066  
**Estado:** Instalación mínima optimizada

