# Spec — Factura electrónica y nota de crédito (mayoristapp)

**Relays:** `relay_factura_electronica.php`, `relay_nota_credito.php`, `relay_facturas_imputar.php`.  
**Checkpoint sugerido:** `mayoristapp_fe`.

---

## 1 — Alcance

- Consultas/listados sobre comprobantes electrónicos e imputaciones según el PHP.
- En esta etapa del plan, FE/imputación en mayoristapp queda en **solo lectura**.

---

## 2 — Synap objetivo

- Reutilizar módulo `fe_afip` o servicios existentes si ya hay flujo Synap; evitar duplicar lógica fiscal.
- Permisos estrictos (operativo/gerencial según caso).

---

## 3 — Pendientes

- `relay_nota_credito.php` v1 implementado:
  - `POST /ecom/api/mayoristapp/fe/nota-credito/listado/?ajax=1`
  - `GET /ecom/api/mayoristapp/fe/nota-credito/sugerencias-nro/?ajax=1&q=...`
  - Solo lectura, JSON; usa filtros de fecha/número/estado y alcance por sesión vendedor/cliente.
- `relay_factura_electronica.php` v1 implementado:
  - `POST /ecom/api/mayoristapp/fe/factura-electronica/listado/?ajax=1`
  - `GET /ecom/api/mayoristapp/fe/factura-electronica/sugerencias-nro/?ajax=1&q=...`
  - Solo lectura, JSON; filtros por fecha/número/tipo comprobante/estado + alcance por sesión.
- `relay_facturas_imputar.php` v1 implementado:
  - `POST /ecom/api/mayoristapp/fe/facturas-imputar/listado/?ajax=1`
  - `GET /ecom/api/mayoristapp/fe/facturas-imputar/sugerencias-nro/?ajax=1&q=...`
  - `POST /ecom/api/mayoristapp/fe/facturas-imputar/accion/?ajax=1`
  - El endpoint de `accion` está **bloqueado por política de plan** (`MAYORISTAPP_FE_WRITE_ENABLED=false` por defecto) para mantener solo listado/consulta.
- **[DECISIÓN-B-FE1]** resuelta: extender `fe_afip` para lógica reutilizable de escritura FE/imputación.
