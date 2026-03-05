# Ingeniería inversa: CargaComprobantesP.frm (Facturas de Compra / NC / ND / Orden de Pago)

**Formulario raíz:** `administranet_vb6/Formularios/CargaComprobantesP.frm`  
**Caption:** " Facturas de Compra / Notas de Credito / Notas de Debito / Ordenes de Pago"  
**ID formulario:** FORM-001  

Documento generado por reverse engineering exhaustivo a partir del formulario raíz y de todos los artefactos vinculados. Trazabilidad mediante IDs (FORM-xxx, PROC-xxx, SQL-xxx).

---

## 1. Inventario de Archivos (top 30 relevantes + conteo total)

### 1.1 Conteo por tipo (proyecto administraNET, sin copias “ 3” ni “Copia Codigos”)

| Tipo | Extensión | Conteo aprox. | Rol |
|------|-----------|--------------|-----|
| Formularios | .frm | ~350+ | UI |
| Proyecto | .vbp | 1 | Raíz proyecto |
| Módulos | .bas | ~30+ | Lógica, utilidades |
| Clases | .cls | ~10+ | Lógica reutilizable |
| Recursos form | .frx | ~350+ | Binarios UI |
| Controles usuario | .ctl | 1+ | UI |
| **Total artefactos VB6/SQL considerados** | | **~1243** | |

### 1.2 Top 30 archivos relevantes para el flujo CargaComprobantesP

| ID | ruta_relativa | tipo | artefacto_id | rol_estimado |
|----|----------------|------|--------------|--------------|
| ARCH-001 | Formularios/CargaComprobantesP.frm | .frm | FORM-001 | UI, lista proveedores y menú comprobantes |
| ARCH-002 | Formularios/CargaComprobantesP.frx | .frx | FORM-001 | Recursos (iconos, imágenes) |
| ARCH-003 | Formularios/PFactura.frm | .frm | FORM-002 | UI Factura de Compra (FA/FB/FC) |
| ARCH-004 | Formularios/PPresupuesto.frm | .frm | FORM-003 | UI Presupuesto de Compra |
| ARCH-005 | Formularios/POrden_Compra.frm | .frm | FORM-004 | UI Orden de Compra |
| ARCH-006 | Formularios/PRemito.frm | .frm | FORM-005 | UI Remito de Compra |
| ARCH-007 | Formularios/PNotaCred.frm / PNotaCredDev | .frm | FORM-006 | UI NC Devolución |
| ARCH-008 | Formularios/PNotaCredDesc.frm | .frm | FORM-007 | UI NC Descuento |
| ARCH-009 | Formularios/PNotaCred_Importe.frm | .frm | FORM-008 | UI NC por importe/descuento factura |
| ARCH-010 | Formularios/PNotaDeb.frm | .frm | FORM-009 | UI Nota de Débito |
| ARCH-011 | Formularios/OrdenPago.frm | .frm | FORM-010 | UI Orden de Pago (a cuenta / por imputación) |
| ARCH-012 | Formularios/AsigPago.frm | .frm | FORM-011 | UI Imputación comprobantes a OP |
| ARCH-013 | Formularios/AsigPagoD.frm | .frm | FORM-012 | UI Desimputación comprobantes |
| ARCH-014 | Formularios/CuentaProveedor.frm | .frm | CtaCteProveedor | UI Cuenta Corriente Proveedor |
| ARCH-015 | Formularios/CargaProveedor.frm | .frm | CargaProveedor | UI ABM Proveedor (referencia en código: ABMProveedor) |
| ARCH-016 | Formularios/Lista_Confeccion_OC_Gral.frm | .frm | - | UI Lista soporte compras general (OC) |
| ARCH-017 | Formularios/Info_RepRapidos.frm | .frm | info_RepRapidos | Reportes rápidos / informes |
| ARCH-018 | Formularios/Principal.frm | .frm | Principal | MDI, sesión, Fecha, permisos, LimiteTotal, Guardar_Error |
| ARCH-019 | Formularios/IngresoUsuario.frm | .frm | IngresoUsuario | Conexión BD (Conex) |
| ARCH-020 | Modulos/Deshabilita_Cerrar.bas | .bas | Deshabilita_Cerrar | RemoveCancelMenuItem (user32) |
| ARCH-021 | administraNET.vbp | .vbp | - | Referencias: ADO 2.8, Crystal 11, MSXML3, FEAFIP, Office, etc. |
| ARCH-022 | Modulos/Funciones.bas | .bas | Funciones | Lógica compartida (si se usa desde este flujo) |
| ARCH-023 | Modulos/Informes.bas | .bas | Informes | Informes (si se usa desde este flujo) |
| ARCH-024 | Formularios/Proveedor.frm | .frm | Proveedor | Posible ABM maestro proveedor |
| ARCH-025 | Formularios/AnulaComp.frm | .frm | - | Anulación comprobantes (flujo alternativo) |
| ARCH-026 | Formularios/ConsultaComprobante.frm | .frm | - | Consulta comprobantes |
| ARCH-027 | Formularios/Lista_Comp_Gral.frm | .frm | - | Listado comprobantes general |
| ARCH-028 | Formularios/Visualiza_POrden_Compra.frm | .frm | - | Visualización Orden de Compra |
| ARCH-029 | Formularios/Visualiza_OrdenPago.frm | .frm | - | Visualización Orden de Pago |
| ARCH-030 | Formularios/Visualiza_PFactura.frm | .frm | - | Visualización Factura Compra |

