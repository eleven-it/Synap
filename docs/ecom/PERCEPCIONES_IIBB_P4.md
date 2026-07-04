# Percepciones IIBB — Checkout mayorista — Fase P4

Change SDD: `openspec/changes/catalogo-carrito-checkout-mayorista/` · Fase **P4** · Requisito **REQ-CHK-009**.

Cálculo e inserción de **percepciones de Ingresos Brutos (IIBB)** al confirmar un
comprobante mayorista (PED/PRE), como **opción configurable por implementación**.

## Configurable por implementación

El cálculo se activa cuando la **sucursal es agente de percepción**:
`sucursales.agente_percep = 'Si'` (MySQL AdministraNET, gestionable desde la config de
sucursal en Synap — `core/services/administranet_sucursales.py`). Es el mismo flag que el
legacy carga en sesión (`control.php`).

- **`agente_percep = 'No'`** → `comp_ped.total_percep = 0`, sin filas `percep_cli`.
- **`agente_percep = 'Si'`** → se calcula e inserta (ver abajo).

**Resolución del flag** (paridad legacy: proviene de la sucursal del **usuario/vendedor**):
1. `CheckoutInput.agente_percep` si la vista lo pasa (override desde sesión, `_session_agente_percep`).
2. Si es `None`, `_fetch_agente_percep(cur, id_usuario)` lo lee de `usuarios → sucursales`
   dentro de la transacción.

## Cálculo (paridad `jcart.php` 1093–1171)

```
base = subtotal_neto del carrito        # neto gravado con descuento (renglón + pie)
tipos = SELECT id_percep_cli_tipo FROM percep_cli_param WHERE id_cliente = ?
por cada tipo:
    alic    = percep_cli_tipo.alicuota_percep_cli_tipo
    importe = round2(base * alic / 100)  # NO se aplica importe_minimo (paridad jcart)
total_percep = Σ importes
```

- Se inserta **una fila por tipo** en `percep_cli` (`id_percep_cli_tipo`, `alicuota_percep_cli`,
  `importe_percep_cli`, `codigo_movimiento`, `id_cliente`, `tipo_comp`) **dentro de la misma
  transacción** del alta (`autocommit off` + `COMMIT`/`ROLLBACK`).
- `comp_ped.total_percep` recibe el total.
- `tipo_comp` guarda el tipo real (PED/PRE); el legacy hardcodea 'PED' incluso en presupuesto
  y aquí se corrige por consistencia.

## Regla de bloqueo (paridad legacy)

Si `agente_percep = 'Si'` pero el cliente **no** tiene filas en `percep_cli_param`, la
confirmación **falla con `ROLLBACK`** y mensaje en español (no se genera un comprobante
fiscalmente incompleto). `mayorista_percepciones.PercepcionesSinConfig`.

> Alternativa tolerante (percep = 0 en ese caso) documentada como opción futura si el negocio
> lo requiere; hoy se prioriza paridad fiscal con AdministraNET.

## Alcance

- **PED** y **PRE**: calculan percepciones.
- **DEV** (devolución): fuera de alcance (`total_percep = 0`).

## Componentes

| Componente | Archivo |
|---|---|
| Servicio de cálculo | `ecom/services/mayorista_percepciones.py` |
| Integración transaccional + INSERT | `ecom/services/mayorista_checkout_service.py` (`_SQL_INSERT_PERCEP_CLI`, `_fetch_agente_percep`) |
| Override de sesión | `ecom/checkout_relay_views.py` (`_session_agente_percep`) |
| Checkpoint | migración `ecom/0025_checkpoint_mayoristapp_percepciones_iibb.py` |

## Tablas legacy

- `percep_cli` (INSERT): `id_percep_cli_tipo`, `alicuota_percep_cli`, `importe_percep_cli`,
  `codigo_movimiento`, `id_cliente`, `tipo_comp`, `anulado='No'`.
- `percep_cli_param` (SELECT): tipos de percepción por cliente.
- `percep_cli_tipo` (SELECT): `alicuota_percep_cli_tipo`, `nombre_percep_cli_tipo`, `cod_afip`.
- `sucursales.agente_percep`: toggle por sucursal.

## Tests

`ecom/tests/test_mayorista_checkout_service.py > TestCheckoutPercepcionesIIBB` (5 casos):
sucursal no agente (percep 0), sucursal agente calcula e inserta, override por sesión,
agente sin config de cliente (bloquea + rollback), y DEV no calcula.

```bash
docker exec Synap_app python manage.py test ecom.tests.test_mayorista_checkout_service --keepdb
```
