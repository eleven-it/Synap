# Spec — Logística y carrito (mayoristapp)

**Logística:** `relay-envio-calculo.php`, `relay_geolocalizacion.php`, `relay_ruta_logistica.php`, `relay-logistica-comprobantes.php`.  
**Pantalla TV estado de pedidos:** `logistica_pantalla_preparacion.php` + `ajax/json_pantalla_pedidos.php` → migrado a Synap: vista `ecom:mayoristapp_estado_pedidos_preparacion`, API `ecom:mayoristapp_logistica_estado_pedidos` (ver `SPEC_ESTADO_PEDIDOS_PREPARACION.md`).  
**Carrito:** `jcart/relay.php`, `tmobile/jcart/relay-mob.php`.  
**Checkpoints:** `mayoristapp_logistica`, `mayoristapp_jcart_web`, `mayoristapp_jcart_mob`.

---

## 1 — Alcance

- Cálculo de envíos, mapas/rutas, comprobantes en contexto logístico.
- Carrito web y variante móvil (estado, líneas, totales; posible dependencia de sesión PHP distinta).

---

## 2 — Synap objetivo

- API REST + eventual PWA; sesión unificada con `mayoristapp` / `user`.
- Integraciones externas (mapas) solo con claves en entorno.

---

## 3 — Decisiones Fase B

- **[DECISIÓN-B-L1]** Carrito móvil (`tmobile`) puede tratarse como **sub-proyecto** después del carrito web si comparten poco código.
- **[DECISIÓN-B-L2]** Geolocalización: no exponer claves API en frontend sin restricción de dominio/referer.

---

## 4 — Pendientes Fase C

- Inventario de endpoints POST/GET por archivo.
- Modelo de carrito en Synap (PostgreSQL vs solo sesión) — **[DECISIÓN PENDIENTE]** producto.
