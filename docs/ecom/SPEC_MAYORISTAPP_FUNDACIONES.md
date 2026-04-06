# Spec — Fundaciones mayoristapp (sesión y permisos)

**Vertical:** prerequisito de todos los relays `mayoristapp/`.  
**Apps Synap:** `login`, `core`, sesión Django.

---

## 1 — Variables de sesión PHP (referencia)

Resumidas en [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md) §A.5 y [REVERSE_ENGINEERING.md](./REVERSE_ENGINEERING.md): `vendedor`, `vendedor_a_cargo`, `todos_clientes`, `deposito`, `idusuario`, `tipousuario`, `usa_id_manual`, `verStock`, flags módulos, etc.

Login: `control.php` + `permiso_sistema_puesto` (no replicar AES en SQL en rutas nuevas).

---

## 2 — Mapeo a Synap (estado actual)

| Necesidad relay | Synap hoy |
|-----------------|-----------|
| Base MySQL empresa | `request.session['user']['base_empresa']` |
| CodViajante vendedor | `request.session['user']['id_vendedor_usr']` |
| Equipo vendedores | `request.session['user']['vendedor_a_cargo']` (lista opcional; si falta, solo viajante único) |
| Estado mayoristapp UI | `request.session['mayoristapp']` (`busca_rubro`, `clase_lista`, extensible) |
| Usuario autenticado | `request.user` + sesión administraNET poblada en login |

---

## Decisiones Fase B

- **[DECISIÓN-B-F1]** Las nuevas API e-com/reportes **no** validan contraseña con AES en MySQL; asumen usuario ya autenticado vía flujo Synap existente.
- **[DECISIÓN-B-F2]** Población de `vendedor_a_cargo`, `todos_clientes` y demás flags PHP en sesión: **pendiente de alinear** con `login`/`core` cuando un relay lo requiera (documentar en el spec del relay concreto).
- **[DECISIÓN-B-F3]** Permiso genérico catálogo: `EcomMayoristappSessionPermission` (sesión + `base_empresa`). Informes relay ventas netas: `OperationalReportsPermission` / `ManagerialReportsPermission` según [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md).

---

## 3 — Pendientes Fase C

- Inventario de claves `session['user']` usadas por cada relay aún no migrado; ampliar login si hace falta.
- Documento único de paridad permisos PHP `permiso_sistema_puesto` ↔ permisos Django (referencia `core/constantes_permisos.py`).
