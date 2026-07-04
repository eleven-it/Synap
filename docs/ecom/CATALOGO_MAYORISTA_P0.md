# Catálogo de productos mayorista — Fase P0

**Change:** `catalogo-carrito-checkout-mayorista`  
**Fecha implementación:** 02/07/2026  
**Alcance:** Solo lectura (listado paginado + ficha de detalle)

---

## Endpoints implementados

### POST `/ecom/api/mayoristapp/catalogo/articulos/listado/`

**Vista:** `CatalogoArticulosListadoRelayAPIView`  
**Servicio:** `ecom.services.catalogo_producto.listar_articulos_paginado`

Listado paginado de artículos del catálogo ecommerce (activos: `Discontinuo='No'`, `ecommerce='Si'`) con precio calculado según lista/cliente de sesión y stock disponible del depósito activo.

**Request body:**
```json
{
  "filtros": {
    "rubro": int,
    "subrubro": int,
    "marca": int,
    "laboratorio": int,
    "proveedor": int,
    "q": "texto búsqueda",
    "solo_promocion": bool
  },
  "pagina": 1,
  "tam": 20
}
```

**Response:**
```json
{
  "items": [
    {
      "id_articulo": int,
      "id_manual": str,
      "codigo": str,
      "nombre": str,
      "rubro": str,
      "subrubro": str,
      "marca": str,
      "precio": float,
      "stock_disponible": float,
      "tiene_foto": bool,
      "en_promocion": bool
    }
  ],
  "total": int,
  "pagina": int,
  "tam": int,
  "total_paginas": int
}
```

**Filtros:**
- `rubro`, `subrubro`, `marca`, `laboratorio`, `proveedor`: WhiteList de columnas artículo (parametrizados).
- `q`: LIKE sobre `NombreArticulo`, `CodigoArticuloT`, `id_manual`.
- `solo_promocion`: `articulo.promocion='Si'`.

**Paginación:** LIMIT/OFFSET (tam máx 100).

---

### GET `/ecom/api/mayoristapp/catalogo/articulos/<int:idart>/detalle/`

**Vista:** `CatalogoArticuloDetalleRelayAPIView`  
**Servicio:** `ecom.services.catalogo_producto.obtener_detalle_articulo`

Ficha de detalle de artículo (por `IDArt`) con precio neto y con IVA, stock por depósito, promociones vigentes.

**Response:**
```json
{
  "id_articulo": int,
  "id_manual": str,
  "codigo": str,
  "nombre": str,
  "descripcion": str,
  "rubro": str,
  "subrubro": str,
  "marca": str,
  "precio": float,
  "precio_neto": float,
  "stock_disponible": float,
  "stock_depositos": [
    {
      "id_deposito": int,
      "nombre_deposito": str,
      "saldo": float,
      "saldo_pedido": float,
      "disponible": float
    }
  ],
  "tiene_foto": bool,
  "promocion": {
    "tipo": str,
    "por": float,
    "cant": int,
    "alcance": str,
    "vigencia_desde": str,
    "vigencia_hasta": str
  }
}
```

**404:** Si el artículo no existe o está inactivo (`Discontinuo='Si'` o `ecommerce='No'`).

---

## Cálculo de precios (REQ-CAT-003)

**Motor único:** `ecom.services.price_rules_engine.calcular_precio_articulo_row`

Función integradora que:
1. Resuelve `precio_base` desde columna de lista del row: `Precio1V..Precio5V` (listas 1..5), `PNOficial` (lista 6).
2. Resuelve `alicuota_iva` (JOIN `iva.Alicuota`, default 21) e `impuesto_interno` (columna `articulo.impuesto_interno`, default 0).
3. `tipo_cliente`: None si no hay cliente (no aplica descuento, per SPEC D).
4. Llama `resolver_regla_precio` (si hay cliente + conn) y `resolver_promocion_articulo`.
5. Delega en `calcular_precio_con_motor` (motor existente, sin duplicar lógica).

**Paridad garantizada:** mismo precio que relays de precio existentes (`price_relay_views`).

---

## Stock disponible

**Fuente:** `self_checkout.services.StockService`

- **Listado:** `get_disponible_map(ids, id_deposito)` → una consulta IN para N artículos.
- **Detalle:** `get_disponible(id_articulo, id_deposito)` + consulta manual a `stock_deposito` para desglose por depósito.

**Disponible:** `max(0, saldo - saldo_pedido_cliente)` (sin confundir con saldo bruto).

---

## Sesión y permisos

**Permiso:** `EcomMayoristappSessionPermission` (requiere `base_empresa` en sesión).

**Lista de precio y cliente:**
- Helpers reutilizados de `precio_relay_views`: `_cod_lista_precio_cliente_desde_sesion` (→ 1..5), `_obtener_lista_id_y_cliente`.
- Si no hay cliente/lista en sesión: usa lista por defecto de `configuracion.lista_precio_web`.
- `leer_idcliente_mayoristapp`, `leer_cliente_seleccionado` (de `mayoristapp_session.py`): descuento de renglón, `iva_incluido`.

**Depósito activo:** `session['deposito']` o `mayoristapp['deposito']`; si no hay, default 1.

---

## Tests

**Archivos:**
- `ecom/tests/test_catalogo_producto_listado.py` (8 casos: paginación/metadata, filtros, precio==motor mock, sin cliente→default, 403 sin permisos).
- `ecom/tests/test_catalogo_producto_detalle.py` (6 casos: detalle ok, promo vigente, 404 inexistente, stock por depósito, 403 sin permisos).

**Ejecución:** `docker exec Synap_app python manage.py test ecom.tests.test_catalogo_producto_listado ecom.tests.test_catalogo_producto_detalle --noinput --keepdb`

**Resultado:** ✅ 8 tests OK (verificado 02/07/2026).

---

## Pendiente para fases siguientes

**Fuera de alcance P0:**
- **Imágenes:** resolver ruta/URL de imagen del artículo (paridad `foto.php`) → P3.
- **Restricciones por PV:** config de catálogo por punto de venta (ex-AMICO) → P3.
- **Carrito:** P1 (tabla propia Postgres `ecom_cart`, sin tocar legacy).
- **Checkout:** P2 (escritura legacy transaccional: `comp_ped`, `stockp`, `stock_deposito`, numeración segura `talonarios`/`codmov`).

---

## Referencias

- **Spec:** `openspec/changes/catalogo-carrito-checkout-mayorista/specs/ecom-catalogo-producto-mayorista/spec.md`
- **Design:** `openspec/changes/catalogo-carrito-checkout-mayorista/design.md` (§2 Fase P0)
- **Tasks:** `openspec/changes/catalogo-carrito-checkout-mayorista/tasks.md`
- **Motor de precios:** `ecom/services/price_rules_engine.py`, `ecom/services/price_calculator.py`
- **SPEC precios:** `docs/ecom/SPEC_PRECIOS.md`
