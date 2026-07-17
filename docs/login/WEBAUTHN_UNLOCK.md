# WebAuthn — Desbloqueo rápido en PWA Synap

## Propósito

Permite desbloquear Synap en la PWA instalada (huella, Face ID o PIN del sistema) tras un login inicial con contraseña AdministraNET. **No reemplaza** la autenticación legacy ni introduce PIN propio de Synap.

## Feature flag

El desbloqueo WebAuthn se activa desde **Settings → System Configuration → Acceso rápido PWA** (`/configuracion/acceso-rapido-pwa/`). Requiere permiso `configuracion.sistema`. El valor se persiste en Postgres:

| Clave `SystemConfiguration` | Valores | Efecto |
|-----------------------------|---------|--------|
| `login.webauthn.unlock_enabled` | `true` / `false` | Si está desactivado: sin UI unlock/enroll global; APIs responden `404` con `{"error":"WebAuthn deshabilitado"}`. Las credenciales en Postgres **no se borran**. |

La variable de entorno `WEBAUTHN_UNLOCK_ENABLED` en `.env` está **deprecada e ignorada**; usar la UI de configuración.

### Preferencia por usuario

Cada usuario puede activar o desactivar su autenticación rápida en **Perfil → Ajustes** (toggle Activo/Inactivo). Se persiste en `login_webauthn_user_preference` (Postgres). Al desactivar **no** se borran las passkeys; el unlock falla hasta reactivar.

| Endpoint | Descripción |
|----------|-------------|
| `GET /login/api/webauthn/preference/` | `{ "enabled": true\|false }` |
| `POST /login/api/webauthn/preference/` | body `{ "enabled": true\|false }` |

Register y authenticate exigen feature global ON **y** preferencia del usuario ON (403 en español si está desactivada).

Otras variables en `django_project/settings.py`:

| Variable | Descripción |
|----------|-------------|
| `WEBAUTHN_RP_ID` | Fallback si no hay request. En runtime, register/authenticate usan el **hostname del request**. |
| `WEBAUTHN_ORIGIN` | Fallback si no hay request. En runtime se usa `scheme://host` del request (incluye puerto). |
| `WEBAUTHN_SESSION_AGE` | TTL sesión post-unlock (default **12 h**). |
| `WEBAUTHN_MAX_CREDENTIALS` | Máximo passkeys activas por `(base_empresa, id_usuario)` (**3**). |
| `WEBAUTHN_CHALLENGE_TTL` | TTL Redis del challenge (**120 s**), un solo uso. |

> **Importante (fix 07/2026):** Activar el toggle de Perfil solo guarda la preferencia; hay que **registrar el dispositivo** (passkey). El enroll se inicia automáticamente al activar si no hay credenciales. RP ID/origin se resuelven desde el host actual (no solo `SITE_URL`), para que LAN/PWA no fallen por mismatch.

## RP ID y origins

WebAuthn exige coherencia entre **RP ID** (hostname), **origin** (esquema + host + puerto) y el dominio desde el que se sirve la PWA.

- **Runtime:** `resolve_webauthn_rp(request)` toma hostname y origin del request (prioridad sobre `WEBAUTHN_*` en settings).
- **Fallback / tests:** `WEBAUTHN_RP_ID` / `WEBAUTHN_ORIGIN` (derivados de `SITE_URL` si no se overridean).
- **Desarrollo LAN:** si entrás por IP (`http://192.168.x.x:8000`), el RP ID será esa IP. WebAuthn en HTTP solo funciona en `localhost`; en dispositivos reales preferí HTTPS.
- Añadir el origin real a `CSRF_TRUSTED_ORIGINS`.

El navegador rechazará enroll/unlock si RP ID u origin no coinciden con la URL real de la PWA.

## Superficie de UI

- **PWA / superficie WebAuthn:** `login/static/login/pwa-standalone.js` detecta `standalone`, `fullscreen`, `minimal-ui`, `navigator.standalone` y guarda un marcador en `localStorage`.
- Al activar la preferencia en Perfil, si no hay passkeys se **dispara el enroll** (Face ID / huella).
- Sin passkey registrada, el botón de desbloqueo en login no puede completar la validación (mensaje claro en español).
- **Desktop v1:** sin WebAuthn dedicado.

## Flujo de enrollment (opt-in)

