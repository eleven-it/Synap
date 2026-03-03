# Inventario y plan de migración: Remitos de compra (PRemito.frm → Synap)

**Formulario origen:** PRemito.frm (AdministraNET VB6) — Remito de compra / entrada de mercadería desde proveedor.  
**Metodología:** [INVENTARIO_MIGRACION_FORMULARIOS.md](INVENTARIO_MIGRACION_FORMULARIOS.md).  
**Plan de referencia:** documento de plan de migración Remitos de compra (Fases 1–4).

**Estado:** Fase 1 completada con código VB6. **Ubicación del código:** `administranet_vb6/Formularios/PRemito.frm` (y `PRemito.frx`); formularios relacionados en el mismo directorio: `Lista_Comp_Gral.frm`, `Visualiza_PRemito.frm`, `Visualiza_PRemitoC.frm`, `ConsultaComprobante.frm`, `trz_trazabilidadComp.frm`.

---

## 1. Inventario de UI (artefactos y layout)

*Fuente: inspección de `administranet_vb6/Formularios/PRemito.frm` (bloques Begin/End de controles) y código que modifica .Visible, .Enabled, .RecordSource.*

| Tipo control VB6 | Nombre interno | Propiedades relevantes | Dependencias UI | Sección / flujo |
|------------------|---------------|------------------------|-----------------|------------------|
| VB.Form | PRemito | Caption = " Remito de Compra", BorderStyle = 1, StartUpPosition = 2 | — | Formulario principal |
| VB.Frame | frame_proyecto | Visible = False por defecto | Principal.activ_proyecto = "Si" | Proyecto (erp_proyecto) |
| OsenXPButton | Lista_Proyecto | ToolTipText = "Listado de proyectos" | frame_proyecto | Proyecto |
| VB.Label | nombre_proyecto, Label_Proyecto | — | frame_proyecto | Proyecto |
| VB.Frame | FramePie | Caption = "Pie de Comprobante" | — | Totales e impuestos |
| VB.TextBox | impuesto_interno, PercepIB, PercepIVA, PercepGan, OtrosImp, ImpDesc1_1, PercepIB_Prov | Text = "0", Alignment = Right | Labels asociados | Pie |
| MSDataListLib.DataCombo | Provincia2, Provincia1 | ListField = "Provincia", BoundColumn = "CodProvincia" | Percepciones IB | Pie |
| VB.Label | ImporteTotal, Exento, Subtotal1/2/3, Iva1/2/3, LtotalGeneral, Lexento, etc. | Caption, DataFormat | Cálculo desde CuerpoStock | Pie |
| VB.Frame | FrameEncabezado | Caption = "Encabezado de Comprobante" | — | Cabecera |
| VB.ComboBox | Deposito_Seleccion, tipo_comp | ListIndex (0=Usuario, 1=Comprobante original, 2=Manual, 3=Por artículo) | Principal.deposito_devol_nc_selec, Principal.cambia_deposito | Depósito / tipo comprobante |
| VB.TextBox | Nro, NroSuc, Detalle | Nro/NroSuc para número comprobante | Validacion_Comp, Nro_LostFocus | Cabecera |
| OsenXPButton | ListaOC | — | ListaOC_Click: abre Lista_Comp_Gral (OC, REM Prov o PFacturas) | Origen de datos |
| MSDataListLib.DataCombo | Deposito_Global | BoundText → CodDeposito | data_deposito.RecordSource | Depósito global |
| VB.Label | Proveedor, LabelComp, LabelAnul, FAcliente, Ldetalle, Lnumero, Lfecha, NroFactA | — | Cabecera |
| TDBDate (u otro) | Fecha, FechaRegistro | Fecha comprobante / registro | periodos, years | Cabecera |
| MSAdodcLib.Adodc | CuerpoStockTemp | RecordSource asignado en código (sumas) | CalculoTotales | Temporales |
| MSAdodcLib.Adodc | DataCV, CuerpoStock | CuerpoStock → cuerpostockp (CodUsuario, visualiza, CodigoMovimiento) | Grid atado a renglones | Renglones remito |
| OsenXPButton | Aceptar, Cancelar | — | Aceptar_Click → Guardar; Cancelar_Click | Acciones |
| MSComctlLib.StatusBar | StatusBar | Panels: Empresa, Sucursal, Usuario | Principal, CargaComprobantesP | Barra estado |
| MSAdodcLib.Adodc | data_deposito | RecordSource → deposito [INNER JOIN deposito_usr] o deposito WHERE CodDeposito = Principal.id_deposito | Form_Load ~5352–5368; Principal.cambia_deposito | Depósito recepción |
| MSAdodcLib.Adodc | DataArt, Adodc1 | RecordSource para artículos / auxiliar | ListaArticulos, búsqueda rápida | Artículos |
| TabproLib.vaTabPro | TabFactura | Pestañas | — | Contenedor renglones |
| VB.Frame | Frame_Total_art_stock, Lote, FrameBotones, FrameCuerpo | Lote: nro_lote, fecha_vto; FrameCuerpo: datos renglón | — | Renglón / botones |
| VB.TextBox | nro_lote, detalle_renglon, unidad_art_peso, Bonif_Importe, Bonif_Renglon, ImpDescRenglon, TotalRenglon, Cantidad, PrecioCostoxU, SubTotalRenglon, DescRenglon | — | GridRenglon, CalculoTotales | Renglón |
| OsenXPButton | Modificar, Eliminar, ListaArticulos, Importar, ABMSerie, AceptarStock, lista_unidad_art_peso | — | Eliminar_Click → DELETE cuerpostockp + serie_entrada_temp; Importar → Lista_Comp_Gral; ABMSerie → Serie_abm/Serie_carga vbModal | Acciones renglón |
| MSDataListLib.DataCombo | Deposito_Articulo | Depósito por renglón | data_deposito | Renglón |
| VB.Label | Codigo, Descripcion, Codigo_manual, Codigo_ID, Label_renglon, Lcantidad, LprecioU, etc. | Caption desde CuerpoStock.Recordset | GridRenglon_RowColChange | Renglón |
| TrueOleDBGrid80.TDBGrid | GridRenglon | DataSource = CuerpoStock; columnas según conf_grilla_final_puesto ('Grilla compras REM') | GridRenglon_DblClick → Modificar; Menu_Contextual | Grid renglones |
| VB.Label | stock_actual_comp, Total_Disponible, Total_Pedido_Cliente | Calculo_Stock_Actual, Calculo_Disponible, Calculo_Pedido_Cliente_Pendiente | — | Info stock |
| VB.Frame | Frame_BusquedaRapida | Caption = "Busqueda rápida artículo" | — | Búsqueda |
| VB.ComboBox | campo_busqueda, tipo_unidad_bulto_br | — | Setea_Lista_Cambio_campo_busqueda | Búsqueda |
| VB.TextBox | Cantidad_busqueda | — | Insertar_Renglon_Busqueda_Rapida | Búsqueda |
| TrueOleDBList80.TDBCombo | ListaArt | RecordSource → articulo (moneda, NombreArticulo, IDArt, id_manual, lote, etc.) | ListaArt_KeyPress, Activa_Lista_Carga_Rapida_Articulo | Búsqueda artículo |
| VB.Label | Label_ID_cuerpostock | Almacena Orden del renglón para Eliminar | Eliminar_Click | Oculto |