**Componentes OCX/DLL referenciados en el formulario raíz:**  
senxpctl.dll (OsenXPCntrl), SmartMenuXP.ocx, MSADODC.OCX, todg8.ocx (TrueOleDBGrid80), MSDATLST.OCX, DBLIST32.OCX (DataCombo Sucursal). En el .vbp: Crystal Reports 11, ADO 2.8, FEAFIP, EASendMail, Office 15, etc.

---

## 2. Mapa de Pantallas y Navegación (desde formulario raíz)

### 2.1 Ficha Formulario Raíz (FORM-001)

| Campo | Valor |
|-------|--------|
| nombre_form | CargaComprobantesP |
| caption | Facturas de Compra / Notas de Credito / Notas de Debito / Ordenes de Pago (varía según modo de entrada) |
| controles_relevantes | MenuPrincipal (SmartMenuXP), GridTodos (TDBGrid, datasource DataProveedor), Busqueda (TextBox), tipo_busqueda (ComboBox), Actualizar (OsenXPButton), Sucursal (DataCombo), DataProveedor, DataTotal, DataSucursal, DataDescOP, DataFactTemp, DataOPFactura, FrameTitulo, FrameBusquedaCliente, Limite, TotalReg |
| eventos_clave | Form_Load, Inicial (público), Menu (construcción menú), MenuPrincipal_Click (dispatch por key), Actualizar_Click, Consulta_Busqueda, GridTodos_DblClick, GridTodos_HeadClick, Busqueda_Change, Busqueda_KeyPress, Cambio_Fuente_Formulario, Buscar_proveedor_Grilla |
| responsabilidad_funcional | Listado y búsqueda de proveedores; menú contextual para abrir distintos tipos de comprobantes de compra (Factura, NC, ND, Presupuesto, OC, Remito, OP) y acciones (Ver Cta Cte, Agregar Proveedor, Informes, Imputación/Desimputación). No persiste datos propios; delega en formularios hijos. |

### 2.2 Nodos (forms) y enlaces desde CargaComprobantesP

Todas las transiciones son por **MenuPrincipal_Click** (menú contextual) o **GridTodos_DblClick** (doble clic según caption). Previo a abrir, se validan: proveedor seleccionado (GridTodos.BOF), CAI proveedor no vencido, formularios conflictivos abiertos (Unload si usuario confirma).

