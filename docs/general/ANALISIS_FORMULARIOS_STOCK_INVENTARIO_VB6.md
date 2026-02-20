# Análisis en profundidad: formularios de stock/inventario (AdministraNET VB6)

**Objetivo:** Inventariar formularios, funciones, procedimientos y procesos del módulo stock/inventario, con foco en **CargaMovStock** y sus formularios vinculantes.

**Referencia:** `administranet_vb6/Formularios/` (CargaMovStock.frm, CargaMovStock.frx y vinculados).

---

## 1. Inventario de formularios stock/inventario

| Formulario | Descripción / Uso |
|------------|--------------------|
| **CargaMovStock.frm** | Alta de movimiento de stock (cabecera + renglones temporales → stock, movimiento_stock, lote, asiento contable). Formulario central. |
| **CargaMovStock.frx** | Recursos binarios del formulario (iconos, imágenes, datos embebidos de controles). |
| **Visualiza_CargaMovStock.frm** | Visualización/consulta de movimientos de stock; repite lógica de guardado (stock, stock_deposito, lote, transferencia). |
| **Visualiza_CargaMovStock_Copia.frm** | Copia/alternativa del visualizador. |
| **CargaRef_movstock.frm** | Alta de referencia de movimiento de stock (tabla `ref_movstock`: nombre, anulado). |
| **ABMref_movstock.frm** | ABM de referencias de movimiento de stock (lista + búsqueda; DataSource `dataRmovstock` → `ref_movstock`). |
| **Stock.frm** | Consulta de stock (por artículo, depósito, fechas); no alta de movimientos. |
| **Stock_Control.frm** | Control de stock. |
| **Stock_Control_Entrada.frm** | Entrada de stock (control). |
| **stock_consulta_avanzada.frm** | Búsqueda avanzada de stock; puede abrir **CargaMovStock** con `Proceso_Llamante = "Stock_Consulta_Avanzada"` para ajuste desde saldo. |
| **Info_Stock.frm** | Información de stock. |
| **Serie_fstock_visualiza.frm** | Visualización de series en stock. |
| **Inventario.frm** | Formulario de inventario (nombre genérico). |

**Formularios que abren o referencian CargaMovStock:**

- **AltaArticulo.frm:** Si `Accion = "CargaMovStock"`, rellena artículo, depósito, motivo, lote y abre CargaMovStock.
- **Lista_Pedidos_OPT.frm:** Rellena `CuerpoStock` con renglones desde pedidos OPT (motivos 10 = Pedido producción, 11 = Parte producción); asigna DepositoOrigen/DepositoDestino según motivo.
- **stock_consulta_avanzada.frm:** Asigna `CargaMovStock.Proceso_Llamante = "Stock_Consulta_Avanzada"`, llama `CargaMovStock.Inicial` y `CargaMovStock.Show` (para ajuste desde consulta).
- **Cont_AbmEjercicio:** `Accion = "CargaMovStock"` para selección de ejercicio/periodo contable.
- **Erp_ABM_Proyecto:** `Accion = "CargaMovStock"` para elegir proyecto.
- **ABMCliente:** `Accion = "CargaMovStock"` para elegir cliente/entidad.
- **En_abm, ABMArticulo_seleccion, ABMArticulo_seleccion_simple:** Apertura de CargaMovStock para selección de artículo.

---

## 2. CargaMovStock.frm – Análisis detallado

### 2.1 Controles y datos (desde .frm y código)

- **Data controls (ADODC):**
  - **CuerpoStock:** RecordSource asignado en runtime a tabla temporal `cuerpostock_mstock` (filtro por `Codusuario`, `visualiza = 'No'`, `CodigoMovimiento = 1` para alta). Es el “carro” de renglones antes de grabar.
  - **DataDepositoO / DataDepositoD:** Depósitos origen y destino (desde `deposito` y opcionalmente `deposito_usr` si el usuario tiene depósitos restringidos).
  - **data_ref_movstock:** Referencia de movimiento (`ref_movstock`); según permiso `acceso_ref_movstock` trae “Todos” o solo `id_refmovstock` del puesto.
  - **DataLote:** Lotes (para artículos con lote); RecordSource sobre `lote`/`lote_stock` según depósito.
  - **data_entidad:** Cliente (para Mov. Interno Salida / entidad).
  - **dataVendedor:** Viajantes (operario/máquina en Frame_Datos_OPT).
  - **DataPartida:** Partida contable (si aplica).
- **Combo Motivo:** Carga en `Inicial()` según permiso `acceso_motivo_movstock` (si "Todos"): Stock Inicial, Ajuste, Faltante, Sobrante, Rotura, Transferencia, Mov. Interno Salida/Entrada, Armado, Desarmado; si `pedidos_parte_produccion = "Si"` agrega "Pedido producción" (10) y "Parte producción" (11).
- **Grid:** GridArticulos enlazado a CuerpoStock (renglones temporales).
- **Frame_Datos_OPT:** Visible para motivos OPT/OPP; TDBCombo operario, Lista_Maquina, etc.

### 2.2 Tablas implicadas (orden lógico del proceso)

| Tabla | Uso en CargaMovStock |
|-------|------------------------|
| **cuerpostock_mstock** | Tabla temporal por usuario: renglones en edición (Orden, IDArt, CodigoArticulo, Descripcion, Cantidad, Entrada/Salida, ES, PrecioCostoxU/R, Alicuota, TipoIVA, id_lote, cod_lote, vto_lote, serie, etc.). Se limpia con `Elimina_Temporal` (y serie_entrada_temp/serie_salida_temp para Mstock). |
| **codmov** | Contador global de movimientos (CodigoMovimiento); se incrementa en Aceptar. |
| **talonarios** | Numeración de comprobante MSTOCK (id_punto_venta, TipoComprobante = 'MSTOCK'). |
| **stock** | Tabla definitiva de movimientos: por cada renglón de CuerpoStock se hace AddNew en `stock` (CodigoMovimiento, Fecha, artículo, cantidades, Entrada/Salida, Saldo, CodDeposito, id_ref_movstock, lote, serie, etc.). |
| **stock_deposito** | Saldo por artículo y depósito; se actualiza (Saldo) o se inserta si no existe. |
| **movimiento_stock** | Cabecera del movimiento: codigo_movimiento, nro_comprobante, Fecha, motivo_movimiento, Detalle, deposito_origen/destino, id_usuario, id_ref_movstock, tipo_comprobante = "MSTOCK", ID_Proyecto, id_cliente, id_vendedor, tipo_mov OPT/OPP, etc. |
| **lote** | Alta/actualización de lotes (cod_lote, fecha_vto_lote, stock_total_lote, id_articulo, id_proveedor). |
| **lote_stock** | Stock por lote y depósito; se actualiza o se inserta en salidas/entradas con lote. |
| **ref_movstock** | Catálogo de referencias; solo lectura en CargaMovStock (combo Referencia). |
| **lista_produccion_agrupada / lista_produccion_historico** | Para motivo 10 (Pedido producción) y 11 (Parte producción): pendientes y historial. |
| **stockp** | Para motivo 11: cantidad_fab_pendiente_opt. |
| **movstock_pedi** | Relación movimiento de stock ↔ pedido interno (comp_ped). |
| **comp_ped** | Estado "Completo" cuando se asocia mov stock a pedido interno. |
| **serie_entrada_temp / serie_salida_temp** | Temporales de números de serie por usuario y tipo Mstock. |
| **conf_grilla_final_puesto** | Configuración de columnas visibles/orden de la grilla (nombre_grilla = 'Grilla Mov Stock'). |
| **deposito_usr** | Restricción de depósitos por usuario si no hay permiso total. |

### 2.3 Procedimientos y funciones clave (CargaMovStock)

| Procedimiento / Función | Descripción |
|-------------------------|-------------|
| **Inicial()** | Menu, Elimina_Temporal, fecha, depósitos (según cambia_deposito y deposito_usr), ref_movstock (según acceso_ref_movstock), lista Motivo (según acceso_motivo_movstock y pedidos_parte_produccion), conf grilla, mov_stock_utiliza_cbarra, Proceso_Llamante Stock_Consulta_Avanzada. |
| **Form_Load** | Frames lote ocultos, data_entidad, dataVendedor, StatusBar, opciones bulto/display, pedidos_parte_produccion (cantidad_armado), Cambio_Fuente_Formulario. |
| **Aceptar_Click** | Validación ESerie/ValCantSerie; confirmación; transacción: codmov, talonarios, por cada renglón CuerpoStock → stock + stock_deposito + lote/lote_stock si aplica; movimiento_stock (cabecera); movstock_pedi si hay nro_pedi; GuardarSerie; generar_asiento_cont si activ_contabilidad; impresión comp_mov_stock.rpt; Elimina_Temporal implícito vía CuerpoStock.RecordSource; si Proceso_Llamante = Stock_Consulta_Avanzada recarga esa consulta; si no, CargaMovStock.Show + Inicial y visualiza_asiento_cont. |
| **AgregarRenglon_Click** | Validaciones (artículo, cantidad, ES, depósito destino si transferencia/ensamble/desarme, lote); para Ensamble/Desarme llama ensamble_desarme; sino AddNew en CuerpoStock (cuerpostock_mstock) con IDArt, CodigoArticulo, Descripcion, Cantidad, Entrada/Salida, PrecioCostoxU, etc.; CalculoTotales. |
| **Elimina_Temporal** | DELETE cuerpostock_mstock para el usuario y visualiza='No'; DELETE serie_entrada_temp/serie_salida_temp para Mstock. |
| **CalculoTotales** | Refresca CuerpoStock y GridArticulos. |
| **Motivo_Click** | Permiso por motivo (Permiso_Motivo_Puesto), visibilidad DepositoDestino (Es_Transferencia / No_Es_Transferencia), visibilidad frame_lote/Lote según tipo de movimiento, Frame_Datos_OPT para motivo 10/11. |
| **Permiso_Motivo_Puesto** | Restringe motivos según permiso del puesto. |
| **MstockE / MstockS** | Lógica de entrada/salida de stock (ensamble/desarme) a nivel detalle. |
| **Lote_ed** | Edición de lote (salida): descuenta stock_lote. |
| **generar_asiento_cont** | Genera asiento contable según motivo (excluye Ajuste por decisión); usa IdEjer, IdPer (Cont_AbmEjercicio si selec_ejer_per_cont). |
| **visualiza_asiento_cont** | Muestra asiento generado. |
| **busqueda_articulo / busqueda_articulo_ensamble** | Búsqueda de artículo (y para ensamble/desarme). |
| **ensamble_desarme** | Alta de renglones para Armado/Desarmado (fórmula, insumos, productos). |
| **GuardarSerie** | Graba series (serie_entrada/serie_salida) desde temporales. |
| **ValCantSerie / ESerie / EsSerie** | Validación de cantidad vs números de serie. |
| **EliminarRenglon_Click / eliminarRenglonSerie** | Borra renglón de cuerpostock_mstock (por Orden). |
| **ModificarRenglon_Click** | Carga renglón en controles para edición (mod_renglon = "Si"). |
| **ListaArticulos_Click** | Abre ABMArticulo_seleccion o ABMArticulo_seleccion_simple con Accion = CargaMovStock. |
| **Busca_PEDI_Click** | Lista pedidos internos (comp_ped + movimiento_stock) para asociar. |
| **Lista_Proyecto_Click** | Valida que existan proyectos en curso; abre Erp_ABM_Proyecto (Accion = CargaMovStock). El usuario elige un proyecto y se asigna ID_Proyecto y nombre_proyecto. Origen: erp_proyecto (id_proyecto <> 1, estado_proyecto = 'En curso') con LEFT JOIN erp_zona y cliente. |
| **Cancelar** | Elimina_Temporal, Unload Me. |