**Conexión de datos (código):** `conn.ConnectionString = IngresoUsuario.Conex`; `CuerpoStock.RecordSource` asignado en Inicial, ListaOC (desde Lista_Comp_Gral), Importar, Elimina_Temporal, etc. (consultas a `cuerpostockp` con filtro CodUsuario, visualiza, CodigoMovimiento).

**Migrado a Synap (tipo_comp y ListaOC):**
- **tipo_comp:** Combo en encabezado siempre visible; sus opciones dependen del permiso del puesto `remite_factura_art` (tabla `permisos_sistema`): si es "Si" se muestran "Ord. Compra" y "Factura"; si no, solo "Ord. Compra" (paridad VB6 Inicial: Principal.remite_factura_art). Formulario: `RemitoCompraCabeceraForm.tipo_comp` con `tipo_comp_choices` inyectado desde `_tipo_comp_choices(base_empresa, id_puesto)` en la vista; template: selector en panel "Datos del comprobante", enlazado a Alpine `tipoComp`.
- **ListaOC:** Botón "Lista OC" / "Lista facturas" según tipo_comp. Abre lista de comprobantes del proveedor (OC pendientes, facturas pendientes o remitos para importar). Ubicación: `compras/views.lista_comp_remito`, template `compras/lista_comp_remito.html`, URL `compras:lista_comp_remito` con `?codigo_proveedor=&tipo=oc|factura|importa_rem`. Servicios: `list_comprobantes_remito` y `importar_comprobante_remito` en `core/services/administranet_compras.py` (origen: stockp para OC, stock para REM/factura; destino: cuerpostockp del usuario).
- **Importar:** Botón "Importar remito" que abre la misma vista con `tipo=importa_rem` (remitos del proveedor desde cuentaproveedor TipoComprobante='REM').

---

## 2. Mapa de eventos (evento → función → efecto → dependencias)

*Fuente: búsqueda en `PRemito.frm` de _Click, _Change, _Load, _KeyPress, etc.*

