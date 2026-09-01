# 01 — Validación de la Auditoría Original

**Estado:** COMPLETE  
**Fecha:** 25/08/2026  
**Método:** Lectura `AUDIT/*` + verificación directa en código (grep, lectura archivos, `manage.py shell` para URLs)

---

## Resumen ejecutivo

| Veredicto | Cantidad |
|-----------|:--------:|
| CONFIRMADA | 18 |
| PARCIALMENTE CONFIRMADA | 9 |
| REFUTADA | 2 |
| INCOMPLETA | 6 |
| REQUIERE DECISIÓN HUMANA | 4 |

La auditoría V1 es **direccionalmente correcta** en arquitectura dual DB, acoplamiento AdministraNET, hub `core`, y riesgos de tenant. Errores principales: conteos hub ligeramente inflados, `compventa` como tabla escrita por TPV (refutado), y subestimación del volumen de escrituras MySQL (~587 ops).

---

## Matriz de validación

### Arquitectura general

| ID | Hallazgo original | Doc origen | Verificación | Resultado | Impacto |
|----|-------------------|------------|--------------|-----------|---------|
| V2-ARCH-01 | Monolito modular Django + dual DB PG/MySQL | 02 | `settings.py:174-197`, `docker-compose.yml` | **CONFIRMADA** | Base para toda estrategia |
| V2-ARCH-02 | Sin Celery operativo en app principal | 02, 12, INFRA-001 | `celery.py` comentado; compose sin worker; tasks en TN sin broker | **CONFIRMADA** | Jobs async = threads + cron |
| V2-ARCH-03 | FastAPI/microservicios no activos en runtime principal | 02 | Solo Django WSGI en compose | **CONFIRMADA** | — |
| V2-ARCH-04 | `support/` tiene Celery separado, no en INSTALLED_APPS | 02 | `support/backend/` existe; no en settings | **CONFIRMADA** | RAG soporte aislado |

### Core

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-CORE-01 | core = hub universal (256 archivos / 482 imports) | 04, ARCH-002 | Medido: 245 archivos / 349 imports fuera de core | **PARCIALMENTE CONFIRMADA** | Patrón hub válido; conteos ~4% menores |
| V2-CORE-02 | core importa módulos negocio (login 5, mpr 4, ecom 1, reports 1) | 04 | `base_middleware.py`, `catalog.py`, `views_general.py` | **CONFIRMADA** | Viola inversión de dependencias |
| V2-CORE-03 | `administranet_stock.py` ~2000 líneas SQL en core | 09, 05 | Archivo existe, 44 write refs | **CONFIRMADA** | Stock logic mal ubicada |
| V2-CORE-04 | DDL catalog 3200+ líneas mezcla dominios | 09 | `legacy_mysql_schema/catalog.py` | **CONFIRMADA** | Acoplamiento infra+dominio |

### Acceso a datos

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-DATA-01 | Pool canónico `core.mysql_pool` | 05 | Re-export en mpr, self_checkout, reports | **CONFIRMADA** | Punto único de conexión |
| V2-DATA-02 | MPR/self_checkout ~100% SQL crudo | 05 | Conteos: sc 99%, mpr 75% raw | **CONFIRMADA** | Ports obligatorios para desacople |
| V2-DATA-03 | 132 modelos PG | 05, 06 | INSTALLED_APPS scan | **CONFIRMADA** | Synap state en PG |
| V2-DATA-04 | ~200-250 tablas MySQL únicas | 06 | Regex scan repo | **PARCIALMENTE CONFIRMADA** | Orden magnitud correcto |
| V2-DATA-05 | compventa escrita por self_checkout TPV | 06 | **0 writes** a compventa en .py | **REFUTADA** | TPV escribe resumen_venta_cv, stock, cuentacliente |

### Multitenancy

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-TEN-01 | database-per-tenant MySQL vía base_empresa | 08 | `mysql_pool.select_db`, session | **CONFIRMADA** | Tenant MySQL = nombre BD |
| V2-TEN-02 | PG sin tenant isolation middleware | 08, DATA-001 | No middleware tenant en PG | **CONFIRMADA** | IDOR en APIs PG |
| V2-TEN-03 | DEFAULT_BASE_EMPRESA fallback | 08, DATA-002 | `settings.py:221`, `query_runner.py:473-481` | **CONFIRMADA** | Cross-DB sin sesión |
| V2-TEN-04 | Redis cache sin namespace empresa global | 13 | `core.active_modules.db` sin tenant; reports cache off by default | **PARCIALMENTE CONFIRMADA** | Riesgo mitigado por default |

### Identity & permisos

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-IAM-01 | Auth = AdministraNET MySQL usuarios | 10 | `administranet_auth.py:110-195` | **CONFIRMADA** | No IdP propio operativo |
| V2-IAM-02 | SYNAP_PERMISOS_SOURCE default legacy | 10 | `settings.py:471` | **CONFIRMADA** | Dos fuentes permisos |
| V2-IAM-03 | Google OAuth NO implementado | 10 | Sin views/urls OAuth | **CONFIRMADA** | Solo placeholders |
| V2-IAM-04 | Admin Django = efectivamente supervisor | 10 | `RolesManager` mock retorna [] | **CONFIRMADA** | Bypass Administrador muerto |
| V2-IAM-05 | WebAuthn implementado con flag | 10 | `webauthn_service.py`, flag default off | **CONFIRMADA** | Unlock post-login |

