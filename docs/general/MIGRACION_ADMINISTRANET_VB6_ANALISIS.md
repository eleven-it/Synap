# Análisis para migración AdministraNET VB6 → Synap

Análisis en profundidad de los ítems del menú **Archivo** de AdministraNET (VB6) para su migración o integración con Synap (Django). Cada ítem se desglosa en: tablas BD, formularios, lógica de negocio, dependencias y recomendación de migración.

**Referencia del menú:** [ADMINISTRANET_VB6_MENU_ARCHIVO.md](ADMINISTRANET_VB6_MENU_ARCHIVO.md).

**Ver también:** [SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md](SYNAP_ALINEACION_ADMINISTRANET_Y_GAPS.md), [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md) — estado de implementación en Synap (Datos empresa, Sucursales).

**Estado:** Análisis de la sección Archivo **completo** (Empresa/Parametros, Entidades, Productos, Variables, Procesos, Exportación, Configuración, Salir).

---

## 1. Objetivo y alcance

- **Objetivo:** Disponer de un análisis técnico detallado que permita decidir, por cada funcionalidad del menú Archivo, si se migra a Synap, se mantiene en VB6 con integración vía API/BD, o se difiere.
- **Alcance:** Todos los ítems bajo Archivo (Empresa/Parametros, Entidades, Productos, Variables, Procesos, Exportación, Configuración, Salir).
- **Criterios de prioridad sugeridos:** (1) Datos maestros críticos para reportes y Self Checkout ya en Synap (empresa, sucursal, cliente, artículo, punto de venta). (2) Paridad operativa con VB6. (3) Variables y procesos auxiliares.

---

## 2. Metodología de análisis

Para cada ítem se documenta:

| Aspecto | Contenido |
|---------|-----------|
| **Tablas MySQL** | Tablas que lee/escribe el formulario VB6 (con schema si aplica). |
| **Formulario VB6** | Archivo .frm, controles clave (DataControl, grids), flujo Load/Guardar. |
| **Reglas de negocio** | Validaciones, cálculos, actualizaciones en cascada. |
| **Dependencias** | Otros formularios, módulos .bas, OCX (SmartMenuXP, TDBGrid, etc.), conexión IngresoUsuario.Conex. |
| **Synap actual** | Si existe modelo o vista en Django que toque la misma información. |
| **Recomendación** | Migrar a Synap / Mantener VB6 + API / Leer solo desde Synap / Diferir. |

---

## 3. Bloque 1: Empresa / Parametros

### 3.1 Datos de la empresa (keyEmpresa → Empresa.frm)

#### Tablas MySQL (administranet)

| Tabla | Uso en Empresa.frm | Observación |
|-------|---------------------|-------------|
| **DatosEmpresa** | Principal. RecordSource `SELECT * FROM DatosEmpresa`. Escritura vía `DataEmpresa.Recordset.Fields!...` + `.Update`. | En Load también se usa `datosempresa2` en una ruta (línea 1743). |
| **datosempresa2** | Alternativa en un flujo (posible vista o copia). | Ver docs [datosempresa.md](tablas/datosempresa.md), [datosempresa2.md](tablas/datosempresa2.md). |
| **pais** | Combo país. `SELECT * FROM pais ORDER BY nombre`. | Catálogo geográfico. |
| **Departamento** | Combo departamento. `SELECT * FROM Departamento ORDER BY NombreDepartamento`; filtrado por provincia. | CodProvincia. |
| **Provincia** | Combo provincia. `SELECT * FROM Provincia WHERE id_pais = ... ORDER BY Provincia`. | id_pais. |
| **Contribuyentes** | Combo condición IVA. `SELECT * FROM Contribuyentes`. | IDIva en datosempresa. |
| **cliente** | Actualización masiva en un flujo de “cambio de contribuyente por país”: `UPDATE cliente SET IDIVA=..., CUIT=... WHERE codigo=1`; también `DELETE FROM contribuyentes WHERE IDIva IN (...)`. | Cliente código 1 = consumidor final. |
| **datos_cliente** | Lectura en un flujo con `Obtener_Datos_Empresa_Interno("cod_cliente_externo")`. | Integración con datos remotos. |

#### Controles y flujo (Empresa.frm)

- **DataEmpresa** (MSADODC): enlazado a `DatosEmpresa`. Un solo registro (id_empresa = 1 en la práctica).
- **Combos enlazados:** pais, Provincia, Departamento, Iva (Contribuyentes). Dependencia en cascada: pais → Provincia; Provincia → Departamento.
- **Campos de texto:** Nombre, Domicilio, Telefono, Fax, Email, CUIT (o NIT según país), IngBrutos, InicioAct, Timbrado, Nestablecimiento, whatsapp, facebook_messenger, twitter, direccion_web, url_ecommerce_cliente, url_ecommerce_vendedor, observaciones, rubro_canal, actividad, cod_postal_distrito.
- **Guardar:** `Guardar()` valida que no falten campos obligatorios; asigna cada control al `DataEmpresa.Recordset` y llama `.Update`; actualiza variables globales en `Principal` (IDIVA, NroEstab, id_pais, nombre_pais); llama `Cambia_Contribuyente_Pais` y `Guarda_Datos_Empresa_Remoto`.