1. Usuario inicia sesión con contraseña AdministraNET.
2. En Perfil móvil, activa **Autenticación rápida** (toggle).
3. Si no hay dispositivos, se inicia automáticamente el registro biométrico (también disponible el botón «Activar desbloqueo en este dispositivo»).
4. `POST /login/api/webauthn/register/options/` → challenge en Redis (RP ID/origin del host actual).
5. Cliente (`webauthn-client.js`) invoca `navigator.credentials.create()`.
6. `POST /login/api/webauthn/register/verify/` → credencial en Postgres + `password_fingerprint`.

Máximo **3** dispositivos activos por usuario y empresa. Al intentar un cuarto, el servidor responde error en español.

## Flujo de unlock

1. PWA standalone sin sesión → `/login/`.
2. Usuario selecciona **empresa** y **cod_usuario** (re-selección obligatoria en cada unlock).
3. `POST /login/api/webauthn/authenticate/options/`.
4. Cliente invoca `navigator.credentials.get()`.
5. `POST /login/api/webauthn/authenticate/verify/` → sesión Django + fila `sesion` MySQL vía `bootstrap_synap_session` con `session_age=WEBAUTHN_SESSION_AGE`.

## Revocación

### Cambio de contraseña AdministraNET

Si el fingerprint actual no coincide con el guardado en enroll, **todas** las passkeys de ese `(base_empresa, id_usuario)` se revocan. El usuario debe iniciar sesión con contraseña y enrollar de nuevo.

### Manual desde perfil

- `GET /login/api/webauthn/credentials/` — lista passkeys activas.
- `POST /login/api/webauthn/credentials/revoke/` — body `{ "credential_id": "..." }` o `{ "all": true }`.

Revocar no cierra la sesión actual.

## Seguridad

- CSRF obligatorio en POST.
- Challenges Redis: TTL 120 s, **un solo uso** (se eliminan al verify).
- Rate limit en verify: **40 intentos / 300 s** por IP (`webauthn_auth_verify`, `webauthn_register_verify`).
- Prefijo `/login/api/webauthn/` en allowlist de `MobileLevelAOnlyMiddleware`.

## Endpoints

| Método | Ruta | Sesión | Descripción |
|--------|------|--------|-------------|
| GET | `/login/api/webauthn/preference/` | Sí | Leer preferencia usuario |
| POST | `/login/api/webauthn/preference/` | Sí | Guardar preferencia usuario |
| POST | `/login/api/webauthn/register/options/` | Sí | Options de registro |
| POST | `/login/api/webauthn/register/verify/` | Sí | Verificar registro |
| POST | `/login/api/webauthn/authenticate/options/` | No | Options de unlock |
| POST | `/login/api/webauthn/authenticate/verify/` | No | Verificar unlock + crear sesión |
| GET | `/login/api/webauthn/credentials/` | Sí | Listar passkeys |
| POST | `/login/api/webauthn/credentials/revoke/` | Sí | Revocar una o todas |

## Checklist E2E (manual)

1. [ ] Activar «Acceso rápido PWA» en Settings → System Configuration.
2. [ ] RP ID y origin alineados con la URL de la PWA.
3. [ ] Login con contraseña en móvil → instalar PWA → abrir en standalone.
4. [ ] Enroll passkey desde perfil; verificar aparece en lista.
5. [ ] Cerrar sesión → unlock con empresa + usuario + biometría → acceso Nivel A.
6. [ ] Cambiar contraseña en AdministraNET → unlock falla → re-login con contraseña → re-enroll.
7. [ ] Revocar passkey desde perfil → unlock ya no funciona con esa credencial.
8. [ ] Con feature global off: sin UI WebAuthn y APIs 404 JSON.
9. [ ] Usuario con preferencia off: unlock/register 403; passkeys conservadas.

## Tests automatizados

```bash
docker exec Synap_app python manage.py test login.tests.test_webauthn core.tests.test_pwa --keepdb -v1
```

## Referencias

- Diseño: `openspec/changes/login-pwa-webauthn/design.md`
- Spec: `openspec/changes/login-pwa-webauthn/specs/login-webauthn-unlock/spec.md`
- Código: `login/services/webauthn_service.py`, `login/webauthn_views.py`
- PWA login: `docs/general/PWA_SYNAP.md`
