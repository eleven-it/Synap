# 07 — Identity Boundary

**Estado:** COMPLETE  
**Fecha:** 25/08/2026

---

## Separación conceptual obligatoria

| Concepto | Qué es hoy | Dónde vive |
|----------|------------|------------|
| **Authentication** | Validar credenciales contra MySQL `usuarios` + AES | `login/administranet_auth.py:110-195` |
| **Identity** | `id_usuario`, `cod_usuario`, nombres | `session['user']` + `AdministraNETUser` mock |
| **Authorization** | Permisos por puesto | `synap_*` o `permiso_sistema*` via `administranet_permisos_usuario.py` |
| **Company Context** | Empresa operativa ERP | `session['user']['base_empresa']`, `id_empresa`, `id_sucursal` |
| **Tenant Context** | Instalación/cliente (deployment) | **Implícito** — 1 deploy = N empresas MySQL; no formalizado |

---

## Flujo reconstruido

```text
POST /login/ (login/views.py:41-93)
  → AdministraNETAuth.validate_user(cod, password, base_empresa)
      → MySQL AES_DECRYPT en usuarios (administranet_auth.py:137-153)
  → bootstrap_synap_session (session_bootstrap.py:11-84)
      → INSERT sesion MySQL (administranet_auth.py:399-413)
      → session["user"] = { id_usuario, cod_usuario, base_empresa, id_empresa, ... }
  → RequestUserMiddleware (base_middleware.py:442-459)
      → request.user = AdministraNETUser
  → @tiene_permiso / DRF permissions
  → mysql_pool.get_connection(session['user']['base_empresa'])
```

---

## ¿Quién es el Identity Provider real?

**AdministraNET MySQL** — tabla `usuarios` en BD `base_empresa`.

| Afirmación | Veredicto | Evidencia |
|------------|-----------|-----------|
| Synap tiene IdP propio operativo | **REFUTADA** | Login requiere validate_user AN |
| UsuarioExtendido (PG) es path primario | **REFUTADA** | Solo legacy Firebase path en middleware |
| WebAuthn reemplaza IdP | **REFUTADA** | Unlock post-auth; resuelve user en AN (`webauthn_service.py`) |
| Supervisor = superuser | **CONFIRMADA** | `cod_usuario == 'supervisor'` → `{"*"}` |

---

## ¿Puede existir usuario Synap sin AdministraNET?

| Tipo | Posible | Evidencia |
|------|---------|-----------|
| Login operativo | **NO** | `login/views.py:79` |
| Registro PG UsuarioExtendido | **SÍ** (modelo existe) | `core/models/models.py:169` — no usado en login UX |
| Permisos sin usuario AN | **NO** | Permisos atados a `id_puesto` MySQL |

---

## Company vs Tenant vs Session

| Key | Semántica | ID space | Set en |
|-----|-----------|----------|--------|
| `session['user']['base_empresa']` | Nombre BD MySQL empresa | string DB name | login |
| `session['user']['id_empresa']` | ID empresa AdministraNET | MySQL int | login |
| `session['empresa_activa_id']` | FK PostgreSQL `core.Empresa` | PG auto-PK | **no en bootstrap** — módulos específicos |
| `core.Empresa` | Metadata Synap | PG | ORM |

**Riesgo CONFIRMADO:** `id_empresa` (MySQL) ≠ `core.Empresa.id` (PG) sin sincronización explícita.

**Evidencia:** `factura_compra_captura/session_empresa.py:9-25` — fallback entre ambos.

---

## Permisos: ¿ERP o Synap?

| Modo | Fuente | Default |
|------|--------|---------|
| `legacy` | `permiso_sistema` MySQL | **settings default** (`settings.py:471`) |
| `synap` | `synap_*` MySQL | `.env.example` sugiere cutover |
| `dual` | Unión + warnings | Validación |

**Veredicto:** Permisos son **conceptualmente Synap** (tablas synap_*) pero **operacionalmente ERP** (default legacy). Cutover pendiente decisión humana.

---

## Respuestas explícitas

| # | Pregunta | Respuesta |
|---|----------|-----------|
| 17 | ¿Qué es el Core identity? | No hay — identity está en login+core services, no formalizado |
| 19 | ¿Cómo funciona Identity? | Heredada 100% de AdministraNET en path productivo |
| 20 | ¿Company Context? | `base_empresa` en session → mysql_pool |
| 21 | ¿Tenant Context? | No formalizado; deployment-level implicit |

---

*Tenancy options en `08-TENANCY-OPTIONS.md`. Seguridad IAM en `09-SECURITY-VALIDATION.md`.*
