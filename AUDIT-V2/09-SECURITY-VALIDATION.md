# 09 — Security Validation

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## Metodología

Revisión de hallazgos `AUDIT/21-SECURITY-ASSESSMENT.md` con **trust path completo**, no solo pattern matching.

---

## SEC-01: AES key hardcoded

| Campo | Valor |
|-------|-------|
| **V1 claim** | CRITICAL — default `a7v8xx2` |
| **Verificación** | `settings.py:280`, `administranet_users.py:14` (duplicado) |
| **Exploitability** | MEDIUM — requiere acceso código + hash password AN |
| **Veredicto V2** | **CONFIRMADA** — severity mantiene HIGH/CRITICAL en prod sin override |
| **Fix scope** | Config only — fuera de V2 |

---

## SEC-02: SQL dinámico Reports

### Trust path

```text
Actor: usuario autenticado
  ↓
Permission: reports.builder (BuilderReportsPermission) OR supervisor *
  ↓
Input: ReportDefinition.config JSON (metrics, dimensions, joins, filters)
  ↓
Validation ON SAVE: sql_validator.py (blocks DML keywords, optional SHOW COLUMNS)
  ↓
Storage: PostgreSQL reports_reportdefinition
  ↓
Runtime: SqlQueryBuilder embeds expressions — NO re-validation
  ↓
Execute: MySQL cursor on base_empresa
```

| Pregunta | Respuesta |
|----------|-----------|
| ¿Quién puede crear SQL? | Usuarios con `reports.builder` o supervisor |
| ¿Campos libres? | Sí — metric/dimension `expression` strings |
| ¿Allowlist tablas? | Parcial — `allowed_tables` opcional en validator |
| ¿Read-only connection? | NO — misma conn read/write |
| ¿Multi-statement? | Bloqueado `;` en validator |
| ¿UNION/subqueries? | No bloqueados explícitamente en expressions |

| Veredicto V2 | **PARCIALMENTE CONFIRMADA** |
|--------------|----------------------------|
| V1 decía CRITICAL universal | V2: **MEDIUM-HIGH** — requiere permiso builder; no endpoint público |
| Escenario exploit | Builder comprometido o supervisor malicioso → exfiltración cross-table |

---

## SEC-03: relationship_validation_service

| Campo | Valor |
|-------|-------|
| **Path** | `RelationshipValidationAPIView` → POST body table/column names |
| **Permission** | `BuilderReportsPermission` |
| **SQL** | `f"SELECT COUNT(*) FROM \`{from_table}\`"` (line ~184) |
| **Allowlist** | NO |
| **Veredicto** | **CONFIRMADA HIGH** — mismo trust boundary que builder |

---

## SEC-04: IDOR factura_compra_captura

| Endpoint | Tenant check | Veredicto |
|----------|--------------|-----------|
| `GET /api/compras/expediente/` | `?empresa=` opcional; sin param = ALL | **EXPLOTABLE** |
| `GET /api/compras/expediente/{pk}/` | Solo pk + perm `ver` | **EXPLOTABLE** |
| `POST create` | empresa from body OR session; no match validation | **PARCIAL** |
| Web views | `filter(empresa_id=eid)` obligatorio | Correcto |

**Evidencia:** `api/views.py:69-99`, `web_views.py:141-149`  
**Veredicto:** **CONFIRMADA CRITICAL/HIGH** — usuario con perm `ver` + UUID ajeno

---

## SEC-05: DEFAULT_BASE_EMPRESA

| Campo | Valor |
|-------|-------|
| **Trigger** | Request sin session + sin base_empresa en filters |
| **Fallback** | `settings.DEFAULT_BASE_EMPRESA` → `DB_NAME` default `administranet` |
| **Exploitability** | LOW en prod normal (login required); HIGH en jobs/scripts |
| **Veredicto** | **CONFIRMADA** |

---

## SEC-06: Cross-tenant cache

| Key pattern | Includes base_empresa? | Risk |
|-------------|------------------------|------|
| `reports:{tenant_id}:{slug}:{hash}` | tenant_id = user.id (not empresa) | MEDIUM if cache on |
| `core.active_modules.db` | NO | LOW |
| data-map cache | SÍ (`api_views.py:2825+`) | LOW |

**Mitigación actual:** `REPORTS_CACHE_ENABLED=False` default.

---

## SEC-07: CSRF exempt webhooks

| Campo | Valor |
|-------|-------|
| **Endpoint** | tiendanube webhooks |
| **Mitigation** | HMAC when secret set / production |
| **Veredicto** | **CONFIRMADA aceptable** con secret obligatorio |

---

## SEC-08: SQL injection en mpr/core f-strings

| Pattern | User input in table name? | Veredicto |
|---------|---------------------------|-----------|
| `{tbl}` from internal config | NO | LOW |
| `IN ({placeholders})` | Params bound | LOW |
| Executive dashboard WHERE | Internal cond lists | LOW-MEDIUM |

---

## Resumen severidad V2 vs V1

| Finding | V1 | V2 (exploitability-adjusted) |
|---------|-----|------------------------------|
| AES key | CRITICAL | CRITICAL (prod) |
| Reports SQL dynamic | CRITICAL | MEDIUM-HIGH |
| IDOR captura API | HIGH | **HIGH — confirmado explotable** |
| relationship_validation | HIGH | HIGH |
| DEFAULT_BASE_EMPRESA | HIGH | HIGH (context-dependent) |

---

## Respuesta pregunta 23

> ¿Los hallazgos SQL injection son explotables?

- **Reports builder:** explotable solo con permisos elevados — no anonymous.
- **relationship_validation:** idem.
- **IDOR captura:** explotable con permiso funcional normal + UUID — **más grave en práctica**.

---

*Cross-tenant vectors completos en `08-TENANCY-OPTIONS.md`.*
