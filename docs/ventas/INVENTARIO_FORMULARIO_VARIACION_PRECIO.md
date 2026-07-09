# Inventario — Variación de precios (referencia VB6)

**Formularios origen:** `VariacionPrecio.frm`, `CargaArticulo.frm`, `PrevPrec.frm`  
**Tablas:** `articulo`, `precios_historial`, `precios_masivo_temp` (staging legacy, no usada en Synap MVP)

## Campos editados en Synap

| Campo articulo | Rol |
|----------------|-----|
| `Precio1V`…`Precio5V` | Precio neto por lista |
| `Precio1VI`…`Precio5VI` | Precio final (IVA + interno) |
| `Util1`…`Util5` | % utilidad recalculada desde `PrecioCosto` |
| `stock_reserva` | Colchón reserva (solo packs terminados MPR) |

## Fórmulas (paridad motor ecom)

- **Final desde neto:** `final = neto + neto×IVA/100 + neto×impuesto_interno/100`
- **Neto desde final:** `neto = final / (1 + (IVA + interno)/100)`
- **Util:** `((Precio{i}V - PrecioCosto) / PrecioCosto) × 100` si costo > 0

## Historial

INSERT en `precios_historial` con `tipo_modificacion = 'Synap precios terminados'`, snapshot de listas y utilidades.

## Operaciones masivas (VariacionPrecio)

Synap implementa: % +/-, sumar/restar monto, establecer valor, redondear — sobre universo filtrado server-side.
