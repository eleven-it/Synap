# Auditoría: Facturas de compras — Reglas de negocio y validaciones

**Convención:** *Confirmado por código* | *Inferencia fuerte* | *Hipótesis / pendiente*

Cada regla incluye **trazabilidad** mínima (formulario / procedimiento).

---

## A. Punto de entrada y permisos

| Regla | Tipo | Evidencia | Notas |
|-------|------|-----------|-------|
| Debe seleccionarse proveedor antes de abrir factura manual | Obligatoria | `CargaComprobantesP.frm`, `Case "keyFact"` BOF check (~1610–1615 según resumen) | *Confirmado por código* en conversación previa |
| Si `proveedor.obliga_oc_carga_comp = "Si"`, no se permite factura manual desde menú | Obligatoria | Mismo Case (~1618–1621) | *Confirmado por código* |
| CAI proveedor vigente vs fecha actual | Obligatoria | `CargaComprobantesP` + `Unload PFactura` si vencido | *Confirmado por código* |
| Letra FA/FB/FC/FM según `IDIVA` proveedor vs empresa | Obligatoria | Asignación `Tipo_Factura` en `CargaComprobantesP` | *Confirmado por código* |

---

## B. Validaciones previas a `Guardar`

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Grilla no vacía | `If GridRenglon.EOF Then Exit Sub` — `PFactura.frm` ~3511 | *Confirmado* |
| Origen Remito: al menos un `cuerpostockp` con `codmov_remito` | SELECT ~3525–3537 | *Confirmado* |
| Origen OC: al menos un `codmov_oc` | ~3548 | *Confirmado* |
| Origen Vale: filas en `en_vale_factura_temp` | ~3571 | *Confirmado* |
| Si `modificar_comp = "Si"` → flujo `modificacion_comp`, no alta | ~3590–3594 | *Confirmado* |
| Contabilidad: modal ejercicio/período si flags activos | ~3600–3608 | *Confirmado* |
| Series: si `ESerie` y `ValCantSerie` falso → aborta | ~3621–3629 | *Confirmado* |
| Confirmación usuario «¿Desea generar…?» | ~3633 | *Confirmado* |
| Período fiscal abierto para **fecha de registro**; vencimiento fiscal vs `Principal.Fecha` | ~3637–3663 | *Confirmado* |
| Año del comprobante en tabla `Years` | ~3686–3699 | *Confirmado* |
| `Nro`, `NroSuc`, `ImporteTotal` obligatorios; total > 0 | ~3703–3710 | *Confirmado* |

---

## C. Numeración y duplicados

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| `CodigoMovimiento` global desde `codmov` (código=1) | ~3756–3761 | *Confirmado* |
| Formato PV + número con ceros (`Principal.Ceros_Nro_Comp`, `Ceros_Nro_pv`) | ~3774–3783 | *Confirmado* |
| Duplicados: consulta `cuentaproveedor` por proveedor + nro + tipos FA/FC/FB (no FM) | ~7641–7668 | *Confirmado* — **laguna FM** |
| Duplicados modulados por `Principal.valida_pv_comp_compra` y `ModTalonario` | ramas ~7641 vs ~7658 | *Confirmado* |

---

## D. Condición de compra, CC y tesorería

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| `cond_venta.Dias <> "0"` → crédito: `cuentaproveedor.Saldo` = saldo proveedor + importe total; `Estado = N/Canc` | ~3834–3842, ~4103–4104 | *Confirmado* |
| `Dias = "0"` → contado: `Saldo` cabecera = saldo proveedor (sin sumar factura); `Estado = Canc`; egreso **caja** + **caja_saldo** | ~3840–3842, ~4034–4101 | *Confirmado* |
| `proveedor.saldo` se iguala al `Saldo` asignado en cabecera antes del `Update` final | ~3867–3870 | *Confirmado* |
| Comentario: «Fondo Fijo» — no mezclar con caja general en ciertos escenarios | ~4033 | *Inferencia fuerte:* regla operativa documentada en comentario |

---

## E. IVA, percepciones, otros impuestos (cabecera)

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Tres buckets IVA (`Iva1–3`, alícuotas, subtotales) en `cuentaproveedor` | ~3876–3881, ~4018–4027 | *Confirmado* |
| `PercepIB` distinto de 0 dispara copia `percep_prov_temp` → `percep_prov` + `percepcion_prov_convenio` | ~3885–3927 | *Confirmado* |
| `PercepGan`, `PercepIVA`, `OtrosImp`, `impuesto_interno`, `sobretasa_iva` en cabecera | ~3975–4031 | *Confirmado* |
| Distribución proporcional al cantidad de renglones para «otros impuestos» en gasto OE | ~4195–4196 | *Confirmado* |