| Origen | Acción / key | Destino | Condición / nota |
|--------|----------------|---------|------------------|
| FORM-001 | keySalir | Unload Me | Cierra CargaComprobantesP |
| FORM-001 | keyPre | PPresupuesto | Proveedor seleccionado; CAI vigente |
| FORM-001 | keyOC | POrden_Compra | idem; tipo_comp_vinculado = "PRE" |
| FORM-001 | keyOC_PEDI | POrden_Compra | idem; tipo_comp_vinculado = "PEDI"; LabelPed = "Ped. Interno" |
| FORM-001 | keyFact | PFactura | obliga_oc_carga_comp = No; según IDIVA empresa/proveedor: FA/FM/FC |
| FORM-001 | keyFactRem | PFactura/PRemito | Flujo Factura+Remito |
| FORM-001 | keyFactOC | PFactura / POrden_Compra | Factura contra OC |
| FORM-001 | keyFactVALE | PFactura | Factura contra Vale |
| FORM-001 | keyRem | PRemito | Remito de Compra |
| FORM-001 | keyNCDev | PNotaCredDev (NC Devolución) | - |
| FORM-001 | keyNCDesF | PNotaCred_Importe | NC Descuento en factura |
| FORM-001 | keyNCDesR | PNotaCredDesc | Exige descuentos en descuento_op_nc (Computado='No', importe>0) |
| FORM-001 | keyNCAnul | (Anulación NC) | Flujo anulación |
| FORM-001 | keyND | PNotaDeb | Nota de Débito |
| FORM-001 | keyPorimp | OrdenPago | OP por imputación; valida op_factura y fact_temporalp (bloqueo usuario) |
| FORM-001 | keyAcuenta | OrdenPago | OP a cuenta; valida fact_temporalp (bloqueo usuario) |
| FORM-001 | keyOP_OE | OrdenPago | Otros Egresos (cuenta corriente) |
| FORM-001 | keyAsignaPag | AsigPago | Imputación comprobantes; consulta op_factura (N/Canc, Saldo<>0, tipos OP/NC/AJC/INIC) y op_factura a cuenta (FA/FB/FC/ND/etc.) |
| FORM-001 | keyDesimputa | AsigPagoD | Desimputación |
| FORM-001 | keyVerCtaCte | CtaCteProveedor | Cuenta Corriente Proveedor |
| FORM-001 | keyABMProveedor | ABMProveedor * | Agregar Proveedor (* en código se usa ABMProveedor; en proyecto existe CargaProveedor.frm con VB_Name = "CargaProveedor") |
| FORM-001 | keyInfPago | info_RepRapidos | Informes rápidos (Accion = "FrmCargaComprobantesP") |
| FORM-001 | keyListaSoporteOC | Lista_Confeccion_OC_Gral | Solo si caption = " Orden de Compra" |

### 2.3 Diagrama de navegación (textual)

```
[Principal MDI] --> Load/Show CargaComprobantesP (caption según ítem menú)
                        |
                        +-- Salir --> Unload Me
                        +-- Comprobantes --> PPresupuesto | POrden_Compra | PFactura | PRemito | PNotaCred* | PNotaDeb | OrdenPago
                        +-- Acciones --> CtaCteProveedor | ABMProveedor | AsigPago | AsigPagoD
                        +-- Informes --> info_RepRapidos
                        +-- (solo OC) --> Lista_Confeccion_OC_Gral
```

---

## 3. Catálogo de Procedimientos/Funciones (por artefacto)

### 3.1 CargaComprobantesP.frm (FORM-001)

| procedimiento_id | nombre | tipo | visibilidad | parámetros | retorno | dependencias | efectos_datos |
|-----------------|--------|------|-------------|------------|---------|--------------|----------------|
| PROC-001 | Inicial | Sub | Public | - | - | Menu, Principal.LimiteTotal, IngresoUsuario.Conex, Principal.*, DataSucursal/DataProveedor/DataTotal, RemoveCancelMenuItem (no; se usa en Form_Load) | Lectura sucursales; asigna ConnectionString/RecordSource |
| PROC-002 | Menu | Sub | Private | - | - | MenuPrincipal.MenuItems, Principal.pGetPicture, CargaComprobantesP.Caption | Ninguno (arma menú) |
| PROC-003 | Actualizar_Click | Sub | Private | - | - | Consulta_Busqueda | SELECT proveedor/contribuyentes (via DataProveedor) |
| PROC-004 | Form_Load | Sub | Private | - | - | RemoveCancelMenuItem(Me), Cambio_Fuente_Formulario | Ninguno |
| PROC-005 | GridTodos_KeyPress | Sub | Private | KeyAscii As Integer | - | Busqueda.SetFocus | Ninguno |
| PROC-006 | MenuPrincipal_Click | Sub | Private | ID As Long | - | MenuPrincipal.MenuItems.key(ID), DataProveedor.Recordset, Principal.*, IngresoUsuario.Conex, conn (ADO), Unload/Show múltiples forms, Principal.Guardar_Error | Varios: RecordSource DataDescOP, DataFactTemp, DataOPFactura; rs_op_factura/rs_op_factura_acuenta (.Open); solo lectura en este form |
| PROC-007 | GridTodos_DblClick | Sub | Private | - | - | MenuPrincipal_Click (ID numérico según Caption) | Ninguno (dispara menú) |
| PROC-008 | Busqueda_Change | Sub | Private | - | - | Principal.tipo_busq, Consulta_Busqueda | Si Tipeo Directo: SELECT proveedor |
| PROC-009 | Busqueda_KeyPress | Sub | Private | KeyAscii As Integer | - | Consulta_Busqueda o GridTodos.SetFocus | Idem |
| PROC-010 | TipoFactura_KeyPress | Sub | Private | KeyAscii As Integer | - | GridTodos.SetFocus | Ninguno |
| PROC-011 | Consulta_Busqueda | Sub | Public | - | - | Principal.ver_proveedor_sucursal, DataProveedor, DataTotal, Busqueda.Text, tipo_busqueda, comodin1/comodin2, Principal.codSucursal, Principal.LimiteTotal | SELECT proveedor+contribuyentes; SELECT SQL_CALC_FOUND_ROWS Codigo FROM proveedor |
| PROC-012 | GridTodos_GotFocus | Sub | Private | - | - | GridTodos.MarqueeStyle | Ninguno |
| PROC-013 | Busqueda_GotFocus | Sub | Private | - | - | - | Ninguno |
| PROC-014 | GridTodos_HeadClick | Sub | Private | ColIndex As Integer | - | CampoClick, Ordenc, Consulta_Busqueda | Ordenación vía Consulta_Busqueda (opción Grid) |
| PROC-015 | Cambio_Fuente_Formulario | Sub | Private | - | - | Principal.fuente_tamano, Principal.fuente_nombre, Principal.tipo_boton_var, Principal.color_formulario_var | Ninguno |
| PROC-016 | Buscar_proveedor_Grilla | Sub | Public | strSearchCodigo As String | - | DataProveedor.Recordset.Find | Ninguno (navega recordset) |

