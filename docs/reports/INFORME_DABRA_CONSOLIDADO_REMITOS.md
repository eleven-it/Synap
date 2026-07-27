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
| E | NumeroLegal | Parse `NroComprobante` → número legal (int) |
| F | Item | `articulo.CodArtProv` (primeros 9 chars + regla espacio) |
| G | Talle | Resto de `CodArtProv` |
| H | Cantidad | `stock.Cantidad` |
| I | Precio | `stock.PrecioVentaxU` |
| J | Bonificacion | `pordesc_bonif` si ≠0, si no `PorDesc` |
| K | ImporteBonificacion | `PrecioVentaxU × bonif% / 100` |
| L | Importe | `Cantidad × PrecioNetoxU` |
| M | Iva | `Cantidad × PrecioIVAxU` |
| N | TotalGravado | `cuentacliente.SubTotal1` (cabecera FA) |
| O–P | (vacías) | — |
| Q | Total | `cuentacliente.ImporteVenta` (cabecera FA) |
| R | CompRef | PV remito zero-pad **5** |
| S | NumeroRef | Nº legal remito |
| T/W | Entrega / Suc | `cliente_domicilio.NroCalle` del REM |
| U–V | NroCAE / VtoCAE | `fe_cae` / `fe_vto_cae` |
| X | Categoria | `articulo_categoria.nombre_articulo_categoria` o `ACCESORIOS` |
| Y–AW | P901…PIVA3 | `0` |

**Preview only:** `NombreArticulo` (`stock.NombreArticulo`) — no se exporta a Excel.

## TOTAL FACTURAS

Una fila por FA: `Comprobante` = letra + PV(4) + legal(8); `Nro. Remito` = primer remito (`R` + PV4 + legal8); `Imp Neto` / `Imp Bruto` = cabecera.

## Alarmas (no bloquean export)

- FA sin CAE → fila incluida, CAE vacío
- FA sin remitos → CompRef/NumeroRef vacíos
- FA con >1 remito → alarma; TOTAL usa primer remito
- Sin `NroCalle` en remito/FA

## Errores (bloquean export — HTTP 409)

Validación Σ por FA **antes** de expansión multi-remito:

- Σ `Cantidad×PrecioNetoxU` vs `SubTotal1`
- Σ `Cantidad×(PrecioNetoxU+PrecioIVAxU)` vs `ImporteVenta`
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