| Evento | Procedimiento / Sub | Efecto | Dependencias |
|--------|---------------------|--------|--------------|
| Form_Load | Form_Load (~5300) | RemoveCancelMenuItem, Menu, Actualiza_Fecha_MySQL, Menu_Contextual (ítems histórico compras/artículo, visualizar ficha, etiqueta), StatusBar (Empresa, Sucursal, Usuario), Deposito_Seleccion según Principal.deposito_devol_nc; data_deposito.RecordSource (deposito + deposito_usr o solo deposito); Deposito_Global/Deposito_Articulo.BoundText; Setea_Lista_Carga_Rapida_Articulo; Cambio_Fuente_Formulario | IngresoUsuario.Conex, Principal |
| Aceptar_Click | Aceptar_Click (~3304) | Llama Guardar | — |
| Guardar | Guardar (~3308) | Si ModTalonario = "Si" → modificacion_comp y sale. Valida ESerie/ValCantSerie (cantidad vs series). MsgBox "¿Desea generar el comprobante?". Validaciones: Nro, NroSuc, ImporteTotal no vacíos. Periodo fiscal (periodos, years) abierto y no vencido. Año en Years. BeginTrans: 1) UPDATE codmov (contador+1); CommitTrans; 2) BeginTrans: INSERT cuentaproveedor (REM), por cada renglón stock AddNew + stock_deposito Update/AddNew, lote/lote_stock si aplica, oc_remp (rs_rem_ped), remp_factp (rs_rem_fact), estado_remito; GuardarSerie (serie_entrada, serie_movimiento); CommitTrans. On Error → captura: RollbackTrans, Principal.Guardar_Error | conn, Principal, IngresoUsuario.Conex |
| Cancelar_Click | Cancelar_Click (~4846) | Cierra formulario | — |
| ListaOC_Click | ListaOC_Click (~5059) | Según opción: TipoComprobante = "Importa REM Prov" / "Orden de Compra - Remito" / "PFacturas"; asigna Lista_Comp_Gral.CodigoCP, Label_CP, NombreCP, Inicial; Lista_Comp_Gral.Show vbModal (remitos) o .Show (OC/facturas) | id_proveedor, nombre_proveedor |
| Importar_Click | Importar_Click (~5004) | Igual que ListaOC para "Importa REM Prov": Lista_Comp_Gral.Show vbModal | — |
| Eliminar_Click | Eliminar_Click (~5240) | MsgBox "¿Desea eliminar el renglon?". conn.Open; DELETE cuerpostockp WHERE Orden = Label_ID_cuerpostock; DELETE serie_entrada_temp WHERE id_articulo, visualiza, id_usuario, tipo_comprobante, orden; CalculoTotales. On Error → captura | CuerpoStock.Recordset, IDArt |
| Elimina_Temporal | Elimina_Temporal (~6234) | conn.Execute "delete from cuerpostockp where Codusuario = Principal.idUsuario AND visualiza = 'No'"; DELETE serie_entrada_temp para mismo usuario/tipo | Inicial / nuevo |
| AceptarStock_Click | AceptarStock_Click (~4285) | Alta/modificación de renglón en CuerpoStock (temporal); validaciones; CalculoTotales | GridRenglon, renglón actual |
| Modificar_Click | Modificar_Click (~5698) | Carga renglón actual en controles (Codigo, Descripcion, Cantidad, etc.); habilita edición | GridRenglon |
| ListaArticulos_Click | ListaArticulos_Click (~5682) | Abre selector de artículos; carga en CuerpoStock.Recordset | — |
| ABMSerie_Click | ABMSerie_Click (~6559) | ValCantSerie; Serie_abm.Show vbModal o Serie_carga.Show vbModal | Artículos seriados |
| GuardarSerie | GuardarSerie (~6652) | conn.Execute INSERT serie_entrada; conn.Execute INSERT serie_movimiento desde serie_entrada_temp | Dentro de Guardar |
| Deposito_Seleccion_Click | Deposito_Seleccion_Click (~6810) | Lógica depósito según ListIndex | data_deposito |
| GridRenglon_DblClick | GridRenglon_DblClick (~6230) | Modificar_Click | — |
| GridRenglon_RowColChange | GridRenglon_RowColChange (~6838) | Carga Codigo, Descripcion, Codigo_manual, Codigo_ID desde CuerpoStock.Recordset; Calculo_Stock_Actual | — |
| CalculoTotales | CalculoTotales (~5847) | CuerpoStock.RecordSource = SELECT sum(PrecioNetoxR), sum(impuesto_interno_subtotal); actualiza ImporteTotal, Exento, Subtotal1/2/3, Iva1/2/3, etc. | Tras cambiar renglones |
| Inicial | Inicial (~5472) | Fecha, FechaRegistro, fecha_vto = Principal.Fecha; conf_grilla_final_puesto ('Grilla compras REM'); CuerpoStock.RecordSource = SELECT * FROM cuerpostockp WHERE CodigoMovimiento = 0; HabilitaObj/DesHabilitaObj | Llamado desde menú / Lista_Comp_Gral al volver |
| modificacion_comp | modificacion_comp (~6334) | Si ModTalonario = "Si": BeginTrans; UPDATE cuentaproveedor (Fecha, NroComprobante, Detalle, etc.); UPDATE stock (NroComprobante); CommitTrans; Unload Me; ConsultaComprobante.Comprobante restablecido | Desde ConsultaComprobante |
| Lista_Proyecto_Click | Lista_Proyecto_Click (~5054) | Listado de proyectos (erp_proyecto) | frame_proyecto Visible |
| Nro_LostFocus, NroSuc_LostFocus | Validacion_Comp (~6078) | Validación número comprobante | — |
| ImpDesc1_1_Change, PercepIVA_Change, etc. | Recalculan totales / actualizan pie | CalculoTotales o actualización de labels | — |
| Menu_Contextual_Click | Menu_Contextual.Show (~6733) | Menú contextual (histórico compras, ficha artículo, ficha stock, etiqueta) | GridRenglon_MouseUp (x, Y) |
| MenuPrincipal_Click | MenuPrincipal_Click (~6185) | Acciones según ID del menú | Menu (~6166) |

