# ¿Dónde se guarda la configuración por UI?

## Estado actual

**La configuración que el usuario cambia en la sección Configuración (Admin) hoy no se persiste.** Los formularios (Canales, IA, RAG, SLA, Storage, Seguridad, Notificaciones, Branding) solo viven en el estado del frontend; al cerrar el drawer o recargar la página, se pierde.

El backend aún **no implementa** los endpoints de configuración documentados en [API_Y_CONFIG.md](API_Y_CONFIG.md). Por tanto, el frontend no tiene dónde enviar GET/PATCH ni de dónde leer el estado guardado.

## Diseño objetivo: guardar en el backend

La idea del producto es que **toda la configuración se guarde en el backend**, para que:

- No haga falta tocar `.env` ni archivos en el servidor para operar.
- Un admin pueda cambiar canales, IA, SLA, etc. desde la UI.
- Los workers (Celery) y la API lean esa misma configuración (desde DB o desde un almacén que el backend rellene con lo guardado por la UI).

### Dónde guardarla en el backend (opciones)

1. **Base de datos PostgreSQL (recomendado)**  
   - Crear una app Django (ej. `apps.config` o `apps.system_config`) con modelos por área, por ejemplo:
     - **ChannelConfig** (o por canal: TelegramConfig, WhatsAppConfig, EmailConfig): token, webhook_url, verify_token, is_active, last_check_at, last_error.
     - **IAConfig**: provider, model, api_key_encrypted (o referencia a secret manager), limits, prompt_version_id, is_active.
     - **RAGConfig**: top_k, sources_enabled (JSON o M2M), cache_ttl_seconds (o un único modelo clave-valor).
     - **SLA** ya existe como `SLAConfig` por empresa; solo falta exponer CRUD por API si se quiere editar desde la UI.
     - **StorageConfig**: endpoint, bucket, region, access_key (enmascarado), secret encriptado, max_size_bytes, allowed_content_types.
     - **SecurityConfig**: rate_limits (JSON), anti_spam_enabled, pii_warning_enabled.
     - **NotificationsConfig**: escalation_emails, sla_warning_message, sla_breach_message, internal_alert_channel.
     - **BrandingConfig** (opcional): assistant_name, welcome_message, default_language; puede ser por empresa o global.
   - Las claves sensibles (API keys, secrets) deben almacenarse encriptadas y mostrarse enmascaradas en los GET.

2. **Tabla clave-valor (SystemSetting)**  
   - Un solo modelo `SystemSetting(key, value_json, updated_at)`. Cada pantalla de config lee/escribe por clave (ej. `channels.telegram`, `ia.provider`). Más flexible pero menos tipado y sin historial por entidad.

3. **Archivos de configuración que el backend escriba**  
   - La API recibe el PATCH y escribe en un archivo (ej. `config/channels.yaml`). El resto del backend lee ese archivo. Menos recomendable: permisos de escritura, despliegue y posibles conflictos con variables de entorno.

### Flujo cuando esté implementado

1. El usuario abre Configuración → Canales (por ejemplo) y pulsa “Configurar”.
2. El frontend hace **GET /api/config/channels/** y recibe el estado actual (o vacío).
3. El usuario rellena el formulario y pulsa “Probar” → **POST /api/config/channels/:id/test/** (el backend prueba sin activar).
4. El usuario pulsa “Guardar” o “Activar” → **PATCH** o **POST** al endpoint correspondiente; el **backend guarda en la base de datos** (o en el almacén elegido).
5. Workers y servicios leen la config desde los modelos o desde un módulo que cachee los valores en memoria y los refresque cuando cambien.

## Resumen

| Pregunta | Respuesta |
|----------|-----------|
| ¿Dónde se guarda hoy la config de la UI? | En ningún sitio; solo en estado del frontend (se pierde al cerrar/recargar). |
| ¿Dónde debería guardarse? | En el **backend** (recomendado: **PostgreSQL** con modelos por área de configuración). |
| ¿Qué falta? | Implementar en el backend los endpoints documentados en [API_Y_CONFIG.md](API_Y_CONFIG.md) y que el frontend los consuma (ya está preparado para ello). |