### 2.3.1 Eventos declarados en CargaMovStock y estado en Synap

Inventario de todos los eventos (y procedimientos llamados desde ellos) del formulario VB6 y si están replicados en Synap (Ingreso Mov. Stock). Leyenda: **Sí** = implementado; **Parcial** = parte de la lógica; **No** = no implementado.

#### Eventos de botón / acción principal

| Evento VB6 | Descripción breve | Synap |
|------------|-------------------|--------|
| **Aceptar_Click** | Confirmación, transacción (codmov, talonarios, stock, stock_deposito, movimiento_stock, movstock_pedi, series), asiento contable, impresión, limpieza temporal. | **Sí** (confirmarMovimiento; sin asiento, impresión ni movstock_pedi persistido) |
| **AgregarRenglon_Click** | Validaciones (artículo, cantidad, ES, depósito destino, lote); ensamble_desarme si Armado/Desarmado; AddNew en CuerpoStock; CalculoTotales. | **Sí** (agregarRenglon; sin ensamble_desarme ni lote) |
| **AgregarRenglonSerie** | Alta de renglón con manejo de números de serie (serie_entrada_temp/serie_salida_temp). | **Sí** (renglones con serie_articulo='Si' usan columna Series + modal; agregar/quitar en temp) |
| **Busca_PEDI_Click** | Lista pedidos PEDI o PED según motivo; abre Lista_Comp_Gral o Lista_Pedidos_OPT. | **Sí** (modal lista pedidos pendientes + API) |
| **Cancelar_Click** | Elimina_Temporal, Unload. | **Sí** (enlace Cancelar a dashboard; backend limpia temporal al confirmar) |
| **EliminarRenglon_Click** | Borra renglón de cuerpostock_mstock por Orden. | **Sí** (quitarRenglon) |
| **eliminarRenglonSerie** | Borra renglón y series asociadas en temporales. | **Parcial** (al quitar renglón se borra cuerpo; series temp se limpian al confirmar movimiento) |
| **Lista_Proyecto_Click** | Valida proyectos en curso; abre Erp_ABM_Proyecto. | **Sí** (modal lista proyectos + API) |
| **ListaArticulos_Click** | Abre ABMArticulo_seleccion con Accion = CargaMovStock. | **Parcial** (búsqueda predictiva en línea, no ventana aparte) |
| **ModificarRenglon_Click** | Carga renglón en controles para edición (mod_renglon). | **Sí** (iniciarEdicion / guardarRenglon inline) |
| **ABMSerie_Click** | Abre gestión de números de serie para el renglón. | **Sí** (columna Series + botón layers → modal Números de serie; entrada: nro_serie/vto_serie; salida: elegir de series disponibles) |
| **btnBuscaCli_Click** | Abre ABMCliente (buscar cliente para Mov. Interno). | **No** (no hay campo Cliente en Synap) |
| **cantidad_armado_Click** | Lógica asociada a cantidad armado (OPT/OPP). | **Sí** (select Cantidad armado: Unidad/Armado cuando pedidos_parte_produccion = Si y motivo Parte producción (12); valor en cabecera; conversión Cantidad/cantidad_armada_opt por fórmula pendiente de ensamble_desarme) |
| **lista_unidad_art_peso_Click** | Abre Carga_Unidad_Peso para unidad de peso. | **Sí** (columna Peso + input por renglón y botón «lista» que abre modal Ingresar peso; visible cuando usa_multiplica_bulto_promedio = Si y tipo_balanza = Bascula; persistencia unidad_art_peso) |
| **MenuPrincipal_Click** | Dispatcher del menú contextual (Busca_PEDI, ModificarRenglon, etc.). | **No** (no hay menú contextual en Synap) |

#### Eventos de cambio de valor (Change / LostFocus)

| Evento VB6 | Descripción breve | Synap |
|------------|-------------------|--------|
| **Motivo_Click** | Permiso_Motivo_Puesto; visibilidad Depósito destino, Busca_PEDI, Frame_Datos_OPT, frameCliente, frameVendedor, cantDesarme, lote; seteo ES, Detalle, DataDepositoD. | **Parcial** (@change motivo + getters mostrarDepDestino, mostrarDatosOPT, mostrarBuscaPEDI; Detalle vacío/cambio; sin frameCliente, frameVendedor 6/7/8, cantDesarme, lote) |
| **DepositoOrigen_change** | Refresco de lista depósito destino y/o validaciones. | **Parcial** (@change dep_origen: limpia destino si igual, actualizarDetalleTransferencia) |
| **DepositoDestino_LostFocus** | Si Transferencia: Detalle = "Transferencia de [origen] a [destino]". | **Sí** (@change dep_destino + actualizarDetalleTransferencia) |
| **DepositoDestino_Click** | Para Transferencia con origen y destino vacío: asigna primer depósito disponible como destino. | **No** (no necesario; usuario elige de lista) |
| **lote_articulo_Click / lote_articulo_SelChange** | Actualiza stock_lote al elegir lote en combo. | **Sí** (modal Elegir lote por renglón; al elegir se asigna id_lote, cod_lote, vto_lote, stock_lote y se muestra en columna Lote) |
| **calculo_saldo_directo_GotFocus / LostFocus / KeyPress** | Cálculo de saldo directo (Ajuste). | **Sí** (campo Saldo deseado visible si calculo_stock_saldo = Si y motivo Ajuste; blur/Enter ejecutan cálculo E/S y cantidad) |

#### Eventos de teclado (KeyPress / KeyUp)

| Evento VB6 | Descripción breve | Synap |
|------------|-------------------|--------|
| **Articulo_KeyPress** | Enter o código de barra para buscar/agregar artículo. | **Parcial** (búsqueda por input, sin KeyPress específico) |
| **Cantidad_KeyPress / GotFocus / LostFocus** | Validación numérica, foco. | **Parcial** (input numérico sin eventos especiales) |
| **Detalle_KeyPress** | Enter u otro atajo. | **No** |
| **DepositoDestino_KeyPress** | Enter → Detalle.SetFocus. | **No** |
| **DepositoOrigen_KeyPress** | Enter → según motivo va a DepositoDestino o Detalle. | **No** |
| **ES_KeyPress** | Enter. | **No** |
| **Fecha_KeyUp** | Atajo. | **No** |
| **fecha_vto_KeyPress** | Validación fecha vto lote. | **No** |
| **Motivo_KeyPress** | Navegación. | **No** |
| **Referencia_KeyPress** | Enter. | **No** |
| **cantDesarme_KeyPress** | Validación numérica. | **No** |
| **nro_lote_KeyPress** | Validación. | **No** |
| **lote_articulo_KeyPress** | Enter. | **No** |
| **tipo_unidad_bulto_KeyPress / unidad_art_peso_KeyPress** | Unidades bulto/peso (Unidad, Display, Bulto). | **Sí** (columna Embalaje y select en fila búsqueda cuando utiliza_bulto_cerrado o utiliza_display = Si; tipo_unidad_defecto en datos iniciales; persistencia tipo_unidad por renglón) |

#### Carga y vida del formulario

| Evento VB6 | Descripción breve | Synap |
|------------|-------------------|--------|
| **Form_Load** | Frames lote ocultos, data_entidad, dataVendedor, StatusBar, opciones bulto/display, cantidad_armado, Cambio_Fuente_Formulario. | **Parcial** (init: carga datos iniciales y renglones; sin lote, cliente, vendedor ni opciones bulto) |
| **Inicial()** | Llamado tras Load o tras Aceptar; Elimina_Temporal, fecha, depósitos, ref_movstock, Motivo, conf grilla, etc. | **Parcial** (init hace carga de datos; no hay “reinicio” post-confirmación igual que Inicial) |
| **GridArticulos_GotFocus** | Foco en grilla. | **No** (tabla no tiene evento equivalente) |
| **AgregarRenglon_GotFocus** | Foco en botón agregar. | **No** |

#### Procedimientos auxiliares (no son eventos de usuario)

| Procedimiento VB6 | Descripción breve | Synap |
|--------------------|-------------------|--------|
| **Permiso_Motivo_Puesto** | Fuerza motivo según permiso (ej. solo Mov. Interno E/S). | **No** (lista de motivos viene filtrada por API; no se fuerza cambio en front) |
| **Es_Transferencia / No_Es_Transferencia** | Muestra/oculta LabelDestino, DepositoDestino, Busca_PEDI, Label_Busca_PEDI. | **Sí** (getters mostrarDepDestino, mostrarBuscaPEDI; controles con x-show) |
| **Elimina_Temporal** | DELETE temporales del usuario. | **Sí** (backend limpia al confirmar; no hay “Cancelar” que borre temporal explícito) |
| **CalculoTotales** | Refresca CuerpoStock y grilla. | **Sí** (renglones vienen de API tras agregar/quitar/actualizar) |
| **Menu** | Construye menú contextual. | **No** |
| **Cambio_Fuente_Formulario** | Ajuste de fuentes. | **No** |
| **generar_asiento_cont** | Genera asiento contable según motivo. | **No** |
| **visualiza_asiento_cont** | Muestra asiento generado. | **No** |
| **busqueda_articulo / busqueda_articulo_ensamble** | Búsqueda de artículo (y para ensamble/desarme). | **Sí** (buscarArticulos + API; sin ensamble_desarme) |
| **ensamble_desarme** | Carga renglones por fórmula (Armado/Desarmado). | **No** |
| **GuardarSerie** | Graba series desde temporales. | **Sí** (en alta_movimiento: validación cantidad=series por renglón seriado; luego temp → serie_entrada/serie_movimiento y serie_entrada.disponible='No' en salida) |
| **MstockE / MstockS** | Entrada/salida de stock en ensamble/desarme. | **No** |
| **Lote_ed** | Edición de lote en salida; descuenta stock_lote. | **Sí** (en confirmación: entrada crea/actualiza lote y lote_stock; salida valida stock_lote >= cantidad y descuenta lote_stock) |
| **Buscar_Articulo_Grilla** | Busca artículo por código en la grilla. | **No** |

