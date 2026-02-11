# Numeración talonario vs AFIP (ARCA)

## Convención (igual que VB6 TPV)

En administraNET y en Synap, **`talonarios.Nro` = próximo número a usar** (no "último usado").  
El TPV en VB6 hace: `RecuperaLastCMP` → próximo AFIP = último + 1; valida `talonarios.Nro = próximo AFIP`; usa ese número; luego `Nro = Nro + 1`. Synap replica la misma lógica.

## Error: "No coincide el Nro. de talonario con el de ARCA"

Cuando confirmás una venta (kiosco o "Emitir comprobante" en Carritos pagados sin comprobante), Synap **valida que el próximo número** en `talonarios.Nro` coincida con el próximo que espera AFIP (último autorizado + 1). Si no coinciden, se muestra este error:

- **Talonario próximo:** valor actual de `talonarios.Nro` (próximo que usaría Synap).
- **ARCA próximo:** próximo número que AFIP espera (último autorizado + 1).

Si son distintos, puede haber facturas emitidas fuera de Synap, talonario modificado a mano, o desfase por fallos previos.

## Cómo corregirlo

Hay que **sincronizar la numeración** poniendo en `talonarios.Nro` el valor **ARCA próximo** (el del mensaje).

1. **Identificar PV y tipo:** El error corresponde a un punto de venta y tipo de comprobante (FA o FB). El autoservicio usa el PV configurado en el kiosco.
2. **En administraNET (o directo en la base):** Tabla **`talonarios`**, filtrar por `id_punto_venta` y `TipoComprobante`.
3. **Ajustar `Nro`:** Poner **Nro = ARCA próximo** (el número que indica el mensaje "ARCA próximo: X").

**Ejemplo:** Si el error dice *Talonario próximo: 2, ARCA próximo: 1*:

- En `talonarios` para ese PV y tipo, poner **Nro = 1** (así el próximo a usar será 1 y coincidirá con AFIP).

**Ejemplo:** Si el error dice *Talonario próximo: 7, ARCA próximo: 4*:

- Poner **Nro = 4** (próximo a usar = 4).  
- Atención: si ya emitiste 4, 5, 6 por otro medio y no en AFIP, AFIP estaría desactualizado; en ese caso hay que regularizar en AFIP o ajustar al revés.

4. Guardar y volver a intentar **Emitir comprobante** o la venta en el kiosco.

## Dónde se valida

En `self_checkout/services/confirmation_service.py`: antes de reservar el número se llama a `get_ultimo_autorizado_afip()` (equivalente a `RecuperaLastCMP` en VB6). Si `talonarios.Nro` no coincide con `ultimo_afip + 1`, se hace rollback y se muestra el mensaje.