#### Reglas de negocio

- País <> 1 (Argentina): etiqueta CUIT pasa a "NIT/NIF" y se usa campo `cuit` en lugar de máscara CUIT.
- Cliente código 1 (consumidor final) se actualiza al cambiar contribuyentes/país.
- Sincronización remota vía `Guarda_Datos_Empresa_Remoto`.

#### Dependencias VB6

- **IngresoUsuario.Conex** (cadena de conexión MySQL).
- **Principal**: variables globales (id_pais, nombre_pais, IDIVA, NroEstab, fuente_tamano, color_formulario_var, etc.).
- **OCX:** SmartMenuXP, MSADODC, TDBGrid, tidate8, MSMASK32, MSDATLST.

#### Synap actual

- **core.models.Empresa** (PostgreSQL): nombre, slug, país, provincia, tipo responsabilidad fiscal, logo, activa. No es un espejo de `datosempresa`; Synap usa Empresa para multiempresa y permisos; la operación diaria sigue en MySQL administraNET.
- **Vista "Datos de empresa":** Implementada. Ruta `core:empresa_listar` redirige al detalle/edición si existe empresa; servicio en `core/services/administranet_empresas.py` escribe en DatosEmpresa y sincroniza datosempresa2; campos opcionales y actividad/rubro_canal como texto.

#### Recomendación migración

- **Corto plazo:** ✅ Flujo "Datos de empresa" en Synap operativo; datos maestros en MySQL (`datosempresa`/datosempresa2). Synap (reportes, self_checkout) sigue leyendo desde MySQL. Ver [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md).
- **Migración futura:** Decisión sobre cliente código 1 y contribuyentes al cambiar país/IVA; posible sincronización remota (Guarda_Datos_Empresa_Remoto) si se requiere paridad total con VB6.

---

### 3.2 Sucursal (keySucursal → ABMSucursal.frm / CargaSucursal.frm)

#### Tablas MySQL

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **sucursales** | Principal. ABMSucursal: `SELECT sucursales.*, datosempresa.Nombre AS NombEmp, provincia.provincia AS nomb_provincia FROM sucursales, datosempresa, provincia WHERE sucursales.id_empresa = datosempresa.id_empresa AND provincia.codprovincia = sucursales.id_provincia ORDER BY sucursales.nombre_sucursal`. | Ver [sucursales.md](tablas/sucursales.md). |
| **datosempresa** | JOIN para nombre de empresa. | id_empresa. |
| **provincia** | JOIN para nombre de provincia. | id_provincia = provincia.codprovincia. |

Schema relevante **sucursales:** id_sucursal (PK), nombre_sucursal, desc_sucursal, id_provincia, domicilio_sucursal, telefono_sucursal, email_sucursal, nro_estab_sucursal, id_empresa, limite_consulta, ruta_reporte_*, cant_renglon_venta, salida_sin_stock, dias_venc_pedido/presup, tipo_calculo_precios_impuesto_venta, anulado, lim_redondeo_tpv, tipo_impresora, nombre_impresora, puerto_impresora, agente_retib/retg/reti/percep, vendedor_defecto, doble_imp_etiqueta, cont, dnf_*, tipo_tpv, geo_*, cot_*, medios_pago_factura, id_articulo_fact_envio, activa_calculo_envios, habilita_sucursal, id_pais, etc.

#### Formularios

- **ABMSucursal.frm:** Listado en grid (DataSucursal + GridSucursal). Menú: Agregar, Modificar, Salir, “Tipo de cobro para envíos” (ABM_Sucursal_Envio), “Más configuraciones”.
- **CargaSucursal.frm:** Alta/edición de una sucursal (abierto desde ABMSucursal). Lectura/escritura sobre `sucursales` con filtro por id_sucursal.

#### Dependencias

- punto_venta (punto_venta.id_sucursal) en muchos comprobantes e informes; caja, stock, ventas filtran por sucursal.
- Más de 120 referencias a `sucursales` en VB6 (JOIN en facturas, remitos, caja, informes, configuración, etc.). Synap reports ya usa `sucursales` en query_runner y api_views.

#### Synap actual

- **core.models.Branch** (PostgreSQL): empresa (FK), name, slug, activa. No replica todos los campos de `sucursales`; Synap usa Branch para permisos y contexto; los reportes siguen usando `sucursales` en MySQL.
- **Vista "Sucursales":** Implementada. Lista/alta/edición en `core:branch_list`; formulario con bloques Datos, COT, Geolocalización, Envíos; estado Activa/Anulada por toggle (no eliminación física); servicio en `core/services/administranet_sucursales.py`.

#### Recomendación migración

- **Corto plazo:** ✅ Pantalla Sucursales en Synap operativa; escritura en MySQL `sucursales`; paridad con ABMSucursal/CargaSucursal (sin eliminación física, estado por anulado). Ver [AVANCES_MIGRACION_ARCHIVO.md](AVANCES_MIGRACION_ARCHIVO.md).
- **Migración futura:** Pruebas exhaustivas con punto_venta, caja y comprobantes; ampliar campos si VB6 incorpora más columnas en sucursales.

---