**Resumen numérico:** De unos 50+ eventos/procedimientos listados, en Synap están **implementados o parcialmente implementados** los equivalentes a: Aceptar, AgregarRenglon, Busca_PEDI, Cancelar, EliminarRenglon, Lista_Proyecto, ModificarRenglon (edición inline), Motivo (parcial), DepositoOrigen/DepositoDestino (parcial), Form_Load/Inicial (parcial), Es_Transferencia/No_Es_Transferencia, Elimina_Temporal, CalculoTotales, busqueda_articulo, **lote por renglón** (Elegir lote / Cambiar, Lote_ed en confirmación), **calculo_saldo_directo** (campo Saldo deseado cuando calculo_stock_saldo = Si y motivo Ajuste; blur/Enter calculan E/S y cantidad), **tipo_unidad_bulto** (columna Embalaje y select en fila búsqueda cuando utiliza_bulto_cerrado o utiliza_display = Si; tipo_unidad_defecto; persistencia tipo_unidad por renglón), **unidad_art_peso + lista_unidad_art_peso** (columna Peso, input por renglón, botón lista → modal Ingresar peso; visible cuando usa_multiplica_bulto_promedio = Si y tipo_balanza = Bascula), **cantidad_armado (OPT/OPP)** (select Unidad/Armado cuando pedidos_parte_produccion = Si y motivo 12 Parte producción; valor en cabecera). **Series (Fase 6 ABMSeries)** implementados: columna Series, modal Números de serie, validación cantidad=series, GuardarSerie en alta. **No implementados** (entre otros): ensamble_desarme y MstockE/MstockS, asiento contable, cliente/vendedor (btnBuscaCli, frameCliente, frameVendedor), cantidad_armado, Permiso_Motivo_Puesto en front, integración báscula real (Carga_Unidad_Peso VB6), y la mayoría de KeyPress/KeyUp/GotFocus/LostFocus.

#### Atajos de teclado (funciones rápidas)

En VB6 el menú SmartMenuXP asigna:

| Tecla | Acción VB6 | Synap |
|-------|------------|--------|
| **Escape** | Salir (Cancelar_Click) | Cierre de modales (no navegación a dashboard) |
| **F12** | Guardar (Aceptar_Click) | **Sí**: abre modal de resumen (Confirmar movimiento) |
| **F2** | Buscar (ListaArticulos_Click) | **Sí**: cambia a tab Artículos y enfoca búsqueda de artículo |
| **F3** | Aceptar renglón (AgregarRenglon_Click) | **Sí**: agrega renglón (si hay artículo y depósito) |
| **F4** | Modificar renglón (ModificarRenglon_Click) | **Sí**: inicia edición del primer renglón o cancela edición actual |
| **F5** | Eliminar (EliminarRenglon_Click) | **Sí**: quita renglón en edición o el primero de la lista |
| **F6** | PEDI (Busca_PEDI_Click) | **Sí**: abre modal lista de pedidos pendientes |
| **F7** | Serie (ABMSerie_Click) | **Sí**: abre modal de números de serie del renglón en foco o del primero seriado (si atajo en uso) |

En Synap se usa `@keydown.window` y un método `handleAtajoTeclado()` que hace `preventDefault` para F2–F7 y F12 y ejecuta la acción correspondiente. La leyenda de atajos se muestra bajo el título del formulario.

#### Campo "Valor variable" (cant_Desarme)

En VB6 el control se llama `cantDesarme` y la etiqueta visible es **"Valor variable:"**. Cumple la siguiente función:

- **Visibilidad:** Solo se muestra cuando el motivo es **Desarmado** (Motivo.ListIndex = 9). En `Motivo_Click`, si `Motivo.ListIndex = 9` se hace visible `lblCantDesarme` y `cantDesarme`; en caso contrario se ocultan.
- **Significado:** Es un **porcentaje (0–100)** que indica qué parte del desarmado se aplica. Por ejemplo, 50 significa que solo el 50% de las cantidades del movimiento se registran (medio desarme).
- **Persistencia:** Se graba en la cabecera del movimiento: `movimiento_stock.cant_Desarme = cantDesarme.Text`.
- **Uso en el guardado:** Al procesar cada renglón en Aceptar, si el motivo es Desarmado y `cantDesarme.Text <> 0`, las cantidades (Saldo, Entrada, Cantidad) se multiplican por `(cantDesarme / 100)`. Si es 0, se usa 100% (1 × cantidad). Solo afecta a renglones de **Entrada** (insumos); la salida del producto desarmado no se escala.
- **Validación:** En flujo con código de barras, para motivo 9 se exige que "La cantidad de desarme debe ser mayor a cero" (cantDesarme > 0).

**Estado en Synap (implementado):** El campo "Valor variable" se muestra solo cuando **motivo_movimiento === 10** (Desarmado), mediante el getter `mostrarValorVariable`. Al confirmar, si el motivo es 10 y el valor es negativo se muestra error; 0 o vacío se interpretan como 100%. La cabecera envía `valor_variable`; el backend persiste en `movimiento_stock.cant_desarme` y aplica el factor solo a renglones con **ES = "E"** (entrada) en el alta del movimiento. El flujo completo de Desarmado (renglones generados por fórmula) requiere en el futuro la implementación de ensamble_desarme / en_abm_formula.

#### Proceso completo Valor variable para migración

- **Correspondencia de motivos:** En VB6 Desarmado es **Motivo.ListIndex = 9**; en Synap el código numérico es **motivo_movimiento = 10** (véase `MOTIVOS_MOVIMIENTO` en `core/services/administranet_stock.py`).
- **VB6 – Visibilidad:** `Motivo_Click` (CargaMovStock.frm aprox. 6447-6452): si `Motivo.ListIndex = 9` entonces `lblCantDesarme.Visible = True`, `cantDesarme.Visible = True`; si no, ambos `False`.
- **VB6 – Validación:** En flujo código de barras (3295-3303): motivo 9 y `cantDesarme.Text <= 0` → mensaje "La cantidad de desarme debe ser mayor a cero" y foco en `cantDesarme`. `cantDesarme_KeyPress` (3432): solo números.
- **VB6 – Persistencia:** En Aceptar_Click, al grabar cabecera: `rs_movimiento_stock.Fields!cant_Desarme = cantDesarme.Text` (aprox. 4358). Tabla `movimiento_stock`, columna **cant_desarme** (DOUBLE, nullable).
- **VB6 – Aplicación del %:** En el bucle que escribe cada renglón en `stock` (aprox. 3739-3787): solo cuando **Motivo.ListIndex = 9** y solo para renglones con **Entrada** no nula; se sobrescriben Saldo, Entrada y Cantidad multiplicando por `(cantDesarme / 100)` o por 1 si cantDesarme = 0.
- **Dependencias:** (1) **ensamble_desarme** y **en_abm_formula**: en VB6 los renglones de un movimiento Desarmado se generan al agregar renglón (motivo 8 o 9) vía `ensamble_desarme`, que usa `en_abm`, `en_abm_formula` y MstockE/MstockS. En Synap no está implementado; los renglones se pueden cargar manualmente y el campo Valor variable ya se persiste y aplica. (2) **Visualiza_CargaMovStock** / Visualiza.bas: al abrir un movimiento se asigna `cantDesarme = rs_mstock.Fields!cant_Desarme` (~7092). Si en Synap se implementa un visor de movimientos, debe incluir lectura y muestra de `cant_desarme`.

### 2.4 Permisos y configuración (Principal) que afectan CargaMovStock

- **cambia_deposito:** Si "Si", depósitos desde deposito (+ deposito_usr); si "No", un solo depósito por usuario.
- **acceso_ref_movstock:** "Todos" → todas las ref_movstock; si no, solo id_refmovstock del puesto.
- **acceso_motivo_movstock:** "Todos" → lista completa de motivos; si no, lista restringida (código comentado con otras variantes).
- **mov_stock_utiliza_cbarra:** Habilita entrada por código de barra y bloquea/desbloquea Articulo.
- **activ_contabilidad / selec_ejer_per_cont:** Contabilidad y selección ejercicio/periodo (Cont_AbmEjercicio).
- **activ_proyecto:** Muestra frame_proyecto y proyecto por defecto. En Synap se lee de `configuracion.activ_proyecto` en los datos iniciales y el bloque Proyecto se muestra solo cuando `activ_proyecto === 'Si'`.
- **utiliza_embalaje / utiliza_bulto_cerrado / utiliza_display:** Cantidad, multiplicadores, tipo_unidad.
- **pedidos_parte_produccion:** Motivos 10 y 11 y controles OPT (Frame_Datos_OPT, cantidad_armado).
- **valida_venc_lote:** Exige fecha vto lote > fecha actual.

### 2.4.1 Comportamiento completo al seleccionar motivo (Motivo_Click)

**Orden de ejecución en VB6:**

1. **Permiso_Motivo_Puesto**  
   Restringe el motivo según permiso del puesto (ej.: si `acceso_motivo_movstock = "Movimiento interno E/S"`, al elegir 0,1,2,3,4,5,8,9 se fuerza ListIndex 6).

2. **Desarmado (ListIndex 9 = codigo 10)**  
   - `lblCantDesarme.Visible = True`, `cantDesarme.Visible = True`.  
   - Cualquier otro motivo: ambos `False`.

3. **Lote (si hay artículo seleccionado y no se usa código de barras)**  
   Visibilidad de `frame_lote` / `Lote` y origen del `DataLote` según motivo y tipo de movimiento (entrada = lote nuevo, salida = lote existente). Detalle por renglón/artículo.