**Secuencia típica de uso:** Abrir desde menú (Inicial) o desde Lista_Comp_Gral → elegir OC / remito / factura proveedor (ListaOC) → renglones cargados en CuerpoStock → editar cantidades, depósito, lotes, series (ABMSerie) → Aceptar → Guardar (transacción codmov + cuentaproveedor + stock + stock_deposito + oc_remp + remp_factp + GuardarSerie).

---

## 3. Funciones / procedimientos y dependencias

*Fuente: análisis de `PRemito.frm`. Líneas aproximadas entre paréntesis.*

| Procedimiento | Tipo | Parámetros | Resumen | Llamadas a módulos / side-effects |
|---------------|------|------------|---------|-----------------------------------|
| Aceptar_Click | Private Sub | — | Llama Guardar | — |
| Guardar | Private Sub | — | Transacción completa: codmov, cuentaproveedor, stock, stock_deposito, lote, lote_stock, oc_remp (rs_rem_ped), remp_factp (rs_rem_fact), GuardarSerie; form_espera; On Error GoTo captura | conn (IngresoUsuario.Conex), Principal, Obtener_Datos_Articulo_Mayorista |
| AceptarStock_Click | Private Sub | — | Alta/actualización renglón temporal en CuerpoStock; CalculoTotales | — |
| HabilitaObj / DesHabilitaObj | Public Sub | — | Habilitar/deshabilitar controles (estado edición) | — |
| Cancelar_Click | Private Sub | — | Unload Me | — |
| Cantidad_GotFocus, Cantidad_KeyPress, Cantidad_LostFocus | Private Sub | KeyAscii / — | Validación cantidad; Desc_Renglon | — |
| ImpDesc1_1_Change, PercepIB_Change, PercepIVA_Change, PercepGan_Change, OtrosImp_Change | Private Sub | — | Recalculan totales / formato | CalculoTotales |
| Desc_Renglon | Private Sub | — | Cálculo descuento renglón | — |
| Importar_Click | Private Sub | — | Lista_Comp_Gral (Importa REM Prov), Show vbModal | — |
| ListaOC_Click | Private Sub | — | Lista_Comp_Gral según tipo (REM Prov / OC / PFacturas); Show vbModal o Show | — |
| Eliminar_Click | Private Sub | — | DELETE cuerpostockp, serie_entrada_temp; CalculoTotales; On Error captura | conn, Principal.Guardar_Error |
| Form_Load | Private Sub | — | Menu, StatusBar, data_deposito, Deposito_Global/Articulo, Setea_Lista_Carga_Rapida_Articulo, Cambio_Fuente_Formulario | IngresoUsuario.Conex, Principal, CargaComprobantesP |
| Cambio_Fuente_Formulario | Private Sub | — | Recorre Controls; aplica Principal.fuente_tamano, color_formulario_var, tipo_boton_var | Principal |
| Inicial | Public Sub | — | Fechas, conf_grilla_final_puesto ('Grilla compras REM'), CuerpoStock.RecordSource (CodigoMovimiento=0), HabilitaObj/DesHabilitaObj | conn, Principal |
| CalculoTotales | Public Sub | — | Sumas sobre cuerpostockp (PrecioNetoxR, impuesto_interno_subtotal); actualiza ImporteTotal, Exento, Subtotal*, Iva*, etc. | CuerpoStock.RecordSource (SELECT sum...) |
| NroSuc_KeyPress, Nro_KeyPress, Nro_LostFocus, NroSuc_LostFocus | Private Sub | — | Validacion_Comp, tab order | — |
| Validacion_Comp | Private Sub | — | Validación número comprobante (evitar duplicados) | — |
| Menu, MenuPrincipal_Click | Private Sub | ID As Long | Menú principal y ítems por ID | Principal |
| Elimina_Temporal | Public Sub | — | DELETE cuerpostockp (CodUsuario, visualiza='No'); DELETE serie_entrada_temp | conn |
| Cancela_Renglon | Public Sub | — | Limpia controles de renglón (Codigo, Descripcion, etc.) | — |
| habilita_renglon / deshabilita_renglon | Public Sub | — | Enabled controles renglón | — |
| modificacion_comp | Private Sub | — | UPDATE cuentaproveedor, stock (solo fecha/nro cuando ModTalonario); CommitTrans; Unload Me; restaura ConsultaComprobante.Comprobante | conn, ConsultaComprobante |
| ValCantSerie | Private Function | — | Boolean: cantidad vs cantidad de series (serie_entrada_temp) | — |
| ABMSerie_Click | Private Sub | — | ValCantSerie; Serie_abm.Show vbModal o Serie_carga.Show vbModal | Serie_abm, Serie_carga |
| ESerie, EsSerie | Private Function | IDArt | Comprueba si artículo es seriado | — |
| GuardarSerie | Private Sub | — | INSERT serie_entrada, INSERT serie_movimiento desde serie_entrada_temp | conn.Execute |
| ListaArticulos_Click, Modificar_Click | Private Sub | — | Selector artículos; carga renglón en controles | — |
| GridRenglon_DblClick, GridRenglon_RowColChange, GridRenglon_GotFocus | Private Sub | — | Modificar; actualiza Codigo/Descripcion/stock actual; MarqueeStyle | — |
| Deposito_Seleccion_Click | Private Sub | — | Lógica depósito (Usuario / Comprobante / Manual / Por artículo) | — |
| Buscar_Articulo_Grilla | Private Sub | strSearchCodigo | Búsqueda en grilla por código | — |
| Calculo_Stock_Actual, Calculo_Pedido_Cliente_Pendiente, Calculo_Disponible | Private Sub | — | rs_saldo_stock, labels stock_actual_comp, Total_Disponible, Total_Pedido_Cliente | conn, stock_deposito, stockp |
| campo_busqueda_Change, ListaArt_KeyPress | Private Sub | — | Búsqueda rápida artículo; Setea_Lista_Cambio_campo_busqueda | DataArt.RecordSource |
| Insertar_Renglon_Busqueda_Rapida | Private Sub | — | Añade renglón desde ListaArt a CuerpoStock; CalculoTotales | — |
| Setea_Lista_Carga_Rapida_Articulo, Activa_Lista_Carga_Rapida_Articulo, Desactiva_Lista_Carga_Rapida_Articulo, Setea_Lista_Cambio_campo_busqueda | Private Sub | — | RecordSource DataArt (articulo); columnas ListaArt según campo_busqueda | — |