### 3.3 Administrador de usuario (keyNuevoUsuario)

- **Acción:** `Nuevo_Usuario` (procedimiento en Principal o módulo).
- **Tablas típicas:** usuarios, puesto, permiso_sistema, permiso_sistema_puesto (y posiblemente sesión). No analizado en detalle en este bloque; dejado para fase “Parametros – Usuarios y permisos”.

#### Recomendación

- Diferir análisis detallado; Synap ya tiene login contra MySQL y permisos por puesto; el ABM de usuarios puede seguir en VB6 o migrarse en una fase posterior.

---

### 3.4 Puesto → Permiso en menú / Permiso en sistema (keyPuestoMenu, keyPuestoSistema)

- **keyPuestoMenu:** ABMPuesto.Show (ABM de puestos).
- **keyPuestoSistema:** ABMPermiso_Sistema.Show (CargaPermiso_Sistema_Puesto: asignación de permisos por puesto).
- **Tablas:** puesto, permiso_sistema, permiso_sistema_puesto (MySQL). Synap ya usa estas tablas para autorización.

#### Recomendación

- Mantener ABM en VB6 por ahora; Synap solo consume permisos. Migración de pantallas de asignación de permisos en fase posterior.

---

### 3.5 Administrador de sesión (keyAdmSesiones → Adm_Sesion.Show)

- Gestión de sesiones activas (tabla **sesion** y relación con usuarios/puesto).
- Sin detalle en este documento.

#### Recomendación

- Diferir; no crítico para primera fase de migración del menú Archivo.

---

## 4. Bloque 2: Entidades

### 4.1 Resumen de entidades (Archivo → Entidades)

| Ítem | Clave | Formulario / Acción | Tabla principal | Observación |
|------|--------|----------------------|------------------|-------------|
| Cliente | keyCliente | Menu_ABM_Cliente → Cliente.frm | cliente | JOIN tipo_cliente, contribuyentes, Viajantes; cliente_domicilio_temp. |
| Proveedor | keyProveedor | Menu_ABM_Proveedor | proveedor | Análisis pendiente mismo patrón. |
| Banco | keyABMBanco | Menu_ABM_Banco | banco / chequera | Análisis pendiente. |
| Vendedor | keyViajantes | Menu_ABM_Vendedor | Viajantes | Análisis pendiente. |
| Depósito | keyDeposito | ABMDeposito.Show | deposito (stock_deposito, etc.) | Análisis pendiente. |
| Laboratorio | keyLaboratorio | ABMLaboratorio.Show | laboratorio | Análisis pendiente. |

### 4.2 Cliente (keyCliente) – Análisis en profundidad

#### Tablas MySQL

| Tabla | Uso en Cliente.frm | Observación |
|-------|---------------------|-------------|
| **cliente** | Principal. `SELECT cliente.*, tipo_cliente.Nombretipocliente AS NombTC, contribuyentes.IVA AS IVA, contribuyentes.Abreviado AS CatIVA_Abrev FROM cliente, tipo_cliente, contribuyentes WHERE ...`. | Ver [cliente.md](tablas/cliente.md). |
| **tipo_cliente** | JOIN para tipo y descripción. | TipoCliente. |
| **contribuyentes** | JOIN condición IVA. | IDIva. |
| **Viajantes** | Vendedor asignado. `SELECT * FROM Viajantes WHERE CodViajante = ...`. | CodViajante. |
| **cliente_domicilio_temp** | `INSERT INTO cliente_domicilio_temp`; `SELECT * FROM cliente_domicilio_temp WHERE id_cliente = ...`. | Domicilios adicionales. |
| **datos_cliente** (datos_cliente) | Uso vía Obtener_Datos_Empresa_Interno en Empresa.frm; no detallado en Cliente.frm aquí. | Datos adicionales. |

#### Formulario y flujo

- **Cliente.frm:** DataCliente (grid principal), combos/filtros, DataViajante para vendedor. Menú Archivo con Salir; posible integración con CRM (Crm_CargaLlamada, DataCli con cliente).
- Alta/edición de domicilios en cliente_domicilio_temp; flujos que abren TPV o otros formularios según registro seleccionado.

#### Reglas de negocio (inferidas)

- Tipo de cliente y condición IVA obligatorios para facturación.
- Vendedor (Viajante) opcional.
- Múltiples domicilios vía tabla temporal o cliente_domicilio.

#### Synap actual

- Reportes y self_checkout leen `cliente` (y sucursales, punto_venta, etc.) desde MySQL. No hay ABM Cliente en Django.

#### Recomendación migración

- **Corto plazo:** Mantener ABM Cliente en VB6; Synap solo lectura.
- **Migración futura:** Pantalla “Clientes” en Synap (Django) que lea/escriba MySQL `cliente`, `tipo_cliente`, `contribuyentes`, `Viajantes`, `cliente_domicilio`/temp. Revisar integración con CRM y con facturación/remitos que usan Codigo cliente.

---

### 4.3 Proveedor (keyProveedor → Menu_ABM_Proveedor → ABMProveedor.frm + CargaProveedor.frm)