4. **Depósito destino y Busca_PEDI**  
   - Si **Motivo = "Transferencia"** (ListIndex 5 = codigo 6): `Es_Transferencia` → LabelDestino, DepositoDestino, Busca_PEDI, Label_Busca_PEDI visibles.  
   - Si no: `No_Es_Transferencia` → esos cuatro ocultos.

5. **Frame_Datos_OPT**  
   - Por defecto `Frame_Datos_OPT.Visible = False`.  
   - Si **ListIndex 11** (Parte producción, codigo 12): `Frame_Datos_OPT.Visible = True`.

6. **Pedido producción (ListIndex 10 = codigo 11)**  
   - Label_Busca_PEDI, Busca_PEDI visibles; caption "Lista de pedidos pendientes".  
   - **LabelDestino.Visible = False**, **DepositoDestino.Visible = False**.

7. **Parte producción (ListIndex 11 = codigo 12)**  
   - Label_Busca_PEDI, Busca_PEDI visibles; LabelDestino, DepositoDestino visibles.  
   - Caption "Lista de pedidos para generar partes de producción".  
   - `Frame_Datos_OPT.Visible = True`.

8. **Seteo Entrada/Salida (ES)**  
   - **Transferencia, Faltante, Rotura, Mov. Interno Salida, Parte producción:** `ES.ListIndex = 1` (Salida), `ES.Enabled = False`.  
   - Si Transferencia o Parte producción y hay depósito origen: se refresca lista de depósitos destino (distintos al origen) y se limpia `DepositoDestino.BoundText`.  
   - **Stock Inicial, Sobrante, Mov. Interno Entrada:** `ES.ListIndex = 0` (Entrada), `ES.Enabled = False`.  
   - **Ajuste:** `ES.Enabled = True` (usuario elige E/S).

9. **Detalle**  
   - Si **Motivo <> "Transferencia"**: `Detalle = ""`.  
   - (En Transferencia el detalle se rellena en `DepositoDestino_LostFocus`.)

10. **Ensamble/Desarme (ListIndex 8 o 9 = Armado/Desarmado, codigo 9 y 10)**  
    - Se llama `Es_Transferencia` (depósito destino visible).  
    - **Label_Busca_PEDI.Visible = False**, **Busca_PEDI.Visible = False**.  
    - `DataDepositoD.RecordSource = DataDepositoO.RecordSource` (mismos depósitos que origen).  
    - `DepositoDestino.BoundText = ""`.  
    - Lógica de lote para el artículo (armado = lote nuevo, desarmado = lote existente).

11. **frameCliente (Lista_entidad)**  
    - Si **ListIndex 6 o 7** (Mov. Interno Salida, Mov. Interno Entrada = codigo 7, 8): `frameCliente.Visible = True`.  
    - Si no: `frameCliente.Visible = False`.

12. **frameVendedor (ListaVendedor / Operario)**  
    - Si **ListIndex 5, 6 o 7** (Transferencia, Mov. Interno Salida, Mov. Interno Entrada = codigo 6, 7, 8): `frameVendedor.Visible = True`.  
    - Si no: `frameVendedor.Visible = False`.  
    - (En VB6 el Operario se muestra para Transferencia y Mov. Interno E/S además de Parte producción; Frame_Datos_OPT es solo para Parte producción.)

13. **Ajuste + cálculo saldo (ListIndex 1 = codigo 2)**  
    - Si `Principal.calculo_stock_saldo = "Si"`: Label_calculo_saldo_directo, calculo_saldo_directo y columna 5 de la grilla visibles.  
    - Si no: ocultos.

**Resumen visibilidad por motivo (códigos Synap):**

| Control / bloque | Visible cuando (codigo motivo Synap) |
|------------------|--------------------------------------|
| Depósito destino (LabelDestino, DepositoDestino) | 6, 9, 10, 11, 12 (en 11 sin label “destino”, solo lista PEDI) |
| Busca_PEDI / Label_Busca_PEDI | 6, 11, 12 (en 9 y 10 ocultos) |
| Frame_Datos_OPT (Operario + Máquina) | Solo 12 |
| frameCliente (Lista_entidad) | 7, 8 |
| frameVendedor (ListaVendedor) | 6, 7, 8 |
| cantDesarme / lblCantDesarme | Solo 10 (Desarmado) |
| calculo_saldo_directo (Ajuste) | 2 si calculo_stock_saldo = Si |
| frame_lote / Lote | Según artículo y motivo (entrada/salida) |

**Seteos de campos en Motivo_Click:**  
- `Detalle = ""` si motivo no es Transferencia.  
- `ES.ListIndex` y `ES.Enabled` según tabla anterior.  
- `DepositoDestino.BoundText = ""` cuando aplica (Transferencia, Parte producción, Armado/Desarmado).  
- `DataDepositoD.RecordSource` y refresh según motivo (destinos distintos al origen, o mismos que origen en Armado/Desarmado).

En Synap se replica: **mostrarDepDestino** (6, 9, 10, 11, 12), **mostrarDatosOPT** (12), **mostrarBuscaPEDI** (6, 11, 12), **Detalle** se vacía al cambiar a motivo distinto de Transferencia y se autocompleta al elegir depósito destino en Transferencia. **Lista_Proyecto:** botón + modal proyectos. **Valor variable (cant_Desarme):** mostrarValorVariable (solo motivo 10), validación al confirmar, persistencia en movimiento_stock.cant_desarme y aplicación del porcentaje a renglones de entrada en el alta. No replicado aún: frameCliente, frameVendedor para 6/7/8 (Operario solo para 12 en Synap), lote por renglón, calculo_saldo_directo.
- **usa_multiplica_bulto_promedio / tipo_balanza:** Unidad de peso (lista_unidad_art_peso, Carga_Unidad_Peso).
- **genera_comp_interno:** Comodato en Mov. Interno Salida con entidad.
- **NombImpMSTOCK, tipo_hoja_crystal_ImpMSTOCK, etc.:** Impresión comprobante.

### 2.5 CargaMovStock.frx

- Archivo binario: iconos, imágenes de botones, datos embebidos de controles (ItemData/List de combos, Bindings de TDBCombo/Grid, etc.). No se puede inspeccionar como texto; los bindings referencian DataSource/DataField de los controles del .frm.

---

## 3. Formularios vinculantes – Resumen

| Formulario | Vinculación con CargaMovStock |
|------------|-------------------------------|
| **CargaRef_movstock** | Alta de ítems de `ref_movstock` (nombre, anulado). CargaMovStock usa ref_movstock en combo Referencia. |
| **ABMref_movstock** | Listado y ABM de `ref_movstock`; mismo catálogo que el combo Referencia. |
| **Visualiza_CargaMovStock** | Consulta de movimientos; duplica lógica de escritura en stock/stock_deposito/lote y cabecera para “visualizar”/confirmar (misma estructura de tablas). |
| **stock_consulta_avanzada** | Asigna Proceso_Llamante y abre CargaMovStock para ajuste desde consulta; tras guardar llama Consulta_Busqueda_Avanzada y Busqueda_Item_Data. |
| **Lista_Pedidos_OPT** | Rellena CuerpoStock con renglones de pedidos de producción (motivos 10/11) y asigna depósitos. |
| **AltaArticulo** | Rellena artículo, ID_Art, depósito, precios, alícuotas, lote, motivo y muestra CargaMovStock. |
| **Cont_AbmEjercicio** | Selección ejercicio/periodo cuando selec_ejer_per_cont = "Si". |
| **Erp_ABM_Proyecto / ABMCliente** | Selección de proyecto o cliente para el movimiento. |
| **ABMArticulo_seleccion / ABMArticulo_seleccion_simple** | Selección de artículo con retorno a CargaMovStock. |

---

## 4. Procesos y flujos destacados

1. **Alta de movimiento**
   - Renglones en `cuerpostock_mstock` (temporal) → Aceptar → transacción: codmov, talonarios, stock, stock_deposito, lote/lote_stock, movimiento_stock, movstock_pedi, series, asiento contable → impresión → limpieza temporal y reapertura o cierre según Proceso_Llamante.

2. **Transferencia (motivo 5 y 11)**
   - Por cada renglón: un registro en stock para salida (depósito origen) y otro para entrada (depósito destino); actualización de stock_deposito en ambos.

3. **Ensamble / Desarme (8 y 9)**
   - ensamble_desarme: fórmulas (en_abm_formula), insumos y productos; MstockE/MstockS; depósito origen/destino; cantDesarme para porcentaje de desarme.

4. **OPT / OPP (10 y 11)**
   - Lista_Pedidos_OPT rellena CuerpoStock; lista_produccion_agrupada, lista_produccion_historico, stockp; tipo_mov "OPT"/"OPP" en movimiento_stock.

5. **Lotes**
   - Según motivo se muestra frame_lote (selección de lote existente) o Lote (nro_lote + fecha_vto); alta en lote y lote_stock; validación de saldo por lote en salidas.

6. **Series**
   - serie_entrada_temp / serie_salida_temp; GuardarSerie; validación cantidad vs cantidad de series (ValCantSerie, ESerie).

7. **Contabilidad**
   - generar_asiento_cont (excepto Ajuste); IdEjer, IdPer; visualiza_asiento_cont.

---

## 5. Módulos .bas con referencias a stock

- **Funciones.bas:** 27 referencias (movimiento_stock, ref_movstock, cuerpostock, stock, stock_deposito).
- **Informes.bas:** 150 referencias.
- **Visualiza.bas:** 1558 referencias (incluye lógica de visualización de movimientos).
- **Cot.bas, Anulaciones.bas, Aler_Informes.bas:** Menor cantidad de referencias.

Para detalle de procedimientos compartidos (p. ej. Obtener_Datos_Articulo, Actualiza_Cotizacion_Dolar_Articulo, Calculo_Cantidad_Multiplicar_Diplay_Bulto) conviene revisar Funciones.bas y Visualiza.bas.

---

## 6. Cambios y puntos sensibles para migración

