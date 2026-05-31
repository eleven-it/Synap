# Guía de Instalación - Synap

Esta guía explica cómo instalar y configurar Synap en una nueva instancia.

## Implementación en servidor Staging (paso a paso)

**→ [docs/general/GUIA_IMPLEMENTACION_SERVIDOR_STAGING.md](docs/general/GUIA_IMPLEMENTACION_SERVIDOR_STAGING.md)**

Incluye: Deploy Key SSH, clone rama `Staging`, Docker, `.env`, arranque automático con DB limpia y systemd.

---

## Instalación Automática (Recomendada)

El script `docker-entrypoint.sh` ejecuta al iniciar el contenedor:

1. Espera a que PostgreSQL y Redis estén listos  
2. Detecta instalación nueva (sin tabla `django_migrations`)  
3. Aplica **migrate** completo en PostgreSQL  
4. En **DB nueva**: `bootstrap_instalacion` (módulos `core`, `login`, `dashboard`, `reports` + permisos)  
5. En **DB existente**: `fix_reports_migrations` + `setup_reports_installation`  
6. Recolecta archivos estáticos e inicia el servidor  

### Pasos de Instalación (resumen)

1. **Clonar el repositorio:**
```bash
git clone -b Staging git@github.com:eleven-it/Synap.git
cd Synap
```

2. **Configurar variables de entorno:**
```bash
cp env.example .env
# Editar .env (ver guía Staging)
```

3. **Construir e iniciar contenedores:**
```bash
docker compose build
docker compose up -d
```

Con volumen Postgres nuevo, no hace falta ejecutar `migrate` manualmente.

## Instalación Manual

Si la instalación automática falla:

### Migraciones y bootstrap

```bash
docker compose run --rm --entrypoint "" \
  -e SYNAP_MIGRATIONS_POSTGRES_ONLY=1 \
  app python manage.py migrate --noinput

docker exec Synap_app python manage.py bootstrap_instalacion --force
docker compose up -d app
```

### Configurar módulo Reports

```bash
docker exec Synap_app python manage.py setup_reports_installation --skip-migrations
```

### Recolectar archivos estáticos

```bash
docker exec Synap_app python manage.py collectstatic --noinput
```

## Verificación de Instalación

```bash
docker exec Synap_app python manage.py setup_modules --list
docker exec Synap_app python manage.py check
docker exec Synap_app python manage.py debug_permissions <usuario>
```

## Comandos Útiles

```bash
docker exec Synap_app python manage.py bootstrap_instalacion --help
docker exec Synap_app python manage.py activate_reports
docker exec Synap_app python manage.py showmigrations reports
docker exec Synap_app python manage.py migrate reports
```

## Solución de Problemas

### Bucle de reinicio en primera instalación

Actualizar al entrypoint reciente o ejecutar:

```bash
docker compose stop app
docker compose run --rm --entrypoint "" -e SYNAP_MIGRATIONS_POSTGRES_ONLY=1 app python manage.py migrate --noinput
docker exec Synap_app python manage.py bootstrap_instalacion --force
docker compose up -d app
```

### Error: "relation reports_reportdefinition does not exist"

```bash
docker exec Synap_app python manage.py migrate reports
```

### Módulo reports inactivo

```bash
docker exec Synap_app python manage.py bootstrap_instalacion --force
```

## Estructura de Archivos

- `docker-entrypoint.sh` — Inicialización automática (migrate + bootstrap)  
- `core/management/commands/bootstrap_instalacion.py` — Primera instalación  
- `core/management/commands/setup_reports_installation.py` — Módulo Reports  
- `core/management/commands/fix_reports_migrations.py` — Reparación reports (solo DB existente)  

## Notas

- En producción/staging: `ENVIRONMENT=production`, secretos obligatorios — [SEGURIDAD_CAMBIOS_SYNAP.md](docs/general/SEGURIDAD_CAMBIOS_SYNAP.md)  
- La documentación detallada vive en **Desarrollo** (`docs/`); Staging no incluye `docs/`  
