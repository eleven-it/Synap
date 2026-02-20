# Informe detallado: Principal.frm (AdministraNET VB6)

**Archivo:** `administranet_vb6/Formularios/Principal.frm`  
**Líneas:** ~13.600  
**Rol:** Formulario principal (shell) de administraNET Gestión: ventana base tras el login, menús, barra de estado, timers y variables globales de sesión.

---

## 1. Resumen ejecutivo

- **Principal** es la ventana que queda abierta después del login (IngresoUsuario). No se cierra hasta Salir.
- Centraliza **variables públicas de sesión** (usuario, empresa, sucursal, puesto, fecha, caja, PV, permisos, módulos, licencias, impresoras, etc.) usadas en todo el sistema.
- Construye y despacha **dos menús**: barra superior (Menu / AltaMenu) y **menú rápido lateral** (Menu_Rapido / Inicia_Menu_Rapido), ambos filtrados por puesto y licencia.
- Orquesta **apertura de todos los formularios** de la aplicación (ventas, compras, stock, caja, bancos, informes, ERP, logística, CRM, etc.) mediante **Menu_Click** y **Menu_Rapido_ListItemClick**.
- Gestiona **salida ordenada** (Salida): cierre de sesión en BD, cierre de logueo vendedor, unload de formularios, unload de IngresoUsuario.
- Incluye **timers** para control de sesión única y mensajería/alertas CRM.
- Contiene **lógica de negocio compartida**: Control_Fecha, Cierra_Logueo_Vendedor, generación de código de barras/QR AFIP, errores fiscales, reportes Crystal, visualización de pedidos/presupuestos, etc.

---

## 2. Estructura del formulario (controles principales)

| Control | Tipo | Uso |
|--------|------|-----|
| **Frame_Principal** | Frame | Zona central; contiene Image1 (fondo), Frame_Aviso, frame_logo |
| **Image1** | Image | Imagen de fondo de la pantalla principal |
| **Frame_Aviso** | Frame | Avisos (ej. vencimiento certificado FE); Label_Aviso |
| **frame_logo** | Frame | Logo empresa (Imagen_Logo); visible si muestra_logo_empresa = "Si" |
| **Menu** | SmartMenuXP | Menú superior (Archivo, Parámetros, Ventas, Compras, etc.) |
| **Menu_Rapido** | SSListBar | Menú lateral por grupos (General, Ventas, Cobranza, Compras, Stock, Caja, Bancos, etc.) |
| **StatusBar** | StatusBar | Paneles: Fecha, Hora, Empresa, Sucursal, Puesto, Usuario |
| **navegador** | WebBrowser | Banner/HTML (CargaBanner; URL banner.administranet.com.ar) |
| **Boton_Tablero** | Botón | Tablero de control (visible según mod_tablero y acceso_tablero_control) |
| **Aviso_Mensaje** | Label/control | Mensajería interna (click → mensaj_abm) |
| **picBarCode** | PictureBox | Soporte para generación de código de barras (oculto) |
| **Timer_Control_Sesion** | MTimer | Intervalo 1; control de sesión única (Control_Sesiones) |
| **Timer1** | Timer | Interval 60000; mensajería no leída y alertas CRM |
| **TimerSesionActiva** | Timer | Sesión activa |
| **TiempoVerificaciondeActualizacion** | Timer | Verificación de actualizaciones |
| **HasarNG** | ImpresoraFiscalRG3561 | Control fiscal Hasar (eventos error/impresora) |

La conexión ADO **no** se declara en Principal como global del form; se usa **IngresoUsuario.Conex** y en cada procedimiento se crean `conn As New ADODB.Connection` locales. Existe **Public conn As New ADODB.Connection** (línea ~1332) que puede usarse en otros módulos.

---

## 3. Variables públicas (resumen por categoría)

Se listan las más relevantes para sesión, permisos, caja/TPV y migración.

### 3.1 Sesión y usuario

| Variable | Tipo | Descripción |
|----------|------|-------------|
| DSN, base, puerto_servidor | String | Conexión |
| Codusuario, NombreUsuario, idUsuario, idpuesto, idEmpresa | — | Usuario actual |
| codSucursal, nombre_sucursal, nombre_empresa, nombre_puesto | — | Sucursal y puesto |
| ip, IdSesion, Datos_Logueo_Usuario, IP_Logueo_Usuario | — | Sesión e IP |
| id_vendedor_usr | String | Vendedor/cajero actual (tras autenticación TPV o por defecto del usuario) |
| Fecha, FechaSesion | Date | Fecha del sistema (actualizada con Control_Fecha) |

