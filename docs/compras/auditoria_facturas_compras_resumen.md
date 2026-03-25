# Auditoría: Facturas de compras (AdministraNET VB6) — Resumen ejecutivo

**Alcance:** circuito de **guardado** de factura de compra en MySQL, reconstruido desde `administranet_vb6`.  
**Convención:** *Confirmado por código* | *Inferencia fuerte* | *Hipótesis / pendiente*

---

## Visión general

El flujo operativo arranca en **CargaComprobantesP.frm** (listado de proveedores y menú contextual). Según la opción elegida se abre **PFactura.frm** con `TipoComprobante` ∈ {`Factura`, `Factura Remito`, `Factura OC`, `Factura Vale`} y `Tipo_Factura` ∈ {FA, FB, FC, FM} según condición fiscal del proveedor y de la empresa.

La persistencia principal ocurre en **`Private Sub Guardar()`** de **PFactura.frm**, disparada por el botón **Aceptar** (texto UI: **«Generar»**) vía `Aceptar_Click` → `Guardar`.

---

## Hallazgos principales (confirmados por código)

1. **Dos transacciones consecutivas sobre `codmov`:** primero `BeginTrans` → lectura/actualización de `codmov` (incremento global `CodigoMovimiento`) → `CommitTrans`; luego segunda `BeginTrans` para el resto del comprobante hasta `CommitTrans` o `RollbackTrans` en error (`PFactura.frm`, ~3750–3772, ~5271–5274, ~5347–5354).

2. **Cabecera:** `cuentaproveedor` con `TipoComprobante` = FA/FB/FC/FM, `TipoFactura` según origen (Factura / Factura Remito / Factura OC), totales, percepciones en cabecera, CAI, condición de compra, sucursal, flags `remite_factura_art`, cotización dólar, etc.

3. **Cuenta corriente proveedor:** actualización de `proveedor.saldo` alineada con el saldo calculado en `cuentaproveedor` según `cond_venta.Dias` (contado vs plazo).

4. **Contado (`cond_venta` código implícito por `Dias = "0"`):** movimiento en **`caja_saldo`** y alta en **`caja`** (`Tipo` = «Factura Compra Contado»), `Estado` de `cuentaproveedor` = `Canc`.

5. **Renglones:** siempre se recorre `CuerpoStock.Recordset` y se hace `rs_stock.AddNew` por ítem; la **entrada física a depósito** y el **campo `stock.no_entregado_fact`** dependen de `TipoComprobante`, `Principal.remite_factura_art` y el combo `remite_factura_art` (Factura Remito → no suma saldo en depósito en la rama correspondiente).

6. **Orden de compra:** actualización de **`stockp`** (`cantidad_pendiente`, `remitido_facturado`) y **`oc_factp`** (relación factura–OC); posible cambio de **`cuentaproveedor`** OC a `Estado` `Facturado` o `Parcial`.

7. **Remito:** **`remp_factp`** + `cuentaproveedor` del remito `estado_remito = "Facturado"` (sin re-entrar stock si la lógica de depósito lo evita).

8. **Vales:** `INSERT` en **`en_vale_factura`** desde **`en_vale_factura_temp`** y `UPDATE` **`en_vale_viaje.estado`** = `'En Factura'`.

9. **Percepciones IB (detalle por jurisdicción):** si `PercepIB <> 0` y hay filas en **`percep_prov_temp`**, se insertan **`percep_prov`** y **`percepcion_prov_convenio`**.

10. **Contabilidad (opcional):** si `Principal.activ_contabilidad = "Si"` y `Principal.conta_suc = "Si"`, **`generar_asiento_cont`** escribe **`cont_asiento`**, actualiza **`cont_ejercicio`**, **`cont_ejercicio_saldo_cta`**, **`cont_periodo_saldo_cta`** según configuración; luego **`Balancea_asiento`** y **`visualiza_asiento_cont`** (posible apertura de **Cont_CargaAsientoM** para centros de costo).