1. **Tabla temporal por usuario:** `cuerpostock_mstock` + `serie_entrada_temp`/`serie_salida_temp` exigen sesión/usuario claro y limpieza al cancelar o al iniciar.
2. **Transacción larga en Aceptar:** Múltiples tablas en un solo BeginTrans/Commit; en web/API conviene mantener transacción única y mismo orden de escrituras.
3. **Permisos por puesto:** acceso_ref_movstock, acceso_motivo_movstock, cambia_deposito deben replicarse en Synap (por rol/puesto).
4. **Numeración:** codmov + talonarios (MSTOCK) debe ser atómica y coherente con otros comprobantes.
5. **Visualiza_CargaMovStock:** Duplica lógica de guardado; en una migración puede unificarse en un solo servicio de “alta de movimiento” y una vista de solo lectura/consulta.
6. **Informe Crystal:** comp_mov_stock.rpt y subreportes (encabezado_empresa_grande, logo); parámetros (Fecha, NroMovStock, Usuario, dep_origen, dep_destino, referencia, Detalle, etc.) deben sustituirse por generación PDF/impresión desde backend o front.

---

## 7. Riesgos identificados

### 7.1 Integridad de datos y consistencia

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Saldo desincronizado** | Si falla a mitad de Aceptar (después de escribir en `stock` pero antes de actualizar `stock_deposito`, o en transferencia solo un depósito), los saldos por depósito pueden quedar incoherentes con la tabla `stock`. | Alta |
| **Contador codmov sin transacción atómica** | codmov se actualiza en una transacción separada (CommitTrans antes de la transacción principal). Si la transacción principal falla, el CodigoMovimiento ya quedó incrementado y no se reutiliza → huecos y posible confusión en auditoría. | Media |
| **Temporales huérfanos** | Si la sesión VB6 termina abruptamente (cierre forzado, error no capturado), registros en `cuerpostock_mstock` y serie_entrada/salida_temp pueden quedar para ese Codusuario sin limpiar, generando “basura” y posible uso indebido si otro usuario reutilizara el mismo id. | Media |
| **Lote sin bloqueo pesimista** | En salidas con lote se lee stock_lote y luego se actualiza; entre lectura y escritura otro movimiento podría consumir el mismo lote → saldo negativo o inconsistencia en lote_stock. | Alta |
| **Numeración talonarios** | Si dos usuarios generan MSTOCK al mismo tiempo, el Nro del talonario podría duplicarse o generarse fuera de orden si no hay bloqueo explícito sobre la fila de talonarios. | Alta |

### 7.2 Concurrencia y uso multi-usuario

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Tabla temporal compartida** | `cuerpostock_mstock` se distingue por Codusuario; en entorno multiestación, un mismo usuario podría tener dos instancias abiertas (dos PCs) y pisar o mezclar renglones del mismo Codusuario. | Media |
| **stock_deposito como recurso crítico** | Varios movimientos simultáneos sobre el mismo artículo/depósito compiten por el mismo registro de stock_deposito; sin bloqueo (SELECT ... FOR UPDATE) o retry, saldo final puede ser incorrecto. | Alta |
| **codmov global** | Un solo contador por base; alta concurrencia puede causar contención y bloqueos en la tabla codmov. | Media |

### 7.3 Rendimiento y escalabilidad

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Transacción larga en Aceptar** | Toda la escritura (codmov, talonarios, N renglones en stock/stock_deposito/lote, movimiento_stock, movstock_pedi, series, asiento) en una sola transacción mantiene locks mucho tiempo; movimientos con muchos renglones o lotes/series pueden degradar a otros usuarios. | Alta |
| **Consultas repetidas en loop** | Por cada renglón se abren/cierran recordsets (stock_deposito, lote, lote_stock, Obtener_Datos_Articulo, etc.); muchas round-trips a la base. | Media |
| **Sin índices documentados** | No está documentado si existen índices adecuados en (id_articulo, id_deposito) para stock_deposito, (CodigoMovimiento) para stock, (id_lote, id_deposito) para lote_stock; su ausencia agrava bloqueos y tiempos. | Media |
| **Crystal en el cliente** | La generación del comprobante (comp_mov_stock.rpt) y conexión a BD desde la estación de trabajo cargan red y cliente; picos de uso pueden saturar. | Baja |

### 7.4 Riesgos funcionales y de negocio

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Lógica duplicada CargaMovStock vs Visualiza** | Visualiza_CargaMovStock repite la lógica de guardado; cualquier corrección o nueva regla (lote, transferencia, OPT) debe replicarse en ambos sitios → riesgo de divergencia y bugs distintos entre “alta” y “visualiza”. | Alta |
| **Permisos por motivo comentados** | Varias ramas de acceso_motivo_movstock están comentadas; si se reactivan, el comportamiento puede diferir entre entornos o versiones. | Baja |
| **Ajuste sin asiento contable** | Por decisión de negocio el Ajuste no genera asiento; si la auditoría o normativa exigen trazabilidad contable de todo movimiento, hay un gap. | Media (según normativa) |
| **Comodato (genera_comp_interno)** | Lógica específica para “Mov. Interno Salida” + entidad y “bienes de uso”; poco visible y acoplada a Principal; fácil de olvidar en migración o pruebas. | Media |

### 7.5 Migración y evolución

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Dependencia de controles ActiveX** | TDBCombo, TDBGrid, MSAdodc, etc.; migración a web exige reimplementar pantallas y flujos sin estos controles; posible pérdida de comportamiento “pixel-perfect”. | Media |
| **Código en español y variables globales** | Nombres en español y uso de Principal/IngresoUsuario globales facilitan lectura pero acoplan todo al entorno VB6; extracción a servicios reutilizables requiere refactor. | Baja |
| **Informes Crystal** | comp_mov_stock.rpt y subreportes dependen de Crystal; migración a otro motor de reportes (PDF por backend, etc.) exige rediseño de layout y parámetros. | Media |
| **Módulos .bas compartidos** | Funciones.bas, Visualiza.bas concentran lógica; hay que identificar bien qué se usa solo por stock y qué por otros módulos para no romper otros formularios al extraer. | Media |

### 7.6 Seguridad y auditoría

| Riesgo | Descripción | Severidad |
|--------|-------------|-----------|
| **Credenciales en código** | Conexión Crystal con usuario/contraseña en claro (ej. "administranet", "a7v8xx0805") en Aceptar_Click; exposición si el código se filtra. | Alta |
| **Validación de permisos en cliente** | Permisos (cambia_deposito, acceso_ref_movstock, acceso_motivo_movstock) se aplican en la UI VB6; un cliente manipulado podría intentar operaciones no permitidas si el servidor no revalida. | Media |
| **Trazabilidad de anulaciones** | No se detalla en este análisis si los movimientos de stock son “soft delete” (anulado) y si hay registro de quién/cuándo anuló; importante para auditoría. | A verificar |

---

## 8. Oportunidades de mejora y optimización

### 8.1 Unificación de lógica y eliminación de duplicación

| Oportunidad | Acción propuesta | Beneficio |
|-------------|------------------|-----------|
| **Un solo servicio de “alta de movimiento”** | Extraer la lógica de Aceptar_Click (y la equivalente en Visualiza_CargaMovStock) a un módulo o servicio (DLL, clase, o en Synap un backend API) que reciba cabecera + renglones y ejecute la transacción. CargaMovStock y Visualiza solo preparan datos y llaman al servicio. | Una sola fuente de verdad; menos bugs y mantenimiento. |
| **Validaciones centralizadas** | Mover validaciones (saldo suficiente, lote vigente, cantidad vs series, depósito destino obligatorio) a funciones reutilizables usadas por alta, visualiza y por API. | Consistencia y mensajes de error unificados. |
| **Cálculo de saldo y multiplicadores** | Unificar Obtener_Datos_Articulo, Calculo_Cantidad_Multiplicar_Diplay_Bulto, y el cálculo de cantidad_multiplicar en una capa de “reglas de stock” reutilizable. | Menos duplicación y misma regla en todos los flujos. |

### 8.2 Transacciones y atomicidad

| Oportunidad | Acción propuesta | Beneficio |
|-------------|------------------|-----------|
| **Una sola transacción para codmov + movimiento** | Incluir la actualización de codmov dentro de la misma transacción que escribe stock, movimiento_stock, etc. Si algo falla, hacer Rollback de todo (incluido codmov). | Evita huecos en CodigoMovimiento y consistencia total. |
| **Bloqueo explícito de filas** | En lecturas/actualizaciones de stock_deposito y lote_stock usar SELECT ... FOR UPDATE (o equivalente) dentro de la transacción para evitar condiciones de carrera. | Saldos correctos bajo concurrencia. |
| **Talonarios** | Bloquear la fila de talonarios (MSTOCK) al inicio de la transacción y actualizar Nro al final; o usar secuencia/auto-incremento atómico por tipo de comprobante. | Numeración sin duplicados ni desorden. |

### 8.3 Rendimiento y optimización de acceso a datos

| Oportunidad | Acción propuesta | Beneficio |
|-------------|------------------|-----------|
| **Batch de inserciones** | En lugar de N inserts individuales en `stock`, construir un INSERT multi-fila o usar bulk insert (según motor) dentro de la transacción. | Menos round-trips y menos tiempo de lock. |
| **Lecturas previas en una sola pasada** | Antes del loop de renglones, pre-cargar en memoria (o en tablas temporales) los datos de artículos, stock_deposito por (articulo, deposito), lotes necesarios, y reutilizar en el loop. | Menos consultas por renglón. |
| **Índices** | Asegurar índices en (id_articulo, id_deposito) para stock_deposito, (CodigoMovimiento) para stock, (id_lote, id_deposito) para lote_stock, (Codusuario, visualiza) para cuerpostock_mstock. | Menor tiempo de búsqueda y bloqueos más acotados. |
| **Limpieza programada de temporales** | Job o tarea que periódicamente elimine registros de cuerpostock_mstock (y series temp) con más de X horas o de sesiones ya cerradas. | Reduce basura y riesgo de reutilización indebida. |

### 8.4 Experiencia de usuario y validación temprana

| Oportunidad | Acción propuesta | Beneficio |
|-------------|------------------|-----------|
| **Validación al agregar renglón** | Comprobar saldo disponible (stock_deposito / lote) en el momento de AgregarRenglon, no solo en Aceptar; avisar de inmediato si no hay stock suficiente. | Menos intentos fallidos al confirmar. |
| **Confirmación por resumen** | Antes de grabar, mostrar resumen (cantidad de renglones, totales, depósitos) y pedir confirmación explícita; opcionalmente vista previa del comprobante. | Menos errores por “clic rápido”. |
| **Guardado progresivo opcional** | Para movimientos muy largos, valorar “borrador” (guardar cabecera + renglones en tabla temporal con estado “Borrador”) y luego “Confirmar” para pasar a definitivo; permite recuperar tras cierre inesperado. | Resiliencia y UX en escenarios de muchos renglones. |

