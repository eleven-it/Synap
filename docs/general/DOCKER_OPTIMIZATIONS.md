# Optimizaciones Docker para Synap

> **Revisar contra código actual.** Verificar que `Dockerfile` y `docker-compose.yml` coincidan con lo descrito; este doc puede reflejar optimizaciones parcialmente aplicadas o variantes (p. ej. Reports-AI no está en la instalación mínima).

## Arranque automático (Docker Desktop / WSL)

En `docker-compose.yml` (y MySQL local) los servicios usan `restart: unless-stopped` para que, al reiniciar Docker Desktop o WSL, los contenedores vuelvan solos.

Además:

- **healthchecks** en `db` y `redis`; `app` espera `condition: service_healthy` antes de arrancar (evita fallos en frío).
- **healthcheck** de `app` contra `http://127.0.0.1:8000/` con `start_period` generoso (migrate/entrypoint).

**Importante:** la política solo aplica a contenedores recreados. Después de cambiar el compose, en WSL:

```bash
docker compose up -d
# Si también usás MySQL local:
docker compose -f docker-compose.mysql.yml up -d
```

En Docker Desktop: Settings → General → “Start Docker Desktop when you sign in”. No detengas los contenedores a mano si querés que vuelvan tras el reboot (`unless-stopped` no reinicia los que el usuario paró con `docker stop`).

Si el bind mount del proyecto WSL aún no está disponible al primer intento, el entrypoint falla y Docker reintenta por la política de restart.

## Resumen de Optimizaciones

Este documento detalla las optimizaciones realizadas en la configuración Docker para reducir significativamente el tiempo de construcción y el tamaño de las imágenes.

## 🚀 Optimizaciones Implementadas

### 1. Imágenes Base Optimizadas

#### Dockerfile Principal
- **Antes**: `python:3.10` (1.2GB)
- **Después**: `python:3.10-slim` (400MB)
- **Reducción**: ~67% en tamaño base

#### Dockerfile Reports-AI
- **Antes**: `pytorch/pytorch:2.0.1-cuda11.7-cudnn8-runtime` (3.1GB)
- **Después**: `pytorch/pytorch:latest` (2.8GB)
- **Reducción**: ~10% en tamaño base

### 2. Consolidación de Capas

#### Antes (Múltiples capas):
```dockerfile
RUN apt-get update && apt-get install -y gnupg2 ca-certificates
RUN apt-get install -y curl
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
RUN apt-get install -y nodejs
RUN npm install -g npm@latest
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/*
```

#### Después (Una sola capa):
```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl gnupg2 ca-certificates build-essential \
        gcc default-libmysqlclient-dev python3-dev gettext \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && apt-get purge -y build-essential gcc python3-dev \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
```

### 3. Optimización de Dependencias Python

#### Antes:
```dockerfile
RUN pip install -r requirements.txt
RUN pip install --upgrade --force-reinstall certifi
```

#### Después:
```dockerfile
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --upgrade --force-reinstall certifi \
    && rm -rf ~/.cache/pip
```

### 4. Docker Compose Optimizado

#### Imágenes Base Ligeras:
- **PostgreSQL**: `postgres:15-alpine` (vs `postgres:15`)
- **Redis**: `redis:7-alpine` (vs `redis:7`)

#### Health Checks:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U myuser -d mydatabase"]
  interval: 30s
  timeout: 10s
  retries: 3
```

#### Límites de Recursos:
```yaml
deploy:
  resources:
    limits:
      memory: 2G
    reservations:
      memory: 512M
```

#### Cache de Construcción:
```yaml
build: 
  context: .
  cache_from:
    - python:3.10-slim
