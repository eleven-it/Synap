# Diseño técnico — Catálogo, carrito y checkout mayorista

**Change:** `catalogo-carrito-checkout-mayorista`
**Fecha:** 02/07/2026
**Alcance del documento:** arquitectura global del vertical + diseño detallado de **Fase P0** (catálogo) y **Fase P2** (checkout/alta). P1 implementada (ver spec `ecom-carrito-mayorista`); P3 se especifica al iniciarse.

---

## 1. Arquitectura general

```
Navegador (portal mayorista, Alpine/JS, base_app.html)
        │  fetch JSON
        ▼
ecom/ (Django REST APIViews)  ── permiso EcomMayoristappSessionPermission
        │
        ├── P0 catálogo_producto_relay_views  → services/catalogo_articulo.py (extend)
        │                                        └─ price_rules_engine (reuse)
        ├── P1 carrito_views                  → services/mayorista_cart_service.py (nuevo, Postgres synap)
        │                                        └─ self_checkout.StockService (reuse)
        └── P2 checkout_views                 → services/mayorista_checkout_service.py (nuevo)
                                                 ├─ adapter escritura legacy (comp_ped/stockp/...)
                                                 ├─ numeración (talonarios/codmov, FOR UPDATE)
                                                 └─ price_rules_engine (recálculo en commit)
Legacy MySQL AdministraNET  ──  core.mysql_pool  (lectura P0/P1, escritura SOLO P2)
Postgres synap             ──  modelos carrito (P1) + EcomMigrationCheckpoint
```

**Separación app/legacy (regla del skill):** el carrito vive en Postgres `synap` (borrador, sin tocar legacy). La única escritura a MySQL legacy ocurre en el **commit** del checkout (P2), dentro de `transaction`/BEGIN-COMMIT-ROLLBACK.

---

## 2. Fase P0 — Catálogo de producto (detalle de diseño)

### 2.1 Endpoints (nuevos, en `ecom/urls.py`)

| Método | Ruta | Vista | Descripción |
|--------|------|-------|-------------|
| POST | `/ecom/api/mayoristapp/catalogo/articulos/listado/` | `CatalogoArticulosListadoRelayAPIView` | Listado paginado por filtros con precio calculado |
| GET | `/ecom/api/mayoristapp/catalogo/articulos/<idart>/detalle/` | `CatalogoArticuloDetalleRelayAPIView` | Ficha de producto |

### 2.2 Servicios (extender `ecom/services/catalogo_articulo.py`)

```python
def listar_articulos_paginado(base_empresa, *, filtros, lista_id, codigo_cliente,
                              iva_incluido, pagina=1, tam=20, conn=None) -> dict:
    """Devuelve {items:[...], total, pagina, tam, total_paginas}.
       SQL parametrizado sobre articulo + JOINs (rubro/subrubro/marca/proveedor),
       WHERE activo='Si' + filtros; LIMIT/OFFSET. Para cada item, precio vía
       price_rules_engine.calcular_precio_con_motor. Normaliza con administranet_types."""

def obtener_detalle_articulo(base_empresa, *, idart=None, codigo=None, lista_id,
                             codigo_cliente, iva_incluido, id_deposito, conn=None) -> dict | None:
    """Ficha: identificación, imagen, stock por depósito, precio (neto y c/IVA),
       promociones vigentes (resolver_promocion_articulo), presentación/bulto.
       None si no existe/inactivo."""
```

**Decisiones de diseño P0:**

- **Precio:** delegar 100% en `price_rules_engine` (REQ-CAT-003). El servicio de catálogo arma el dict `art` (campos `Precio1V..Precio5V`, promo, iva, interno) y llama al motor; no recalcula.
- **Stock disponible:** leer de `stock_deposito` (saldo − saldo_pedido_cliente) reutilizando el criterio de `self_checkout.StockService.obtener_disponible_deposito` (unificar la fuente para evitar divergencia).
- **Imagen:** resolver ruta/URL (paridad `foto.php`); no incrustar base64 en el listado (solo en detalle si aplica) para performance.
- **Paginación:** LIMIT/OFFSET con `tam` acotado (p.ej. máx 100). `COUNT(*)` para total.
- **Filtros:** whitelist de columnas; construcción de WHERE con params, nunca interpolación directa.

