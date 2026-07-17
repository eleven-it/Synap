# Spec — Instalabilidad PWA en login móvil

**Capability:** `pwa-instalabilidad-login`
**Change:** `login-pwa-webauthn`
**Estado:** Propuesto

---

## Purpose

Habilitar que Synap sea instalable como PWA desde la pantalla de login móvil (`start_url=/login/`), con iconos de marca del producto y registro de manifest + service worker en esa primera pantalla, prerequisito para el desbloqueo WebAuthn en modo standalone.

---

## Requirements

### Requirement: Iconos PWA derivados del logo del producto

El sistema MUST generar y servir iconos PNG en `/static/img/pwa/icon-*.png` (incluyendo al menos 192×192 y 512×512 con propósito `any maskable`) derivados del logo del producto AdministraNET/Synap (familia `Logo_Signo_administraNET` / asset resuelto por `get_administranet_logo`). Los iconos MUST referenciarse en `manifest.json` y MUST cumplir criterios de instalabilidad de Chrome y Safari iOS.

#### Scenario: Instalación con iconos de marca

- **GIVEN** un usuario en login móvil con iconos PWA presentes y derivados del logo del producto
- **WHEN** el navegador evalúa instalabilidad de la PWA
- **THEN** la app instalada muestra el icono de marca AdministraNET/Synap en la pantalla de inicio

#### Scenario: Iconos faltantes impiden instalación

- **GIVEN** el directorio `/static/img/pwa/` sin los PNG requeridos por el manifest
- **WHEN** el usuario intenta instalar la PWA
- **THEN** el navegador no ofrece instalación o la marca falla el criterio de iconos mínimos

---

### Requirement: Manifest y service worker en login móvil

La plantilla de login móvil MUST incluir `<link rel="manifest">`, meta tags PWA aplicables y registro del service worker, aunque no extienda `base_app.html`. El `start_url` del manifest MUST ser `/login/`.

#### Scenario: Primera apertura de PWA instalada en login

- **GIVEN** una PWA instalada cuyo `start_url` es `/login/`
- **WHEN** el usuario abre la app instalada por primera vez
- **THEN** la página de login carga manifest, meta PWA y registra el service worker

#### Scenario: Paridad con rutas PWA existentes

- **GIVEN** rutas `/manifest.json` y `/sw.js` operativas
- **WHEN** el login móvil referencia el manifest
- **THEN** el navegador obtiene el mismo manifest que el resto de la app móvil

---

### Requirement: Alcance móvil sin desktop v1

La instalabilidad PWA en login MUST aplicarse solo en contexto móvil (`request.is_mobile`). El sistema MUST NOT promover ni habilitar instalación PWA WebAuthn en desktop en v1.

#### Scenario: Desktop sin promoción PWA login

- **GIVEN** un usuario en navegador desktop
- **WHEN** accede a `/login/`
- **THEN** no se muestra flujo de instalación PWA orientado al desbloqueo rápido móvil

---

### Requirement: Middleware y rutas PWA en Nivel A

Las rutas PWA existentes (`/manifest.json`, `/sw.js`, `/offline/`) y el login móvil MUST permanecer accesibles bajo `MobileLevelAOnlyMiddleware` sin regresión respecto a `core/tests/test_pwa.py`.

#### Scenario: Manifest accesible en móvil Nivel A

- **GIVEN** petición móvil autenticada o no en Nivel A
- **WHEN** solicita `/manifest.json`
- **THEN** recibe HTTP 200 con JSON válido e iconos referenciados