### 3.2 Empresa y punto de venta

| Variable | Descripción |
|----------|-------------|
| PV, PVC, id_punto_venta, id_punto_ventac, cant_pv | Punto de venta |
| selec_pv, obliga_selecpv, obliga_selecTipoDevol | Permisos PV y devoluciones |
| NroEstab, TipoIVA, IDIVA, Decimales | Datos fiscales |
| Alicuota_IVA1..6, Alicuota_IVA1_AFIP..6_AFIP | Alicuotas IVA |

### 3.3 Caja y depósito

| Variable | Descripción |
|----------|-------------|
| id_caja, id_caja_deposito, id_caja_tarjeta_deposito | Cajas asignadas al usuario |
| cambia_caja, caja_opciones_total | Permisos caja |
| id_cierre_tarjeta, id_cierre_efectivo, id_cierre_cheque | IDs de cierre para arqueo/reportes |
| Nro_Caja_General, NroComp_Caja_General, codigo_mov_cierre_efectivo | Cierre unificado |
| apertura_cierre_caja_vendedor, pedir_autenticacion_cierre_caja_vendedor | Autenticación cajero TPV |
| caja_obliga_cierre_vendedor_tpv, oculta_boton_arqueo_cierre, imprime_cierre_caja_general | Comportamiento caja/arqueo |
| visualiza_montos_caja, obliga_cierre_caja | Visualización y obligación de cierre |
| control_cierre_caja_sucursal, control_cierre_caja_central | Control por sucursal/central |

### 3.4 Permisos de sistema (muestra)

Modificación de precios, descuentos, anulación, depósito, lista de precios, cond. venta, talonarios, stock, facturación, TPV, etc. Ejemplos:

- mod_descuento_pie, mod_descuento_renglon, lim_desc_pie, lim_desc_renglon  
- anular_comprobantes, reimprimir_comprobantes, visualizar_comprobantes  
- cambia_deposito, id_deposito  
- mod_lista_de_precio, cambia_cv  
- salida_sin_stock  
- tipo_tpv_funcionalidad, tpv_permite_nc, tpv_permite_cancelacion_facturacion, inicio_facturacion_tpv  
- (y muchas más, cargadas desde **permisos_sistema** por puesto en Funciones.bas / IngresoUsuario)

### 3.5 Módulos y licencias

| Variable | Descripción |
|----------|-------------|
| mod_conta, mod_erp, mod_crm, mod_en, mod_logi, mod_tablero, mod_su, mod_cot, mod_ml, mod_pd, … | Habilitación de módulos |
| licencia_gestion (Basic/Small/PV/Full), licencia_gestion_pago, licencia_cont, … | Tipo de licencia |
| tipo_de_licencia (Free/Full/Trial) | Alcance del menú |
| cantidad_usuarios, cantidad_sucursales, cantidad_empresas, … | Límites comerciales |

### 3.6 Impresión e impresoras fiscales

Decenas de variables por tipo de comprobante (FA, FB, FM, NCA, NCB, REM, PED, REC, MCAJ, etc.): nombre impresora, puerto, copias, detalle, orientación Crystal, tipo/marca/modelo fiscal, IP, baudios. Y variables globales de impresora fiscal (Hasar): Error_Fiscal, Detalle_Error_Fiscal, Comp_Fiscal_abierto.

### 3.7 Facturación electrónica

fe_CUIT_empresa, fe_regimen_tipo, ruta_certificado, fe_url_login, fe_url_acceso_servidor, certificado_afip_local, padron_afip, resol_afip_5003, texto_resol_afip_5003, etc.

### 3.8 Listas de precios y utilidades

valor_util1..5, desc_util1..5, lista_precio_pv, recalculo_lp_tpv_cliente, tpv_lista_precio_x_pv, etc.

---

## 4. Ciclo de vida y arranque

### 4.1 Form_Load