**Variables/objetos globales o de módulo (en PRemito):** `conn` (ADODB.Connection), `CodigoProv`, `CodMov`, `id_condcompra`, `nombre_condcompra`, `ID_Proyecto`, `ModTalonario`, `mod_manual_impuesto_interno`, `DepositoOrigen`, `id_sucursal`, `factura_no_remite`, `Estado_Factura`, `codigo_mov_fact`. **Referencias externas:** `Principal`, `IngresoUsuario.Conex`, `CargaComprobantesP.Sucursal`, `form_espera`, `Lista_Comp_Gral`, `ConsultaComprobante`, `Serie_abm`, `Serie_carga`, `Obtener_Datos_Articulo_Mayorista`, `Impresion_Etiquetas_Articulo_Chico`, `Actualiza_Fecha_MySQL`, `RemoveCancelMenuItem`, `Menu_Contextual`.

---

## 4. Relaciones con otros formularios / módulos

| Formulario / módulo | Uso (Show/Load/Unload) | Modal | Parámetros / contexto |
|---------------------|------------------------|-------|------------------------|
| **Lista_Comp_Gral** | Listado de OC, remitos o facturas de proveedor; el usuario elige y al confirmar se rellenan PRemito.CuerpoStock y cabecera. Llamado desde **ListaOC_Click** e **Importar_Click**. | **vbModal** para "Importa REM Prov"; **Show** (no modal) para "Orden de Compra - Remito" y "PFacturas" | TipoComprobante ("Importa REM Prov" / "Orden de Compra - Remito" / "PFacturas"), CodigoCP = id_proveedor, NombreCP = nombre_proveedor, Label_CP.Caption = "Proveedor", GridComprobante.Columns(3).DataField, GridRenglon.Columns(3).DataField, Caption del form, Inicial. Lista_Comp_Gral escribe en PRemito.CuerpoStock.Recordset (AddNew, Fields!IDArt, Cantidad, PrecioCostoxU, nro_oc, codmov_oc, etc.). |
| **Lista_Comp_Fact** | Lista factura/remito compra; en ventas delega a Remito.frm; en compras puede abrir PRemito (referencia en documentación). | — | No invocado desde PRemito.frm en el código revisado. |
| **Visualiza_PRemito** | Visualización de remito de compra ya grabado (solo lectura o reimpresión). | — | codigo_movimiento del remito. No invocado desde PRemito.frm; se abre desde menú o ConsultaComprobante. |
| **Visualiza_PRemitoC** | Copia/alternativa del visualizador. | — | — |
| **ConsultaComprobante** | Consulta/anulaciones de comprobantes. Puede abrir PRemito para **modificación por talonario**: PRemito.ModTalonario = "Si" → al guardar ejecuta **modificacion_comp** (solo actualiza Fecha, NroComprobante, Detalle en cuentaproveedor y stock). Al salir restaura ConsultaComprobante.Comprobante ("REM Compra" → valor anterior). | — | Comprobante = "REM Compra"; TipoComp; ModTalonario. |
| **trz_trazabilidadComp** | Trazabilidad compras; usa oc_remp, cuentaproveedor, cuerpostockp. | No abre PRemito | — |
| **Serie_abm** | ABM de números de serie (alta/edición). | **vbModal** | Llamado desde ABMSerie_Click. |
| **Serie_carga** | Carga de series por renglón. | **vbModal** | Llamado desde ABMSerie_Click. |
| **form_espera** | Formulario de espera con barra de progreso durante Guardar. | Show + DoEvents | label_mje = "Espere por favor procesando datos...Generando comprobante"; ProgressBar.Value 25, 50. |
| **Principal** | Menú, permisos, Fecha, idUsuario, id_deposito, codSucursal, nombre_empresa, activ_proyecto, modifica_sucursal_comp, cambia_deposito, deposito_devol_nc, utiliza_embalaje, etc. | — | Global. |
| **IngresoUsuario** | Conexión a la base: `IngresoUsuario.Conex` usada en conn.ConnectionString. | — | — |
| **CargaComprobantesP** | Sucursal para StatusBar. | — | Sucursal. |