### 8.5 Reportes e impresión

| Oportunidad | Acción propuesta | Beneficio |
|-------------|------------------|-----------|
| **Generación de PDF en servidor** | Sustituir Crystal en el cliente por generación de PDF en backend (Synap o servicio) con plantilla (Jinja2 + WeasyPrint, ReportLab, o similar) y los mismos datos. | Sin dependencia de Crystal, impresión centralizada y trazable. |
| **Parámetros desde BD** | No hardcodear usuario/contraseña del informe; usar la misma conexión o credenciales configuradas por empresa. | Seguridad y configuración por entorno. |
| **Comprobante descargable** | Ofrecer “Descargar comprobante” además de imprimir; el usuario puede guardar PDF sin imprimir. | Mejor trazabilidad y menos impresiones innecesarias. |

### 8.6 Configuración y permisos

| Oportunidad | Acción propuesta | Beneficio |
|-------------|------------------|-----------|
| **Permisos validados en servidor** | En cualquier API o servicio que ejecute el alta, revalidar acceso_ref_movstock, acceso_motivo_movstock, cambia_deposito (y lista de depósitos permitidos) antes de escribir. | Seguridad independiente del cliente. |
| **Configuración por empresa** | Centralizar activ_contabilidad, pedidos_parte_produccion, utiliza_embalaje, etc. en tabla de configuración o parámetros por base/empresa, en lugar de depender solo de Principal (sesión). | Configuración auditable y consistente. |
| **Grilla configurable sin conf_grilla_final_puesto** | Si se migra a web, la visibilidad/orden de columnas puede ser preferencia de usuario o rol en front, sin necesidad de tabla conf_grilla por puesto. | Simplificación y flexibilidad. |

### 8.7 Arquitectura para Synap

| Oportunidad | Acción propuesta | Beneficio |
|-------------|------------------|-----------|
| **API “alta movimiento de stock”** | Un endpoint que reciba cabecera (motivo, depósitos, referencia, detalle, proyecto, cliente, etc.) y lista de renglones (artículo, cantidad, entrada/salida, lote, serie, etc.), ejecute la transacción y devuelva codigo_movimiento y nro comprobante. | Integración con otros módulos (TPV, kiosco, integraciones) y un solo lugar donde se aplican reglas. |
| **Eventos post-alta** | Después de grabar el movimiento, emitir evento (interno o cola) para asiento contable, impresión, notificaciones o integraciones; desacoplar pasos que no son críticos para la consistencia del movimiento. | Transacción más corta y extensibilidad. |
| **Lectura de saldos vía vista o función** | Exponer saldo actual por artículo/depósito (y por lote si aplica) mediante vista materializada o función que consolide stock/stock_deposito de forma coherente; usarla en consultas y en validaciones. | Una sola definición de “saldo” y menos errores de cálculo. |

---

Este documento sirve como base para diseño de APIs, modelos y flujos de un eventual módulo de movimientos de stock en Synap alineado con AdministraNET, e incorpora riesgos y oportunidades de mejora para priorizar correcciones y evolución.

---

## 9. Decisiones de implementación (Synap)

- **App Django:** `stock` (sin modelos Django; solo vistas, servicios y URLs). Conexión MySQL vía `core.mysql_pool` y `base_empresa` de sesión.
- **Servicio único de alta:** `core/services/administranet_stock.py`: lectura (depósitos, ref_movstock, motivos), temporales (cuerpostock_mstock), alta en una transacción (codmov, talonarios, movimiento_stock, stock, stock_deposito), listado y detalle de movimientos.
- **Permisos Synap:** `stock.ver`, `stock.crear_movimiento`, `stock.consultas`, `stock.ref_movstock`, `stock.informes` (sincronizados con `sync_permisos_synap`; mapeo a permisos de puesto: cambia_deposito, acceso_ref_movstock, acceso_motivo_movstock).
- **URLs:** `/stock/ingreso-movimiento/`, `/stock/movimientos/`, `/stock/movimientos/<id>/`, `/stock/movimientos/<id>/pdf/`, `/stock/referencias/`, `/stock/consulta-ficha/`, `/stock/consulta-avanzada/`. API: `POST /core/api/movimiento-stock/`.
- **Menú:** Ítem Stock en APPS_MENU (orden VB6): Ingreso Mov. Stock, Remito Compra/Venta, Pedido interno, Inventario, Consulta Ficha, Consultas y Anulaciones, Informes. Referencia de movimiento en Archivo > Parámetros.
- **Comprobante:** PDF generado con ReportLab desde vista `stock:movimiento_pdf`; misma información que comp_mov_stock.rpt (sin Crystal).
- **Campos por motivo y “movimiento en artículo”:** Detalle de seteo de TipoComp, deposito_destino, tipo_mov, CodViajante y paridad VB6–Synap en [MOVIMIENTO_STOCK_CAMPOS_POR_MOTIVO.md](MOVIMIENTO_STOCK_CAMPOS_POR_MOTIVO.md).

---

## 10. Estado de artefactos y pendientes de migración

### 10.1 Artefactos VB6 sin función (no migrar)

Estos controles existen en CargaMovStock.frm pero **no están referenciados en código** (ni eventos ni lectura de valores). No corresponde replicarlos en Synap.

| Artefacto VB6 | Ubicación | Observación |
|---------------|-----------|-------------|
| **TDBCombo1** | Frame_Datos_OPT | Combo enlazado a dataVendedor (codViajante/Nombre). Duplicado; el valor que se graba viene de **ListaVendedor**. |
| **Lista_Maquina** | Frame_Datos_OPT | Mismo datasource que ListaVendedor; nombre sugiere “máquina” pero enlaza viajantes. Nunca se lee en código. En Synap el bloque OPT tiene campo texto “Máquina” (cabecera.maquina) que sí se usa. |

### 10.2 Artefactos ya mapeados con función en Synap

Resumen de controles/procesos VB6 que tienen equivalente en Synap (Ingreso Mov. Stock).

| Categoría | Artefactos VB6 | Equivalente Synap |
|-----------|----------------|-------------------|
| **Cabecera** | Motivo, Fecha, DepositoOrigen, DepositoDestino, Referencia, Detalle | Selects e inputs en cabecera; getters mostrarDepDestino, actualizarDetalleTransferencia |
| **Cabecera por motivo** | frameVendedor (ListaVendedor), frameCliente (Lista_entidad), cantDesarme, Frame_Datos_OPT | mostrarVendedor (6,7,8), mostrarCliente (7,8), mostrarValorVariable (10), mostrarDatosOPT (12) con Operario, Máquina (texto), Cantidad armado |
| **Proyecto** | frame_proyecto, Lista_Proyecto | Bloque Proyecto + modal lista proyectos (activ_proyecto) |
| **Renglones** | GridArticulos, CuerpoStock, AgregarRenglon, EliminarRenglon, ModificarRenglon | Tabla renglones + API temporales; agregar/quitar/editar inline |
| **Búsqueda artículo** | Articulo, ListaArticulos, busqueda_articulo | Fila búsqueda predictiva + sugerencias; sin ventana ABM aparte |
| **Lote por renglón** | frame_lote, lote_articulo, Lote (nro_lote, fecha_vto) | Columna Lote; botón solo si lote_articulo='Si'; modal Elegir lote / Cambiar; Lote_ed en alta |
| **Series** | ABMSerie_Click, serie_entrada_temp/serie_salida_temp, GuardarSerie | Columna Series (si serie_articulo='Si'); modal Números de serie; validación y persistencia en alta |
| **PEDI** | Busca_PEDI | Modal lista pedidos pendientes + API |
| **Cálculo saldo** | calculo_saldo_directo (Ajuste) | Campo Saldo deseado (mostrarSaldoDeseado); blur/Enter calculan E/S y cantidad |
| **Embalaje / peso** | tipo_unidad_bulto, unidad_art_peso, lista_unidad_art_peso | Columna Embalaje; columna Peso + modal Ingresar peso (según configuración) |
| **Confirmación** | Aceptar_Click, Cancelar | confirmarMovimiento (validación + API); enlace Cancelar; limpieza temporales en backend |
| **Atajos** | F2–F7, F12 | handleAtajoTeclado (leyenda bajo título) |
| **Data controls** | CuerpoStock, DataDepositoO/D, data_ref_movstock, dataVendedor, data_entidad | APIs y datos iniciales (depósitos, ref_movstock, viajantes, clientes); renglones desde listar_renglones_temporales |

### 10.3 Pendientes de migrar (funciones/procesos)

| Ítem | Descripción VB6 | Estado Synap | Prioridad sugerida |
|------|-----------------|--------------|--------------------|
| **ensamble_desarme** | Carga renglones por fórmula (Armado/Desarmado); usa en_abm_formula, MstockE/MstockS. | No implementado. Valor variable (Desarmado) y cant_desarme sí; renglones se cargan manualmente. | Alta si se usan motivos Armado/Desarmado con fórmulas |
| **movstock_pedi** | Persistencia de relación movimiento_stock ↔ pedido interno (comp_ped); estado "Completo". | No persistido en alta (solo cabecera + renglones). | Media si se requiere trazabilidad pedido–movimiento |
| **generar_asiento_cont / visualiza_asiento_cont** | Asiento contable según motivo (excepto Ajuste); selección ejercicio/periodo (Cont_AbmEjercicio). | No implementado. | Según activ_contabilidad y normativa |
| **Impresión Crystal (comp_mov_stock.rpt)** | Informe en cliente con parámetros. | Sustituido por PDF en servidor (ReportLab). | N/A (resuelto con PDF) |
| **Permiso_Motivo_Puesto en front** | Fuerza motivo según acceso_motivo_movstock (ej. solo Mov. Interno E/S). | Lista de motivos filtrada por API; no se fuerza cambio en front. | Baja (backend puede filtrar) |
| **MenuPrincipal (menú contextual grilla)** | Menú contextual sobre renglón (Busca_PEDI, ModificarRenglon, etc.). | No existe; acciones vía botones/columnas. | Baja |
| **Buscar_Articulo_Grilla** | Busca artículo por código dentro de la grilla. | No implementado. | Baja |
| **KeyPress / GotFocus / LostFocus** | Navegación y validación por tecla (Enter, etc.). | Parcial (Enter en búsqueda, blur en Saldo deseado). | Baja |
| **Visualiza_CargaMovStock** | Formulario de consulta/visualización de movimientos con lógica de guardado duplicada. | Synap tiene listado y detalle de movimientos y PDF; no hay “visualizar y re-guardar” como en VB6. | Media si se requiere flujo “visualizar y confirmar” |
| **stock_consulta_avanzada → CargaMovStock** | Abrir ingreso desde consulta avanzada para ajuste desde saldo. | Consulta avanzada y ingreso son pantallas separadas; no hay apertura directa “desde consulta con contexto”. | Baja |
| **Limpieza temporal al Cancelar** | Elimina_Temporal al pulsar Cancelar (antes de cerrar). | Backend limpia al confirmar; Cancelar es enlace que sale sin borrar temporal explícito. | Baja (opcional: endpoint “limpiar temporal” al salir) |

