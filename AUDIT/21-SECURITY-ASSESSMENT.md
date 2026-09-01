# 21 — Security Assessment

**Estado:** COMPLETE (Fase 21)  
**Fecha:** 25/08/2026

---

## Resumen de hallazgos

| Severidad | Cantidad |
|-----------|:--------:|
| CRITICAL | 2 |
| HIGH | 7 |
| MEDIUM | 9 |
| LOW | 6 |
| INFO | 8 |

---

## CRITICAL

### SEC-C001: AES key default hardcoded (duplicada)

- **Componente:** `django_project/settings.py:280`, `core/services/administranet_users.py:14`
- **Evidencia:** `ADMINISTRANET_MYSQL_AES_KEY` default `'a7v8xx2'`; duplicado hardcoded en user service
- **Impacto:** Password validation predecible si no se override en prod
- **Escenario:** Atacante con acceso a código conoce key default
- **Recomendación:** Eliminar defaults; unificar vía settings; obligatorio en production

### SEC-C002: SQL dinámico en query_runner

- **Componente:** `reports/services/query_runner.py`
- **Evidencia:** f-strings construyendo SQL con input de report definitions
- **Impacto:** SQL injection si config de reporte es manipulable
- **Escenario:** Usuario con permisos reportes crea definition maliciosa
- **Recomendación:** Sandbox SQL, whitelist tablas, parametrización estricta

---

## HIGH

### SEC-H001: IDOR multi-tenant — factura compra API

- **Componente:** `factura_compra_captura/api/views.py:69-99`, `332-376`
- **Evidencia:** GET list sin filtro obligatorio por `empresa_activa_id`; detail/document por `pk` solo — web views sí filtran por sesión
- **Impacto:** Usuario autenticado puede leer expedientes de otra empresa por UUID
- **Recomendación:** Forzar filtro `session['empresa_activa_id']` en todas las rutas API

### SEC-H002: Cross-tenant data en PostgreSQL (otros módulos)

- **Componente:** reports, ia (además de captura)
- **Evidencia:** Modelos PG sin middleware tenant; acceso por UUID sin check empresa
- **Impacto:** IDOR cross-tenant
- **Recomendación:** Tenant middleware + validación empresa en cada query PG

### SEC-H003: DEFAULT_BASE_EMPRESA fallback

- **Componente:** `reports/services/query_runner.py`, settings
- **Evidencia:** Reportes sin sesión usan empresa default
- **Impacto:** Exposición datos empresa incorrecta

### SEC-H004: Permisos dual legacy/synap

- **Componente:** `SYNAP_PERMISOS_SOURCE=dual|legacy`
- **Evidencia:** Dos fuentes de verdad, posible escalada si difieren
- **Recomendación:** Cutover a synap con validación

### SEC-H005: @csrf_exempt en webhooks

- **Componente:** `tiendanube_administranet/views/webhook_views.py:173`
- **Evidencia:** CSRF deshabilitado; HMAC obligatorio en prod cuando secret configurado
- **Recomendación:** Verificar HMAC en cada request; rate limit

### SEC-H006: Endpoints API sin verificación permiso granular

- **Componente:** Varias api_views en ecom, stock, mpr
- **Evidencia:** Session auth sin @tiene_permiso en algunos endpoints
- **Recomendación:** Audit endpoint-by-endpoint

### SEC-H007: f-string SQL con nombres tabla dinámicos

- **Componente:** `mpr/services.py`, `core/services/administranet_stock.py`
- **Evidencia:** `cursor.execute(f"UPDATE {tbl} SET ...")` — tablas de config interna
- **Impacto:** Menor que query_runner pero patrón riesgoso

---

## MEDIUM

| ID | Hallazgo | Componente |
|----|----------|-------------|
| SEC-M001 | CSRF_COOKIE_HTTPONLY=False | settings.py (permite JS leer token) |
| SEC-M002 | runserver en Docker CMD | Dockerfile (no gunicorn) |
| SEC-M003 | Media files servidos por Django en prod | urls.py fallback |
| SEC-M004 | Sin rate limiting activo | RateLimitMiddleware inactivo |
| SEC-M005 | IA tools sin sandbox datos | ia/services |
| SEC-M006 | Celery tasks sin worker (jobs perdidos) | tiendanube tasks |
| SEC-M007 | Logging DEBUG en dev expone queries | settings LOGGING |
| SEC-M008 | WebAuthn deprecado pero código presente | settings WEBAUTHN_UNLOCK_ENABLED |

---

## LOW

| ID | Hallazgo |
|----|----------|
| SEC-L001 | X_FRAME_OPTIONS=SAMEORIGIN (permite iframe same-origin) |
| SEC-L002 | Sin Content-Security-Policy header activo |
| SEC-L003 | HSTS preload habilitado (correcto pero verificar) |
| SEC-L004 | Archivos `* 2.py` duplicados (confusión, no vulnerabilidad directa) |
| SEC-L005 | pytest fixtures con DB credentials en tests |

---

## INFO

| ID | Hallazgo |
|----|----------|
| SEC-I001 | SECRET_KEY validation en production ✓ |
| SEC-I002 | DB_PASSWORD validation en production ✓ |
| SEC-I003 | SESSION_COOKIE_SECURE en production ✓ |
| SEC-I004 | defusedxml + bleach en requirements ✓ |

---

## Controles positivos detectados

- `ImproperlyConfigured` para SECRET_KEY y passwords en production
- CSRF middleware activo (excepto webhooks documentados)
- `@administranet_login_required` en mayoría de vistas
- `sql_validator.py` para reportes
- `administranet_types` previene type confusion
- SFTP backup con cifrado bootstrap
- No se detectó `eval()`, `pickle`, `subprocess` en código de aplicación

---

*Assessment READ ONLY — no se explotaron vulnerabilidades.*
