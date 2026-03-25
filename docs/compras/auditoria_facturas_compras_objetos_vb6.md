# Auditoría: Facturas de compras — Mapa de objetos VB6

**Convención:** *Confirmado por código* | *Inferencia fuerte* | *Hipótesis / pendiente*

---

## 1. Punto de entrada y shell

| Objeto | Tipo | Rol |
|--------|------|-----|
| **Principal.frm** | Formulario MDI / principal | Menú que abre **CargaComprobantesP** con distintos perfiles de visibilidad de ítems (p. ej. «Compras», presupuesto, factura proveedor). *Confirmado por búsqueda de referencias `CargaComprobantesP` en `Principal*.frm`.* |
| **CargaComprobantesP.frm** | Formulario | Listado de proveedores; menú **Comprobantes** con `keyFact`, `keyFactRem`, `keyFactOC`, `keyFactVALE`; prepara **PFactura** (CAI, `Tipo_Factura`, `TipoComprobante`, `CodigoProv`, etc.) y llama `PFactura.Inicial` + `Show`. |

---

## 2. Formulario núcleo

### PFactura.frm

**Declaración:** formulario de carga y generación de factura de compra.

| Elemento | Evidencia |
|----------|-----------|
| **Botón Aceptar** (caption típico «Generar») | `Aceptar_Click` → `Guardar` (~3500 en adelante; líneas exactas varían por versión del .frm). |
| **Guardar** | `Private Sub Guardar()`: transacciones, `cuentaproveedor`, `stock`, efectos colaterales. |
| **modificacion_comp** | Flujo alternativo de **actualización** de comprobante ya grabado (no incrementa `codmov`). |
| **generar_asiento_cont** | Asiento en `cont_asiento` + saldos `cont_ejercicio_saldo_cta` / `cont_periodo_saldo_cta` + numeración `cont_ejercicio.Nro_asiento_ejercicio`. |
| **Balancea_asiento** | Ajuste de centavos entre líneas de `cont_asiento` si debe ≠ haber. |
| **visualiza_asiento_cont** | Tras commit: puede abrir **Cont_CargaAsientoM** para CC o solo visualización. |
| **Elimina_Temporal** | `DELETE` en `cuerpostockp`, `percep_prov_temp`, `serie_entrada_temp` (condición OR en último — ver doc pendientes). |
| **Validacion_Comp** | Duplicados en `cuentaproveedor` (FA/FC/FB, no FM en el SQL activo). |
| **GuardarSerie** | `INSERT` masivo `serie_entrada` / `serie_movimiento` desde `serie_entrada_temp`. |
| **Inicial** | Limpieza temporal, `DataCV`, grilla `conf_grilla_final_puesto`, proyecto, caja. |
| **ESerie / ValCantSerie** | Validación cantidad de series vs `cuerpostockp` / `serie_entrada_temp`. |

**Controles de datos típicos (confirmado por nombres en `Guardar`):** `CuerpoStock` (ADODC), `DataCV`, `GridRenglon`, `Fecha`, `FechaRegistro`, `Nro`, `NroSuc`, `CV`, `caja_abm`, `Caja.caja_abm` (fondo fijo), `remite_factura_art`, `ImporteTotal`, `Iva1`–`Iva3`, `Subtotal*`, `PercepIB`, `PercepGan`, `PercepIVA`, `OtrosImp`, `impuesto_interno`, `sobretasa_iva`, `ID_Proyecto`, `id_sucursal`, `Cotizacion_Dolar`, etc.

---

## 3. Formularios auxiliares (circuito factura compra)

| Formulario | Invocación / rol |
|------------|------------------|
| **Cont_AbmEjercicio** | Si `Principal.activ_contabilidad = "Si"` y `Principal.selec_ejer_per_cont = "Si"`: modal antes de generar; `Accion = "PFactura"` (`PFactura.frm` ~3605). |
| **Cont_CargaAsientoM** | `visualiza_asiento_cont`: asignación o visualización de centros de costo sobre `cont_asiento` ya grabado (`ProcAsientoAsigCCFact`). |
| **form_espera** | Barra de progreso durante `Guardar`. |
| **Lista_Comp_Gral** | Desde `ListaRem_Click` / flujo OC: copia renglones a `cuerpostockp`. *Inferencia fuerte* alineada con `ORIGEN_DATOS_FACTURA_COMPRA_VB6.md` y uso de `codmov_remito` / `codmov_oc`. |
| **En_Liquidacion_Vales** | Llena `en_vale_factura_temp` para origen Factura Vale. |
| **Serie_carga** (referenciado en PFactura ~5789) | Carga temporal de series. |

