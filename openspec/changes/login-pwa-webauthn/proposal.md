# Propuesta: Acceso rápido PWA con WebAuthn (desbloqueo post-login)

## Intención

Usuarios móviles con Synap instalada como PWA desbloquean la app con **huella, Face ID o PIN del SO** (WebAuthn) tras login inicial con contraseña AdministraNET — sin reemplazar auth legacy ni PIN propio Synap.

**Referencias:** `docs/general/PWA_SYNAP.md`, `docs/general/ESPEC_PWA_SYNAP.md`, `docs/general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md`, `openspec/changes/login-pwa-webauthn/exploration.md`.

## Alcance

### In Scope

- **Fase 0:** iconos PWA 192/512 (y maskable) generados desde el **logo del producto Synap/AdministraNET** (misma familia que `get_administranet_logo`); manifest + SW en login móvil (`start_url=/login/`); instalable Android/iOS.
- **Fase 1:** enrollment **opt-in** post-login; hasta **3 passkeys** por `(base_empresa, id_usuario)`; API register/authenticate; verify → `create_session()` sin password; **re-selección de empresa** en cada unlock; revocación al cambiar password AdministraNET + revocación manual en perfil; TTL de sesión post-unlock; UI unlock **solo en PWA standalone** (no browser móvil genérico ni desktop v1); rate limit + CSRF; allowlist middleware.
- Tests PWA + `login/tests/test_webauthn.py`; docs `docs/login/` o `PWA_SYNAP.md`.

### Out of Scope

Passwordless WebAuthn; PIN custom Synap; auth-cashier TPV; desktop v1; unlock en browser móvil no instalado.

## Capabilities

### New

- `pwa-instalabilidad-login`: instalabilidad PWA en login móvil.
- `login-webauthn-unlock`: desbloqueo WebAuthn post-login, multi-dispositivo y revocación.

### Modified

Ninguna (sin specs login/PWA en `openspec/specs/`).

## Enfoque

Fase 0 habilita “PWA instalada → `/login/`”. Fase 1: librería `webauthn`; settings `WEBAUTHN_*`; modelo `login/models.py`; `user_handle`=`{base_empresa}:{id_usuario}`; challenges en cache; UI unlock cuando hay credential sin `sessionid`. Paridad sesión/negocio con login normal; UX móvil puede divergir de VB6.

## Áreas afectadas

| Área | Impacto |
|------|---------|
| `theme/static/img/pwa/`, login móvil template | Modificado |
| `login/views.py`, `urls.py`, `models.py`, `administranet_auth.py` | Nuevo/Modificado |
| `settings.py`, `requirements.txt`, `mobile_level_a_middleware.py` | Modificado |
| `core/tests/test_pwa.py`, `login/tests/` | Modificado/Nuevo |

## Decisiones de producto (resueltas 17/07/2026)

| # | Tema | Decisión |
|---|------|----------|
| 1 | Enrollment | **Opt-in** (default de propuesta; no contradicho) |
| 2 | Passkeys por usuario | Hasta **3** |
| 3 | Dispositivos compartidos / TPV | **No ocultar** el feature; cada persona debe desbloquear con **su** usuario/passkey |
| 4 | Empresa en unlock | **Sí** — re-selección de empresa en cada unlock |
| 5 | Cambio de password AdministraNET | **Sí** — revocar passkeys del usuario |
| 6 | TTL sesión post-unlock | **Sí** — sesión con TTL configurable (valor concreto en design; default sugerido alineado a `SESSION_COOKIE_AGE` o menor en móvil) |
| 7 | Superficie | **Solo PWA standalone** (instalada); no browser móvil ni desktop v1 |
| 8 | Desktop v1 | **No** |
| — | Iconos PWA | Usar el **logo del producto** (AdministraNET/Synap: familia `Logo_Signo_administraNET` / asset de marca) para generar `/static/img/pwa/icon-*.png` |

## Preguntas abiertas (producto)

Ninguna bloqueante. Confirmar en design el valor numérico del TTL (p. ej. 8 h / 24 h / igual a sesión desktop).

## Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Dispositivo compartido con passkeys de varios usuarios | Re-selección empresa + UI que pide passkey del usuario; enrollment opt-in; máx. 3 credenciales; revocación en perfil |
| Password VB6 vs passkey | Revocación automática al detectar cambio de password |
| RP ID / HTTPS | Config por `ENVIRONMENT` |
| Login sin SW/iconos | Fase 0 primero; iconos desde logo producto |
| Unlock fuera de PWA | Detectar `display-mode: standalone` (y equivalentes iOS) y no ofrecer unlock en browser |

## Rollback

Fase 0: revert iconos + bloque PWA login. Fase 1: `WEBAUTHN_UNLOCK_ENABLED=false`; UI/endpoints off; modelo intacto. Logout ≠ eliminar passkey.

## Dependencias

HTTPS staging/prod; asset de logo producto disponible para generar iconos PWA.

## Criterios de éxito

- [ ] PWA instalable desde login móvil con iconos del logo producto.
- [ ] Enroll opt-in (máx. 3) + unlock solo en PWA standalone; sesión con TTL.
- [ ] Unlock exige elegir empresa; revocación al cambiar password e impide unlock.
- [ ] Tests verde en `docker exec Synap_app`.
- [ ] Docs operativas actualizadas.
