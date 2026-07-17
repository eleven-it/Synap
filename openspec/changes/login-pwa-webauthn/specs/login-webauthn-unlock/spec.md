# Spec — Desbloqueo WebAuthn post-login

**Capability:** `login-webauthn-unlock`
**Change:** `login-pwa-webauthn`
**Estado:** Propuesto

---

## Purpose

Permitir que usuarios con PWA instalada desbloqueen Synap con huella, Face ID o PIN del sistema operativo (WebAuthn) tras un login inicial con contraseña AdministraNET, sin reemplazar la autenticación legacy ni introducir PIN propio Synap.

---

## Requirements

### Requirement: Feature flag global

El desbloqueo WebAuthn MUST estar controlado por un flag de configuración (p. ej. `WEBAUTHN_UNLOCK_ENABLED`). Cuando el flag está desactivado, el sistema MUST NOT exponer UI de enrollment/unlock ni endpoints funcionales de registro/autenticación WebAuthn; las credenciales almacenadas MUST permanecer intactas.

#### Scenario: Flag desactivado oculta el feature

- **GIVEN** `WEBAUTHN_UNLOCK_ENABLED=false`
- **WHEN** un usuario abre login móvil o perfil
- **THEN** no ve opciones de activar ni desbloquear con passkey y las APIs responden deshabilitadas

---

### Requirement: Superficie solo PWA standalone

La UI de desbloqueo WebAuthn MUST mostrarse únicamente cuando la app corre en modo PWA standalone (`display-mode: standalone` o equivalente iOS `navigator.standalone`). El sistema MUST NOT ofrecer desbloqueo en navegador móvil no instalado ni en desktop v1.

#### Scenario: Unlock en PWA instalada

- **GIVEN** PWA en modo standalone sin cookie de sesión válida y flag activo
- **WHEN** el usuario visita `/login/`
- **THEN** ve la pantalla de desbloqueo con passkey (si tiene credenciales registradas)

#### Scenario: Browser móvil sin standalone

- **GIVEN** Safari/Chrome móvil en pestaña normal (no standalone)
- **WHEN** el usuario visita `/login/` sin sesión
- **THEN** ve solo login con contraseña AdministraNET; no se ofrece desbloqueo WebAuthn

#### Scenario: Desktop v1 excluido

- **GIVEN** navegador desktop
- **WHEN** accede a login
- **THEN** no se ofrece enrollment ni unlock WebAuthn

---

### Requirement: Enrollment opt-in con máximo tres passkeys

El registro de passkey MUST ser opt-in tras login exitoso con contraseña; el sistema MUST NOT registrar passkeys automáticamente. Cada par `(base_empresa, id_usuario)` MUST admitir como máximo **3** credenciales WebAuthn activas. Al intentar registrar una cuarta, el sistema MUST rechazar el enrollment.

#### Scenario: Usuario activa desbloqueo voluntariamente

- **GIVEN** sesión válida post-login con contraseña y flag activo en PWA standalone
- **WHEN** el usuario elige activar desbloqueo rápido
- **THEN** completa enrollment WebAuthn y queda registrada una credencial para ese `(base_empresa, id_usuario)`

#### Scenario: Límite de tres passkeys

- **GIVEN** un usuario con 3 passkeys activas para la misma `(base_empresa, id_usuario)`
- **WHEN** intenta registrar una cuarta
- **THEN** el sistema rechaza el registro e informa que debe revocar una credencial existente

#### Scenario: Sin enrollment no hay unlock

- **GIVEN** usuario que nunca enrolló passkey
- **WHEN** abre la PWA standalone sin sesión
- **THEN** debe autenticarse con contraseña AdministraNET; no puede desbloquear con WebAuthn

---

### Requirement: Dispositivos compartidos sin ocultar el feature

En dispositivos compartidos (p. ej. tablet de mostrador), el sistema MUST NOT ocultar enrollment ni unlock por contexto de puesto. Cada persona MUST desbloquear con **su** usuario y passkey propios; la UI MUST dejar claro qué usuario/empresa se está desbloqueando.

#### Scenario: Varios usuarios en el mismo dispositivo

- **GIVEN** una tablet compartida con passkeys de usuarios A y B
- **WHEN** el usuario B inicia unlock
- **THEN** debe identificarse y usar la passkey de B; no se obtiene sesión de A