11. **No hay en PFactura referencias a tablas con nombre explícito tipo `libro_iva_compras`:** el crédito fiscal queda modelado en **`cuentaproveedor`** / **`stock`** y en exportaciones (p. ej. **Exportacion.frm** / libro IVA digital). *Inferencia fuerte:* los informes AFIP leen esas tablas; *pendiente:* mapear vistas o jobs si existen en MySQL fuera del VB6 analizado.

---

## Componentes clave

| Rol | Artefacto |
|-----|-----------|
| Entrada menú / hub | `CargaComprobantesP.frm` |
| Formulario carga y guardado | `PFactura.frm` (`Guardar`, `generar_asiento_cont`, `modificacion_comp`, `Validacion_Comp`, `Elimina_Temporal`, `GuardarSerie`) |
| Carga renglones desde OC/Remito | `Lista_Comp_Gral.frm` (traslado a `cuerpostockp` / `CuerpoStock`) |
| Vales | `En_Liquidacion_Vales.frm` |
| Funciones compartidas | `Modulos/Funciones.bas` (`Obtener_Datos_Articulo_Mayorista`, `Actualiza_Cotizacion_Dolar_Articulo`, …) |
| Controles | MSADODC (`CuerpoStock`, `DataCV`, …), TrueDB Grid, OsenXPButton, TabPro, tidate8, SmartMenuXP |

---

## Riesgos de replicación en Django/PWA

- **Paridad numérica:** uso extensivo de `Format`, `CDbl`, redondeos y compensación de **0,01** en `Balancea_asiento`; divergencias si el stack web redondea distinto.
- **Dos fases de transacción (`codmov` vs resto):** si Django usa una sola transacción atómica puede ser *mejor*, pero cambia el comportamiento ante fallos intermedios; documentar decisión.
- **Validación duplicados:** `Validacion_Comp` compara FA/FC/FB; **no incluye FM** en el `WHERE` — riesgo de duplicados lógicos para FM si no se replica el mismo criterio o se corrige a propósito.
- **Buffers por usuario:** `cuerpostockp`, `percep_prov_temp`, `serie_entrada_temp`, `en_vale_factura_temp` están ligados a `Principal.idUsuario`; en web hay que aislar por sesión/usuario de forma equivalente.
- **Efectos posteriores al `CommitTrans`:** asignación de centros de costo y UI de asiento (`Cont_CargaAsientoM`) ocurren tras confirmar; Synap debe decidir si los deja como paso posterior manual o los integra.

---

## Dependencias críticas

- Maestros: `proveedor`, `cond_venta`, `articulo`, `iva`, `periodos`/`years`, `codmov`.
- Configuración global: propiedades de **`Principal`** (permisos, flags de stock, contabilidad, embalaje, etc.).
- Integridad referencial explícita en MySQL puede ser mínima; el VB6 asume **orden de escritura** y claves generadas (`last_insert_id()` en lotes).

---

## Documentación relacionada

- [auditoria_facturas_compras_flujo_completo.md](auditoria_facturas_compras_flujo_completo.md)
- [auditoria_facturas_compras_objetos_vb6.md](auditoria_facturas_compras_objetos_vb6.md)
- [auditoria_facturas_compras_tablas_campos.md](auditoria_facturas_compras_tablas_campos.md)
- [auditoria_facturas_compras_sql.md](auditoria_facturas_compras_sql.md)
- [auditoria_facturas_compras_reglas_negocio.md](auditoria_facturas_compras_reglas_negocio.md)
- [auditoria_facturas_compras_integracion_django.md](auditoria_facturas_compras_integracion_django.md)
- [auditoria_facturas_compras_pendientes_dudas.md](auditoria_facturas_compras_pendientes_dudas.md)
- [ORIGEN_DATOS_FACTURA_COMPRA_VB6.md](ORIGEN_DATOS_FACTURA_COMPRA_VB6.md) (actualizado con enlace a esta auditoría)
