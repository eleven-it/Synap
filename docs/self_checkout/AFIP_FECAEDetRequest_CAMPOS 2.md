# AFIP WSFEv1 – Campos FECAEDetRequest y reglas por tipo de comprobante

Referencia: pyafipws (reingart/pyafipws) `wsfev1.py` → `CAESolicitar()` / `CAEARegInformativo()` construyen el SOAP desde el dict `factura` (creado por `CrearFactura()`). Este documento resume qué envía Synap y las reglas AFIP que aplican para evitar errores por tipo.

## Tipos de comprobante (CbteTipo)

| Id | Letra | Uso |
|----|--------|-----|
| 1  | FA     | Factura A (RI a RI) |
| 6  | FB     | Factura B (RI a CF) |
| 11 | FC     | Factura C (Monotributo/Exento) |

## Concepto (Concepto)

| Id | Significado |
|----|-------------|
| 1 | Productos |
| 2 | Servicios |
| 3 | Productos y servicios |

- **FchVtoPago** (fecha_venc_pago): AFIP **10049** – Solo debe informarse si Concepto es 2 o 3. Para Concepto 1 debe ser **None** (no enviar).
- **FchServDesde / FchServHasta**: Solo para Concepto 2 o 3.

## Campos enviados en FECAEDetRequest (mapeo pyafipws → SOAP)

| Campo interno (factura) | SOAP FECAEDetRequest | Tipo | Notas |
|-------------------------|----------------------|------|--------|
| concepto | Concepto | int | 1, 2 o 3 |
| tipo_doc | DocTipo | int | 80=CUIT, 96=DNI, 99=Sin identificar |
| nro_doc | DocNro | string | |
| tipo_cbte | CbteTipo | int | 1=FA, 6=FB, 11=FC |
| punto_vta | PtoVta | int | |
| cbt_desde, cbt_hasta | CbteDesde, CbteHasta | int | |
| imp_total | ImpTotal | decimal | |
| imp_tot_conc | ImpTotConc | decimal | |
| imp_neto | ImpNeto | decimal | |
| imp_iva | ImpIVA | decimal | |
| imp_trib | ImpTrib | decimal | |
| imp_op_ex | ImpOpEx | decimal | |
| fecha_cbte | CbteFch | string YYYYMMDD | |
| fecha_venc_pago | FchVtoPago | string o null | Solo si Concepto 2 o 3 (10049) |
| fecha_serv_desde/hasta | FchServDesde/Hasta | string o null | Solo Concepto 2 o 3 |
| moneda_id, moneda_ctz | MonId, MonCotiz | string | |
| condicion_iva_receptor_id | CondicionIVAReceptorId | int | RG 5616 (10246). 5=CF, 1=RI |
| iva | Iva (array AlicIva) | array | **FC: no informar (10071)** |
| tributos | Tributos | array | |
| cbtes_asoc | CbtesAsoc | array | |
| opcionales | Opcionales | array | |

## Reglas AFIP por tipo de comprobante

### Factura C (tipo_cbte = 11, FC)

- **10047**: El campo **ImpIVA** debe ser **0**.
- **10048**: **ImpTotal** debe ser igual a **ImpNeto + ImpTrib** (no se incluye IVA en el total).
- **10071**: El objeto **IVA no debe informarse** (array vacío; no enviar alícuotas).
- **10049**: Con **Concepto 1**, **FchVtoPago** no debe informarse (enviar None).

Resumen para FC en Synap:

- `concepto = 1`
- `fecha_venc_pago = None`
- `imp_iva = "0.00"`
- `imp_total = imp_neto + imp_trib` (en nuestro caso `imp_trib = 0` → `imp_total = imp_neto`)
- `imp_tot_conc = "0.00"` (o el que corresponda; para FC sin IVA suele ser 0)
- `iva = []` → no llamar a `AgregarIva` para FC.

### Factura A y B (tipo_cbte = 1 y 6)

- Se envían alícuotas IVA (`iva` con Id, BaseImp, Importe).
- ImpTotal = ImpNeto + ImpIVA + ImpTrib + ImpOpEx + ImpTotConc (según diseño).
- FchVtoPago solo si Concepto 2 o 3; con Concepto 1 = None.

## Flujo en Synap (invoice_service.py)

1. **`_obtener_datos_factura()`** arma el dict `datos` con las claves que `CrearFactura(**datos)` acepta.
2. Para **FC** se aplica la lógica anterior: sin IVA, total = neto + trib, sin fecha vto pago cuando concepto=1.
3. **`emitir_fe()`** llama `CrearFactura(**datos)` y luego solo llama `AgregarIva(**iva)` para cada ítem si `datos["iva"]` no está vacío (FA/FB).
4. Para FC, `datos["iva"]` debe ser `[]` y no se llama `AgregarIva`.

Referencia oficial: manual WSFEv1 AFIP (R.G. 4291) y código reingart/pyafipws `wsfev1.py`.
