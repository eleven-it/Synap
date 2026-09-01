# 03 — Execution Context Model

**Estado:** COMPLETE | **Fecha:** 25/08/2026

```text
ExecutionContext
├── PrincipalContext
│     principal_id (Synap-stable UUID or int)
│     identity_provider: synap | administranet | oidc | saml
│     external_principal_ref (e.g. cod_usuario AN)
│     display_name
│     roles[] (logical, not puesto name)
│     permissions[] (resolved set)
├── TenantContext
│     tenant_id (installation / customer deployment)
│     deployment_mode: dedicated | shared_app
├── CompanyContext
│     company_id (Synap canonical)
│     external_company_ref (e.g. base_empresa, id_empresa AN)
│     branch_id, pos_id (optional)
├── SecurityContext
│     auth_method, session_id, ip, mfa_level
├── CorrelationContext
│     request_id, operation_id, idempotency_key
└── LocaleContext
      locale, timezone, date_format (dd/MM/yyyy UI)
```

**Domain MUST NOT see:** `base_empresa`, `AdministraNETUser`, raw MySQL connection, `session['user']` dict.

**Resolution today (legacy):** `RequestUserMiddleware` + `session_bootstrap` → maps to ExecutionContext at boundary only.

**Evidence gap:** `empresa_activa_id` vs `id_empresa` — CompanyContext MUST unify via mapping table or bootstrap.