#### 10.3.1 Fases de construcción detalladas

A continuación se detallan las fases de construcción para cada ítem pendiente con prioridad Alta o Media, y para mejoras de UX acotadas. La numeración sigue a la Fase 6 (ABMSeries).

**Fase 7 — movstock_pedi** (prioridad Media) — **Implementada**

- **Alcance:** Persistir la relación movimiento_stock ↔ pedido interno: INSERT en `movstock_pedi` (codmov_movstock, codmov_pedi, anulado='No') por cada renglón que tenga codmov_pedi/nro_pedi; opcionalmente actualizar estado en `comp_ped` a "Completo" según regla VB6.
- **Backend:** En `core/services/administranet_stock.py`, dentro de `alta_movimiento`, después del INSERT de `stock` y antes del commit: por cada renglón con `codmov_pedi` (o equivalente leído de renglones temporales), INSERT en `movstock_pedi`. Reutilizar misma transacción/cursor. Referencia VB6: CargaMovStock.frm ~4419–4426 (AddNew movstock_pedi con codmov_movstock = contador, codmov_pedi = CuerpoStock!codmov_nro_pedi).
- **API:** La confirmación ya envía renglones desde el backend (listar_renglones_temporales). Asegurar que los renglones temporales incluyan `codmov_nro_pedi` o `nro_pedi` cuando vienen de PEDI; el alta debe leer ese campo por renglón para generar los INSERT en movstock_pedi.
- **Frontend:** Verificar que al cargar renglones desde el modal PEDI se persista en el renglón temporal el identificador del pedido (nro_pedi / codmov_pedi) y que el backend lo reciba (puede venir ya en cuerpostock_mstock si el flujo PEDI rellena ese campo).
- **Documentación:** Actualizar ESQUEMA_TABLAS_STOCK_MIGRACION.md y tabla 10.3 indicando movstock_pedi como implementado; opcional doc breve `docs/general/FASE7_MOVSTOCK_PEDI.md`.
- **Estado:** Implementada. Backend: `listar_renglones_temporales` incluye `codmov_nro_pedi`; `agregar_renglon_temporal` y `actualizar_renglon_temporal` aceptan y persisten `codmov_nro_pedi` (derivado de `nro_pedi` si es numérico); `alta_movimiento` inserta en `movstock_pedi` una fila por renglón con pedido. API: add/update renglón aceptan `nro_pedi` y `codmov_nro_pedi`. Frontend: al agregar renglón se envía `cabecera.nro_pedi` si hay pedido seleccionado. Ver `docs/general/FASE7_MOVSTOCK_PEDI.md`.

**Fase 8 — ensamble_desarme** (prioridad Alta si se usan motivos Armado/Desarmado)

- **Alcance:** Carga de renglones por fórmula para motivos Armado (9) y Desarmado (10): leer `en_abm_formula` (y tablas relacionadas) para un artículo producto/insumo y generar renglones en cuerpostock_mstock; aplicar cant_desarme a entradas en Desarmado (ya existe aplicación de porcentaje en alta).
- **Backend:** (1) Servicio que consulte `en_abm_formula` por id_articulo (producto en Armado, insumos en Desarmado) y devuelva lista de ítems con cantidades según fórmula. (2) Función que, dado motivo Armado/Desarmado, artículo y cantidad, inserte en cuerpostock_mstock los renglones generados (paridad con ensamble_desarme y MstockE/MstockS en VB6). (3) Integrar con flujo de alta para que cant_desarme siga aplicándose a renglones de entrada (ya implementado).
- **API:** Nuevo endpoint (ej. `POST api/ingreso/renglones-desde-formula/`) que reciba motivo, id_articulo, cantidad, depósito; devuelva lista de renglones a insertar o inserte directamente en temporales y devuelva renglones actualizados. Referencia: VB6 AgregarRenglon_Click llama ensamble_desarme cuando motivo es Armado/Desarmado.
- **Frontend:** En `stock/templates/stock/alta_movimiento.html`, cuando motivo sea Armado o Desarmado y el usuario agregue un artículo con fórmula: llamar al nuevo endpoint y rellenar la tabla de renglones con los ítems generados; si no hay fórmula, mantener comportamiento actual (agregar un renglón manual).
- **Documentación:** Crear `docs/general/FASE8_ENSMABLE_DESARME.md` (alcance, tablas en_abm_formula/en_abm, flujo backend/API/frontend); actualizar 10.3 y 10.5.

- **Búsqueda de artículos ensamblados desde la línea:**
  - **Paridad VB6:** En CargaMovStock, al hacer clic en el botón de búsqueda de artículo con motivo Armado (8) o Desarmado (9), se abre la ventana **En_abm** («Artículos ensamblados / Definición de ensamblaje o formula») con grilla «Artículo ensamblado» (Cod. Sistema, Cod. Manual, Nombre, Anulado), grilla «Insumos» (componentes con Cantidad, Costo, etc.) y Búsqueda rápida por Nombre, Cod Sist, Cod manual. Alternativamente se usa `busqueda_articulo_ensamble`, que ejecuta una consulta con **RIGHT JOIN en_abm** sobre `articulo`, de modo que solo devuelve artículos con `id_en_abm` (artículos ensamblados). Relación: `articulo.id_en_abm` → `en_abm.id_en_abm`; `en_abm_formula` tiene `id_en_abm` e `id_articulo` (insumo) con `cantidad_articulo`.
  - **Decisión Synap:** No depender de botón ni ventana separada. La **misma búsqueda en la línea** (campo de la fila de búsqueda en alta_movimiento.html) sirve para Armado/Desarmado: cuando motivo es 9 o 10, la API de artículos recibe un parámetro opcional `solo_ensamblados=1` (o motivo 9/10) y filtra por `articulo.id_en_abm IS NOT NULL` y `en_abm.anulado = 'No'`. Al confirmar la fila: si el artículo tiene fórmula (`tiene_formula` o `id_en_abm` en la respuesta de búsqueda), se llama a `POST api/ingreso/renglones-desde-formula/`; si no, se mantiene el flujo actual (`api_ingreso_renglon_add`). La API de búsqueda puede devolver `tiene_formula` o `id_en_abm` para que el front decida.
  - **Búsqueda completa (ver todos los ensamblados):** El usuario debe poder ver la lista completa de artículos ensamblados sin conocer nombre ni código. Se usa **asterisco (*)** como criterio de búsqueda completa: cuando motivo es Armado/Desarmado y el usuario escribe **`*`** en el campo de búsqueda, el front envía `q=*` y la API devuelve los primeros N artículos ensamblados. Placeholder o hint opcional: «Buscar por nombre o código, o * para ver todos los artículos ensamblados».
  - **Si no hay artículos ensamblados:** La API devuelve `articulos: []`. El front **muestra en la lista una única opción con el texto «No hay artículos ensamblados»**, que **no es seleccionable** (ítem deshabilitado o sin acción al clic). Así el usuario ve el mensaje en contexto y se ve forzado a corregir (cambiar búsqueda, motivo, etc.) o cancelar; no puede seleccionar esa opción.
  - **Proceso de búsqueda actual y variantes (ingreso movimiento):**
    - **Disparo por tecleado:** El input de la fila de búsqueda tiene `@input="buscarArticulosDebounce()"` → tras 250 ms se llama `buscarArticulos()`. En `buscarArticulos()` existe **mínimo de 2 caracteres**: `if (q.length < 2) return;` por tanto **no se hace petición** si el usuario escribe solo un carácter. **Por eso `*` (longitud 1) no dispara la búsqueda** en el flujo actual.
    - **Disparo por Enter:** `@keydown.enter.prevent="onEnterFilaBusqueda()"` llama a `onEnterFilaBusqueda()`, que usa **api_ingreso_articulos_por_codigo** (búsqueda exacta por código/id_manual/código de barras), no la API de lista. Si el usuario escribe `*` y pulsa Enter, se busca un artículo con código literal `*` y no se obtiene lista.
    - **Backend actual:** `api_ingreso_articulos` recibe `q`; si está vacío, `buscar_articulos` / `buscar_articulos_para_movimiento` devuelven `[]`. No hay tratamiento especial para `q=*` (se interpretaría como LIKE '%*%').
  - **Cambios necesarios para que `*` despliegue todos los ensamblados:**
    - **Frontend (alta_movimiento.html):** (1) En `buscarArticulos()`, cuando motivo es 9 o 10 (Armado/Desarmado) y `q.trim() === '*'`, **permitir la petición** aunque `q.length < 2`: p. ej. condición `if (q.length < 2 && !(motivo 9 o 10 && q === '*')) return;`. (2) Cuando motivo 9 o 10, añadir en la URL el parámetro `solo_ensamblados=1` (o `motivo=9`/`10`). (3) En `onEnterFilaBusqueda()`, cuando motivo 9 o 10 y `texto.trim() === '*'`, **no** usar búsqueda por código exacto; en su lugar llamar a `buscarArticulos()` (lista) y dejar el dropdown visible con los resultados, para que Enter con `*` también muestre todos los ensamblados. (4) Placeholder/hint cuando motivo 9 o 10: «… o * para ver todos los artículos ensamblados». (5) Si la API devuelve `articulos: []` y se envió `solo_ensamblados=1`, mostrar en el dropdown un ítem no seleccionable «No hay artículos ensamblados».
    - **API (api_views.py):** Aceptar parámetro `solo_ensamblados=1` (o motivo en query). Si `solo_ensamblados` y `q.strip() == '*'`, invocar servicio que devuelva listado completo de artículos ensamblados (sin LIKE). Si `solo_ensamblados` y `q` no vacío y no `*`, filtrar ensamblados por nombre/código (LIKE).
    - **Backend (administranet_stock.py):** Nueva función o rama en la búsqueda: cuando `solo_ensamblados=True` y `q == '*'`, SELECT artículos con `articulo.id_en_abm IS NOT NULL` y `en_abm.anulado = 'No'`, ordenados por nombre, LIMIT N. Cuando `solo_ensamblados=True` y `q` distinto de `*`, mismo filtro de ensamblados más LIKE sobre nombre/código.
  - **Resumen de cambios (búsqueda en línea):**