**Dependencias cíclicas:** Lista_Comp_Gral rellena PRemito.CuerpoStock y luego se cierra; PRemito no abre Lista_Comp_Gral de forma cíclica. ConsultaComprobante puede abrir PRemito con ModTalonario; al guardar PRemito modifica cuentaproveedor/stock y restablece ConsultaComprobante.Comprobante.

---

## 5. Contrato de persistencia (capa de datos)

*Fuente: búsqueda de .Execute, Recordset.Open, AddNew, Update, Delete, BeginTrans/CommitTrans/RollbackTrans en `PRemito.frm`. Versión desglosada: [ANALISIS_REMITOS_DE_COMPRA_PERSISTENCIA.md](ANALISIS_REMITOS_DE_COMPRA_PERSISTENCIA.md).*

| Operación / flujo | SQL / operación | Tablas/campos impactados | Transacción | Manejo de errores |
|-------------------|-----------------|---------------------------|-------------|-------------------|
| Lectura contador | rs_codmov.Open "SELECT * FROM codmov where codigo = 1" (~3443) | codmov (lectura) | No | — |
| **Transacción 1 (solo codmov)** | conn.BeginTrans; SET AUTOCOMMIT=0; rs_codmov.Open, contador+1, rs_codmov.Update; CommitTrans (~3438–3454) | codmov.CodigoMovimiento | Sí (transacción corta) | — |
| Lectura cabecera OC/remito/factura | SELECT * FROM cuentaproveedor WHERE CodigoMovimiento = ... (múltiples en Guardar) | cuentaproveedor (lectura) | No | — |
| Lectura renglones temporales | CuerpoStock.RecordSource = "SELECT * FROM cuerpostockp WHERE ..." (~4348, 4497, 4644, 7109); rs_cuerpostock.Open SELECT DISTINCT ... | cuerpostockp (lectura) | No | — |
| Borrar renglón temporal | conn.Execute "DELETE FROM cuerpostockp WHERE Orden = " & id_cuerpostock (~5255) | cuerpostockp.Orden | No (conn.Open sin transacción) | On Error GoTo captura; Principal.Guardar_Error; conn.Close |
| Limpieza series temporales | conn.Execute "DELETE serie_entrada_temp.* FROM serie_entrada_temp WHERE id_articulo = ... AND orden = ..." (~5260); id. "DELETE FROM serie_entrada_temp ..." (~6244) | serie_entrada_temp | No (Eliminar) / Sí (Elimina_Temporal dentro de flujo) | captura |
| **Transacción 2 (remito completo)** | conn.BeginTrans; SET AUTOCOMMIT=0 (~3458–3459) | — | Sí | On Error GoTo captura |
| Alta cabecera remito | rs_cuentaproveedor.Open "SELECT * FROM cuentaproveedor WHERE CodigoMovimiento = 1"; AddNew; Fields!Fecha, TipoComprobante="REM", NroComprobante, Codigo, CodigoMovimiento, ImporteCompra, Iva1/2/3, Percep*, Exento, etc.; Update (~3496–3591) | cuentaproveedor | Sí | RollbackTrans en captura (~4276) |
| Por cada renglón: stock | rs_stock.Open "SELECT * FROM stock where CodigoMovimiento = 1"; rs_stock.AddNew; Fields!Fecha, CodigoArticulo, Entrada, Cantidad, TipoComp="Remito Entrada", Comprobante="REM", CodDeposito, IDArt, NroRemito, codmov_remito, id_lote, etc. (~3612–3818) | stock | Sí | — |
| Por cada renglón: stock_deposito | rs_saldo_stock.Open SELECT stock_deposito WHERE id_articulo AND id_deposito; si RecordCount > 0: Update Saldo (y saldo_pedido_proveedor si nro_oc); si no: AddNew (~3628–3698) | stock_deposito.Saldo, saldo_pedido_proveedor | Sí | — |
| Lotes | rs_lote SELECT/Update o AddNew; rs_lotestock SELECT/Update o AddNew (~3852–3918) | lote, lote_stock | Sí | Si lote obligatorio faltante: MsgBox + RollbackTrans (~3826–3829) |
| Estado OC (cuentaproveedor) | rs_pedido.Open cuentaproveedor WHERE CodigoMovimiento = rs_cuerpostock!CodigoMovimiento; Fields!Estado = "En Remito" o "Parcial"; Update (~4105–4118) | cuentaproveedor.Estado | Sí | — |
| Vínculo remito–OC | rs_rem_ped.AddNew; codigo_movimiento_oc, codigo_movimiento_remp = contador, anulado = "No"; Update (~4121–4130) | oc_remp | Sí | — |
| Relación Remito–Factura | rs_rem_fact.AddNew; Codigo_MovimientoF, codigo_movimientor = contador, anulado; rs_factura UPDATE estado_fact_remito; rs_remito UPDATE estado_remito = "Facturado" (~4146–4205) | remp_factp, cuentaproveedor.estado_fact_remito, estado_remito | Sí | — |
| Series | conn.Execute "INSERT INTO serie_entrada ..."; conn.Execute "INSERT INTO serie_movimiento ..." (~6658, 6675) desde serie_entrada_temp | serie_entrada, serie_movimiento | Sí (dentro de misma transacción Guardar) | — |
| Commit / Rollback | conn.CommitTrans; conn.Close (~4225–4226) / captura: conn.RollbackTrans; conn.Close (~4275–4277) | — | Sí | Call Principal.Guardar_Error(Err.Description, Me.Caption, Err.Number) |
| modificacion_comp (solo talonario) | BeginTrans; UPDATE cuentaproveedor (Fecha, NroComprobante, Detalle, ID_Proyecto); UPDATE stock (Fecha, NroComprobante) por CodigoMovimiento del temporal; CommitTrans (~6381–6485) | cuentaproveedor, stock | Sí | RollbackTrans en captura (~6511) |