### 3.2 Grafo de llamadas (caller → callee, motivo)

| caller | callee | motivo |
|--------|--------|--------|
| Form_Load | RemoveCancelMenuItem | Deshabilitar cerrar con X |
| Form_Load | Cambio_Fuente_Formulario | Aplicar fuentes/colores |
| Inicial | Menu | Construir menú contextual |
| Inicial | Principal.LimiteTotal, IngresoUsuario.Conex, Principal.* | Configuración y permisos |
| Actualizar_Click | Consulta_Busqueda | Refrescar lista proveedores |
| MenuPrincipal_Click | Principal.Guardar_Error | Manejo errores |
| MenuPrincipal_Click | Varios Form.Inicial / Form.Show / Unload | Navegación y apertura de comprobantes |
| GridTodos_DblClick | MenuPrincipal_Click | Simular ítem de menú por doble clic |
| Busqueda_Change | Consulta_Busqueda | Búsqueda en tiempo real (si Tipeo Directo) |
| Busqueda_KeyPress | Consulta_Busqueda o GridTodos.SetFocus | Enter: buscar o ir a grid |
| GridTodos_HeadClick | Consulta_Busqueda | Reordenar por columna |
| Consulta_Busqueda | DataProveedor.Refresh, DataTotal.Refresh | Ejecutar SQL y actualizar grid/conteo |

### 3.3 Módulo Deshabilita_Cerrar.bas

| procedimiento_id | nombre | tipo | visibilidad | parámetros | dependencias |
|-----------------|--------|------|-------------|------------|--------------|
| PROC-020 | RemoveCancelMenuItem | Sub | Public | frm As Form | user32 GetSystemMenu, RemoveMenu |

---

## 4. Mapa de Datos y CRUD (tablas, SP, SQL embebido, campos)

### 4.1 Inventario SQL (origen FORM-001)

