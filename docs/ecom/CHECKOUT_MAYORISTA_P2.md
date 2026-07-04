# Checkout mayorista — Fase P2 (alta de comprobante legacy)

Change SDD: `openspec/changes/catalogo-carrito-checkout-mayorista/` · Fase **P2**.
Migra la confirmación del carrito de `administraNET-ecom/mayoristapp` (PHP
`alta_pedido_confirmado.php` / `alta_presupuesto_confirmado.php`) a Synap.

## Alcance

- Alta de **Pedido (`PED`)**, **Presupuesto (`PRE`)** y **Devolución (`DEV`, Fase P3)**
  desde un carrito borrador (P1).
- Escritura transaccional en MySQL AdministraNET (bases compartidas con VB6).
- Numeración segura, validación de stock, autorización por crédito e idempotencia.

**Fuera de alcance (siguientes fases / gaps documentados):**

- Factura electrónica / CAE AFIP: el comprobante nace `Estado='Pendiente'`.
- Medios de pago / caja / TPV.
- **Percepciones IIBB:** ✅ **implementado en Fase P4** (configurable por implementación vía
  `sucursales.agente_percep`). Ver `docs/ecom/PERCEPCIONES_IIBB_P4.md` y REQ-CHK-009.
- Devolución (`DEV`) → Fase P3.
- `CotiDolar`, `ImpDesc1/2` desagregado por alícuota: el descuento al pie ya se
  refleja dentro de los netos recalculados; se registra `PorDesc1/2` y `SubtotalDesc`.

## Arquitectura

| Componente | Rol |
|---|---|
| `ecom/services/mayorista_checkout_service.py` | Orquestación transaccional `confirmar()` |
| `ecom/services/mayorista_credito.py` | `evaluar_autorizacion()` por límite de crédito |
| `ecom/checkout_relay_views.py` | Vista API `CheckoutConfirmarRelayAPIView` |
| `ecom/models.py` (`EcomCart`) | Campos de resultado: `codigo_movimiento`, `nro_comprobante`, `autorizacion`, `confirmed_at` |

### Secuencia transaccional

1. Idempotencia: si el carrito ya está `confirmado` con `codigo_movimiento`, se
   devuelve el resultado previo sin reescribir.
2. Lectura de cliente (`id_sucursal`, `id_cv`/`condVenta`, `credito_limite_dias`,
   `descuento_por_cli`).
3. **Recalculo de precios** de cada renglón con el motor único
   (`resolver_precio_articulo`) + `recalcular_totales` → el carrito no es autoridad
   de precio en el commit.
4. `get_connection(base)` → `autocommit(False)` y:
   - `evaluar_autorizacion` (consulta `cuentacliente` + `credito_limite_dias`).
   - `SELECT CodigoMovimiento FROM codmov WHERE codigo=1 FOR UPDATE` → `+1` → `UPDATE`.
   - `SELECT Nro, PV FROM talonarios ... FOR UPDATE` → `NroComprobante` (`PV-Nro`) → `UPDATE Nro+1`.
   - `INSERT cliente_datos_adicionales`, `INSERT comp_ped` (cabecera con totales).
   - Por renglón: en **PED** `UPDATE stock_deposito` condicional
     (`disponible >= cantidad`); si `rowcount==0` → **rollback** (stock insuficiente).
     `INSERT stockp`.
   - `COMMIT`. Ante cualquier excepción → `ROLLBACK`.
5. Persistencia del resultado en el carrito (Postgres) para idempotencia.

### Mejoras sobre el PHP legacy

- **Concurrencia:** `FOR UPDATE` en `codmov` y `talonarios` evita numeración
  duplicada (el PHP numera sin lock).
- **Stock:** validación atómica en el `UPDATE` condicional (no lee-y-luego-escribe).
- **Precio:** autoridad del motor en el commit.
- **Idempotencia:** por estado del carrito (reintento no duplica comprobante).

## Autorización por crédito (`mayorista_credito.py`)

- Atraso = días desde el comprobante impago más antiguo del cliente
  (`cuentacliente`, tipos de deuda `FA/FB/FC/FE/FM/ND*`, `Estado='N/Canc'`, `Anulado='No'`).
- `credito_limite_dias > 0` y atraso mayor → `comp_ped.autorizacion_sistema = 'No Autorizado'`.
- Alta por el propio cliente (`es_cliente=True`) → siempre `'No Autorizado'`.
- **No bloquea** el alta: solo etiqueta el comprobante.

## API

`POST /ecom/api/mayoristapp/checkout/confirmar/`

Body (todos opcionales; toma contexto de sesión mayoristapp):

```json
{
  "tipo": "PED",
  "id_punto_venta": 3,
  "forma_entrega": "Retira",
  "id_cliente_domicilio": 12,
  "id_ruta": 4,
  "observaciones": "…",
  "es_cliente": false
}
```

Respuestas: `201` `{codigo_movimiento, nro_comprobante, tipo, autorizacion, total, subtotal_neto}`,
`409` stock insuficiente, `400` validación (carrito vacío, sin PV, cliente inexistente),
`500` error interno.

## Devolución (DEV) — Fase P3

La devolución reutiliza el **mismo servicio y endpoint** (`confirmar` con `tipo='DEV'`),
por su estructura idéntica al pedido (se arma desde el carrito). Diferencias:

| Aspecto | PED | DEV |
|---|---|---|
| `stockp.TipoComp` / `comp_ped.TipoComprobante` | `Pedido` / `PED` | `Devolucion` / `DEV` |
| `stock_deposito.saldo_pedido_cliente` | `+= cantidad` con validación de disponible | `+= cantidad` **sin** validación (paridad legacy) |
| Numeración | talonario `PED` | talonario `DEV` |

**Bug legacy corregido:** `alta_devolucion_confirmado.php` numeraba el talonario con
`TipoComprobante='PED'` al dar de alta un `DEV` (línea 966). En Synap se numera el
talonario correcto (`DEV`) dentro de la transacción con `FOR UPDATE`.

Uso: `POST /ecom/api/mayoristapp/checkout/confirmar/` con `{"tipo": "DEV", ...}`.
Checkpoint `mayoristapp_devolucion` (`ecom/0020`).

## Tests

`ecom/tests/test_mayorista_checkout_service.py` (13 casos, `FakeConn`/`FakeCursor`,
sin MySQL real): alta PED/PRE/DEV ok, `stock_deposito` solo en PED/DEV con `FOR UPDATE`,
DEV incrementa saldo sin validar disponible, stock insuficiente → rollback, rollback ante
fallo de renglón, carrito vacío, sin punto de venta, idempotencia, y autorización
(al día / con exceso / alta por cliente).

Ejecutar:

```bash
docker exec Synap_app python manage.py test ecom.tests.test_mayorista_checkout_service --keepdb
```
