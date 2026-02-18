# Support – Docker Compose (independiente de Synap)

Support es un producto independiente: este stack (PostgreSQL, Redis, backend Django, opcional frontend) **no comparte servicios ni red con Synap**. El backend de Support debe levantarse siempre con este compose, nunca dentro del contenedor o red de Synap.

Levanta todo el stack: PostgreSQL (pgvector), Redis, backend Django y opcionalmente frontend en modo dev y MinIO.

## Requisitos

- Docker y Docker Compose (v2).
- En `.env` debes definir **CONFIG_ENCRYPTION_KEY** (clave Fernet para cifrar la configuración por UI). Generar con:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

## Uso rápido

**Desde este directorio** (si estás en la raíz del repo, `support/docker`; si ya estás en `support/`, solo `cd docker`):

```bash
cd support/docker   # desde la raíz del repo
# o:  cd docker     # si ya estás en support/
cp .env.example .env
# Editar .env y poner CONFIG_ENCRYPTION_KEY=...
docker compose up -d
```

**Desde la raíz del repo** (solo Support, no levanta Synap). Usar siempre `-p support` para que stop/down desde raíz afecten a estos contenedores:

```bash
docker compose -f docker-compose.support.yml -p support up -d
# Para parar: docker compose -f docker-compose.support.yml -p support down
```

El `.env` se lee de `support/docker/.env`; créalo desde `support/docker/.env.example` antes de usar la opción desde raíz.

Con esto se levantan:

- **db** (PostgreSQL 16 + pgvector) en `localhost:5432`
- **redis** en `localhost:6379`
- **backend** (Django, migrate + gunicorn) en **http://localhost:8250**

Crear usuario admin (con TTY para poder escribir usuario y contraseña):

```bash
docker compose exec -it backend python manage.py createsuperuser
```

Si no tienes TTY (script o CI), crear desde shell:

```bash
docker compose exec backend python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'changeme')
    print('Superuser admin creado. Cambiar contraseña en /admin/')
else:
    print('Ya existe usuario admin')
"
```

Luego en **http://localhost:8250/admin/** → Perfiles de agente → asignar rol **Administrador** a ese usuario.

### Frontend en modo desarrollo

Para levantar también el frontend (Vite, hot reload) en **http://localhost:3000**:

```bash
docker compose --profile dev up -d
```

El navegador debe poder alcanzar el backend en `http://localhost:8250` (configurado por defecto en `VITE_API_BASE_URL` en `.env`).

### MinIO (almacenamiento S3)

Si quieres MinIO para adjuntos/storage:

```bash
docker compose --profile storage up -d
```

En `.env` del directorio `docker` (o en el backend) configura:

- `S3_ENDPOINT_URL=http://minio:9000`
- `S3_ACCESS_KEY=minioadmin`
- `S3_SECRET_KEY=minioadmin`
- `S3_BUCKET_NAME=support-attachments`

Y crea el bucket en MinIO (por ejemplo desde la consola en http://localhost:9000).

## Servicios y puertos

| Servicio   | Puerto por defecto | Descripción                    |
|-----------|--------------------|--------------------------------|
| backend   | 8250               | API Django + admin             |
| frontend  | 3000               | SPA React (solo con `--profile dev`) |
| db        | 5432               | PostgreSQL + pgvector          |
| redis     | 6379               | Redis                          |
| minio     | 9000               | S3 compatible (solo con `--profile storage`) |

## Parar contenedores manualmente

Si `docker compose down` o `docker compose -f docker-compose.support.yml -p support down` no detectan los contenedores, pararlos por nombre:

```bash
docker stop support_backend support_redis support_db
```

Opcional: eliminarlos (para poder volver a levantar con compose sin conflicto):

```bash
docker rm support_backend support_redis support_db
```

## Comandos útiles

```bash
# Ver logs del backend
docker compose logs -f backend

# Migraciones a mano
docker compose exec backend python manage.py migrate

# Crear superusuario
docker compose exec backend python manage.py createsuperuser

# Shell Django
docker compose exec backend python manage.py shell

# Parar todo
docker compose down
```

## Volúmenes

- `support_postgres_data`: datos de PostgreSQL.
- `support_redis_data`: datos de Redis.
- `support_static`: staticfiles del backend.
- `support_frontend_node_modules`: node_modules del frontend (para no reinstalar en cada arranque).
- `support_minio_data`: datos de MinIO (si usas el perfil storage).

Documentación general: [support/docs/PASO_A_PASO_PONER_EN_MARCHA.md](../docs/PASO_A_PASO_PONER_EN_MARCHA.md).
