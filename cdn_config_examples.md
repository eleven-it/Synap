# Configuración de CDN para Synap

Este documento contiene ejemplos de configuración para diferentes CDNs que puedes usar para optimizar el rendimiento de las imágenes en tu proyecto Synap.

## 1. Cloudflare CDN (Recomendado para empezar)

### Configuración en .env
```bash
USE_CLOUDFLARE_CDN=True
CLOUDFLARE_DOMAIN=cdn.tudominio.com
```

### Pasos de configuración:
1. **Crear cuenta en Cloudflare**
2. **Agregar tu dominio**
3. **Configurar DNS** para apuntar a tu servidor
4. **Activar CDN** en la sección "Speed" > "Optimization"
5. **Configurar Page Rules** para cache de imágenes

### Ventajas:
- ✅ Plan gratuito generoso (100GB/mes)
- ✅ Protección DDoS incluida
- ✅ Optimización automática de imágenes
- ✅ Fácil configuración
- ✅ SSL gratuito

### Precios:
- **Gratuito**: 100GB/mes
- **Pro**: $20/mes - 1TB/mes
- **Business**: $200/mes - 10TB/mes

---

## 2. AWS CloudFront

### Configuración en .env
```bash
USE_AWS_CDN=True
AWS_S3_CUSTOM_DOMAIN=cdn.tudominio.com
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_STORAGE_BUCKET_NAME=tu-bucket
AWS_S3_REGION_NAME=us-east-1
```

### Instalación de dependencias:
```bash
pip install django-storages boto3
```

### Configuración adicional en settings.py:
```python
# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False

# Usar S3 para archivos estáticos y media
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
```

### Ventajas:
- ✅ Integración nativa con S3
- ✅ Alta disponibilidad global
- ✅ Métricas detalladas
- ✅ Cache inteligente
- ✅ Integración con otros servicios AWS

### Precios:
- **Transferencia de datos**: $0.085/GB (primeros 10TB)
- **Requests**: $0.0075 por 10,000 requests
- **S3 Storage**: $0.023/GB/mes

---

## 3. Bunny CDN

### Configuración en .env
```bash
USE_BUNNY_CDN=True
BUNNY_CDN_DOMAIN=cdn.tudominio.com
BUNNY_CDN_API_KEY=tu_api_key
BUNNY_CDN_ZONE_ID=tu_zone_id
```

### Ventajas:
- ✅ Precios muy bajos
- ✅ Fácil configuración
- ✅ Optimización de imágenes automática
- ✅ API simple
- ✅ Sin límites de ancho de banda

### Precios:
- **Europa**: $0.01/GB
- **América del Norte**: $0.01/GB
- **Asia**: $0.03/GB
- **Sin cargos por requests**

---

## 4. DigitalOcean Spaces + CDN

### Configuración en .env
```bash
USE_DIGITALOCEAN_CDN=True
DIGITALOCEAN_SPACES_KEY=tu_spaces_key
DIGITALOCEAN_SPACES_SECRET=tu_spaces_secret
DIGITALOCEAN_SPACES_BUCKET=tu-bucket
DIGITALOCEAN_SPACES_REGION=nyc3
```

### Instalación:
```bash
pip install django-storages
```

### Configuración en settings.py:
```python
# DigitalOcean Spaces Configuration
AWS_ACCESS_KEY_ID = os.getenv('DIGITALOCEAN_SPACES_KEY')
AWS_SECRET_ACCESS_KEY = os.getenv('DIGITALOCEAN_SPACES_SECRET')
AWS_STORAGE_BUCKET_NAME = os.getenv('DIGITALOCEAN_SPACES_BUCKET')
AWS_S3_ENDPOINT_URL = f'https://{os.getenv("DIGITALOCEAN_SPACES_REGION")}.digitaloceanspaces.com'
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_DEFAULT_ACL = 'public-read'
AWS_QUERYSTRING_AUTH = False

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3StaticStorage'
```

### Ventajas:
- ✅ Precios competitivos
- ✅ API compatible con S3
- ✅ CDN global incluido
- ✅ Fácil integración

### Precios:
- **Spaces**: $5/mes por 250GB
- **CDN**: $0.01/GB transferido

---

## 5. Configuración del Middleware

Agregar el middleware en `settings.py`:

```python
MIDDLEWARE = [
    # ... otros middlewares ...
    'core.middleware.CDNCacheMiddleware',
]
```

---

## 6. Optimización de Imágenes

### Configuración recomendada para imágenes:

```python
# settings.py
IMAGE_OPTIMIZATION = {
    'JPEG_QUALITY': 85,
    'PNG_COMPRESS_LEVEL': 6,
    'WEBP_QUALITY': 80,
    'MAX_WIDTH': 1920,
    'MAX_HEIGHT': 1080,
}
```

### Instalación de herramientas de optimización:
```bash
# Para Ubuntu/Debian
sudo apt-get install jpegoptim optipng webp

# Para macOS
brew install jpegoptim optipng webp
```

---

## 7. Monitoreo y Métricas

### Configurar logging para CDN:
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'cdn_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/cdn.log',
        },
    },
    'loggers': {
        'cdn': {
            'handlers': ['cdn_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

---

## Recomendación Final

**Para empezar**: Cloudflare CDN
- Fácil configuración
- Plan gratuito generoso
- Protección incluida

**Para producción a gran escala**: AWS CloudFront
- Máxima confiabilidad
- Integración completa con AWS
- Métricas avanzadas

**Para optimizar costos**: Bunny CDN
- Precios muy bajos
- Sin límites de ancho de banda
- API simple 