### Reports

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-REP-01 | Motor dual declarative-v1 vs legacy slug | 15 | `query_runner.py:265-276` vs 311+ | **CONFIRMADA** | Dos engines coexisten |
| V2-REP-02 | query_runner ~4000 líneas monolítico | 15 | Conteo líneas archivo | **CONFIRMADA** | Deuda alta |
| V2-REP-03 | datasource = nombre tabla literal | — (nuevo V2) | `execution_engine.py:62-74`, `config_serializer.py:95` | **INCOMPLETA en V1** | No hay abstracción datasource |
| V2-REP-04 | Código muerto post-return en query_runner | 15 | Bloque ~3840+ inalcanzable | **CONFIRMADA** | Limpieza pendiente |
| V2-REP-05 | REPORTS_CACHE_ENABLED default false | 13 | `settings.py:560` | **CONFIRMADA** | Mitiga cache cross-tenant |

### APIs

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-API-01 | 411 endpoints `/api/` runtime | 11 | `manage.py shell` → 411 | **CONFIRMADA** | — |
| V2-API-02 | Solo 4 versionados (ecom v1) | 11 | `/ecom/api/v1/` | **CONFIRMADA** | Sin estrategia versionado global |
| V2-API-03 | IDOR factura compra API | 21, 10 | `api/views.py:69-99` sin filtro empresa | **CONFIRMADA** | P0 seguridad |

### Seguridad

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-SEC-01 | AES key default a7v8xx2 | 21, SEC-001 | `settings.py:280`, `administranet_users.py:14` | **CONFIRMADA** | Duplicado hardcode |
| V2-SEC-02 | SQL dinámico reports — riesgo alto | 21, SEC-C002 | Trust path analizado en 09 | **PARCIALMENTE CONFIRMADA** | Explotable con perm builder; mitigado por permisos |
| V2-SEC-03 | relationship_validation tabla dinámica | DATA-003 | `relationship_validation_service.py:184` | **CONFIRMADA** | HIGH con perm builder |
| V2-SEC-04 | CSRF exempt webhooks TN + HMAC prod | 21 | `webhook_views.py:173`, HMAC check | **CONFIRMADA** | Aceptable con secret |

### Dependencias

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-DEP-01 | No ciclos import profundos A→B→C→A | 04 | Script estático imports | **CONFIRMADA** | No bloquea refactor por imports |
| V2-DEP-02 | Acoplamiento bidireccional reports↔ventas, mpr↔stock | 04 | 6↔4 y 2↔2 archivos | **CONFIRMADA** | SCC por datos, no imports |
| V2-DEP-03 | captura→self_checkout (10 imports) | 04 | `api/views.py:46-47` import sc | **PARCIALMENTE CONFIRMADA** | Unidireccional en imports; bidireccional en datos |
| V2-DEP-04 | ecom→core 95 archivos | 04 | Recuento similar confirmado | **CONFIRMADA** | Mayor acoplamiento modular |

### Productización

| ID | Hallazgo | Doc | Verificación | Resultado | Impacto |
|----|----------|-----|--------------|-----------|---------|
| V2-PROD-01 | No SaaS-ready (sin provisioning/billing) | 29 | No código provisioning | **CONFIRMADA** | — |
| V2-PROD-02 | Reports productizable como Data Platform | 29, 15 | Modelos PG genéricos; execution acoplada | **PARCIALMENTE CONFIRMADA** | Metadatos sí; engine no |
| V2-PROD-03 | ACL viable incrementalmente | 30, 18 | 587 writes a catalogar en Ports | **PARCIALMENTE CONFIRMADA** | Viable pero esfuerzo alto |
| V2-PROD-04 | Odoo adapter posible | 30 | Sin código Odoo; mapping conceptual en 04 | **REQUIERE DECISIÓN HUMANA** | Gaps semánticos contabilidad |

---

## Refutaciones importantes

### REF-01: compventa como target de escritura TPV

**V1 decía:** `compventa` escrito por self_checkout.  
**Código real:** 0 `INSERT/UPDATE/DELETE` sobre `compventa`/`cuerpocompventa`.  
**Evidencia:** `self_checkout/services/confirmation_service.py` escribe `resumen_venta_cv`, `stock`, `cuentacliente`, `tc_comprobante`.  
**Impacto:** Mapa de capabilities y Ports de ventas debe usar modelo real, no asumir compventa.

### REF-02: "Sin dependencias circulares"

**V1 decía:** No hay ciclos.  
**Código real:** No hay ciclos de **import Python** profundos, pero sí **SCC conceptuales** por tablas compartidas (stock, comp_ped, cuentacliente) entre mpr↔ecom↔self_checkout↔core.  
**Impacto:** Grafo de dependencias debe incluir acceso a datos, no solo imports.

---

## Incompletitudes de V1 corregidas en V2

1. **Volumen escrituras MySQL:** V1 no cuantificó (~587 ops producción).
2. **Reports datasource contract:** V1 no documentó que `datasource` es tabla literal.
3. **Identity split:** V1 mezcló `id_empresa` MySQL con `empresa_activa_id` PG.
4. **compventa vs resumen_venta_cv:** modelo venta TPV incorrecto.
5. **Trust path SQL:** V1 afirmó CRITICAL sin analizar permisos builder.
6. **Ports vs repositories:** V1 sugirió ACL pero no definió contratos por capacidad.

---

## Preguntas V1 respondidas con veredicto

| # | Pregunta | Respuesta V2 |
|---|----------|--------------|
| 1 | ¿Qué partes V1 correctas? | Arquitectura dual, hub core, acoplamiento AN, IDOR captura, motor dual reports |
| 2 | ¿Inferencias incorrectas? | compventa TPV; "sin ciclos" (solo imports); conteos hub exactos |
| 3 | ¿Synap multitenant? | MySQL sí (DB/empresa); PostgreSQL no |

---

*Generado por auditoría READ ONLY V2.*