| sql_id | origen (proc/control) | tipo | tablas | campos / filtros clave | CRUD | intención_funcional |
|--------|------------------------|------|--------|------------------------|------|---------------------|
| SQL-001 | Inicial (DataSucursal) | SELECT | sucursales | * ; ORDER BY nombre_sucursal | R | Listar sucursales (todas o una si no cambia_sucursal) |
| SQL-002 | Inicial (DataSucursal) | SELECT | sucursales | * ; WHERE id_sucursal = Principal.codSucursal | R | Filtrar sucursal del usuario |
| SQL-003 | Consulta_Busqueda (DataProveedor) | SELECT | proveedor, contribuyentes | obliga_oc_carga_comp, cod_ret_iva, id_cc, CodCatRet, CodCatRetG, Tipo, NroCAI, FechaCAI, CUIT, Codigo, Nombre, idIVA, IVA, saldo; proveedor.idIVA=contribuyentes.idIVA; Codigo<>1,2; estado='Activo'; (Codigo/Nombre/CUIT/id_manual_prov LIKE comodines); ORDER BY nombre,Codigo; LIMIT Principal.LimiteTotal; opcional: id_sucursal = Principal.codSucursal | R | Búsqueda proveedores para grid |
| SQL-004 | Consulta_Busqueda (DataTotal) | SELECT | proveedor | SQL_CALC_FOUND_ROWS Codigo | R | Conteo total para paginación (mismo filtro implícito) |
| SQL-005 | MenuPrincipal keyNCDesR (DataDescOP) | SELECT | descuento_op_nc | * ; CodProveedor = DataProveedor.Recordset.Fields!Codigo; Computado='No'; importe>0 | R | Validar si hay descuentos para NC descuento |
| SQL-006 | MenuPrincipal keyPorimp/keyAcuenta (DataFactTemp) | SELECT | fact_temporalp, usuarios | fact_temporalp.*, usuarios.id_usuario, cod_usuario AS codigo_usuario; fact_temporalp.Codusuario=usuarios.id_usuario; fact_temporalp.Codigo=proveedor; fact_temporalp.visualiza='No'; Codusuario<>Principal.idUsuario | R | Bloqueo: otro usuario cargando OP mismo proveedor |
| SQL-007 | MenuPrincipal keyPorimp (DataOPFactura) | SELECT | op_factura | * ; Codigo=proveedor; Estado='N/Canc'; TipoComprobante IN ('FA','FB','FC','FM','ND','INIC','INID','AJD','AJC'); Anulado='No'; ORDER BY NroComprobante | R | Facturas pendientes para imputar en OP |
| SQL-008 | MenuPrincipal keyAsignaPag (rs_op_factura) | SELECT | op_factura | * ; Codigo=proveedor; Estado='N/Canc'; Saldo<>0; TipoComprobante IN ('OP','NC','AJC','INIC'); Anulado='No' | R | Comprobantes a cuenta para imputación |
| SQL-009 | MenuPrincipal keyAsignaPag (rs_op_factura_acuenta) | SELECT | op_factura | * ; Codigo=proveedor; Estado='N/Canc'; Saldo<>0; TipoComprobante IN ('FA','FB','FC','FM','ND','AJD','INID'); Anulado='No' | R | Facturas/ND para imputar en OP |
| SQL-010 | Buscar_proveedor_Grilla | Recordset.Find | (recordset ya abierto) | codigo = strSearchCodigo | R | Posicionar en proveedor por código (riesgo: strSearchCodigo sin escapar en Find) |

**Riesgo SQL injection (legacy):** En SQL-003 a SQL-009 se usan concatenaciones con `DataProveedor.Recordset.Fields!Codigo`, `Principal.codSucursal`, `Principal.idUsuario`, `Busqueda.Text`. Si algún valor llegara desde usuario sin validar, podría ser vulnerable. En Buscar_proveedor_Grilla el criterio `"codigo = '" & strSearchCodigo & "'"` es vulnerable si strSearchCodigo contiene comillas.

### 4.2 Modelo de datos inferido (entidades y relaciones)

- **proveedor:** Codigo (PK), Nombre, CUIT, idIVA, NroCAI, FechaCAI, estado, id_cc, id_sucursal, obliga_oc_carga_comp, cod_ret_iva, CodCatRet, CodCatRetG, Tipo, saldo, telefonotrabajo, email, whatsapp_empresa, id_manual_prov. Relación: contribuyentes.idIVA = proveedor.idIVA.
- **contribuyentes:** idIVA, IVA (alias usado en SELECT).
- **sucursales:** id_sucursal, nombre_sucursal.
- **descuento_op_nc:** CodProveedor, Computado, importe (para NC por descuento).
- **fact_temporalp:** Codigo (proveedor), Codusuario, visualiza (bloqueo multiusuario OP).
- **op_factura:** Codigo (proveedor), Estado, Saldo, TipoComprobante, NroComprobante, Anulado (cuentas corrientes e imputación).
- **usuarios:** id_usuario, cod_usuario (para fact_temporalp y permisos).

### 4.3 Matriz CRUD por pantalla/proceso (FORM-001)