---

### Requirement: Re-selección de empresa en cada unlock

Cada desbloqueo MUST exigir selección explícita de `base_empresa` antes de verificar la passkey. El lookup de credencial MUST usar la clave compuesta `(base_empresa, id_usuario)`.

#### Scenario: Unlock con cambio de empresa

- **GIVEN** un usuario con passkeys en empresas X e Y
- **WHEN** elige empresa Y y completa WebAuthn
- **THEN** la sesión creada tiene `base_empresa=Y` y permisos de Y

#### Scenario: Empresa incorrecta para la passkey

- **GIVEN** passkey registrada solo para empresa X
- **WHEN** el usuario selecciona empresa Y e intenta unlock
- **THEN** la verificación falla y no se crea sesión

---

### Requirement: Sesión post-unlock con TTL

Tras verify exitoso, el sistema MUST crear sesión Django y fila `sesion` MySQL equivalente al login con contraseña (mismos hooks de negocio). La sesión MUST tener TTL acotado; la duración MUST ser configurable (valor concreto en design; default sugerido alineado a `SESSION_COOKIE_AGE` o menor en móvil, p. ej. 12 h).

#### Scenario: Unlock crea sesión válida acotada

- **GIVEN** verify WebAuthn exitoso
- **WHEN** el servidor emite `sessionid`
- **THEN** el usuario accede a rutas Nivel A y la sesión expira según TTL configurado

---

### Requirement: Revocación al cambiar contraseña AdministraNET

Cuando se detecte cambio de contraseña del usuario en AdministraNET (MySQL legacy), el sistema MUST revocar **todas** las passkeys de ese `(base_empresa, id_usuario)`. Tras revocación, unlock MUST fallar hasta nuevo enrollment tras login con contraseña.

#### Scenario: Password cambiada invalida passkeys

- **GIVEN** usuario con passkey activa
- **WHEN** su contraseña AdministraNET cambia en legacy
- **THEN** todas sus passkeys quedan revocadas y el próximo unlock falla

#### Scenario: Re-enrollment tras cambio de password

- **GIVEN** passkeys revocadas por cambio de password
- **WHEN** el usuario inicia sesión con la nueva contraseña y opta por enrollar de nuevo
- **THEN** puede registrar una nueva passkey

---

### Requirement: Revocación manual desde perfil

El usuario autenticado MUST poder listar y revocar sus passkeys desde perfil (por credencial o todas). Revocar MUST NOT cerrar la sesión actual salvo acción explícita de logout.

#### Scenario: Revocar passkey desde perfil

- **GIVEN** usuario con sesión activa y al menos una passkey
- **WHEN** revoca una credencial desde perfil
- **THEN** esa passkey deja de funcionar para unlock y las demás siguen activas si no fueron revocadas

#### Scenario: Logout no elimina passkey

- **GIVEN** usuario con passkey registrada
- **WHEN** cierra sesión
- **THEN** la passkey permanece y puede usarse en el próximo unlock en PWA standalone

---

### Requirement: Seguridad de endpoints WebAuthn

Los endpoints de registro y autenticación WebAuthn MUST exigir CSRF en mutaciones, challenges de un solo uso y rate limiting reutilizando la política de login. Deben estar en allowlist de `MobileLevelAOnlyMiddleware`.

#### Scenario: Rate limit en authenticate

- **GIVEN** múltiples intentos fallidos de unlock desde la misma IP/usuario
- **WHEN** se supera el umbral configurado
- **THEN** el sistema bloquea temporalmente nuevos intentos y responde con error de límite

#### Scenario: Challenge de un solo uso

- **GIVEN** un challenge WebAuthn ya consumido
- **WHEN** se reutiliza en un segundo POST verify
- **THEN** la verificación falla

---

### Requirement: Identificador de usuario WebAuthn

Cada credencial MUST vincularse a `(base_empresa, id_usuario)` con `user_handle` estable `{base_empresa}:{id_usuario}`. Las credenciales MUST persistir en PostgreSQL (app Synap), no en MySQL legacy.

#### Scenario: Mismo cod_usuario en distintas bases

- **GIVEN** el mismo `cod_usuario` en bases A y B
- **WHEN** enrolla passkey en base A
- **THEN** la credencial no permite unlock en base B sin enrollment separado
