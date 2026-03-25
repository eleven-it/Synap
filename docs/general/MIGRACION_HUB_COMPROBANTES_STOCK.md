# Migración: Hub de Comprobantes de Compra

**Formulario origen:** CargaComprobantesP.frm (FORM-001).  
**Ubicación en Synap:**
- **Menú Compras** (barra superior): **Compras** → **Facturación** (pantalla única Factura de Compra), **Listado de proveedores** (hub) o **Remito de Compra**.
- **Menú Stock** (alternativo): Stock → sección "Comprobantes de compra" → **Facturación** o **Listado de proveedores**.

El menú **Compras** es un módulo core (no requiere registro en ModuleConfig en la base de datos). Para verlo, el usuario debe tener el permiso **compras.ver** (o **compras.crear** para Remito de Compra). Asignar estos permisos desde Archivo → Puesto → Permiso en sistema.

## Qué se implementó

### 1. Hub (listado de proveedores + acciones)

- **Vista:** `compras.views.hub_comprobantes_proveedor`
- **URL:** `/compras/comprobantes-proveedor/` (`compras:hub_comprobantes`)
- **Template:** `compras/hub_comprobantes.html`

Funcionalidad (paridad con CargaComprobantesP):

- Listado de proveedores con **búsqueda** (texto, tipo: Incluye / Comienza con / Finaliza con), **filtro por sucursal** (si el usuario no tiene `ver_proveedor_sucursal`), **paginación** y **ordenación** por Código, Nombre, CUIT o saldo (whitelist, sin inyección).
- Datos vía **legacy_db.repositories** (`buscar_proveedores_paginado`, `count_proveedores`, `listar_sucursales`) y **legacy_db.mappers** (DTOs con `administranet_types`).
- Por cada proveedor, **acciones**: Factura de Compra, NC Devolución, NC Descuento, ND, Orden de Pago (imputación / a cuenta), Ver Cuenta Corriente.

### 2. Precheck antes de abrir comprobante

Al elegir una acción con un proveedor, se ejecuta la **misma lógica que en VB6** (y que en `legacy_db.api_precheck`):

- **keyFact:** CAI vigente, `obliga_oc_carga_comp` (no exigir OC para esta acción si está en "Si" → mensaje y no abrir).
- **keyPorimp / keyAcuenta:** Bloqueo OP (`fact_temporalp`); para "por imputación" además se exige que existan facturas para imputar.
- **keyNCDesR:** Que existan descuentos en `descuento_op_nc` (Computado='No', importe>0).

Si el precheck falla, se muestra mensaje de error en español y no se redirige. Si pasa, se redirige al formulario correspondiente (hoy placeholders).

### 3. Pantalla única Factura de Compra (Facturación)

- **Vista:** `compras.views.factura_compra`
- **URL:** `/compras/facturacion/` (`compras:factura_compra`)

Pantalla principal centrada en cargar facturas: **proveedor predictivo** (autocomplete vía `core_api:proveedor_search`), **origen de los datos** (Manual, Desde Remito, Desde OC, Desde Vale — no "tipo de factura", ver [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](../compras/ORIGEN_DATOS_FACTURA_COMPRA_VB6.md)), barra con Ver Cuenta Corriente, Agregar Proveedor, Informes, encabezado/cuerpo/pie. Si se accede desde el hub con acción Factura, se redirige aquí con `?codigo_proveedor=X`. El guardado vía legacy_db se implementará en la siguiente iteración.

### 4. Placeholders (otros formularios en construcción)

- **Orden de Pago:** `compras:orden_pago_form` (OrdenPago.frm), `tipo`: imputacion | acuenta.
- **Nota de Crédito:** `compras:nota_credito_form`, `tipo`: devolucion | descuento.
- **Nota de Débito:** `compras:nota_debito_form` (PNotaDeb.frm).
- **Cuenta Corriente Proveedor:** `compras:ctacte_proveedor` (CuentaProveedor.frm).

Todos muestran la plantilla "En construcción" y enlace de vuelta al hub. La **persistencia** se implementará usando **legacy_db** (repositories + services) para grabar igual que VB6.

### 5. Menú

- **Compras** (barra superior) → **Facturación** → pantalla única Factura de Compra (`compras:factura_compra`); **Listado de proveedores** → hub (`compras:hub_comprobantes`); **Remito de Compra** → formulario remito.
- **Stock** → **Comprobantes de compra** → **Facturación** o **Listado de proveedores** (acceso alternativo).
- Permisos: menú Compras requiere `compras.ver` (hub) o `compras.crear` (Remito de Compra). Entrada bajo Stock usa `stock.ver`.
- El módulo `compras` está en `core_modules` (siempre visible si el usuario tiene permiso); no es necesario activarlo en Module Management.

## Riesgos tratados

| Riesgo | Medida |
|--------|--------|
| SQL injection (VB6 concatenaba Busqueda.Text, Codigo) | Toda la lectura en `legacy_db.repositories` con parámetros; ordenación por whitelist `PROVEEDOR_ORDER_COLUMNS`. |
| Doble usuario OP mismo proveedor | Precheck con `check_lock_op_proveedor` (fact_temporalp) antes de abrir Orden de Pago. |
| CAI vencido / obliga_oc | Validadores `validar_cai_vigente` y `validar_obliga_oc_para_factura` antes de abrir Factura. |

## Próximos pasos (escritura como VB6)

1. Completar **Factura de Compra** en pantalla única: guardado (botón Generar) vía `legacy_db.services.factura_compra_service`; cabecera + detalle según origen de datos (Manual, Desde Remito, OC, Vale); mismos tipos/orden que VB6 (ver [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](../compras/ORIGEN_DATOS_FACTURA_COMPRA_VB6.md)).
2. **Orden de Pago:** abrir = `open_orden_pago` (lock fact_temporalp); confirmar = `confirmar_orden_pago_a_cuenta` o por imputación; cerrar = `close_orden_pago`.
3. NC, ND, Imputación/Desimputación: según inventario de cada .frm y checklist en [CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md](CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md).

## Referencias

- [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](../compras/ORIGEN_DATOS_FACTURA_COMPRA_VB6.md) — Origen de los datos para Factura de Compra (Manual, Remito, OC, Vale).
- [INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md](INVENTARIO_INGENIERIA_INVERSA_CARGA_COMPROBANTES_P.md)
- [CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md](CONVIVENCIA_VB6_DJANGO_LEGACY_DB.md)
- [TIPOS_DATOS_ADMINISTRANET.md](TIPOS_DATOS_ADMINISTRANET.md)