#### Tablas MySQL

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **proveedor** | Principal. Listado: `SELECT proveedor.*, contribuyentes.IVA AS IVA FROM proveedor, contribuyentes WHERE ...`. Alta: `SELECT * FROM proveedor WHERE Codigo = 0` (AddNew implícito); actualización por Codigo. | Ver [proveedor.md](tablas/proveedor.md). Campos: Codigo (PK), Nombre, CUIT, IDIva, domicilio, contactos, retenciones, saldo, estado, id_sucursal, etc. |
| **contribuyentes** | JOIN condición IVA. | IDIva. |
| **proveedor_contacto_temp** | Alta/edición de contactos antes de grabar. `DELETE FROM proveedor_contacto_temp WHERE ...`; `INSERT INTO proveedor_contacto SELECT ... FROM proveedor_contacto_temp`. | Tabla temporal por sesión. |
| **proveedor_contacto** | Destino final de contactos al guardar proveedor. | FK a proveedor. |

#### Formularios y flujo

- **ABMProveedor.frm (Proveedor.frm):** Listado con filtros; abre CargaProveedor para alta/edición.
- **CargaProveedor.frm:** Alta con `Codigo = 0` o edición por Codigo; validación de duplicados por Nombre, id_manual_prov, CUIT; INSERT de contactos desde temp a proveedor_contacto; refresco de ABMProveedor.DataProveedor.

#### Reglas de negocio (inferidas)

- Unicidad: Nombre, id_manual_prov y CUIT no duplicados (excluyendo el registro actual en edición).
- Contactos: se gestionan en temp y se vuelcan a proveedor_contacto al guardar.

#### Dependencias cruzadas

- ABM Proveedor se abre desde muchos formularios: CargaArticulo, VariacionPrecio, Info_Banco, Info_Stock, CargaComprobantesP, Info_Venta, Info_Compra, AsigProvArt, Rprecios, CorreoEnvio, etc. (selección de proveedor en compras/artículos/informes).

#### Synap actual

- Reportes e informes leen `proveedor` desde MySQL. No hay ABM en Django.

#### Recomendación migración

- **Corto plazo:** Mantener ABM en VB6; Synap solo lectura.
- **Migración futura:** Pantalla Proveedores en Synap con CRUD sobre MySQL `proveedor` y `proveedor_contacto`; reutilizar misma API/lectura en pantallas que hoy abren ABMProveedor para elegir proveedor.

---

### 4.4 Banco (keyABMBanco → Menu_ABM_Banco)

#### Tablas MySQL (inferidas desde Info_Banco y LibroBanco)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **banco** | Catálogo de bancos. Info_Banco: JOIN con cuenta_banco. | CodBanco, Nombre, cuentaabierta. |
| **cuenta_banco** (Cuenta_Banco) | Cuentas bancarias. `SELECT cuenta_banco.*, banco.Nombre AS NombreBanco FROM Cuenta_Banco, Banco WHERE ...`. | CodCuenta, CodBanco, NroCuenta. |
| **librobanco** | Movimientos de cuenta. | codmov, etc. |
| **gastosbancarios** | Catálogo gastos bancarios. | |
| **tarjetas_credito** | Referencia en informes. | |

El ABM de Banco puede estar en CargaBanco.frm o similar; no verificado en detalle. Menu_ABM_Banco abre el listado/alta de bancos y cuentas.

#### Recomendación migración

- **Corto plazo:** Mantener en VB6. Synap no requiere escritura sobre banco/cuenta_banco para reportes actuales.
- **Migración futura:** Si se migran pagos/cobranzas, incluir ABM Banco y Cuenta en Synap con escritura MySQL.

---

### 4.5 Vendedor (keyViajantes → Menu_ABM_Vendedor)

#### Tablas MySQL

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **Viajantes** | Principal. Cliente.frm: `SELECT * FROM Viajantes WHERE CodViajante = ...`. ABM típico en ABMViajantes.frm o similar. | CodViajante, nombre, comisiones, etc. |

Cliente tiene CodViajante (FK implícita). Informes de ventas y comisiones dependen de Viajantes.

#### Recomendación migración

- **Corto plazo:** Mantener ABM en VB6; Synap solo lectura si se consumen vendedores en reportes.
- **Migración futura:** Pantalla Vendedores en Synap con CRUD sobre MySQL `Viajantes` si se unifican criterios con cliente y comisiones.

---

### 4.6 Depósito (keyDeposito → ABMDeposito.Show)

#### Tablas MySQL

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **deposito** | Principal. `SELECT * FROM deposito ORDER BY NombreDeposito`. Filtros por nombre. CargaDeposito para alta/edición. | NombreDeposito, relación con stock_deposito y movimientos de stock. |

ABMDeposito.frm: listado; CargaDeposito (o CargaBDeposito) para datos del depósito. Crítico para stock y remitos.

#### Synap actual

- Reportes y validaciones de stock usan depósito/stock_deposito en MySQL.

#### Recomendación migración

- **Corto plazo:** Mantener ABM en VB6; Synap solo lectura.
- **Migración futura:** Si se migra módulo Stock, incluir ABM Depósito con escritura en MySQL `deposito`.

---

### 4.7 Laboratorio (keyLaboratorio → ABMLaboratorio.Show)

#### Tablas MySQL