| Capa | Acción |
|------|--------|
| Backend | Servicio que lea en_abm_formula por id_articulo / id_en_abm; función que genere renglones para Armado/Desarmado; INSERT en cuerpostock_mstock. |
| API búsqueda | Aceptar `solo_ensamblados=1` (o motivo 9/10); filtrar por articulo.id_en_abm; **si q = '*'**, devolver búsqueda completa (primeros N ensamblados, sin LIKE); si q distinto de * y no vacío, filtrar ensamblados por LIKE; devolver `tiene_formula` / `id_en_abm` opcional. |
| API renglones | Nuevo `POST api/ingreso/renglones-desde-formula/` (motivo, id_articulo, cantidad, depósito). |
| Frontend | Si motivo 9 o 10: enviar `solo_ensamblados=1`; **excepción a mínimo 2 caracteres cuando q === '\*'** para que la petición se dispare; **Enter con texto '\*'** debe llamar a búsqueda por lista (buscarArticulos) y mostrar dropdown, no búsqueda por código exacto; placeholder cuando motivo 9/10: «… o * para ver todos»; **si articulos.length === 0** (y se pidió solo_ensamblados), mostrar ítem no seleccionable «No hay artículos ensamblados»; en confirmarFilaBusqueda, si artículo tiene fórmula → renglones-desde-formula, sino → renglon add como hoy. |

**Fase 9 — Asiento contable** (prioridad según activ_contabilidad)

- **Alcance:** Llamar a generación de asiento contable tras el alta del movimiento (excepto Ajuste), usando IdEjer/IdPer si existe Cont_AbmEjercicio; opcionalmente mostrar asiento generado (visualiza_asiento_cont).
- **Backend:** (1) Identificar en AdministraNET las tablas y el procedimiento de generación de asiento (generar_asiento_cont en VB6). (2) Módulo o servicio en Synap que, dado codigo_movimiento, motivo y parámetros contables, genere los registros de asiento. (3) Tras commit exitoso de alta_movimiento, si configuración activ_contabilidad = 'Si' y motivo distinto de Ajuste, invocar generación de asiento (misma transacción o post-commit según diseño contable).
- **API:** No obligatorio exponer asiento en API de ingreso; opcional endpoint `GET movimientos/<id>/asiento/` para vista de detalle.
- **Frontend:** Opcional: en vista detalle de movimiento, botón "Ver asiento" si existe asiento generado.
- **Documentación:** Decisión de diseño (tablas contables, momento de generación); doc `docs/general/FASE9_ASIENTO_CONTABLE_MOV_STOCK.md` y actualización de 10.3.

**Fase 10 — Visualiza: flujo "visualizar y re-guardar"** (prioridad Media)

- **Alcance:** Permitir abrir un movimiento existente en modo edición (cargar cabecera y renglones en temporales) y re-ejecutar guardado (actualización o re-alta según regla de negocio).
- **Backend:** (1) Servicio que lea movimiento_stock + stock por codigo_movimiento y vuelque renglones en cuerpostock_mstock (y series en serie_entrada_temp/serie_salida_temp si aplica) para un usuario dado. (2) Decidir si "re-guardar" es UPDATE del movimiento existente o nuevo movimiento; si es actualización, implementar lógica de actualización (reversión de saldos anteriores y aplicación de nuevos). (3) Reutilizar al máximo validaciones y escrituras de alta_movimiento para evitar duplicación.
- **API:** Endpoint ej. `POST api/ingreso/reabrir-movimiento/` con codigo_movimiento; carga temporales y devuelve cabecera + renglones para que el front muestre el formulario de ingreso en modo edición.
- **Frontend:** En listado/detalle de movimientos, botón "Reabrir para edición" que llame al endpoint y redirija a `/stock/ingreso-movimiento/` con contexto de edición (y flag para guardar como actualización si aplica).
- **Documentación:** Actualizar 10.3 y 10.4; opcional `docs/general/FASE10_VISUALIZA_REGUARDAR.md`.

**Fase 11 — Permiso_Motivo_Puesto en front** (prioridad Baja) — **Implementada**

- **Alcance:** Verificar que la API de datos iniciales (motivos) filtre por acceso_motivo_movstock del puesto; en front, si la lista ya viene filtrada, no permitir seleccionar motivo no presente (o forzar cambio si el permiso cambia).
- **Backend:** Revisar `stock/api_views.py` y servicio que devuelve motivos; asegurar filtro por permiso del puesto.
- **Frontend:** Validación al cambiar motivo (solo valores presentes en la lista).
- **Documentación:** Actualizar 10.3 cuando esté verificado.
- **Estado:** Implementada. `get_motivos_permitidos` en administranet_stock.py filtra por acceso_motivo_movstock: "Todos" → todos; "Movimiento interno E/S" → códigos 7 y 8; "Ajuste" → 2,3,4,5; "Transferencia" → 6. La API de datos iniciales ya usa ese servicio, por lo que el front solo recibe motivos permitidos. `_validar_permisos_alta` revalida el motivo antes del alta.

**Fase 12 — Menú contextual grilla** (prioridad Baja)

- **Alcance:** En la tabla de renglones, menú contextual (clic derecho) con acciones: Modificar renglón, Eliminar, Abrir PEDI, Abrir Series (según disponibilidad).
- **Backend:** No requiere cambios.
- **Frontend:** Añadir listener de contexto (clic derecho) sobre filas de renglones; menú con ítems que deleguen a métodos existentes (iniciarEdicion, quitarRenglon, abrirModalSeries, abrir modal PEDI si aplica).
- **Documentación:** Actualizar 10.3.

**Fase 13 — Buscar_Articulo_Grilla** (prioridad Baja)

- **Alcance:** Input o atajo (ej. Ctrl+F) que busque por código de artículo en la tabla actual de renglones y haga scroll/selección a la fila encontrada.
- **Backend:** No requiere cambios.
- **Frontend:** Campo de búsqueda o atajo que filtre/recorra renglones por CodigoArticulo o IDArt y enfoque la fila.
- **Documentación:** Actualizar 10.3.

**Fase 14 — stock_consulta_avanzada → ingreso** (prioridad Baja)

- **Alcance:** En la vista de consulta avanzada de stock, botón "Ajuste desde aquí" (o similar) que abra `/stock/ingreso-movimiento/` con motivo Ajuste, artículo y depósito (y opcional saldo deseado) preseleccionados vía query params o estado.
- **Backend:** No obligatorio; opcional endpoint o aceptar query params en la vista de ingreso.
- **Frontend:** En consulta avanzada, botón que construya URL con query params (motivo=2, id_articulo, id_deposito, saldo_deseado) y navegue a ingreso-movimiento.
- **Documentación:** Actualizar 10.3.

**Fase 15 — Limpieza temporal al Cancelar** (prioridad Baja) — **Implementada**

- **Alcance:** Llamar a limpieza de temporales al salir del ingreso sin confirmar (Cancelar o cierre de pestaña).
- **Backend:** Endpoint `POST api/ingreso/limpiar-temporales/` que llame a `limpiar_temporales_usuario` (core/services/administranet_stock.py).
- **Frontend:** Al hacer clic en Cancelar, llamar al endpoint antes de navegar; opcional beforeunload para cierre de pestaña.
- **Documentación:** Actualizar 10.3.
- **Estado:** Implementada. API `POST api/ingreso/limpiar-temporales/` en stock/api_views.py y stock/urls.py; botón Cancelar llama a `cancelarYSalir()` que invoca el endpoint y redirige al dashboard; beforeunload advierte si hay renglones sin confirmar al cerrar la pestaña.

**Orden de implementación sugerido:** Fase 7 → Fase 15 → Fase 11 → Fase 8 → Fase 10 → Fase 9 → Fases 12, 13, 14.

### 10.4 Formularios vinculantes – estado

| Formulario VB6 | Uso | Estado en Synap |
|----------------|-----|-----------------|
| **CargaRef_movstock / ABMref_movstock** | Catálogo ref_movstock (combo Referencia). | Referencias en API y combo en ingreso; ABM en Archivo > Parámetros si aplica. |
| **Lista_Pedidos_OPT** | Rellena renglones desde pedidos OPT/OPP. | Modal lista pedidos pendientes; carga renglones desde pedido. |
| **Erp_ABM_Proyecto** | Elegir proyecto. | Modal lista proyectos. |
| **ABMCliente** | Elegir cliente (Mov. Interno). | Select de clientes en cabecera (datos desde API). |
| **ABMArticulo_seleccion** | Ventana de selección de artículo. | Búsqueda predictiva en línea. |
| **Cont_AbmEjercicio** | Ejercicio/periodo contable. | No migrado (solo si se implementa asiento). |
| **Visualiza_CargaMovStock** | Ver movimientos y re-guardar. | Listado y detalle + PDF; sin flujo “visualizar y confirmar”. |

### 10.5 Conclusión

- **Artefactos con función:** Los controles y eventos principales de CargaMovStock están mapeados en Synap (cabecera, renglones, lote, series, PEDI, proyecto, vendedor/cliente por motivo, valor variable, cálculo saldo, embalaje/peso, confirmación). Los combos **TDBCombo1** y **Lista_Maquina** no tienen función en VB6 y no se migran.
- **Pendientes relevantes:** (1) **ensamble_desarme** (fórmulas Armado/Desarmado) si se usan esos motivos con fórmulas; (2) **movstock_pedi** — implementado (Fase 7); (3) **asiento contable** según contabilidad; (4) **Visualiza** con flujo “visualizar y confirmar” si se requiere paridad total.
- El resto son mejoras de UX (menú contextual, KeyPress, limpieza al cancelar) o integraciones (consulta avanzada → ingreso con contexto).
- **Fases de construcción:** Para cada ítem pendiente, las fases detalladas de construcción (alcance, backend, API, frontend, documentación) figuran en la subsección **10.3.1 Fases de construcción detalladas** (Fases 7 a 15).