| Pantalla / proceso | Tablas | C | R | U | D |
|-------------------|--------|---|---|---|---|
| CargaComprobantesP (lista/búsqueda) | proveedor, contribuyentes, sucursales | - | X | - | - |
| CargaComprobantesP (keyNCDesR) | descuento_op_nc | - | X | - | - |
| CargaComprobantesP (keyPorimp/keyAcuenta) | fact_temporalp, usuarios | - | X | - | - |
| CargaComprobantesP (keyPorimp) | op_factura | - | X | - | - |
| CargaComprobantesP (keyAsignaPag) | op_factura | - | X | - | - |

(La persistencia de comprobantes y movimientos está en los formularios hijos: PFactura, POrden_Compra, OrdenPago, etc.)

---

## 5. Flujo funcional completo (paso a paso + alternativos)

### 5.1 Flujo BPMN textual (Facturas de Compra / Comprobantes Proveedor)

1. **Inicio:** Usuario abre CargaComprobantesP desde Principal (según ítem menú: Factura de Compra, NC/ND, Orden de Pago, etc.). Caption del form puede ser " Factura de Compra", " Orden de Pago", " Nota de Crédito / Nota de Débito - Proveedores", etc.
2. **Form_Load:** RemoveCancelMenuItem(Me), Cambio_Fuente_Formulario.
3. **Inicial (llamado desde Principal o al mostrar):** Conexiones DataProveedor/DataTotal con IngresoUsuario.Conex; carga menú (Menu); configura GridTodos; carga combo Sucursal (SELECT sucursales según permiso Principal.cambia_sucursal); tipo_busqueda por defecto; Opcion_Busqueda = "Normal".
4. **Búsqueda:** Usuario escribe en Busqueda (y opcionalmente elige tipo_busqueda: Comienza con / Finaliza con / Incluye texto). Según Principal.tipo_busq (Tipeo Directo / Tipeo Enter), Consulta_Busqueda se ejecuta al cambiar texto o al pulsar Enter. Consulta_Busqueda arma SELECT a proveedor+contribuyentes con filtro por sucursal (si aplica) y LIMIT; asigna a DataProveedor/DataTotal y refresca grid. Si no hay registros, FrameTitulo.Visible = True.
5. **Selección de proveedor:** Usuario selecciona fila en GridTodos (o doble clic). DataProveedor.Recordset tiene el proveedor actual (Codigo, Nombre, NroCAI, FechaCAI, id_cc, IDIVA, obliga_oc_carga_comp, etc.).
6. **Decisión menú:** Usuario elige ítem del menú (o doble clic según caption).
   - **keySalir:** Unload Me.
   - **keyPre / keyOC / keyOC_PEDI / keyFact / keyFactRem / keyFactOC / keyFactVALE / keyRem:** Validar GridTodos no BOF; validar CAI no vencido (FechaCAI >= FechaActual); opcionalmente validar obliga_oc_carga_comp para keyFact. Comprobar si ya está abierto PPresupuesto, POrden_Compra, PFactura, PRemito, PNotaCredDev (y según caso PNotaCredDesc, PNotaCred_Importe, PNotaDeb, OrdenPago): si está abierto, preguntar y Unload. Asignar variables públicas del form destino (id_proveedor, nombre_proveedor, id_cc, Tipo_Factura según IDIVA, id_sucursal si permiso), luego Inicial y Show del form hijo.
   - **keyNCDev / keyNCDesF / keyNCAnul:** Similar; para keyNCDesR además ejecutar SQL-005 (descuento_op_nc) y si RecordCount=0 mostrar "No existen descuentos...".
   - **keyND:** Abrir PNotaDeb con validaciones análogas.
   - **keyPorimp:** Validar fact_temporalp (SQL-006) para evitar dos usuarios OP mismo proveedor; validar que no estén abiertos AsigPago/AsigPagoD; DataOPFactura (SQL-007); si hay facturas, abrir OrdenPago (Tipo_OP = "Imputacion").
   - **keyAcuenta:** Validar fact_temporalp (SQL-006); abrir OrdenPago (Tipo_OP = "A cuenta", TabOP.ActiveTab = 2).
   - **keyOP_OE:** OrdenPago para Otros Egresos.
   - **keyAsignaPag:** Abrir conn; rs_op_factura (SQL-008) y rs_op_factura_acuenta (SQL-009); si ambos tienen registros, AsigPago.Inicial y AsigPago.Show; si no, MsgBox "No existen facturas para imputar...".
   - **keyDesimputa:** Validar que no estén abiertos AsigPago/OrdenPago; AsigPagoD.Inicial y Show.
   - **keyVerCtaCte:** CtaCteProveedor.Nombre/Codigo desde DataProveedor; Inicial y Show.
   - **keyABMProveedor:** ABMProveedor.Inicial y Show (nota: nombre de form puede ser CargaProveedor en proyecto).
   - **keyInfPago:** info_RepRapidos (Accion = "FrmCargaComprobantesP"), Show.
   - **keyListaSoporteOC:** Lista_Confeccion_OC_Gral.Show.