- **laboratorio** (o equivalente): catálogo de laboratorios; típicamente usado en artículos (origen/fabricante). ABMLaboratorio.frm con Accion = "Principal".

#### Recomendación migración

- **Corto plazo:** Mantener en VB6. Prioridad menor que Cliente/Proveedor/Depósito.
- **Migración futura:** Incluir en fase Productos si se migra ABM Artículo y relaciones artículo–laboratorio.

---

## 5. Bloque 3: Productos (keyArticulos)

### 5.1 Rubro (keyRubros → ABMRubro.Show / Rubro.frm)

| Tabla | Uso | Formulario |
|-------|-----|------------|
| **rubro** | `SELECT * FROM rubro ORDER BY NombreRubro`; filtros por nombre. Alta/edición en formulario de carga. | Rubro.frm (listado), AltaRubro o similar (alta/edición). |
| **rubro_categoria** | JOIN en AltaSubRubro: `SELECT rubro.*, rubro_categoria.nombre_categoria FROM rubro...`. | Relación rubro → categoría. |

**Recomendación:** Mantener en VB6; Synap solo lectura. Migración futura con ABM Artículo (rubro/subrubro son FK en articulo).

---

### 5.2 Sub rubro (keySubRubros → ABMSubRubro / AltaSubRubro, CargaSubRubro)

| Tabla | Uso | Formulario |
|-------|-----|------------|
| **subrubro** | `SELECT * FROM SubRubro WHERE CodigoRubro = ... ORDER BY NombreSubRubro`. Alta: MAX(CodigoSubRubro)+1 por rubro; validación nombre único por CodigoRubro. | AltaSubRubro.frm (listado rubro+subrubro), CargaSubRubro.frm (alta/edición). |

**Recomendación:** Igual que Rubro; migrar junto a Productos si se unifica catálogo en Synap.

---

### 5.3 Categoria rubro (keyABMRubroCategoria → ABMRubroCategoria.Show)

| Tabla | Uso | Formulario |
|-------|-----|------------|
| **rubro_categoria** | `SELECT * FROM rubro_categoria ORDER BY nombre_categoria`; búsqueda por nombre; alta con id_categoria=0, edición por id_categoria. Unicidad nombre. | ABMRubroCategoria.frm, CargaRubroCategoria.frm. |

**Recomendación:** Mantener en VB6; prioridad baja; migrar con Rubro/Subrubro.

---

### 5.4 Artículo (keyABMArticulo → Menu_ABM_Articulo → CargaArticulo / ABMArticulo)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **articulo** | Principal. Alta: `SELECT * FROM articulo WHERE IDArt = 0`; edición por IDArt. Validaciones: id_manual, NombreArticulo, CodArtProv+codigoproveedor, nrocodbarra, nrocodbarraf, MAX(CodigoArticulo) por rubro/subrubro. | Ver [articulo.md](tablas/articulo.md). Campos: IDArt, CodigoRubro, CodigoSubRubro, NombreArticulo, Alicuota, PrecioCosto, listas de precio, stock, etc. |
| **articulo_foto** | INSERT/DELETE por idart; SELECT por idart para grilla fotos. | url_interno, url_externo, foto_principal. |
| **articulo_prov** | Relación artículo–proveedor (código proveedor, barras). | CargaArticulo. |
| **precios_historial** | Historial de precios; JOIN proveedor. | Consulta en CargaArticulo. |
| **deposito_reposicion** | Consultas de reposición. | CargaArticulo. |
| **rubro, subrubro** | Combos y validación CodigoArticulo. | FK. |
| **stock_deposito, deposito, lote, lote_stock** | Pestañas stock/lotes en ABM. | ABMArticulo_seleccion_simple. |

**Formularios:** Menu_ABM_Articulo abre listado (AltaArticulo o ABMArticulo); CargaArticulo.frm para alta/edición completa (muchas pestañas). ABMArticulo_seleccion_simple para selección rápida.

**Recomendación:** Crítico para reportes y Self Checkout. Corto plazo: Synap solo lectura sobre articulo. Migración futura: pantalla Artículos en Synap con CRUD MySQL (articulo, articulo_foto, articulo_prov) y reglas de unicidad/códigos.

---

### 5.5 Presentación de artículo (keyPresArticulo → ABMPresentacion.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **presentacion_abm** (o equivalente) | ABM de presentaciones (unidad de venta, bulto, etc.). | Relación con articulo. |

**Recomendación:** Mantener en VB6; migrar con Artículo.

---

### 5.6 Campos especiales (keyArticuloCE → Articulo_ce.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **articulo_ce** | Campos personalizados por artículo. | Ver [articulo_ce.md](tablas/articulo_ce.md). |

**Recomendación:** Mantener en VB6; migrar con ABM Artículo si se requiere paridad.

---

### 5.7 Marca y modelo (keyModelo → ABMModelo.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **modelo** (o marca/modelo) | Catálogo marca y modelo; usado en artículos. | ABMModelo.Accion = "No". |

**Recomendación:** Mantener en VB6; prioridad baja.

---

### 5.8 Categoría de artículo (keyCategoria_Articulo → ABMArticulo_Categoria.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **articulo_categoria** | Catálogo categorías de artículo. | Ver [articulo_categoria.md](tablas/articulo_categoria.md). |

