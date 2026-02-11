# Tabla `datosempresa`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_empresa | INT | No | ✓ |  |  |
| Nombre | VARCHAR | Sí |  |  |  |
| Domicilio | VARCHAR | Sí |  |  |  |
| CodProvincia | INT | Sí |  |  |  |
| CodDepartamento | INT | Sí |  |  |  |
| Pais | VARCHAR | Sí |  |  |  |
| Telefono | VARCHAR | Sí |  |  |  |
| Email | VARCHAR | Sí |  |  |  |
| Fax | VARCHAR | Sí |  |  |  |
| Timbrado | VARCHAR | Sí |  |  |  |
| CUIT | VARCHAR | Sí |  |  |  |
| Establecimiento | VARCHAR | Sí |  |  |  |
| IngBrutos | VARCHAR | Sí |  |  |  |
| InicioAct | DATE | Sí |  |  |  |
| NroSucursal | VARCHAR | Sí |  |  |  |
| IDIva | INT | Sí |  |  |  |
| agente_retib | VARCHAR | Sí |  |  |  |
| agente_retg | VARCHAR | Sí |  |  |  |
| agente_reti | VARCHAR | Sí |  |  |  |
| agente_percep | VARCHAR | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |
| rubro_canal | VARCHAR | Sí |  |  |  |
| actividad | VARCHAR | Sí |  |  |  |
| whatsapp | VARCHAR | Sí |  |  |  |
| facebook_messenger | VARCHAR | Sí |  |  |  |
| twitter | VARCHAR | Sí |  |  |  |
| direccion_web | VARCHAR | Sí |  |  |  |
| observaciones | MEDIUMTEXT | Sí |  |  |  |
| url_ecommerce_cliente | VARCHAR | Sí |  |  |  |
| url_ecommerce_vendedor | VARCHAR | Sí |  |  |  |
| cod_postal | VARCHAR | Sí |  |  |  |
| id_localidad | INT | Sí |  |  |  |
| cod_provincia_ecomm | VARCHAR | Sí |  |  |  |
| provincia_ecomm | VARCHAR | Sí |  |  |  |
| cod_localidad_ecomm | VARCHAR | Sí |  |  |  |
| localidad_ecomm | VARCHAR | Sí |  |  |  |
| calle_ecomm | VARCHAR | Sí |  |  |  |
| nro_calle_ecomm | VARCHAR | Sí |  |  |  |
| piso_ecomm | VARCHAR | Sí |  |  |  |
| depto_ecomm | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

*No se encontraron JOINs que involucren esta tabla en el código escaneado.*

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| CargaUsuario.frm | 2059 | SELECT | .Source = "select * from datosempresa" |
| IngresoUsuario.frm | 2300 | SELECT | .Source = "select * from datosempresa" |
| Exportacion.frm | 2434 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 2607 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 3288 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 3482 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 4303 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 4472 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 11697 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 11813 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 11927 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 12038 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 12189 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Exportacion.frm | 12400 | SELECT | rs_datos.Open "select * from DatosEmpresa", conn, adOpenDyna… |
| Facturacion.frm | 915 | SELECT | .Source = "select * from datosempresa where id_empresa = 1" |
| Pedido_Avanzado.frm | 3548 | SELECT | .Source = "select * from datosempresa where id_empresa = 1" |
| Pedido_Avanzado.frm | 6014 | SELECT | .Source = "select IDIVA from datosempresa where id_empresa =… |
| Pedido_Avanzado.frm | 8733 | SELECT | .Source = "select IDIVA from datosempresa where id_empresa =… |
| CargaComprobantesPed.frm | 953 | SELECT | .Source = "select * from datosempresa where id_empresa = 1" |
| Empresa.frm | 1324 | SELECT | DataEmpresa.RecordSource = "select * from DatosEmpresa" |
| Empresa.frm | 1535 | SELECT | DataEmpresa.RecordSource = "select * from DatosEmpresa" |
| ABMSucursal.frm | 635 | SELECT | .Source = "select * from datosempresa" |
| Lista_Comp_Fact.frm | 2497 | SELECT | .Source = "select * from datosempresa where id_empresa = 1" |
| Lista_Comp_Fact.frm | 4189 | SELECT | .Source = "select IDIVA from datosempresa where id_empresa =… |
| Lista_Comp_Fact.frm | 5075 | SELECT | .Source = "select IDIVA from datosempresa where id_empresa =… |
| Lista_Comp_Fact.frm | 6825 | SELECT | .Source = "select IDIVA from datosempresa where id_empresa =… |
| Lista_Comp_Fact.frm | 9747 | SELECT | .Source = "select IDIVA from datosempresa where id_empresa =… |
| Geolocalizacion_Comprobante.frm | 2007 | SELECT | rs_datosempresa.Open "select * from datosempresa where id_em… |
| Geolocalizacion_Cliente.frm | 1774 | SELECT | rs_datosempresa.Open "select * from datosempresa where id_em… |
| Funciones.bas | 2555 | SELECT | rs_consulta.Open "SELECT datosempresa.IDIVa FROM datosempres… |
| Funciones.bas | 2855 | SELECT | rs_consulta.Open "SELECT * FROM datosempresa", conn, adOpenD… |
| Funciones.bas | 12782 | SELECT | " FROM datosempresa " & _ |
| Cot.bas | 205 | SELECT | "FROM datosempresa " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)