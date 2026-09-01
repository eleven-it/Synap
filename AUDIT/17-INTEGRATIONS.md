# 17 — Integraciones Externas

**Estado:** COMPLETE (Fase 17)  
**Fecha:** 25/08/2026

---

| Provider | Módulo | Protocolo | Auth | Dirección | Coupling |
|----------|--------|-----------|------|-----------|:--------:|
| **AdministraNET VB6** | Todos | MySQL compartido | DB creds | Bidireccional | 4 |
| **administraNET-ecom PHP** | ecom | HTTP relays | Session | Synap→PHP | 3 |
| **AFIP/ARCA** | fe_afip, self_checkout | SOAP (pyafipws) | X.509 certs | Synap→AFIP | 2 |
| **Tienda Nube** | tiendanube_administranet | REST + webhooks | OAuth token | Bidireccional | 2 |
| **Odoo 19** | odoo_migracion | XML-RPC/REST | API key | Synap→Odoo | 1 |
| **Azure SQL BEST** | mpr/best_migration | TDS (pymssql) | SQL auth | Lectura | 1 |
| **Google OAuth** | login | OAuth2 | Client ID/Secret | Entrada | 1 |
| **Google Geocoding** | core/api | REST | API key server | Salida | 0 |
| **OpenAI** | ia | REST | API key | Salida | 1 |
| **Anthropic** | ia | REST | API key | Salida | 1 |
| **SMTP** | core/backup | SMTP | EMAIL_* | Salida | 0 |
| **SFTP** | core/backup | SFTP | Key/password | Salida | 0 |
| **Support ↔ Synap** | support | HTTP+JWT | JWT secret | Bidireccional | 1 |
| **Cloudflare** | Infra | CDN/WAF | DNS | Entrada | 0 |

---

## Detalle por integración crítica

### AdministraNET (MySQL)

- **Coupling: 4 (crítico)**
- Protocolo: MySQL directo via pool
- Sin API intermedia
- VB6 y Synap escriben mismas tablas
- Retry: reconexión pool automática
- Timeout: POOL_IDLE_SECONDS=30

### AFIP/ARCA

- **Coupling: 2 (moderado)**
- pyafipws local en `pyafipws/`
- Certificados en volumen Docker `synap_afip_secrets`
- WSAA (auth) → WSFE (factura) → respuesta CAE
- Error handling: excepciones pyafipws → log → UI

### Tienda Nube

- **Coupling: 2**
- API REST: productos, clientes, pedidos
- Webhooks: @csrf_exempt, validación token
- Outbox pattern para sync bidireccional
- Kill switches: `TIENDANUBE_SYNC_ENABLED`, `TIENDANUBE_WEBHOOKS_ENABLED`

### administraNET-ecom (PHP)

- **Coupling: 3**
- HTTP relays desde `ecom/services/*_relay.py`
- Docker compose separado para dev
- Depende de sesión/tokens compartidos
- Sin contrato API formal documentado

---

*Detalle acoplamiento AdministraNET en `18-ADMINISTRANET-COUPLING.md`.*