```

### 5. .dockerignore Optimizado

Excluye archivos innecesarios del contexto de construcción:
- Archivos de desarrollo y IDE
- Logs y archivos temporales
- Media y static files (se montan como volúmenes)
- Documentación y tests
- Node modules **anidados** (`**/node_modules`: `theme/` y `support/frontend/`)
- Git anidado y copias (`.git.corrupt-*`, `**/.git` dentro de `administraNET-ecom/`)
- Árboles locales que no usa la imagen `Synap_app`: `administraNET-ecom/`, `administranet_vb6/`, `Best Sox/`, `support/`

`.gitignore` **no** se aplica a `docker compose build`. Si un directorio está en gitignore pero no en `.dockerignore`, Docker Desktop igual lo transfiere. En un build de 20/08/2026 el contexto llegó a ~686 MB y el paso `load build context` pasó de 50 minutos (Excel de Best Sox + `.git.corrupt-*` + clone de ecom) sin haber llegado a `pip install`.

No ignorar `pyafipws/`: el Dockerfile lo instala si está en el contexto (ver `docs/self_checkout/PYAFIPWS_DOCKER.md`).

### 6. Script de Construcción Optimizada

`build_optimized.sh` incluye:
- Construcción paralela de imágenes
- Cache de imágenes base
- Limpieza automática
- Estadísticas de construcción

## 📊 Resultados Esperados

### Tiempo de Construcción
- **Antes**: ~20-30 minutos
- **Después**: ~8-12 minutos
- **Mejora**: ~60% reducción

### Tamaño de Imágenes
- **Imagen Principal**: ~800MB (vs ~1.5GB)
- **Imagen Reports-AI**: ~3.2GB (vs ~4.1GB)
- **Reducción Total**: ~25-30%

### Uso de Recursos
- **Memoria**: Límites definidos por servicio
- **CPU**: Optimización de workers
- **Disco**: Cache eficiente

## 🛠️ Uso de las Optimizaciones

### Construcción Rápida
```bash
# Construcción normal con cache
./build_optimized.sh

# Construcción paralela
./build_optimized.sh --parallel

# Construcción sin cache (para cambios importantes)
./build_optimized.sh --no-cache
```

### Inicio de Servicios
```bash
# Inicio normal
docker-compose up -d

# Inicio con logs
docker-compose up -d && docker-compose logs -f
```

### Monitoreo de Recursos
```bash
# Ver uso de recursos
docker stats

# Ver estadísticas de imágenes
docker system df
```

## 🔧 Configuraciones Específicas

### Gunicorn Optimizado
```bash
gunicorn --bind 0.0.0.0:8002 \
         --workers 3 \
         --timeout 120 \
         --max-requests 1000 \
         --max-requests-jitter 100 \
         django_project.wsgi:application
```

### Celery Optimizado
```bash
celery -A django_project worker -l info --concurrency=2
```

### Uvicorn Optimizado
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

## 🚨 Consideraciones Importantes

### Para VPS en la Nube
1. **PyTorch**: Instalado con `--no-cache-dir` para ahorrar espacio
2. **Dependencias**: Purga de build-essential después de compilación
3. **Cache**: Uso eficiente del cache de Docker
4. **Recursos**: Límites definidos para evitar sobrecarga

### Para Desarrollo Local
1. **Volúmenes**: Código montado para desarrollo en tiempo real
2. **Hot Reload**: Configurado para cambios automáticos
3. **Debug**: Logs detallados habilitados

## 📈 Próximas Optimizaciones

### Posibles Mejoras Futuras
1. **Multi-stage builds** para reducir aún más el tamaño
2. **Distroless images** para mayor seguridad
3. **BuildKit** para construcciones más rápidas
4. **Registry cache** para entornos de producción
5. **Compresión de imágenes** para transferencias más rápidas

### Monitoreo Continuo
- Tiempo de construcción por build
- Tamaño de imágenes por versión
- Uso de recursos en producción
- Performance de aplicaciones

## 🎯 Beneficios Obtenidos

1. **Desarrollo más rápido**: Construcciones en minutos vs horas
2. **Menor uso de recursos**: Imágenes más pequeñas y eficientes
3. **Mejor experiencia**: Health checks y dependencias optimizadas
4. **Escalabilidad**: Configuración lista para producción
5. **Mantenibilidad**: Scripts automatizados y documentación clara

---

*Última actualización: $(date)*
*Optimizaciones aplicadas para Synap v1.0* 