**Conexión VB6:** `conn.ConnectionString = IngresoUsuario.Conex`; `conn.CursorLocation = adUseClient`; `conn.Open` al inicio de Guardar y en otros puntos (Eliminar_Click, Inicial, Form_Load usa rs_depo con conn). Objeto global o de formulario `conn` (ADODB.Connection). En Synap usar el mismo patrón que en stock/compras: `core.mysql_pool` o `core.services.administranet_*` con `base_empresa` de sesión.

**Orden de escritura a replicar en Django (regla de oro):** 1) **Transacción 1:** UPDATE codmov (incrementar CodigoMovimiento); Commit. 2) **Transacción 2:** BeginTrans; INSERT cuentaproveedor (cabecera REM); por cada renglón: SELECT/UPDATE o AddNew stock_deposito (Saldo, saldo_pedido_proveedor si OC); AddNew stock (Comprobante='REM', TipoComp='Remito Entrada', Entrada, etc.); si lote: SELECT/INSERT/UPDATE lote y lote_stock; UPDATE cuentaproveedor (Estado) de OC si aplica; INSERT oc_remp (rs_rem_ped); INSERT remp_factp (rs_rem_fact) y UPDATE estado_remito/estado_fact_remito si aplica; GuardarSerie (INSERT serie_entrada, serie_movimiento); CommitTrans. En error: RollbackTrans.

---

## 6. Diseño Django 1:1 (estructura y responsabilidades)

**Estructura de archivos propuesta (mínima):**

