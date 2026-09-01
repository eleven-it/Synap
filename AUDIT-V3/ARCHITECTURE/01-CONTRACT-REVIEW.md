# 01 — Revisión del Contrato V2

**Estado:** COMPLETE | **Fecha:** 25/08/2026

Clasificación de cada regla en `AUDIT-V2/SYNAP-ARCHITECTURE-CONTRACT.md`:

| Regla V2 | Clasificación | Notas |
|----------|---------------|-------|
| Domain → Port → Adapter | **PERMANENT** | Principio producto |
| MUST NOT core import domain | **PERMANENT** | Invertir dependencias |
| Core limitado a infra | **PERMANENT** | Target state |
| MAY retain administranet_* services | **TRANSITIONAL** | No permanente |
| MUST NOT new logic in administranet_* | **PERMANENT** (target) | Transición permite legacy |
| MUST NOT MySQL direct in new code | **PERMANENT** | |
| MUST use mysql_pool | **TRANSITIONAL** → **PERMANENT** como infra; detalle `base_empresa` → **ADMINISTRANET-SPECIFIC** en adapter |
| MUST pass base_empresa | **ADMINISTRANET-SPECIFIC** | Domain usa CompanyContext |
| administranet_types | **ADMINISTRANET-SPECIFIC** | Adapter concern |
| MUST NOT ORM on AN tables | **PERMANENT** | Excepciones documentadas |
| ERP behind Ports | **PERMANENT** | |
| SQL in adapters/administranet | **PERMANENT** | |
| MUST NOT table names in domain | **PERMANENT** | |
| TenantContext explicit | **PERMANENT** | |
| MUST NOT DEFAULT_BASE_EMPRESA | **PERMANENT** | |
| PG empresa scope | **PERMANENT** | |
| CompanyContextPort | **PERMANENT** | V2 decía "once introduced" — ahora requisito |
| MUST NOT conflate id_empresa | **PERMANENT** | |
| AdministraNETUser primary | **TRANSITIONAL** | Target: Principal |
| MUST check API permissions | **PERMANENT** | |
| ReportDataSourcePort | **PERMANENT** | |
| MUST NOT new slug branches | **PERMANENT** | |
| AI PolicyGate | **PERMANENT** | |
| Cache tenant keys | **PERMANENT** | |
| Jobs CompanyContext | **PERMANENT** | |
| Webhook HMAC | **PERMANENT** | |
| MUST NOT default secrets | **PERMANENT** | |
| MUST NOT alert/confirm/prompt | **UI STANDARD** → mover a Design System Contract; **PERMANENT** como regla UX |
| docker exec tests | **OPERATIONAL RULE** | Fuera del contrato permanente |
| Architectural Deviations | **PERMANENT** | |

**INVALID:** Ninguna regla V2 refutada; algunas mezclaban implementación actual con target.

**REQUIRES DECISION:** ¿Usuario operativo = Principal Synap o siempre proxy ERP?