- RemoveCancelMenuItem (oculta Cerrar del título).
- Servidor = IngresoUsuario.Servidor.
- CargaBanner: descarga HTML del banner y lo muestra en **navegador** (WebBrowser).

No se construye aquí el menú ni la barra de estado; eso ocurre en **Inicial()**.

### 4.2 Inicial()

Llamado desde **IngresoUsuario** tras login correcto (después de cargar configuración y permisos en Principal).

1. ChDir a carpeta Informes.
2. **AltaMenu**: construye el menú superior (Menu.MenuItems) con todas las entradas (Archivo, Parámetros, Entidades, Productos, Ventas, Compras, Stock, Caja, Bancos, Impuestos, Contabilidad, ERP, Ensamblaje, Logística, CRM, Soporte, etc.) y atajos.
3. cierre = 0.
4. **StatusBar**: agrega paneles Fecha, Hora, Empresa, Sucursal, Puesto, Usuario.
5. **Inicia_Menu_Rapido**: arma el menú lateral (Menu_Rapido) desde BD.
6. Unload form_espera.
7. Inicializa variables por defecto (Comp_Fiscal_abierto, Error_Fiscal, index_estado_ped_pa, id_ruta_ultima_seleccionada).
8. Habilita/deshabilita Timer1 según popup_mensajeria.
9. Principal.Show.
10. Habilita TiempoVerificaciondeActualizacion.
11. Muestra/oculta Boton_Tablero según mod_tablero y acceso_tablero_control.
12. Verifica vencimiento certificado (Verifica_Vencimiento_Certificado).
13. Muestra logo empresa (frame_logo, Cargar_Logo) si muestra_logo_empresa = "Si".

### 4.3 Inicia_Menu_Rapido

- Abre conexión con IngresoUsuario.Conex.
- Según **licencia_gestion** (Basic, Small, PV) arma una cláusula **consulta_basic** que excluye grupos (Bancos, Pagos, Compras, Caja, Cobranzas, etc.).
- Según flags **mod_conta**, **mod_erp**, **mod_en**, **mod_logi**, **mod_crm** arma la consulta a **menurapido_grupo** (id_puesto = Principal.idpuesto + filtros por módulo y consulta_basic).
- Recorre **menurapido_grupo** y por cada grupo lee **menurapido_item**; agrega grupos e ítems al control Menu_Rapido (SSListBar) con key único (ej. General_Clientes, Ventas_PV, Caja_General).
- Los ítems del menú rápido se resuelven en **Menu_Rapido_ListItemClick** (Select Case ItemClicked.key).

### 4.4 AltaMenu

- Construye el menú **Menu** (SmartMenuXP) con estructura jerárquica:
  - keyArchivo → Empresa, Entidades, Productos, Variables, Procesos, Exportación, Configuración, Salir.
  - keyTabla → Cliente, Proveedor, Banco, Vendedor, Depósito, Laboratorio.
  - keyArticulos → Rubro, Sub rubro, Artículo, presentación, campos especiales, marcas, categoría, UM, asignación proveedores, actualización precios/descuentos, reglas de precios, programa descuentos, etc.
  - keyPar → Datos, Sucursal, Administrador usuario, Puesto, Administrador sesión.
  - keyPuesto → Permiso menú, Permiso sistema.
  - Y ramas para Ventas (Presupuesto, Pedido, Facturación, NC-ND, CtaCte, Consulta, Pro Fiscal, etc.), Compras, Stock, Caja, Bancos, Impuestos, Contabilidad, ERP, Ensamblaje, Logística, CRM, Soporte (TeamViewer, Manual, Canal, etc.).
- Cada hoja tiene una **key** (ej. keyPuntoVenta, keyCajaG, keyCajaCierre, keyCajaArqueo).
- El evento **Menu_Click(ID)** usa Menu.MenuItems.key(ID) en un **Select Case** con más de 219 casos para abrir el formulario o ejecutar el sub correspondiente.

---

## 5. Navegación: menú superior vs menú rápido

