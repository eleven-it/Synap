# Checkout mayorista — Fase P2 (alta de comprobante legacy)

Change SDD: `openspec/changes/catalogo-carrito-checkout-mayorista/` · Fase **P2**.  
**Cabecera comercial (fechas, condición, lista):** ver `docs/ecom/PEDIDO_CABECERA_COMERCIAL.md` (change `ecom-pedido-cabecera-comercial`).
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
- `ImpDesc1/2` desagregado por alícuota: el descuento al pie ya se
  refleja dentro de los netos recalculados; se registra `PorDesc1/2` y `SubtotalDesc`.

## Paridad AdministraNET — campos corregidos (PED/PRE/DEV)

Correcciones en `mayorista_checkout_service.py` para alinear el alta con `Pedido.frm` /
`Visualiza_Pedido.frm` y evitar grids vacíos en VB6.

### Causa raíz Visualiza_Pedido

`Visualiza_Pedido` arma el grid de renglones con `cuerpostockpe.Alicuota = IVA.id` (JOIN a
tabla `iva`). Si Synap persistía el **porcentaje** (ej. 21) en `stockp.Alicuota` en lugar del
**id** (ej. 1), el JOIN no encontraba filas y el grid quedaba vacío.

### Renglones (`stockp`)

| Campo | Valor correcto (legacy) | Notas |
|---|---|---|
| `Alicuota` | `articulo.Alicuota` (id en tabla `iva`) | El % va en `imp_alicuota_iva` |
| `imp_alicuota_iva` | % IVA (`Obtener_Alicuota_IVA` → `iva.alicuota`) | Cálculos usan `it.alicuota_iva` |
| `AlicuotaIB` | `articulo.AlicuotaIB` (id en `activ_iibb`) | No es el porcentaje |
| `imp_alicuota_iibb` | % IIBB (`Obtener_Alicuota_IIBB` → `activ_iibb.alicuota`) | JOIN en `_fetch_articulo_extras` |
| `saldo` | `stock_deposito.saldo_pedido_cliente` **tras** el UPDATE de reserva | `SELECT` en la misma transacción; 0 en PRE o sin fila |
| `coti_dolar` / `id_cotizacion` | Cotización vigente (`cotizacion.ValorPesos` / `id_cotizacion`) | Una lectura por transacción |
| `cantidad_pendiente_opt` / `cantidad_fab_pendiente_opt` | `Cantidad` del renglón | Paridad `Pedido.frm` |
| `promocion_tipo` / `promocion_cant` | Vacío y 0 si `promocion='No'` | No dejar `'Importe descuento'` residual |

### Cabecera (`comp_ped`)

| Campo | Valor correcto (legacy) | Notas |
|---|---|---|
| `ImporteVenta` | Total con IVA (+ imp. interno + percepciones) | `cart.total + total_percep` |
| `SubtotalDesc` | Neto gravado post-descuento al pie | `cart.subtotal_neto` (no el total bruto) |
| `CotiDolar` | `cotizacion.ValorPesos` | Misma lectura que renglones |
| `ImporteVentaL` | Importe en letras | `ecom/services/numero_a_letras.py` |
| `cod_mov_ped_orginal` / `Nro_Comp_PED_orginal` | Autorreferencia al propio PED | Solo `tipo='PED'` |
| `fecha_control` | `%d/%m/%Y %H:%M:%S` | Paridad `Actualiza_Fecha_Hora_MySQL('Fecha-Hora')` |

### Backfill de PED ya confirmados (antes del fix)

Los pedidos ecom/masivos grabados con `stockp.Alicuota = 21` (porcentaje) no se ven en
`Visualiza_Pedido` hasta corregir datos. Comando:

```bash
docker exec Synap_app python manage.py backfill_paridad_ped_ecom \
  --base administranet1 \
  --detalle-like 'Pedido masivo Synap%' \
  --dry-run

docker exec Synap_app python manage.py backfill_paridad_ped_ecom \
  --base administranet1 \
  --detalle-like 'Pedido masivo Synap%'
```

Opciones: `--codigos 1132,1133` para acotar. Actualiza `stockp` (alícuotas id/IIBB, saldo,
cotización, OPT) y `comp_ped` (ImporteVenta/SubtotalDesc invertidos, CotiDolar,
ImporteVentaL, autorreferencia).

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

`ecom/tests/test_mayorista_checkout_service.py` (14+ casos, `FakeConn`/`FakeCursor`,
sin MySQL real): alta PED/PRE/DEV ok, paridad `comp_ped`/`stockp` (alícuotas id/%, saldo,
cotización, ImporteVenta/SubtotalDesc, autorreferencia PED), `stock_deposito` solo en
PED/DEV con `FOR UPDATE`, DEV incrementa saldo sin validar disponible, stock insuficiente
→ rollback, rollback ante fallo de renglón, carrito vacío, sin punto de venta,
idempotencia, y autorización (al día / con exceso / alta por cliente).

Ejecutar:

```bash
docker exec Synap_app python manage.py test ecom.tests.test_mayorista_checkout_service --keepdb
```