| Ruta | Responsabilidad |
|------|-----------------|
| **compras/** (o **premito/** como submódulo de una app compras) | App Django para remitos de compra |
| compras/views.py | GET: formulario vacío o cargado desde OC/remito (por CodigoMovimiento o parámetro). POST: validar y llamar al servicio de guardado. Respuesta redirect o JSON si hay endpoints AJAX. |
| compras/forms.py | Form(s) para cabecera (proveedor, fecha, depósito, nro comprobante, estado, etc.) y validaciones. FormSet o estructura equivalente para renglones si se editan en servidor. |
| compras/services.py | Lógica del formulario: validaciones de negocio, construcción de INSERT/UPDATE en el mismo orden que VB6, uso de transacción única. Sin cambiar reglas de negocio. |
| core/services/administranet_compras.py (o compras/repository.py) | Acceso a datos: ejecutar SQL equivalente a VB6 (cuentaproveedor, codmov, cuerpostockp, stock, stock_deposito, oc_remp, serie_entrada, serie_entrada_temp, serie_movimiento, lote, lote_stock). Sin ORM que altere orden o forma de escritura. |
| compras/templates/compras/remito_compra_form.html | Vista principal: cabecera (inputs/selects) y renglones (tabla editable o grid). Botones Aceptar / Cancelar. |
| compras/urls.py | Rutas: listado (opcional), alta remito, edición/carga por CodigoMovimiento (si aplica). |

**Mapeo de eventos VB6 → Django:**

- Form_Load → vista GET + contexto (depósitos, período, proveedores, etc.).
- Aceptar_Click → vista POST o endpoint POST; validación en forms + services; persistencia en services/repository con transacción.
- Cambios de valor que afectan RecordSource o listas (Depósito, origen) → recarga de opciones vía GET o endpoint AJAX que devuelva JSON; replicar solo lo necesario para equivalencia 1:1.
- Eliminar renglón → endpoint POST que borre de cuerpostockp (y serie_entrada_temp) por Orden; respuesta con lista actualizada de renglones.

**Persistencia idéntica:** No migrar a ORM si cambia la forma de escribir. Usar cursor MySQL (core.mysql_pool) y ejecutar los mismos INSERT/UPDATE en el mismo orden que en el contrato de persistencia (sección 5). Transacción única con commit al final o rollback en excepción.

---

## 7. Plan por etapas (paralelismo VB6/Django) y checklist de pruebas espejo

**Etapas:**

1. **Preparación:** Mapeo completo (Fase 1 y 2) con código VB6 cuando esté disponible; entorno Synap con conectividad a la misma base AdministraNET; datos de prueba o fixtures si se definen (ej. una OC y un proveedor).
2. **Implementación Django 1:1:** UI (templates + forms) + lógica (views + services) + persistencia (queries equivalentes a VB6). No aplicar ítems del backlog (Fase 4).
3. **Validación de equivalencia:** Casos de prueba espejo (mismo dato de entrada que en VB6; comparar salida en DB: cuentaproveedor, stock, stock_deposito, oc_remp, series).
4. **Coexistencia:** Mismos datos y estados; evitar doble escritura (ej. no grabar dos veces el mismo remito desde VB6 y Synap); control de concurrencia si ambos sistemas operan sobre la misma OC/remito (ej. bloqueo optimista o mensaje al usuario).
5. **Criterios de salida:** Remito de compra generado desde Synap produce los mismos registros y valores en las tablas afectadas que PRemito.frm para el mismo caso de uso (misma OC, mismos renglones, mismo depósito).

**Checklist de pruebas espejo (a detallar cuando exista el código VB6):**

- [ ] Alta remito nuevo desde cero: cabecera + N renglones; comparar cuentaproveedor (1 fila), stock (N filas), stock_deposito (saldo actualizado), codmov (incrementado).
- [ ] Remito desde OC: cargar renglones desde OC; guardar; verificar oc_remp (vínculo codigo_movimiento_remp, codigo_movimiento_oc) y saldo_pedido_proveedor en stock_deposito.
- [ ] Renglón con serie: cantidad = número de series; verificar serie_entrada y serie_movimiento; limpieza de serie_entrada_temp.
- [ ] Renglón con lote: verificar lote y lote_stock (id_lote, cod_lote, vto_lote, cantidades).
- [ ] Eliminar renglón: DELETE cuerpostockp y serie_entrada_temp; no dejar huérfanos.
- [ ] Error en medio de transacción: rollback completo (no insertar cabecera sin renglones, o renglones sin cabecera).
- [ ] Depósito restringido por usuario: solo depósitos permitidos (deposito_usr) en lista.

---

## 8. Backlog (no implementar en fase 1:1)

### A) Mejoras UX (prioridad; riesgo: alto/medio/bajo)

| # | Problema (evento/control) | Impacto usuario | Propuesta (web-friendly) | Riesgo |
|---|---------------------------|------------------|--------------------------|--------|
| *A completar durante/después de Fase 1 con código VB6* | — | — | — | — |

### B) Optimizaciones técnicas (no cambiar resultados ni persistencia)

| # | Descripción | Impacto estimado | Condición |
|---|-------------|------------------|-----------|
| *A completar con código VB6* | — | — | — |

### C) Bugs y comportamientos anómalos (compatibilidad requerida si es esperado por usuarios)

| # | Descripción | Cómo reproducir | Severidad | ¿Compatibilidad requerida? |
|---|-------------|-----------------|-----------|----------------------------|
| *A completar con código VB6* | — | — | — | — |

---

## 9. Referencias

- **Código VB6:** `administranet_vb6/Formularios/PRemito.frm`, `PRemito.frx`; `Lista_Comp_Gral.frm`, `Visualiza_PRemito.frm`, `Visualiza_PRemitoC.frm`, `ConsultaComprobante.frm`, `trz_trazabilidadComp.frm`.
- [INVENTARIO_MIGRACION_FORMULARIOS.md](INVENTARIO_MIGRACION_FORMULARIOS.md)
- [ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md](ANALISIS_FORMULARIOS_STOCK_INVENTARIO_VB6.md)
- [INVENTARIO_FORMULARIO_MODIFICAR_USUARIO.md](INVENTARIO_FORMULARIO_MODIFICAR_USUARIO.md)
- [STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md](../self_checkout/STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md) (sección 2.6 PRemito)
- [INFO_COMPRA_TABLAS_CAMPOS.md](INFO_COMPRA_TABLAS_CAMPOS.md)
- Tablas: [cuerpostockp](tablas/cuerpostockp.md), [cuentaproveedor](tablas/cuentaproveedor.md), [oc_remp](tablas/oc_remp.md), [stock](tablas/stock.md), [stock_deposito](tablas/stock_deposito.md), [serie_entrada](tablas/serie_entrada.md), [serie_entrada_temp](tablas/serie_entrada_temp.md), [codmov](tablas/codmov.md), [deposito](tablas/deposito.md), [deposito_usr](tablas/deposito_usr.md), [conf_grilla_final_puesto](tablas/conf_grilla_final_puesto.md), [remp_factp](tablas/remp_factp.md), [lote](tablas/lote.md), [lote_stock](tablas/lote_stock.md), [serie_movimiento](tablas/serie_movimiento.md), [periodos](tablas/periodos.md), [years](tablas/years.md), [erp_proyecto](tablas/erp_proyecto.md), [proveedor](tablas/proveedor.md)
- [POLITICA_DOCUMENTACION.md](POLITICA_DOCUMENTACION.md)
