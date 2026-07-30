# Informe DABRA consolidado remitos

**Slug:** `dabra-consolidado-remitos`  
**Permiso:** `reports.dabra_consolidado_remitos`  
**Cliente fijo:** `Codigo=368` (DABRA)

## Resumen

Informe mensual que exporta líneas de factura FA del cliente DABRA con referencia de remito, preview en dashboard Synap y validación de totales Σ vs cabecera.

## Endpoints

| Acción | Método | Ruta |
|--------|--------|------|
| Preview JSON | GET | `/api/reports/dabra-consolidado-remitos/relay/?mes=&anio=` |
| Export Excel | GET | `/api/reports/dabra-consolidado-remitos/relay/export/?mes=&anio=` |

Dashboard: `/reports/dashboard/dabra-consolidado-remitos/`

## Mapeo columnas REPORTE (A–AW)

| Col | Header sample | Origen legacy |
|-----|---------------|---------------|
| A | NroCUIT | `datosempresa.CUIT` (11 dígitos) |
| B | Fecha | `cuentacliente.Fecha` (FA) |
| C | DocType | Constante `1` |
| D | PuntoVenta | Parse `NroComprobante` → PV zero-pad **5** |
| E | NumeroLegal | Parse `NroComprobante` → máscara **00000000** (texto) |
| F | Item | `articulo.CodArtProv` (primeros 9 chars + regla espacio) |
| G | Talle | Resto de `CodArtProv` |
| H | Cantidad | `stock.Cantidad` |
| I | Precio | `stock.PrecioVentaxU` (predescuento de cabecera) |
| J | Bonificacion | `pordesc_bonif` si ≠0, si no `PorDesc` de línea; si ambos 0 → % pie `(SubTotal1−SubtotalDesc)/SubTotal1×100` (`PorDesc1`/`ImpDesc1`) |
| K | ImporteBonificacion | `PrecioVentaxU × bonif% / 100` |
| L | Importe | `Cantidad × PrecioNetoxU × (SubtotalDesc/SubTotal1)` (neto post pie) |
| M | Iva | `Cantidad × PrecioIVAxU × (SubtotalDesc/SubTotal1)` |
| N | TotalGravado | `cuentacliente.SubtotalDesc` (neto post descuento al pie; no `SubTotal1`) |
| O–P | (vacías) | — |
| Q | Total | `cuentacliente.ImporteVenta` (cabecera FA) |
| R | CompRef | PV de `comp_ped.NroComprobante` (REM vía `rem_fact`) zero-pad **5** |
| S | NumeroRef | Nº legal remito con máscara **00000000** (texto) |
| T/W | Entrega / Suc | `cliente_domicilio.NroCalle` del REM |
| U–V | NroCAE / VtoCAE | `fe_cae` (int en Excel si numérico) / `fe_vto_cae` |
| X | Categoria | `articulo_categoria.nombre_articulo_categoria` o `ACCESORIOS` |
| Y–AW | P901…PIVA3 | `0` |

**Preview only:** `NombreArticulo` (`COALESCE(articulo.NombreArticulo, stock.Descripcion)`) — no se exporta a Excel. Join artículo por `stock.IDArt`.

## TOTAL FACTURAS

Una fila por FA: `Comprobante` = letra + PV(4) + legal(8); `Nro. Remito` = primer remito (`R` + PV4 + legal8); `Imp Neto` = `SubtotalDesc` (post pie); `Imp Bruto` = `ImporteVenta`.

## Exclusión por NC/ND

No se incluyen FA con nota de crédito o débito **no anulada** vinculada por `cuentacliente.NroFacturaMov` = `CodigoMovimiento` de la FA (tipos NCA–NCM / NDA–NDM). El preview muestra una sola alarma resumen con la cantidad excluida (`meta.fa_excluidas_nc_nd`).

## Vínculo FA ↔ remito

Misma lógica que Trazabilidad VB6 (`trz_trazabilidad.frm`):

1. `rem_fact.CodigoMovimientoF` = `cuentacliente.CodigoMovimiento` (FA)
2. `rem_fact.CodigoMovimientoR` = `comp_ped.CodigoMovimiento` (REM)
3. CompRef/NumeroRef se parsean de `comp_ped.NroComprobante` del remito

**Importante:** el remito de venta se guarda en `comp_ped`, no en `cuentacliente`. El nº `0008-00000001` puede existir a la vez como REM y como FA (tipos distintos, `CodigoMovimiento` distintos); el match no es por texto de número.

## Alarmas (no bloquean export)

- FA sin CAE → fila incluida, CAE vacío
- FA sin remitos en `rem_fact` → CompRef/NumeroRef vacíos
- FA con >1 remito → alarma; TOTAL usa primer remito
- Sin `NroCalle` en remito/FA

En el dashboard **no** se lista cada alarma (puede ser muy extensa): solo el banner de resumen y las filas afectadas se marcan en **ámbar** (REPORTE sin CompRef/NumeroRef; TOTAL FACTURAS sin Nro. Remito).

## Errores (bloquean export — HTTP 409)

Validación Σ por FA **antes** de expansión multi-remito:

- Σ `Cantidad×PrecioNetoxU` vs `SubTotal1` (ambos **predescuento** de cabecera)
- Σ `Cantidad×(PrecioNetoxU+PrecioIVAxU) × (SubtotalDesc/SubTotal1)` vs `ImporteVenta`
  - Las líneas de `stock` conservan precios predescuento; `ImporteVenta` ya aplica el descuento de cabecera (`PorDesc1`/`ImpDesc1`, etc.) y el IVA recalculado sobre la base descontada
  - Si no hay descuento, `SubtotalDesc = SubTotal1` y el factor es 1
- Tolerancia: `max(0.05, 0.01 × n_lineas)`

## Archivo export

`DABRA MMYYYY.xlsx` — hojas `REPORTE` y `TOTAL FACTURAS`.

## Override dev / LAN

No se modifica `.env`. Para probar contra BEST SOX: sesión con `base_empresa` apuntando a la base LAN (ej. Mes=7, Año=2026, FA 24/07/2026 PV 0008).

## Nota CAE v1

El cierre de producto incluye FA con CAE vacío + alarma (no excluye). REQ-DABRA-003 escenario “excluir sin CAE” queda superseded por este comportamiento.

## Tests

```bash
docker exec Synap_app python manage.py test reports.tests.test_dabra_consolidado_remitos
```