7. **Error en cualquier paso:** captura → Principal.Guardar_Error(Err.Description, Me.Caption, Err.Number); si conn.State=1, conn.Close.

### 5.2 Casos de uso

- **CU-01 (Principal):** Usuario abre lista de proveedores, busca por código/nombre/CUIT, selecciona un proveedor y abre un comprobante (Factura, NC, ND, Presupuesto, OC, Remito, OP). El formulario hijo recibe proveedor y tipo de comprobante y gestiona el alta/edición.
- **CU-02 (Alternativo):** Usuario sin permiso mult sucursal ve solo proveedores de su sucursal (id_sucursal = Principal.codSucursal).
- **CU-03 (Alternativo):** Usuario con permiso modifica_sucursal_comp puede cambiar Sucursal antes de abrir el comprobante; el form hijo recibe id_sucursal.
- **CU-04 (Alternativo):** Proveedor con obliga_oc_carga_comp = "Si" no puede abrir Factura de Compra sin OC asociada; se muestra mensaje y no se abre PFactura.
- **CU-05 (Alternativo):** CAI del proveedor vencido → mensaje y no se abre comprobante fiscal.
- **CU-06 (Alternativo):** Otro usuario está cargando OP del mismo proveedor (fact_temporalp) → mensaje y no se abre OrdenPago.
- **CU-07 (Alternativo):** Sin facturas para imputar (DataOPFactura.RecordCount=0) → mensaje y no se abre OrdenPago por imputación.
- **CU-08 (Alternativo):** Sin descuentos para NC descuento (DataDescOP.RecordCount=0) → mensaje y no se abre PNotaCredDesc.
- **CU-09 (Alternativo):** Ordenar por columna: HeadClick en GridTodos → Opcion_Busqueda = "Grid", Consulta_Busqueda (mismo SQL con orden por CampoClick/Ordenc).
- **CU-10 (Alternativo):** Llamada externa a Buscar_proveedor_Grilla(strSearchCodigo) para posicionar en un proveedor por código (ej. desde otro form).

---

## 6. Checklist de migración a Django (componentes, riesgos, pendientes)

### 6.1 Componentes sugeridos Django

| Componente | Descripción |
|------------|-------------|
| **Views (endpoints/pantallas)** | Listado y búsqueda de proveedores (filtros por sucursal, texto, tipo búsqueda); redirección o SPA a vistas de cada comprobante (factura compra, NC, ND, presupuesto, OC, remito, OP). Endpoints para: lista proveedores, detalle proveedor (para prellenar), abrir formulario de comprobante. |
| **Services** | ProveedorSearchService (criterios, sucursal, límite, orden); permisos (cambia_sucursal, modifica_sucursal_comp, obliga_oc_carga_comp, ver_proveedor_sucursal); validaciones CAI y fact_temporalp (bloqueo OP); reglas de tipo de factura (FA/FB/FC) según IDIVA. |
| **Repositories** | ProveedorRepository (listado con joins contribuyentes, filtros, paginación); SucursalRepository; DescuentoOPNCRepository; OpFacturaRepository (lectura para imputación); FactTemporalPRepository (lectura para bloqueo). |
| **Models** | Proveedor, Contribuyente, Sucursal, DescuentoOPNC, OpFactura, FactTemporalP, Usuario (alineados a tablas existentes MySQL). |
| **Serializers/Forms** | ProveedorListSerializer (campos para grid); filtros de búsqueda (texto, tipo búsqueda, sucursal). Formularios de comprobantes en sus respectivos módulos (no en este documento). |

### 6.2 Lista de bloques migrables y prioridad

