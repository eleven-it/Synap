# Tasks: Acceso rápido PWA con WebAuthn

## Phase 0: PWA icons + login manifest/SW

- [x] 0.1 Crear `theme/static/img/brand/logo_signo_administranet.png` como fallback de marca.
- [x] 0.2 Crear `login/management/commands/generate_pwa_icons.py` (Pillow, logo MEDIA o fallback, maskable 80 %).
- [x] 0.3 Ejecutar `generate_pwa_icons` y commitear PNG en `theme/static/img/pwa/icon-*.png` (≥192, 512 maskable).
- [x] 0.4 Crear `login/templates/login/includes/pwa_head.html` (manifest, meta, apple-touch-icon).
- [x] 0.5 Crear `login/templates/login/includes/pwa_sw_register.html` (registro SW, paridad `base_app.html`).
- [x] 0.6 Modificar `login/templates/login/mobile/login_administranet.html`: includes PWA solo si `request.is_mobile`.

## Phase 1: Model + migration + settings + webauthn dependency

- [x] 1.1 Añadir `webauthn>=2.0,<3` en `requirements.txt` e instalar en contenedor.
- [x] 1.2 Definir `WebAuthnCredential` en `login/models.py` (campos e índice `(base_empresa, id_usuario)`).
- [x] 1.3 Crear migración `login/migrations/0001_initial.py` (WebAuthnCredential) y aplicar en Postgres.
- [x] 1.4 Añadir `WEBAUTHN_*` en `django_project/settings.py` (flag, RP ID, origin, session age 12 h, max 3, challenge TTL).

## Phase 2: Session bootstrap refactor

- [x] 2.1 Crear `login/services/session_bootstrap.py` con `bootstrap_synap_session(..., session_age=None)`.
- [x] 2.2 Añadir `get_user_by_id()` y `get_password_fingerprint()` en `login/administranet_auth.py`.
- [x] 2.3 Refactorizar `login/views.py` (bloque post-login ~87–131) para usar `session_bootstrap`.

## Phase 3: WebAuthn APIs

- [x] 3.1 Crear `login/services/webauthn_service.py` (options/verify, Redis challenge TTL 120 s, límite 3, user_handle).
- [x] 3.2 Crear `login/webauthn_views.py`: 6 endpoints JSON bajo `/login/api/webauthn/` con CSRF y rate limit.
- [x] 3.3 Registrar rutas en `login/urls.py` y guard 404 JSON si flag desactivado.

## Phase 4: Frontend enroll/unlock (standalone only, company reselect)

- [x] 4.1 Crear `login/static/login/pwa-standalone.js` con `isPwaStandalone()`.
- [x] 4.2 Crear `login/static/login/webauthn-client.js` (fetch options/verify + CSRF).
- [x] 4.3 Modificar `login_administranet.html`: UI unlock sin sesión (standalone + flag + selector `base_empresa`/`cod_usuario`).
- [x] 4.4 Añadir UI enroll opt-in post-login en PWA standalone (máx. 3, etiqueta dispositivo).

## Phase 5: Password fingerprint revoke + profile revoke UI

- [x] 5.1 En `webauthn_service`: comparar fingerprint en unlock; mismatch → revocar todas `(base_empresa, id_usuario)`.
- [x] 5.2 Persistir fingerprint al enroll y actualizar `last_used_at`/`sign_count` en verify exitoso.
- [x] 5.3 Modificar `login/templates/login/mobile/perfil.html`: listar passkeys y revocar por credencial o todas.

## Phase 6: Middleware allowlist + feature flag

- [x] 6.1 Añadir prefijo `/login/api/webauthn/` al allowlist en `core/middleware/mobile_level_a_middleware.py`.
- [x] 6.2 Verificar flag off: sin UI enroll/unlock en templates y APIs 404 `{"error":"WebAuthn deshabilitado"}`.

## Phase 7: Tests + docs

- [x] 7.1 Extender `core/tests/test_pwa.py`: manifest/SW en login móvil e iconos referenciados (CA spec PWA).
- [x] 7.2 Crear `login/tests/test_webauthn.py`: límite 3, challenge single-use, rate limit, flag off, fingerprint revoke, unlock TTL.
- [x] 7.3 Test integración: authenticate/options+verify con `@override_settings(WEBAUTHN_UNLOCK_ENABLED=True)` y mocks.
- [x] 7.4 Crear `docs/login/WEBAUTHN_UNLOCK.md` (RP ID, enroll, revoke, checklist E2E).
- [x] 7.5 Actualizar `docs/general/PWA_SYNAP.md` (Fase 0, comando `generate_pwa_icons`).