**Recomendación:** Mantener en VB6; migrar con Productos.

---

### 5.9 Unidades de medida (keyUM → ABMUniMed.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **unidad_medida** (o equivalente) | Catálogo UM; usado en articulo y comprobantes. | ABMUniMed.Accion = "No". |

**Recomendación:** Mantener en VB6; migrar con Artículo/listas de precios.

---

### 5.10 Asignación de proveedores a artículo (keyAsigProvArt → AsigProvArt.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **articulo_prov** | Relación artículo–proveedor (código en proveedor, barras, etc.). | AsigProvArt, AsigProvArt_Carga. |

**Recomendación:** Mantener en VB6; migrar con ABM Artículo.

---

### 5.11 Actualización de precios (keyCambioPrecio → ActPrecio.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **articulo** | Actualización masiva de precios (PrecioCosto, listas, etc.). | VariacionPrecio.frm (ActPrecio). |
| **precios_historial** | Posible escritura de historial. | |

**Recomendación:** Mantener en VB6; proceso crítico; migración futura como “proceso” o dentro del módulo Productos en Synap.

---

### 5.12 Actualización de descuentos en venta (keyCambioDescuento → ActDescuento.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **articulo** / listas descuento | Descuentos por lista o artículo. | ActDescuento.frm. |

**Recomendación:** Mantener en VB6; migrar con precios si se unifica.

---

### 5.13 Consulta avanzada de artículos (keyConsulta_Avanzada_Articulo → Menu_Stock_Consulta_Avanzada)

Formulario de consulta/filtro avanzado sobre articulo (y tablas relacionadas). Solo lectura.

**Recomendación:** Synap puede ofrecer equivalente vía reportes o pantalla de consulta; no prioritario migrar el formulario VB6.

---

### 5.14 Descuento de proveedor / Actualización descuentos proveedor (keyDescuento_Proveedor, keyDescuento_Proveedor_Act)

| Tabla | Uso | Formulario |
|-------|-----|------------|
| **descuento_proveedor** | ABM descuentos por proveedor/artículo. | ABM_Descuento_Proveedor, ActDescuento_Prov. |

**Recomendación:** Mantener en VB6; migrar con Compras/Proveedor si aplica.

---

### 5.15 Reglas de precios (keyRprecios → Rprecios_abm.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **reglas_precio_masivas** (o equivalente) | Reglas de precio (por tipo cliente, lista, etc.). | Rprecios_abm, Rprecios_alta_art, Rprecios_eliminar. |

**Recomendación:** Mantener en VB6; lógica compleja; migración futura como módulo de precios en Synap.

---

### 5.16 Asignación de artículos a tipo de cliente (keyAsigArtTipo → Articulo_tipo_cliente.Show)

Tablas: articulo, tipo_cliente y tabla de asignación (artículo por tipo de cliente para listas/precios).

**Recomendación:** Mantener en VB6; migrar con Productos/Precios.

---

### 5.17 Armado / Desarmado (keyDesarmeArt → En_abm.Show)

| Tabla | Uso | Observación |
|-------|-----|-------------|
| **en_abm** (ensamblaje), fórmulas, renglones | Productos armado/desarmado (kit). | En_abm con Caption "Armado y desarmado..."; GridArtEn. |

**Recomendación:** Mantener en VB6; módulo específico; migración solo si se requiere paridad de producción/ensamblaje.

---

### 5.18 Programa de descuentos y voucher (keyPrograma_Descuentos → Programa_Descuentos.Show)

Tablas propias de promociones/descuentos/vouchers (sp_*, programa_descuentos, etc.).

**Recomendación:** Mantener en VB6; migración baja prioridad.

---

### 5.19 Consulta de precios (keyConsulta_Precios → Menu_Consulta_Articulo → Consulta_Precio_Articulo_Usr.Show)

Consulta de precios por artículo (lectura). Tablas: articulo, listas de precio, tipo_cliente.

**Recomendación:** Synap puede ofrecer equivalente; no prioritario migrar formulario VB6.

---

## 6. Bloque 4: Variables (keyVariable)

### 6.1 Impositivas (keyImpositiva)

| Ítem | Clave | Tablas | Formulario | Recomendación |
|------|--------|--------|------------|----------------|
| Impuesto | keyImpuesto | impuesto, impuesto_detalle | ABMImpuestos.Show | VB6; migrar si se unifica FE. |
| Alícuota IVA | keyImpuestos | IVA (alicuota) | ABMIVA.Show | VB6; crítico para facturación. |
| Alícuota IIBB | keyIngBrutos | activ_iibb o similar | ABMIngBrutos.Show | VB6. |
| Retención (Proveedor/Cliente) | keyRet → keyTipoRetPro* / keyTipoRetCli | tipo_retencion_pro, tipo_retencion_cli, retenciones_* | ABMRetProv, ABMRetProvG, ABMRetProvIVA, ABMRetCli | VB6. |
| Percepciones (Proveedor/Cliente) | KeyPercep → keyPerPro, keyPerCli | percepcion, percepciones_cli, etc. | ABMPercepciones, ABMPercepcionesCli, ABMPercepcionesCliTipo | VB6. |
| Impuestos internos | keyImpuestoInterno | impuesto interno | ABM_ImpuestoInterno.Show | VB6. |
| Año y período fiscal | keyABMPeriodos | período fiscal | ABMPeriodos.Show | VB6. |
| Config. Factura electrónica (CAEA) | keyConfCompElect | adm_felectronicas, talonarios, serie | adm_felectronicas_caea.Show | VB6; crítico para FE. |