| Prioridad | Bloque | Descripción |
|-----------|--------|-------------|
| **Alta** | Búsqueda y listado proveedores | Consulta_Busqueda + filtros sucursal y permisos; paginación (LimiteTotal). |
| **Alta** | Validaciones antes de abrir comprobante | CAI vigente, obliga_oc_carga_comp, fact_temporalp (bloqueo OP), existencia de facturas para imputar / descuentos para NC. |
| **Alta** | Reglas tipo comprobante (FA/FB/FC) y tipo OP | Según IDIVA proveedor y empresa; Tipo_OP (Imputacion / A cuenta / Otros Egresos). |
| **Media** | Navegación a formularios hijos | Reemplazar Show/Unload por rutas front (SPA o multi-página) y estado (proveedor seleccionado, tipo de comprobante). |
| **Media** | Menú contextual / shortcuts | Recrear como acciones en UI (botones o menú) con las mismas claves lógicas (keyPre, keyFact, etc.). |
| **Media** | Permisos y sucursal | Principal.cambia_sucursal, modifica_sucursal_comp, ver_proveedor_sucursal; combo Sucursal. |
| **Baja** | Cambio_Fuente_Formulario | Tema/fuentes desde configuración; no crítico para funcionalidad. |
| **Baja** | RemoveCancelMenuItem | En web no aplica; cierre por navegación o botón. |
| **Baja** | Controles OCX (Grid, DataCombo, SmartMenuXP) | Sustituir por componentes web (tabla, select, menú). |

### 6.3 Riesgos y ambigüedades

| ID | Riesgo / ambigüedad | Hipótesis / acción |
|----|---------------------|----------------------|
| R-01 | **ABMProveedor** referenciado en código; en .vbp solo existe CargaProveedor.frm (VB_Name = "CargaProveedor") | Verificar en tiempo de ejecución qué form se muestra con keyABMProveedor; si es el mismo CargaProveedor, puede haber alias o error de nombre en código. |
| R-02 | **Traidos** usado en Inicial (Traidos = Principal.LimiteTotal); no definido en este form | Variable global o en Principal; al migrar usar mismo límite de paginación desde configuración/sesión. |
| R-03 | **SQL con concatenación** (Busqueda.Text, Codigo, idUsuario, codSucursal) | Parametrizar todas las consultas en Django; no construir SQL por concatenación. |
| R-04 | **Buscar_proveedor_Grilla(strSearchCodigo)** con Find "codigo = '" & strSearchCodigo & "'" | Riesgo de inyección y de fallo si strSearchCodigo tiene comillas; en Django filtrar por código con parámetro. |
| R-05 | **Ordenación en Consulta_Busqueda** por CampoClick/Ordenc | CampoClick se setea en GridTodos_HeadClick; el SQL actual no muestra ORDER BY dinámico en los fragmentos leídos (solo "order by nombre,Codigo Limit"). Verificar en código completo si se añade ORDER BY por columna. |
| R-06 | **SQL_CALC_FOUND_ROWS** en DataTotal | MySQL; en Django equivalente con count() o paginación con total. |
| R-07 | **Formularios hijos** (PFactura, OrdenPago, AsigPago, etc.) | Este documento no incluye su flujo interno; cada uno debe tener su propio inventario y mapa de datos para migración completa. |
| R-08 | **conn (ADODB.Connection)** usado en keyAsignaPag para rs_op_factura y rs_op_factura_acuenta | Reemplazar por conexión Django/ORM y transacciones; cerrar correctamente en todos los caminos. |

### 6.4 Pendientes (trazabilidad)

- [ ] Confirmar nombre real del form "Agregar Proveedor" (ABMProveedor vs CargaProveedor).
- [ ] Extraer en formularios hijos (PFactura, POrden_Compra, OrdenPago, AsigPago, AsigPagoD, PNotaCred*, PNotaDeb) procedimientos y SQL para CRUD completo.
- [ ] Documentar uso de Traidos y LimiteTotal (Principal o módulo global).
- [ ] Revisar si Consulta_Busqueda aplica ORDER BY por columna al cambiar GridTodos_HeadClick (orden ascendente/descendente).
- [ ] Definir en Synap permisos equivalentes a cambia_sucursal, modifica_sucursal_comp, ver_proveedor_sucursal, modifica_oc_presupuesto.
- [ ] Catálogo de tipos de comprobante (FA, FB, FC, NC, ND, OP, etc.) y relación con IDIVA (contribuyentes) para reglas de negocio.

---

**Referencias:**  
- Plan de migración: `docs/general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md`  
- Metodología inventario: `docs/general/INVENTARIO_MIGRACION_FORMULARIOS.md`  
- Tipos de datos AdministraNET: `docs/general/TIPOS_DATOS_ADMINISTRANET.md`