- **Menú superior:** Menu_Click(ByVal ID As Long) → Select Case .key(ID) → Case "keyPuntoVenta" → Menu_Punto_Venta, Case "keyCajaG" → Menu_Caja_Efectivo, Case "keyCajaCierre" → Menu_Caja_Cierre_General, Case "keyCajaArqueo" → Menu_Visualizar_Arqueo_Efectivo, etc.
- **Menú rápido:** Menu_Rapido_ListItemClick(ItemClicked) → Select Case ItemClicked.key → Case "Ventas_PV" → Menu_Punto_Venta, Case "Caja_General" → Menu_Caja_Efectivo, Case "Caja_Cierre_General" → Menu_Caja_Cierre_General, etc.

Ambos terminan llamando a los mismos **Menu_*** (Menu_Punto_Venta, Menu_Caja_Efectivo, Menu_Caja_Cierre_General, Menu_Visualizar_Arqueo_Efectivo, Menu_ABM_Cliente, etc.), por lo que la lógica de negocio está en esos subs y no duplicada.

---

## 6. Flujos clave

### 6.1 Menu_Punto_Venta (acceso al TPV)

1. **Control_Sesiones**: si devuelve "Cierra", muestra mensaje y ejecuta Salida + End.
2. Comprueba formularios abiertos (NotaCred, FacturaA, FacturaB, NotaCred_SinCompO, TPV, Remito): si alguno está abierto, pregunta si seguir y opcionalmente Unload.
3. **Control_Fecha**: actualiza Principal.Fecha con NOW() de MySQL.
4. Si **obliga_cierre_caja = "Si"**: valida que la caja PV del usuario tenga cerrada la caja del día anterior (caja_abm, caja_saldo, caja); si no, mensaje y Exit Sub.
5. Si **apertura_cierre_caja_vendedor = "Si"** y **pedir_autenticacion_cierre_caja_vendedor = "Si"**: muestra Clave_Supervisor con Motivo "Autentica Vendedor Caja PV"; al aceptar, Clave_Supervisor actualiza viajantes e id_vendedor_usr y luego TPV.Inicial, TPV.Show.
6. Si no pide autenticación (o ya autenticado): si **tpv_permite_cancelacion_facturacion = "Si"** e **inicio_facturacion_tpv = "Si"**, pide Clave_Supervisor "Autoriza Cancelar Comp TPV Principal"; según respuesta abre o no TPV.
7. En resto de casos: TPV.EstadoAntTipoComp = "", TPV.Inicial, TPV.Show.
8. Último chequeo: si FacturaA, FacturaB o NotaCred están abiertos, pregunta y hace Unload antes de seguir.

### 6.2 Salida (cierre de aplicación)

1. Actualiza **sesion**: UPDATE sesion SET fechafin = NOW() WHERE id_sesion = Principal.IdSesion.
2. **Cierra_Logueo_Vendedor**: UPDATE viajantes SET logueado = 'No', detalle_logueo = Null, ip_logueo = Null WHERE codviajante = Principal.id_vendedor_usr.
3. Unload de todos los formularios (For Each Formulario In Forms → Unload Formulario).
4. Unload IngresoUsuario.

### 6.3 Cierra_Logueo_Vendedor

- Conexión con IngresoUsuario.Conex.
- UPDATE viajantes SET logueado = 'No', detalle_logueo = Null, ip_logueo = Null WHERE codviajante = Principal.id_vendedor_usr.
- Llamado desde Salida y desde CargaMovCaja al terminar cierre de caja general.

### 6.4 Control_Fecha

- Ejecuta en MySQL: SELECT DATE_FORMAT(NOW(),'%d/%m/%Y') FROM dual.
- Asigna resultado a Principal.Fecha.
- Llamado antes de abrir TPV, Caja, AnulaComp, Exportacion, etc., para que la fecha mostrada sea la del servidor.

### 6.5 Menu_Caja_Efectivo / Menu_Caja_Cierre_General / Menu_Visualizar_Arqueo_Efectivo

- **Caja efectivo:** Menu_Caja_Efectivo_Codigo → Caja.Caption = " Caja de efectivo", TipoCaja = "Caja Gral", Tipo_Caja_Menu = " Caja General"; según permiso cambia_caja muestra todas las cajas o solo las del usuario; Caja.Inicial, Caja.Show.
- **Cierre general:** Si apertura_cierre_caja_vendedor y pedir_autenticacion_cierre_caja_vendedor, muestra Clave_Supervisor "Autentica Vendedor Caja Cierre General"; luego Menu_Caja_Cierre_General_Codigo → CargaMovCaja con Cierre_Caja_General = "Si", caja origen/destino prellenados.
- **Arqueo:** Si visualiza_montos_caja = "No", pide Clave_Supervisor "Autentica Vendedor Arqueo"; luego se abre Caja_Arqueo (desde Caja o desde este menú según implementación).

