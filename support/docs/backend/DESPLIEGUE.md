# Despliegue del Backend

## Requisitos

- Python 3.10+
- PostgreSQL (con extensión pgvector opcional para RAG futuro)
- Redis
- Opcional: MinIO o S3 para adjuntos

## Instalación local

```bash
cd support/backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Editar .env (DATABASE_URL, REDIS_URL, SECRET_KEY, etc.)
export DJANGO_SETTINGS_MODULE=config.settings.local
python manage.py migrate
python manage.py createsuperuser
# Crear perfil de agente en Admin → Perfiles de agente para el usuario creado
```

## Scripts de arranque

- **scripts/run.sh** — Ejecuta `migrate --noinput` y `runserver 0.0.0.0:8000`. Útil en desarrollo.
- Para producción se usa **gunicorn** (no runserver). Ejemplo:  
  `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2`

## Docker

- **Dockerfile** en `support/backend`: imagen basada en Python 3.11-slim; instala dependencias, copia el código y define CMD que ejecuta `migrate` y luego `gunicorn` en el puerto 8000.
- Construcción: `docker build -t support-backend .` desde `support/backend`.
- Variables de entorno: inyectar las mismas que en `.env.example` (DATABASE_URL, REDIS_URL, SECRET_KEY, etc.). En Compose se suelen definir en `environment` o en un archivo `env_file`.

## Healthcheck

- **GET /api/health/** — Sin autenticación. Responde 200 con JSON: `status`, `db`, `redis`, `environment`.
- Criterio recomendado para el healthcheck del contenedor: respuesta 200 y, si se desea comprobar dependencias, `db: "ok"` y `redis: "ok"`. No se exige que Synap ni S3 estén disponibles para marcar el servicio como healthy.

## Celery (worker y beat)

- Misma imagen que el backend; comando distinto:
  - Worker: `celery -A config worker -l info`
  - Beat: `celery -A config beat -l info`
- Deben tener acceso a la misma REDIS_URL y DATABASE_URL que el backend.

## Recopilación de estáticos

- En producción, si se sirven estáticos con el mismo proceso: `python manage.py collectstatic --noinput`. El Dockerfile puede incluir este paso antes del CMD. Alternativamente, servir estáticos con nginx u otro servidor frontal.

## Resumen para Docker Compose

- Servicios típicos: **backend** (migrate + gunicorn), **worker** (celery worker), **beat** (celery beat), **postgres**, **redis**, y opcionalmente **minio** para desarrollo.
- Backend depende de postgres y redis; worker y beat de redis (y en la práctica de postgres para las tareas). Variables de entorno comunes para los tres (backend, worker, beat).