---

## F. Stock, depósito, remito y «entrega»

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Lógica distinta si ítem «viene de remito» (evitar doble ingreso) | comentario ~4204 | *Confirmado* |
| `Principal.remite_factura_art` y combo usuario controlan `remite_factura_art` / `estado_fact_remito` en cabecera | ~4119–4171 | *Confirmado* |
| Factura Remito fuerza `remite_factura_art = "No"` en rama permiso Sí | ~4149–4160 | *Confirmado* |

---

## G. Orden de compra

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Actualización `stockp` (`cantidad_pendiente`, `remitido_facturado`) cuando hay OC y no es solo flujo remito-factura según condiciones del bucle | ~4582–4597 | *Confirmado* |
| Estado OC `Facturado` o `Parcial` según existencia de `stockp` con `remitido_facturado='No'` | ~5157–5174 | *Confirmado* |
| Insert `oc_factp` con códigos movimiento factura y OC | ~5176–5182 | *Confirmado* |

---

## H. Remito

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| `remp_factp` + `cuentaproveedor` REM `estado_remito` actualizado | ~5202–5229 | *Confirmado* |

---

## I. Vales

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Relación vale–factura por INSERT desde temp | ~3849 | *Confirmado* |
| Estado `en_vale_viaje` = «En Factura» | ~3860–3862 | *Confirmado* |

---

## J. Lotes y artículos

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Validaciones de lote obligatorio según tipo artículo (bloque ~4447+) | lectura previa | *Confirmado* |
| Nuevo `lote` usa `last_insert_id()` | ~4542 | *Confirmado* |
| Opción `compras_cambia_prov_factura` actualiza `articulo.codigoProveedor` | ~4663 | *Confirmado* |
| Opción `actualiza_lista_compra` recalcula costos y `precios_historial` | ~4674–5083 | *Confirmado* |

---

## K. Contabilidad

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Si ejercicio/período cerrado (`Principal.ContCerrado`) → no asiento, `Error_conta` | ~9228–9231 | *Confirmado* |
| Numeración `Nro_asiento_ejercicio` en `cont_ejercicio` | ~9249–9257 | *Confirmado* |
| Cuentas desde `cont_paramatriz` (IVA 10–12, 50, impuestos, percepciones, descuentos, proveedor/caja) | ~8600–9077 | *Confirmado* |
| Post-commit `Balancea_asiento` corrige diferencias de redondeo | ~5281, subs ~9641+ | *Confirmado* |
| CC: `visualiza_asiento_cont` abre formulario según `cont_pc.asig_cc` | ~9569–9617 | *Confirmado* |

---

## L. Modificación de comprobante existente

| Regla | Evidencia | Tipo |
|-------|-----------|------|
| Confirmación «¿Desea actualizar…?» | ~7901 | *Confirmado* |
| `Nro` y `NroSuc` obligatorios | ~7907 | *Confirmado* |
| Valida período fiscal para **FechaRegistro** y **Fecha** comprobante | ~7922–7958 | *Confirmado* |
| Actualiza `cuentaproveedor`, `stock`, `op_factura`, `op_factura_par`, `imputacion_p`, `caja` | ~8022–8133 | *Confirmado* |
| No recalcula asiento ni `codmov` en el fragmento leído | ausencia en `modificacion_comp` | *Inferencia fuerte* |

---

## M. Clasificación validación

- **UI:** MsgBox confirmación, grid vacío, LostFocus número.  
- **Técnica:** existencia en `Years`, período abierto.  
- **Funcional:** coherencia origen Remito/OC/Vale con buffer.  
- **Fiscal:** período y vencimiento fiscal.  
- **Contable:** ejercicio cerrado, parametrización `cont_paramatriz`.

---

## Trazabilidad resumida

| Conclusión | Evidencia | Confianza |
|------------|-----------|-----------|
| Contado descuenta caja y marca `Canc` | `PFactura.frm` ~4034–4101 | Confirmado |
| FM fuera de anti-duplicado en SQL mostrado | ~7641–7668 | Confirmado |
| Libro IVA no es tabla nombrada en PFactura | ausencia de string en grep | Inferencia / pendiente schema |