---

## 7. Timers y tareas en segundo plano

- **Timer_Control_Sesion_Timer**: llama a Control_Sesiones; si devuelve "Cierra", mensaje y Salida + End (cierra la app si el usuario inició sesión en otra estación).
- **Timer1** (cada 60 s):  
  - Si popup_mensajeria = "Ventana": consulta **mensajeria** (id_usuario_destino, estado_mensaje = 'No leido') y muestra mensaj_abm si hay mensajes.  
  - Si popup_mensajeria = "Normal": muestra/oculta Aviso_Mensaje según mensajes no leídos.  
  - Si alerta_crm = "Si": consulta **crm_llamada** (id_usuario o id_vendedor, estado = 'Abierto', fecha_prox_llamada = hoy) y abre Crm_AbmLlamada con Alerta = "Si".
- **TiempoVerificaciondeActualizacion**: verificación de actualizaciones de la aplicación.

---

## 8. Tablas y recursos externos referenciados

| Recurso | Uso en Principal |
|---------|-------------------|
| **sesion** | UPDATE fechafin al salir (Salida). |
| **viajantes** | UPDATE logueado/detalle_logueo/ip_logueo (Cierra_Logueo_Vendedor). |
| **menurapido_grupo** | Grupos del menú lateral por id_puesto y módulos. |
| **menurapido_item** | Ítems por grupo para Menu_Rapido. |
| **permisos** | Menu_Permisos: visibilidad de ítems del menú superior. |
| **permisos_sistema** | Permisos por puesto (cargados en IngresoUsuario/Funciones; Principal solo usa las variables ya cargadas). |
| **caja_abm** | Validación caja PV en Menu_Punto_Venta (obliga_cierre_caja). |
| **caja_saldo** | Saldo y validación de cierre en Menu_Punto_Venta. |
| **caja** | Último movimiento para validar cierre del día anterior. |
| **mensajeria** | Timer1: mensajes no leídos para el usuario. |
| **crm_llamada** | Timer1: alertas de llamadas abiertas con fecha_prox_llamada = hoy. |
| **dual** (MySQL) | Control_Fecha: DATE_FORMAT(NOW(),'%d/%m/%Y'). |

Otras tablas aparecen en subs que Principal solo invoca (p. ej. CargaMovCaja, Caja_Arqueo, TPV, Visualizar_PED, etc.).

---

## 9. Procedimientos públicos relevantes (lista parcial)

- **Inicial**, **Inicia_Menu_Rapido**, **AltaMenu** — arranque y menús.
- **Menu_Punto_Venta**, **Menu_Caja_Efectivo**, **Menu_Caja_Efectivo_Codigo**, **Menu_Caja_Cierre_General**, **Menu_Caja_Cierre_General_Codigo**, **Menu_Visualizar_Arqueo_Efectivo**, **Menu_Visualizar_Arqueo_Efectivo** (y el resto de Menu_*).
- **Salida**, **Cierra_Logueo_Vendedor**, **Control_Fecha**.
- **Menu_Permisos** — aplica permisos de menú desde tabla permisos.
- **Borra_Temp**, **Borra_Temp_Usr** — limpieza de tablas temporales.
- **Guardar_Error** — registro de errores.
- **Valid_CAI** — validación CAI.
- **Generacion_CodBarra**, **Generacion_QR_AFIP**, **Generacion_QR_AFIP_2**, **Generacion_CodBarra_Articulo**, **Genera_Cod_Barra_Cod128** — códigos de barras y QR AFIP.
- **pGetPicture** — carga de iconos para menú.
- **Visualizar_PED**, **Visualizar_Presupuesto**, **Reimprimir_Ped**, **Reimprimir_Ped_PDF**, **Reimprimir_PREP**, **Reimpresion_POE** — pedidos, presupuestos, preparación, OE.
- **impresion_etiqueta**, **impresion_etiqueta_extendida**.
- **Informe_hoja_ruta**, **Informe_Resumen_ruta_factura**, **Informe_Resumen_cobranza_recibo**.
- **ReporteC**, **SubReporteC** — reportes Crystal.
- **Calcula_Promo_Intervalo**, **limite_efectivo_caja**, **reformula_nombre_articulos**.
- **CrearBanner**, **Verifica_Vencimiento_Certificado**, **Cargar_Logo**.
- **Size_Paper_CR**, **ID_PV_Manual**, **Conta_PV_Esp**, **ContCerrado** — utilidades contables/CR.
- **Visualiza_NCconcepto**.
- Eventos HASAR: **HASAR1_ErrorImpresora**, **HASAR1_ErrorFiscal**, **HASAR1_EventoFiscal**, **HASAR1_EventoImpresora**, **HASAR1_ImpresoraOcupada**, **HASAR1_ImpresoraNoResponde**.