### 2.3 Tests P0 (`ecom/tests/`)

- `test_catalogo_producto_listado.py`: paginación, filtros, precio == motor (mock/real), sin cliente → 400/default.
- `test_catalogo_producto_detalle.py`: detalle ok, inexistente → 404, promo vigente, stock por depósito.

---

## 3. Fase P1 — Carrito mayorista (esbozo de diseño)

- **Persistencia:** tabla propia `ecom_cart` / `ecom_cart_item` en Postgres `synap` (decisión abierta #1 del proposal; recomendado para no acoplar TPV). Campos por ítem: idart, código, descripción, cantidad, precio_unitario, alícuota_iva, %desc, promo, presentación (comoCuento), lista_precio.
- **Servicio `mayorista_cart_service.py`:** `crear_carrito`, `agregar_item` (valida stock disponible con `StockService`), `actualizar_cantidad`, `quitar_item`, `limpiar`, `_recalcular_totales` (netos/IVA 21/10.5/exento/impuesto interno/percepciones/descuento pie) — paridad `Jcart.update_subtotal`.
- **Precios en carrito:** calculados con `price_rules_engine` al agregar; el **checkout recalcula** para autoridad final.
- **Sin escritura legacy.**

---

## 4. Fase P2 — Checkout / alta de comprobante (diseño detallado, alto riesgo)

> Basado en la exploración field-level de `alta_pedido_confirmado.php` / `alta_presupuesto_confirmado.php` y los patrones de `self_checkout.ConfirmationService` / `talonarios_service`. Alcance P2: **PED** y **PRE** (DEV → P3).

### 4.1 Componentes nuevos

```
ecom/checkout_relay_views.py         → CheckoutConfirmarRelayAPIView (POST)
ecom/services/mayorista_checkout_service.py
    confirmar(cart, *, tipo, id_punto_venta, forma_entrega, cond_venta, ...) -> (ok, error, result)
    ├─ validaciones pre-commit (crédito, autorización, PV, carrito no vacío)
    ├─ recálculo de precios/totales con motor (autoridad)
    ├─ numeración segura (codmov + talonarios, FOR UPDATE)
    ├─ escritura legacy (comp_ped + stockp + percep_cli + cliente_datos_adicionales + stock_deposito)
    └─ marca carrito 'confirmado' (Postgres) + resultado
ecom/services/mayorista_credito.py   → evaluar_autorizacion(base, id_cliente, es_cliente) -> ('Autorizado'|'No Autorizado', dias_exceso)
```

Reutiliza: `core.mysql_pool.get_connection`, `core.utils.administranet_types`, `ecom.services.price_rules_engine`, `self_checkout.services.talonarios_service` (patrón de numeración con `FOR UPDATE`).

### 4.2 Firma del servicio

```python
@dataclass
class CheckoutInput:
    tipo: str               # 'PED' | 'PRE'
    id_punto_venta: int
    forma_entrega: str = ''
    cond_venta: Optional[str] = None
    id_condventa: Optional[int] = None
    observaciones: str = ''
    id_cliente_domicilio: Optional[int] = None
    id_ruta: Optional[int] = None
    es_cliente: bool = False   # True si el alta la hace el propio cliente (autogestión)

def confirmar(cart: EcomCart, datos: CheckoutInput, *, id_usuario: int, cod_viajante: Optional[int]) \
        -> Tuple[bool, Optional[str], Optional[dict]]:
    """result = {codigo_movimiento, nro_comprobante, nro_comp_busq, tipo, id_pv,
                 autorizacion, total, subtotal_neto, iva_total, ...}"""
```

### 4.3 Secuencia transaccional (una sola transacción MySQL)

```python
with get_connection(base_empresa) as conn:
    try:
        conn.autocommit(False)
        cur = conn.cursor()

        # 0) Idempotencia (Postgres): si cart.estado == 'confirmado' → devolver resultado previo (sin escribir)
        # 1) Validar carrito no vacío + PV válido para el tipo
        # 2) Recalcular precios/totales con el motor (autoridad) sobre los ítems del carrito
        # 3) Autorización = evaluar_autorizacion(...)  (no bloquea; setea estado)
        # 4) CodigoMovimiento:  SELECT CodigoMovimiento FROM codmov WHERE codigo=1 FOR UPDATE
        #                       UPDATE codmov SET CodigoMovimiento = %s WHERE codigo=1
        # 5) Numeración: SELECT Nro,PV FROM talonarios WHERE id_punto_venta=%s AND TipoComprobante=%s FOR UPDATE
        #                nro_comp = f"{PV:04d}-{Nro:08d}";  UPDATE talonarios SET Nro=Nro+1 WHERE ...
        # 6) FechaEntrega (solo PED): suma dias_entrega evitando no laborables
        # 7) INSERT cliente_datos_adicionales(...)
        # 8) INSERT percep_cli(...) por cada percepción
        # 9) INSERT comp_ped(...)  (cabecera con totales recalculados)
        # 10) por cada ítem:
        #       (PED) UPDATE stock_deposito SET saldo_pedido_cliente = saldo_pedido_cliente + %s
        #             WHERE id_articulo=%s AND id_deposito=%s
        #             AND (COALESCE(saldo,0) - COALESCE(saldo_pedido_cliente,0)) >= %s   -- valida disponible
        #             → si rowcount==0: ROLLBACK "Stock insuficiente: <art>"
        #       INSERT stockp(...)
        # 11) conn.commit()
        # 12) (Postgres) cart.estado='confirmado'; cart.codigo_movimiento=..., cart.nro_comprobante=...
        return True, None, result
    except Exception:
        conn.rollback()
        return False, "No se pudo confirmar el comprobante.", None
    finally:
        conn.autocommit(True)
```

**Diferencias respecto al PHP (mejoras):**
- `talonarios` con **`FOR UPDATE`** (el PHP no bloquea → corrige duplicados bajo concurrencia).
- `stock_deposito` con **`UPDATE ... AND disponible >= cantidad`** (el PHP no valida en commit).
- **Idempotencia** por estado del carrito Postgres (el PHP no controla doble submit).
- Sin los DELETE defensivos extra-transaccionales del PHP: la transacción atómica los hace innecesarios.

### 4.4 Mapeo de campos (columnas reales del schema)

**`comp_ped` (cabecera):** `Fecha`(hoy), `TipoComprobante`(PED/PRE), `NroComprobante`, `NroCompBusq`, `Codigo`(cliente), `CodigoMovimiento`, `id_pv`, `CodSucursal`, `IdUsuario`, `CodViajante`, `TipoPedido`('Ecom vendedor'), `Detalle`, `ImporteVenta`(subtotal s/IVA), `IVA1`/`IVA2`(21/10,5), `Alicuota1`='21'/`Alicuota2`='10.5', `Exento`, `SubTotal1`/`SubTotal2`(netos grav.), `SubTotalGral`, `PorDesc1`/`PorDesc2`, `ImpDesc1`/`ImpDesc2`, `SubTotalDesc1`/`SubTotalDesc2`, `SubtotalDesc`, `impuesto_interno_total`, `total_percep`, `autorizacion_sistema`, `Estado`='Pendiente', `Vencimiento`, `FechaEntrega`(PED), `FormaEntrega`, `id_deposito_despacho`, `CotiDolar`, `geo_latitud`/`geo_longitud`, `Anulado`='No'.

**`stockp` (renglón):** `IDArt`, `CodigoArticulo`, `Descripcion`, `id_manual`, `CodigoMovimiento`, `Fecha`, `Salida`=`Cantidad`(cant. en unidad mínima), `Alicuota`, `imp_alicuota_iva`(%), `AlicuotaIB`, `imp_alicuota_iibb`, `PrecioVentaxU`/`PrecioNetoxU`/`PrecioIVAxU`/`PrecioBrutoxU`/`PrecioCostoxU`, `PrecioVentaxR`/`PrecioNetoxR`/`PrecioIVAxR`/`PrecioBrutoxR`/`PrecioCostoxR`, `PorDesc`/`ImpDesc`, `impuesto_interno`/`impuesto_interno_subtotal`, `promocion`/`promocion_por`/`promocion_tipo`/`promocion_cant`, `TipoIVA`, `CodigoCP`(cliente), `Tipo`='Cliente', `TipoComp`('Pedido'/'Presupuesto'), `Comprobante`(PED/PRE), `NroComprobante`, `CodDeposito`, `CodSucursal`, `idusuario`, `CodViajante`, `CodLaboratorio`, `lista_precio`, `tipo_art`, `Orden`, `cantidad_entregada`/`cantidad_pendiente`, `tipo_unidad`, `cantidad_unidad_display`, `cantidad_dividir`, `Anulado`='No', `coti_dolar`.

**`cliente_datos_adicionales`:** `fechaEntrega`, `id_deposito_despacho`, `Fentrega`, `origen_pedido`='Web', `TipoComprobante`, `id_cliente`, `CodigoMovimiento`, `id_cliente_domicilio`, `id_ruta`.

**`percep_cli`:** `id_percep_cli_tipo`, `alicuota_percep_cli`, `importe_percep_cli`, `codigo_movimiento`, `id_cliente`, `tipo_comp` (**fix**: usar el tipo real, PRE en presupuesto; el PHP tenía el bug de dejar 'PED').

### 4.5 Numeración — SQL

```sql
-- CodigoMovimiento (con lock)
SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE;
UPDATE codmov SET CodigoMovimiento = %(nuevo)s WHERE codigo = 1;

-- Talonario por PV + tipo (con lock; corrige el PHP)
SELECT Nro, PV FROM talonarios
 WHERE id_punto_venta = %(pv)s AND TipoComprobante = %(tipo)s
 LIMIT 1 FOR UPDATE;
UPDATE talonarios SET Nro = Nro + 1
 WHERE id_punto_venta = %(pv)s AND TipoComprobante = %(tipo)s;
```

> Alternativa a `FOR UPDATE` en `codmov`: lock optimista con reintento acotado (paridad PHP): `UPDATE codmov SET CodigoMovimiento=%(new)s WHERE codigo=1 AND CodigoMovimiento=%(old)s` y reintentar si `rowcount==0`. Elegimos `FOR UPDATE` por simplicidad y por alineación con `ConfirmationService`.

### 4.6 Autorización / crédito (`mayorista_credito.py`)

```sql
SELECT MIN(Fecha) AS ultimaf FROM cuentacliente
 WHERE TipoComprobante IN ('FA','FB','FC','FE','FM','NDA','NDB','NDC','NDE','NDM')
   AND Estado = 'N/Canc' AND Anulado = 'No' AND Codigo = %(cliente)s;
```
- `dias_atraso = (hoy − ultimaf).days` (si `ultimaf`).
- `exceso = credito_limite_dias > 0 AND dias_atraso > credito_limite_dias`.
- `autorizacion = 'No Autorizado' if es_cliente or exceso else 'Autorizado'`.
- **No bloquea** el alta; sólo setea `comp_ped.autorizacion_sistema`.

### 4.7 Precio como autoridad (REQ-CHK-006)

En el commit se recalcula cada renglón con `resolver_precio_articulo`/`price_rules_engine` (misma fuente que P0/P1) y se derivan todos los totales de `comp_ped`/`stockp` desde ese recálculo (reusar la lógica de `mayorista_cart_service.recalcular_totales` sobre datos frescos). El carrito P1 es sólo un borrador.

### 4.8 Selección de punto de venta (REQ-CHK-007)

`id_punto_venta` desde sesión mayorista (`id_punto_venta_activo`; fiscal/no fiscal vía `punto_venta_activo_cont`). Si no hay PV válido para el `TipoComprobante` en `talonarios` → error sin escritura.

### 4.9 Endpoint

| Método | Ruta | Vista | Body |
|--------|------|-------|------|
| POST | `/ecom/api/mayoristapp/checkout/confirmar/` | `CheckoutConfirmarRelayAPIView` | `{tipo, id_punto_venta?, forma_entrega, cond_venta?, id_cliente_domicilio?, id_ruta?, observaciones?}` |

Respuesta 201: `{codigo_movimiento, nro_comprobante, tipo, autorizacion, total}`. 409 si stock insuficiente; 400 validación; 500 genérico.

### 4.10 Tests P2 (`ecom/tests/`)

- Alta PED ok (mocks de conexión/cursor): verifica INSERT comp_ped + N stockp + UPDATE stock_deposito con mismo CodigoMovimiento y número formateado.
- Alta PRE ok: no toca stock_deposito; `TipoComprobante='PRE'`.
- **Stock insuficiente en commit** (UPDATE condicional rowcount=0) → ROLLBACK, sin comprobante.
- **Concurrencia numeración**: dos llamadas → `FOR UPDATE` serializa; números distintos (simulado con mock que verifica el SQL `FOR UPDATE` y el incremento).
- **Idempotencia**: cart ya `confirmado` → devuelve mismo CodigoMovimiento, no reinserta.
- **Autorización**: cliente con exceso → 'No Autorizado'; al día → 'Autorizado'; alta por cliente → 'No Autorizado'.
- **Rollback**: fallo en un stockp → ninguna fila persistida (verifica rollback llamado).

### 4.11 Migración de esquema legacy (si aplica)

Para robustecer idempotencia/consistencia se evaluará un índice único en `comp_ped.CodigoMovimiento` (hoy no hay). De agregarse, **debe** implementarse en `core/services/legacy_mysql_schema/catalog.py` (regla del repo), nunca como SQL suelto. Riesgo: datos legacy con duplicados → primero auditar antes de crear el índice; si no es viable, la idempotencia se garantiza sólo por estado del carrito Postgres.

---

## 5. Fase P3 — Extras (esbozo)

- Alta de **devolución** (DEV, reverso de stock).
- **Export lista de precios PDF** (seguir `docs/general/RUNBOOK_EXPORTACION_PDF.md`, `reportlab`, umbrales `LP_PDF_MAX_*`, background).
- **Restricciones de catálogo por PV** (ex-AMICO): config en BD (no hardcode), aplicada como filtro en listado/detalle P0.
- **UI web** completa (catálogo grilla, ficha, carrito, checkout) con patrones canónicos.

---

## 5.bis Fase P4 — Percepciones IIBB (configurable por implementación)

### Origen legacy

- **Cálculo:** `administraNET-ecom/mayoristapp/jcart/jcart.php` líneas 1093–1171 (método `update`/subtotal). Solo si `$_SESSION['agente_percep'] == 'Si'`.
- **INSERT:** `alta_pedido_confirmado.php` 407–421 y `alta_presupuesto_confirmado.php` 222–236 (ambos insertan en `percep_cli`; `comp_ped.total_percep` en 497 / 308).
- **Toggle:** `sucursales.agente_percep` (cargado en sesión por `control.php:716`). Es el flag **configurable por implementación/sucursal** que pide el negocio.

### Fórmula (paridad)

```
si sucursales.agente_percep != 'Si':  total_percep = 0, sin filas percep_cli
si 'Si':
    base = subtotal_neto del carrito  # neto gravado con descuento renglón+pie (= jcart totalNetoPer)
    tipos = SELECT id_percep_cli_tipo FROM percep_cli_param WHERE id_cliente = ?
    si tipos vacío:  ABORTAR (ROLLBACK) con mensaje español  # paridad legacy (no genera comprobante incompleto)
    por cada tipo:
        alic = percep_cli_tipo.alicuota_percep_cli_tipo
        importe = round2(base * alic / 100)   # NO se aplica importe_minimo (paridad jcart)
        INSERT percep_cli (id_percep_cli_tipo, alicuota_percep_cli, importe_percep_cli,
                           codigo_movimiento, id_cliente, tipo_comp)
    total_percep = Σ importes
```

### Componentes Synap

- **Servicio** `ecom/services/mayorista_percepciones.py`:
  - `calcular_percepciones(cur, id_cliente, base, agente_percep) -> (detalle: list[dict], total: Decimal)`; usa el cursor de la transacción abierta (no abre conexión propia) para lecturas `percep_cli_param`/`percep_cli_tipo`.
  - Lanza `PercepcionesSinConfig` cuando `agente_percep and not tipos` → el checkout traduce a `(False, mensaje, None)` con ROLLBACK.
- **Resolución del flag `agente_percep`** (paridad `control.php`: proviene de la **sucursal del usuario/vendedor**, no del cliente):
  - `CheckoutInput.agente_percep` (override desde sesión, `$_SESSION['agente_percep']` legacy) si la vista lo provee.
  - Si es `None`, `_fetch_agente_percep(cur, id_usuario)` lo lee con `usuarios LEFT JOIN sucursales ON sucursales.id_sucursal = usuarios.id_sucursal` dentro de la transacción.
- **Checkout** (`confirmar`): tras insertar `comp_ped`, para PED/PRE calcula percepciones sobre `cart.subtotal_neto`, inserta filas `percep_cli` con el `cod_mov`/`nro_comp` de la transacción y setea `total_percep` en el `comp_ped` (se computa **antes** del INSERT de `comp_ped` para poder pasar `total_percep`). DEV: `total_percep = 0`.

### Tablas (schema real)

- `percep_cli` (INSERT): `id_percep_cli_tipo` INT, `alicuota_percep_cli` DECIMAL, `importe_percep_cli` DECIMAL, `codigo_movimiento` DOUBLE, `id_cliente` DOUBLE, `tipo_comp` VARCHAR. `id_percep_cli` (PK) autonumérico; `anulado` default legacy.
- `percep_cli_param` (SELECT): `id_percep_cli_tipo`, `id_cliente`.
- `percep_cli_tipo` (SELECT): `id_percep_cli_tipo`, `alicuota_percep_cli_tipo`, `nombre_percep_cli_tipo`, `cod_afip`, `importe_minimo` (no usado).

### Decisiones P4

- **Configurabilidad:** se reusa `sucursales.agente_percep` (no se crea modelo Postgres) porque ya es la config por implementación y mantiene paridad exacta con VB6/PHP.
- **Cliente agente sin `percep_cli_param`:** se **bloquea** (paridad legacy). Alternativa tolerante (percep=0) documentada como opción futura si el negocio lo pide.
- **`tipo_comp`:** se persiste el tipo real (PED/PRE) en `percep_cli.tipo_comp` (el legacy hardcodea 'PED' incluso en presupuesto; se corrige por consistencia).
- **DEV:** fuera de alcance P4.

---

## 6. Cumplimiento de reglas del repo

- **UI canónica:** `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` (reports/MPR), NO objetivos/presupuestos.
- **Tipos AdministraNET:** `core.utils.administranet_types` en toda lectura/escritura MySQL.
- **Migraciones esquema legacy:** si P2 requiere índice/constraint (p.ej. único en `comp_ped.CodigoMovimiento`), vía `core/services/legacy_mysql_schema/catalog.py`.
- **Tests en contenedor:** `docker exec Synap_app python manage.py test ecom`.
- **Docs:** actualizar `docs/ecom/` + DELTA al cerrar cada fase.
- **Idioma:** todo en español; fechas dd/MM/yyyy en UI/mensajes.
