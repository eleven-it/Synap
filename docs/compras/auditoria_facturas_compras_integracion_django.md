# Auditoría: Facturas de compras — Especificación de replicación Django/PWA

**Convención:** *Confirmado por código* | *Inferencia fuerte* | *Hipótesis / pendiente*

---

## 1. Qué replicar sí o sí (paridad funcional con AdministraNET)

1. **Numeración `codmov`** coherente con la fila `codmov` donde `codigo = 1` (mismo valor `CodigoMovimiento` en cabecera, stock, caja, op_factura, puentes, asiento). *Confirmado por código.*

2. **Formato de `NroComprobante` / `NroCompBusq`** idéntico al VB6 (PV con ceros + guión + número con ceros). *Confirmado.*

3. **Cabecera `cuentaproveedor`:** todos los campos listados en `auditoria_facturas_compras_tablas_campos.md` sección 1, incluyendo `TipoComprobante`, `TipoFactura`, totales, percepciones en cabecera, CAI, `remite_factura_art`, `CotiDolar`, `Estado`/`Saldo` según `cond_venta.Dias`. *Confirmado.*

4. **Actualización atómica `proveedor.saldo`** alineada con el saldo dejado en la cabecera del movimiento. *Confirmado.*

5. **Contado:** movimiento en `caja` + `caja_saldo` con mismos signos y moneda `Pesos` (o regla equivalente si el cliente usa otra convención en DB). *Confirmado en VB6 para label «Pesos».*

6. **Crédito:** alta `op_factura` cuando `Dias <> "0"`. *Confirmado.*

7. **Detalle `stock` + efectos `stock_deposito`, `stockp`, `lote`, `otro_egreso`** según mismas ramas condicionales (origen remito, OC, permisos `remite_factura_art`). *Confirmado estructura;* detalle campo a campo en código VB6.

8. **Puentes `oc_factp`, `remp_factp` y actualización de estados** en `cuentaproveedor` OC/REM. *Confirmado.*

9. **Vales:** `en_vale_factura` + `en_vale_viaje`. *Confirmado.*

10. **Percepciones IB:** `percep_prov` + `percepcion_prov_convenio` desde buffer equivalente a `percep_prov_temp`. *Confirmado.*

11. **Series:** `serie_entrada` y `serie_movimiento` vía misma lógica de INSERT…SELECT. *Confirmado.*

12. **Contabilidad (si activa):** mismas cuentas `cont_paramatriz`, actualización de saldos en `cont_ejercicio_saldo_cta` / `cont_periodo_saldo_cta`, numeración asiento, líneas `cont_asiento`, luego compensación tipo `Balancea_asiento`. *Confirmado.*

13. **Validaciones fiscales:** período abierto y no vencido respecto a «fecha servidor» del ERP (`Principal.Fecha` en VB6 → equivalente en Synap). *Confirmado.*

14. **Anti-duplicados:** replicar criterio actual (incluyendo la **exclusión de FM** si se busca paridad estricta) o documentar corrección explícita. *Confirmado comportamiento VB6.*

---

## 2. Qué puede abstraerse o modernizar (sin romper DB)

| Aspecto | Recomendación | Riesgo |
|---------|---------------|--------|
| Dos transacciones (`codmov` + resto) | Una sola transacción DB con `SELECT … FOR UPDATE` sobre numerador | Bajo si el valor final de `CodigoMovimiento` es el mismo |
| Buffers `cuerpostockp` por usuario | Tablas temporales en sesión Django o JSON + persistencia al confirmar | Medio: hay que mapear 1:1 campos al insertar `stock` |
| `form_espera` | Jobs asíncronos + UI progreso | Solo UX |
| Post-commit `Cont_CargaAsientoM` | Paso workflow Synap «Asignar CC» | Medio: usuarios esperan mismo momento del proceso |
| ADO Recordset | SQL explícito o ORM con `raw`/procedures | Bajo si el SQL generado coincide |

---

## 3. Servicios Django sugeridos (capas)

1. **`NumeradorMovimientosService`:** obtiene y persiste siguiente `CodigoMovimiento` (tabla `codmov`).  
2. **`FacturaCompraCabeceraService`:** construye y escribe `cuentaproveedor` + `proveedor.saldo` + vales + percepciones + rama caja.  
3. **`FacturaCompraDetalleService`:** loop ítems → `stock`, `stock_deposito`, `stockp`, `lote`, `otro_egreso`, opciones artículo/precios.  
4. **`FacturaCompraCreditoService`:** `op_factura` y vínculos OC/remito.  
5. **`FacturaCompraSerieService`:** equivalencia `GuardarSerie`.  
6. **`FacturaCompraContabilidadService`:** encapsular `generar_asiento_cont` + `Balancea_asiento`.  
7. **`FacturaCompraValidacionFiscalService`:** períodos, duplicados, años.  
8. **`FacturaCompraModificacionService`:** paridad con `modificacion_comp` (subset de tablas).

Cada servicio debe usar **`core.utils.administranet_types`** al escribir MySQL compartido con VB6 (proyecto Synap).

---

## 4. Orden de grabación recomendado (Django)

Alineado a `auditoria_facturas_compras_tablas_campos.md` §10. Ejecutar en **una transacción** salvo decisión documentada de replicar las dos fases VB6.

---

## 5. Consistencia con MySQL legacy

- No asumir FKs: validar existencia de proveedor, artículo, depósito, OC/remito antes de insert.  
- Respetar strings mágicos: `TipoComp = "Compra"`, `anulado = "No"`, estados `Canc` / `N/Canc`, `estado_remito`, `remitido_facturado`.  
- Convivencia: Synap y VB6 no deben correr dos altas concurrentes sin bloqueo en `codmov`.

---

## 6. Riesgos de divergencia

- Redondeo y `Format(…, "##,###.00")` vs `Decimal` Python.  
- Zonas horarias en fechas «short date».  
- FM duplicados si Synap «corrige» validación.  
- Asiento contable si falla después del primer `Commit` en VB6 (en Django una sola transacción evita el hueco).

---

## 7. Trazabilidad

| Decisión | Basada en |
|----------|-----------|
| Paridad de saldo proveedor y cabecera | `PFactura.frm` ~3831–3870 |
| Caja solo contado | ~4034–4101 |
| Asiento opcional con cierre ejercicio | ~9228–9231 |