---

## 10. Formularios que abre Principal (resumen)

Principal no crea formularios; los muestra con `.Show` o `.Show vbModal`. Entre los que se abren desde Menu_Click o Menu_Rapido:

- **Ventas:** Presupuesto, Pedido, FacturaA/FacturaB, NotaCred (y variantes), TPV, TPV_2, ConsultaComp, ReciboCobro, Pedido_Avanzado, Lista_Comp_Fact, etc.
- **Compras:** PPresupuesto, POrden_Compra, PFactura, PRemito, PNotaCred, OrdenPago, etc.
- **Stock:** CargaMovStock, Remito, Stock, Ficha_Stock, Inventario, etc.
- **Caja:** Caja, CargaMovCaja, Caja_Arqueo, Info_Caja.
- **Bancos:** LibroBanco, ChequeTercero, ListaCheqEmitidos, Info_Banco.
- **ABM / Parámetros:** Empresa, ABMSucursal, ABMUsuarios, ABMPuesto, ABMPermiso_Sistema, ABMCliente, ABMProveedor, ABMArticulo, ABMViajantes, ABMBanco, ABMDeposito, ABMCajas, ABMTalonario, ABMRubro, ABMSubRubro, Configuracion, etc.
- **Informes:** Info_Venta, Info_Compra, Info_Caja, Info_Banco, Info_Impositivo, Info_Comercial, Info_Estadistica.
- **Otros:** Clave_Supervisor, AnulaComp, Exportacion, ConsultaComp, mensaj_abm, Crm_AbmLlamada, form_espera, acercade, etc.

---

## 11. Integración en Synap: equivalencias

| Concepto en Principal | En Synap |
|------------------------|----------|
| Ventana principal tras login | Vista dashboard o shell post-login (por ejemplo base_app.html + menú). |
| Variables públicas de sesión | Atributos de request.user, sesión Django, o modelo Perfil/Usuario con relación a empresa, sucursal, puesto; almacenar en sesión o en cache lo que se use en cada request. |
| Menú superior + menú rápido | Menú de navegación (sidebar o top) generado por permisos (Django permissions o reglas por rol/puesto). |
| Menu_Click / Menu_Rapido_ListItemClick | Rutas nombradas y vistas; permisos por vista o por objeto. |
| Inicial() | Lógica post-login: cargar permisos, módulos, opciones de menú (desde BD o desde configuración por rol). |
| Control_Fecha | Obtener fecha/hora del servidor (MySQL o servidor app) y exponerla en contexto o API. |
| Cierra_Logueo_Vendedor | Al cerrar caja o logout TPV: API que actualice viajantes (logueado = 'No') usando la misma base MySQL. |
| Salida | Logout: cerrar sesión Django, actualizar sesion y viajantes en MySQL si se mantiene ese modelo. |
| Menu_Punto_Venta | Ruta/vista TPV; antes de entrar comprobar obliga_cierre_caja y apertura_cierre_caja_vendedor; si aplica, pantalla de clave de caja (auth-cashier). |
| Timers (sesión, mensajería, CRM) | Jobs en background (Celery, cron) o polling desde el front (API de mensajes y alertas). |
| Tablas menurapido_grupo / menurapido_item | Pueden migrarse a modelos Django o a JSON/config por rol; el menú se arma en backend o en front según permisos. |

Este informe sirve como referencia para entender el rol de Principal.frm en AdministraNET y para diseñar el shell, menús, sesión y flujos equivalentes en Synap.