---

## 4. Módulos y clases (.bas / .cls)

| Artefacto | Funciones relevantes al circuito |
|-----------|----------------------------------|
| **Modulos/Funciones.bas** | `Obtener_Datos_Articulo_Mayorista` (embalaje/bulto/display en `stock_deposito`); `Actualiza_Cotizacion_Dolar_Articulo` tras cada ítem. *Confirmado por llamadas desde `Guardar`.* |
| **Principal** (como objeto global en VB6) | Decenas de flags: `activ_contabilidad`, `selec_ejer_per_cont`, `conta_suc`, `remite_factura_art`, `actualiza_lista_compra`, `compras_cambia_prov_factura`, `modifica_sucursal_comp`, `activ_proyecto`, `valida_pv_comp_compra`, `idUsuario`, `codSucursal`, `Fecha`, `Ceros_Nro_Comp`, etc. |

*Hipótesis / pendiente:* otras `.cls` o `.bas` que intercepten errores globales (`Principal.Guardar_Error`) o conexión (`IngresoUsuario.Conex`) sin tocar la lógica de negocio de compras.

---

## 5. ActiveX / controles de terceros

- **MSADODC** (`CuerpoStock`, `DataCV`, …): recordsets enlazados a tablas temporarias o maestros.
- **TrueDB Grid** (`GridRenglon`): edición de renglones.
- **OsenXPButton**, **TabPro**, **tidate8**, **SmartMenuXP**: UI; no alteran persistencia directamente.

---

## 6. Árbol de invocación aproximado (alta nueva factura)

```
Principal → CargaComprobantesP (menú keyFact*)
         → PFactura.Inicial
         → PFactura (usuario edita)
         → Aceptar_Click
              → Cont_AbmEjercicio.Show (condicional)
              → Guardar
                    → [Trans 1] codmov SELECT/UPDATE
                    → [Trans 2]
                         → cuentaproveedor.AddNew + campos + vales + percepciones + caja (contado)
                         → loop CuerpoStock → stock, stock_deposito, stockp, lote, otro_egreso, articulo (opcional)
                         → bloque precios (articulo, precios_historial)
                         → op_factura (crédito)
                         → oc_factp / estado OC / remp_factp / estado remito
                         → GuardarSerie
                         → generar_asiento_cont
                    → CommitTrans
                    → Balancea_asiento
                    → visualiza_asiento_cont
                    → Elimina_Temporal
```

**Rama paralela:** `modificacion_comp` desde `Guardar` si `modificar_comp = "Si"` (sin pasar por `codmov` nuevo ni por el bloque completo anterior).

---

## 7. Conexión y transacciones

- **ADODB.Connection** `conn`: `IngresoUsuario.Conex`, `BeginTrans` / `CommitTrans` / `RollbackTrans`, `SET AUTOCOMMIT=0`.
- **Recordsets** nombrados en `Guardar`: `rs_codmov`, `rs_cuentaproveedor`, `rs_stock`, `rs_saldo_stock`, `rs_stockp`, `rs_lote`, `rs_lotestock`, `rs_otro_egreso`, `rs_op_factura`, `rs_pedido`, `rs_pedido_factura`, `rs_cuerpostock`, `rs_remito_proveedor`, `rs_remp_factp`, etc.

---

## 8. Trazabilidad mínima obligatoria

| Hallazgo | Evencia | Conclusión |
|----------|---------|------------|
| Guardado principal en PFactura | `rs_cuentaproveedor.AddNew` … `Update`; `rs_stock.AddNew` … `Update` | *Confirmado por código* |
| Asiento contable opcional | `generar_asiento_cont` + `cont_asiento` | *Confirmado por código* |
| Hub de menú compras | `CargaComprobantesP` + claves `keyFact*` | *Confirmado por código* (detalle en `ORIGEN_DATOS…` y `CargaComprobantesP.frm`) |
