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
| Equipo vendedores | `request.session['user']['vendedor_a_cargo']` (lista de `CodViajante`; supervisor: JSON en `configuracion_ecom`) |
| Vendedor operativo pedidos | `request.session['mayoristapp']['cod_viajante_operativo']` (default `id_vendedor_usr`; ver §4) |
| Estado mayoristapp UI | `request.session['mayoristapp']` (`busca_rubro`, `clase_lista`, extensible) |
| Usuario autenticado | `request.user` + sesión administraNET poblada en login |

---

## Decisiones Fase B

- **[DECISIÓN-B-F1]** Las nuevas API e-com/reportes **no** validan contraseña con AES en MySQL; asumen usuario ya autenticado vía flujo Synap existente.
- **[DECISIÓN-B-F2]** Población de `vendedor_a_cargo`, `todos_clientes`, `usa_id_manual` y `id_vendedor_usr`: **`ecom/services/mayoristapp_sesion_contexto.py`** hidrata desde MySQL (usuarios + permiso_sistema_puesto) en cada API/vista mayoristapp; paridad `control.php`.
- **[DECISIÓN-B-F3]** Permiso genérico catálogo: `EcomMayoristappSessionPermission` (sesión + `base_empresa`). Informes relay ventas netas: `OperationalReportsPermission` / `ManagerialReportsPermission` según [SPEC_VENTAS_NETAS.md](./SPEC_VENTAS_NETAS.md).

---

## 4 — Cartera supervisor (`vendedor_a_cargo`) y vendedor operativo

### Origen PHP (hardcode)

En `administraNET-ecom/control.php` (aprox. L472–507), cuando `permiso_supervisor_venta == "Si"`, un `switch` por `id_usuario` asigna manualmente un array de `CodViajante` a `$_SESSION["vendedor_a_cargo"]` (L703). **No hay tabla MySQL** para esta relación.

Ejemplo documentado en código PHP (cliente chapini):

| `id_usuario` (PHP) | `CodViajante` en cartera |
|--------------------|--------------------------|
| 16 | 10, 49, 46, 54 |

> El mapeo PHP usa `id_usuario`; en Synap la clave de configuración usa el **`CodViajante` del supervisor** (consultar `usuarios.CodViajante`).

### Resolución Synap (sin DDL)

| Clave `configuracion_ecom.key_permiso` | Valor `valor_permiso` |
|----------------------------------------|------------------------|
| `ecom_vendedores_a_cargo_<CodViajante>` | JSON array de enteros, ej. `[10,49,46,54]` |

- Lectura: `ecom/services/vendedor_operativo.py` → `leer_vendedores_a_cargo_config`.
- Hidratación sesión: `mayoristapp_sesion_contexto.py` cuando `supervisor_venta='Si'`.
- **Fallback** sin fila: `vendedor_a_cargo = [CodViajante propio]`.

### Seed opcional (por base)

```sql
-- Ejemplo: supervisor CodViajante=16 con cartera chapini
INSERT INTO configuracion_ecom (key_permiso, valor_permiso)
VALUES ('ecom_vendedores_a_cargo_16', '[10,49,46,54]')
ON DUPLICATE KEY UPDATE valor_permiso = VALUES(valor_permiso);
```

Ajustar `16` al `CodViajante` real del supervisor en la base.

### Vendedor operativo (`cod_viajante_operativo`)

- Clave: `session['mayoristapp']['cod_viajante_operativo']`.
- Default: `id_vendedor_usr` del usuario logueado.
- Resolver único: `ecom/services/vendedor_operativo.py` → `resolver_viajante_operativo` (consumido por checkout, masivo, clientes).
- APIs: `GET /ecom/api/mayoristapp/vendedores-cartera/`, `POST /ecom/api/mayoristapp/vendedor-operativo/`.
- Al cambiar operativo: limpiar cliente + carrito/borrador; al logout: restablecer al viajante propio.

---

## 5 — Change `ecom-pedidos-usabilidad-supervisor` — oleadas A–E (13/07/2026)

Corte vertical que consolidó supervisor operativo, VCM, descuentos y masivo sobre estas fundaciones. La pieza fundacional es el **resolver único de viajante efectivo** (§4).

| Oleada | Resumen | Artefactos clave |
|--------|---------|------------------|
| **A — Sesión y vendedor operativo** | `cod_viajante_operativo` (default `id_vendedor_usr`) resuelto por `resolver_viajante_operativo`; cartera supervisor desde `configuracion_ecom` (`ecom_vendedores_a_cargo_<CodViajante>`), fallback `[cv]`. Fix `_session_cod_viajante` en checkout. | `ecom/services/vendedor_operativo.py`, `mayoristapp_sesion_contexto.py`, `includes/pedidos_selector_vendedor.html`, APIs `vendedores-cartera/` y `vendedor-operativo/` |
| **B — VCM simple + lista RO** | Clientes/artículos por ternas del viajante efectivo también en pedido simple; badge de lista de precios solo lectura. | `cliente_relay.py`, `vendedor_asignacion_sql.py`, `includes/pedidos_lista_badge.html` |
| **C — Descuentos pedido simple** | % desc. por renglón (PATCH) y desc. al pie precargado; totales siempre backend. | `pedidos_lineas_tabla.html`, `pedidos_order_summary.html`, `mayorista_cart_service.py` |
| **D — Pedido masivo** | Precio real por fila (`price_rules_engine`), % desc. fila + pie, endpoint preview con límite blando, modal canon, `CodViajante` operativo. | `pedido_masivo_matriz.py`, `pedido_masivo_views.py`, `batch_checkout_masivo.py`, `static/ecom/pedido_masivo_app.mjs` |
| **E — Visual slate/sky** | Barrido de purple en el flujo de pedido (simple y masivo); PED = sky; token compartido `.pedidos-badge-lista`. | `pedidos_page_styles.html`, `pedidos_breadcrumb.html`, `pedidos_order_summary.html`, `pedidos_modal.html`, `compra_mayorista.html` |

> **Nota de paridad:** este documento ya no afirma hidratación completa "automática" de `vendedor_a_cargo` para supervisores; la cartera del supervisor se resuelve desde `configuracion_ecom` (§4) con fallback al viajante propio.

---

## 3 — Pendientes Fase C

- Inventario de claves `session['user']` usadas por cada relay aún no migrado; ampliar login si hace falta.
- Documento único de paridad permisos PHP `permiso_sistema_puesto` ↔ permisos Django (referencia `core/constantes_permisos.py`).