**Recomendación global Impositivas:** Mantener en VB6; Synap y Self Checkout consumen datos de IVA/contribuyentes para cálculos; no reemplazar ABM en corto plazo.

---

### 6.2 Administrativas (keyAdministrativa)

| Ítem | Clave | Tablas | Formulario | Recomendación |
|------|--------|--------|------------|----------------|
| Punto de venta y talonario | keyPV | punto_venta, sucursales, talonarios | ABMPV.Inicial + ABMPV.Show | VB6; crítico para comprobantes. Synap reportes ya usan punto_venta/sucursales. |
| Talonario | keyTalon | talonarios | ABMTalonario | VB6. |
| Condición venta/compra | keyCondventa | cond_venta | ABMCondVenta.Show | VB6. |
| Cotización moneda | keycotizacion | moneda, cotización | Menu_Cotizacion_Moneda | VB6. |
| Grupo de gasto / Gasto | keyGastos_Grupo, keyGastos | gastos, gastos_grupo | ABMGastos_Grupo, ABMGastos | VB6. |
| Descuentos recibo/OP | keyDescRec | descuento_rec, descuento_rec_nc | ABMDescuentoREC | VB6. |
| Caja | keyABMCajas | caja_abm, caja_saldo, caja | ABMCajas | VB6; crítico para caja. Ver [caja.md](tablas/caja.md). |
| Tarjetas / Plan tarjeta | keyABMTarjetasCredito, keyABMPlanes_TarjetasCredito | tarjetas_credito, planes | ABMTarjetaC, ABMPlantc | VB6. |
| Referencia mov. stock | KeyABMref_movstock | ref_movstock | ABMref_movstock.Show | VB6. |
| Transporte | keyABMTransporte | transporte | ABMTransporte.Show | VB6. |
| Tipo/Medio cobro pago | keyTipoMedioCP, keyMedioCP | medio_cobpag_tipo, medio_cobpag | ABM_medio_cobpag_tipo, ABM_medio_cobpag | VB6. |
| Ingreso / Deuda | keyIngreso, keyDeuda | ingreso, deuda_abm | ABM_ingreso, ABMDeuda | VB6. |

**Recomendación global Administrativas:** Mantener en VB6; caja, punto_venta y cond_venta son críticos para operación; migración solo en fase avanzada de reemplazo de VB6.

---

### 6.3 Bancarias (keyBancarias)

| Ítem | Clave | Tablas | Formulario | Recomendación |
|------|--------|--------|------------|----------------|
| Gasto bancario | keyGastoB | gastosbancarios | ABMGastoBancario.Show | VB6. |
| Cuenta bancaria y chequera | keyChequeras | banco, cuenta_banco, chequera | ABMChequera | VB6. |

---

### 6.4 Generales (keyGeneral)

| Ítem | Clave | Tablas | Formulario | Recomendación |
|------|--------|--------|------------|----------------|
| Tipo de cliente | keyTC | tipo_cliente | ABMTipoCliente.Show | VB6; usado en cliente y precios. |
| Grupo de cliente | keyGrupo_Cliente | cliente_grupo | ABM_Cliente_Grupo.Show | VB6. |
| País/Provincia/Depto | keyDep | pais, provincia, departamento | ABMDpto.Show | VB6; catálogo geográfico. |
| Zona | keyZona | erp_zona o zona | ABMZona.Show | VB6. |
| Config. impresora fiscal | keyConfImpFiscal | configuración fiscal | Proceso_Fiscal_Conf.Show | VB6. |
| Config. báscula | keyConfiguracion_Carga_Bascula | configuración báscula | Configuracion_Carga_Bascula.Show | VB6. |
| Publicidades | keyPublicidades | publicidad | ABM_Publicidad.Show | VB6. |

---

### 6.5 Ecommerce (keyEcommerce)

| Ítem | Clave | Tablas | Formulario | Recomendación |
|------|--------|--------|------------|----------------|
| Plantilla característica artículo | keyEcom_Plantilla_Caract | ecom_caract_plantilla (o similar) | ecom_caract_plantilla.Show | VB6; prioridad baja. |

---

## 7. Bloque 5: Procesos, Exportación, Configuración, Salir

### 7.1 Procesos (keyProceso)

| Ítem | Clave | Tablas | Formulario | Descripción |
|------|--------|--------|------------|-------------|
| Anulación numeración comprobantes | keyAnulComp | numeración por tipo/serie/sucursal; comprobantes | AnulaComp.frm | Control_Fecha + AnulaComp.Show. Libera números anulados o marca anulados. Crítico para integridad de numeración. |
| Liquidación de comisiones | keyAnulCheq | viajantes, comisiones, liquidación | Liq_ABM_Viajante.Show | ABM liquidación comisiones vendedores. |
| Liquidación comisiones avanzadas | keyComisiones_Avanzadas | idem + reglas avanzadas | Menu_Comisiones_Avanzadas | Flujo más complejo. |

