# 20 — Configuración

**Estado:** COMPLETE (Fase 20)  
**Fecha:** 25/08/2026

---

## Fuentes de configuración

| Fuente | Path | Prioridad |
|--------|------|:---------:|
| Variables entorno | `.env` / `env.example` | 1 |
| Django settings | `django_project/settings.py` | 2 |
| SystemConfiguration | `core/models/system_config.py` (PG) | 3 |
| ModuleConfig.settings | `core/models/module_config.py` (PG JSON) | 4 |
| Hardcoded defaults | settings.py defaults | 5 (riesgo) |

---

## Variables críticas

### Seguridad

| Variable | Default | Prod obligatorio |
|----------|---------|:----------------:|
| `SECRET_KEY` | insecure-placeholder | **Sí** |
| `ENVIRONMENT` | production | — |
| `DB_PASSWORD` | '' | **Sí** |
| `POSTGRES_PASSWORD` | mypassword | **Sí** |
| `ADMINISTRANET_MYSQL_AES_KEY` | **a7v8xx2** | Debería ser Sí |

### Bases de datos

| Variable | Default | Uso |
|----------|---------|-----|
| `POSTGRES_*` | synap_db/myuser | PostgreSQL |
| `DB_*` | administranet/mysql | MySQL AdministraNET |
| `REDIS_URL` | redis://redis:6379/0 | Cache |
| `DEFAULT_BASE_EMPRESA` | DB_NAME | Fallback tenant |

### Feature flags

| Variable | Default | Función |
|----------|---------|---------|
| `SYNAP_PERMISOS_SOURCE` | legacy | Fuente permisos |
| `SYNAP_AUTO_ENSURE_SCHEMA` | True | DDL synap_* auto |
| `REPORTS_CACHE_ENABLED` | False | Cache reportes |
| `FACTURA_COMPRA_POSTING_BACKEND` | fake | Posting compras |
| `FACTURA_COMPRA_LEGACY_SQL_ENABLED` | False | SQL legacy compras |
| `TIENDANUBE_SYNC_ENABLED` | True | Kill switch TN |
| `WEBAUTHN_UNLOCK_ENABLED` | False | Passkeys PWA |

### Integraciones

| Variable | Default |
|----------|---------|
| `GOOGLE_CLIENT_ID/SECRET` | '' |
| `GOOGLE_GEOCODING_API_KEY` | '' |
| `SYNAP_AFIP_STORAGE` | private/afip |
| `SITE_URL` | synap.administranet.com.ar |
| `BACKUP_SFTP_*` | disabled |

---

## Valores hardcoded de clientes

| Hallazgo | Ubicación | Riesgo |
|----------|-----------|--------|
| DEFAULT base_empresa 'administranet' | settings, env.example | Medio |
| SITE_URL synap.administranet.com.ar | settings, env.example | Bajo |
| CSRF_TRUSTED_ORIGINS synap.administranet.com.ar | settings | Bajo |
| AES key 'a7v8xx2' | settings default | **Alto** |
| ALLOWED_HOSTS incluye synap.administranet.com.ar | settings | Bajo |

**No se detectaron** company IDs hardcoded en lógica de negocio (grep `id_empresa ==` sin resultados significativos).

---

## Configuración por módulo (ModuleConfig)

Almacenada en PostgreSQL como JSON en `core_moduleconfig.settings`. Ejemplos en `MODULE_CONFIGS` (estático) vs runtime (DB).

---

*Generado por auditoría READ ONLY.*
