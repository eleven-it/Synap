# 07 — Identity Architecture (Target)

**Estado:** COMPLETE | **Fecha:** 25/08/2026

## Separation

| Concern | Today | Target |
|---------|-------|--------|
| **Authentication** | AN MySQL password + AES | Pluggable: AN adapter, OIDC, SAML, Synap native |
| **Identity** | `session['user']` dict | `Principal` entity (PG) + external refs |
| **Authorization** | synap_* / permiso_sistema | AuthorizationPort — Synap-owned permissions |
| **Tenant** | Implicit deployment | `TenantContext.tenant_id` |
| **Company** | `base_empresa` + mixed IDs | `CompanyContext` with canonical `company_id` |

## Domain sees

```text
Principal { id, permissions[], company_scope }
```

NOT: `AdministraNETUser`, `cod_usuario`, `id_puesto` (those are adapter mapping inputs).

## Future IdP support (without domain change)

```text
AuthProviderPort.authenticate(credentials) → Principal
IdentityPort.link_external_ref(provider, external_id)
```

Providers: `administranet`, `synap`, `oidc`, `saml`, `oauth` — registered in adapter layer.

## WebAuthn

Unlock path remains in login module; maps to Principal after AN user resolution (`webauthn_service.py`).

## Evidence

- Login: `administranet_auth.py:110-195`
- Session: `session_bootstrap.py:42-55`
- Permisos: `administranet_permisos_usuario.py:71-111`