**Recomendación:** Mantener en VB6; AnulaComp es sensible (no migrar sin reglas claras); comisiones pueden migrarse en fase de informes/gestión comercial.

---

### 7.2 Exportación (keyExportacion → keyExSIAP → Exportacion.frm)

| Aspecto | Detalle |
|---------|---------|
| **Formulario** | Exportacion.frm. Control_Fecha + Exportacion.Show. |
| **Tablas leídas** | DatosEmpresa, sucursales, cuentacliente, cuentaproveedor, comprobantes, stock, articulo, IVA, retenciones, percepciones, contribuyentes, y muchas más según tipo de archivo. |
| **Salidas** | Archivos en `C:\administraNET\Archivos` o `App.Path & "\Archivos"`: REGINFO (ventas/compras, alícuotas), SIFERE (retención/percepción), Citi ventas/compras, Sicore, DPIP San Luis, WooCommerce (completo/resumido), Balanza Systel, Balanza Kretz Itegra, Percepción IVA RG 5329, etc. |
| **Lógica** | Por tipo de exportación: OPEN file FOR Output/Append, escritura de líneas con formato fijo o CSV según normativa. |

**Recomendación:** Mantener en VB6; es un “proceso batch” pesado y dependiente de normativas (AFIP, bancos, balanzas). Synap podría exponer un job que invoque el mismo flujo o reimplementar solo los formatos prioritarios en Django (ej. REGINFO) en fase avanzada.

---

### 7.3 Configuración (keyConf → VerConfiguracion → Configuracion.Show)

| Aspecto | Detalle |
|---------|---------|
| **Formulario** | Configuracion.frm (y Configuracion_Adicional, Configuracion2, etc.). VerConfiguracion en Principal valida y abre Configuracion. |
| **Tablas** | configuracion (principal: `SELECT * FROM configuracion`), sucursales (datos por sucursal). Parámetros globales de la aplicación. |
| **Contenido** | Opciones de negocio, impresión, rutas, integraciones, flags de comportamiento. |

**Recomendación:** Mantener en VB6; central para el comportamiento del cliente VB6. Si Synap pasa a ser el front principal, replicar solo los parámetros que Synap necesite (ej. en Django settings o en tabla config en MySQL leída por Synap).

---

### 7.4 Salir (keySalir → MenuSalir)

Cierre de sesión: limpieza de sesión, desconexión, posible registro en tabla sesión. No requiere migración de “pantalla”; el equivalente en Synap es el logout ya existente (login).

---

## 8. Resumen y estado del análisis

### 8.1 Cobertura

| Bloque | Estado | Observación |
|--------|--------|-------------|
| Empresa / Parametros | Completo | Datos empresa, Sucursal, Usuario, Puesto, Sesión. |
| Entidades | Completo | Cliente, Proveedor, Banco, Vendedor, Depósito, Laboratorio. |
| Productos | Completo | 19 ítems desde Rubro hasta Consulta de precios. |
| Variables | Completo | Impositivas, Administrativas, Bancarias, Generales, Ecommerce. |
| Procesos | Completo | Anulación numeración, Liquidación comisiones (y avanzadas). |
| Exportación | Completo | Exportacion.frm y tipos de archivo. |
| Configuración / Salir | Completo | VerConfiguracion, MenuSalir. |

### 8.2 Recomendación global por fase

| Fase | Alcance | Prioridad |
|------|---------|-----------|
| **Corto plazo** | Synap solo lectura sobre MySQL (empresa, sucursal, cliente, proveedor, articulo, punto_venta, caja, etc.). Mantener todos los ABM y procesos en VB6. | En curso (reportes, self_checkout). |
| **Media** | Migrar a Synap pantallas de consulta o reportes equivalentes a “Consulta avanzada artículos”, “Consulta precios”, “Informes” que hoy abren desde Archivo u otros menús. | Media. |
| **Largo plazo** | Migrar ABM críticos en este orden: (1) Datos empresa / Sucursal si Synap es el front único; (2) Cliente / Proveedor; (3) Artículo y listas de precios; (4) Variables administrativas (PV, caja, cond_venta, medios de pago). Procesos (AnulaComp, comisiones) y Exportación solo si se retira VB6. | Baja hasta decisión de retiro de VB6. |

### 8.3 Próximos pasos opcionales

1. Por cada ítem que se decida migrar: especificación de API (REST o escritura directa MySQL), mapeo campo a campo y reglas de validación.
2. Documentar dependencias entre ítems (ej. Artículo → Rubro, Subrubro, IVA, unidad de medida) para orden de migración.
3. Mantener este documento alineado con cambios en VB6 o en Synap (nuevos reportes, pantallas que lean las mismas tablas).

---

**Origen:** análisis sobre `administranet_vb6/Formularios/`, `Principal.frm`, y `docs/general/tablas/`.  
**Última actualización:** análisis completo de la sección Archivo (Empresa/Parametros, Entidades, Productos, Variables, Procesos, Exportación, Configuración, Salir).
