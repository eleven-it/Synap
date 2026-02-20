# Tabla `ml_configuracion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ml_configuracion | INT | No | ✓ |  |  |
| lista_precio | VARCHAR | Sí |  |  |  |
| id_deposito | INT | Sí |  |  |  |
| appid_ml | VARCHAR | Sí |  |  |  |
| secretkey_ml | VARCHAR | Sí |  |  |  |
| redirecturi_ml | VARCHAR | Sí |  |  |  |
| siteid_ml | VARCHAR | Sí |  |  |  |
| nickname_ml | VARCHAR | Sí |  |  |  |
| url_api | VARCHAR | Sí |  |  |  |
| fecha_token_ml | DATE | Sí |  |  |  |
| id_sucursal | INT | Sí |  |  |  |
| id_punto_venta | INT | Sí |  |  |  |
| id_viajante | INT | Sí |  |  |  |
| id_deposito_despacho | INT | Sí |  |  |  |

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
| IngresoUsuario.frm | 4436 | SELECT | rs.Open "SELECT * FROM ml_configuracion ", conn, adOpenDynam… |
| ecom_datos_articulo.frm | 3904 | SELECT | rs.Open "SELECT * FROM ml_configuracion ", conn, adOpenDynam… |
| ml_configuracion.frm | 685 | SELECT | rs.Open "SELECT * from ml_configuracion", conn, adOpenDynami… |
| ml_configuracion.frm | 718 | SELECT | rs.Open "SELECT * FROM ml_configuracion " & _ |
| ml_configuracion.frm | 766 | SELECT | rs.Open "SELECT * FROM ml_configuracion ", conn, adOpenDynam… |
| ml_configuracion.frm | 807 | SELECT | rs.Open "SELECT * from ml_configuracion", conn, adOpenDynami… |
| Funciones.bas | 10003 | UPDATE | conn.Execute "UPDATE ml_configuracion SET fecha_token_ml = '… |
| Funciones.bas | 10034 | SELECT | rs.Open "SELECT * FROM ml_configuracion ", conn, adOpenDynam… |
| Funciones.bas | 10099 | UPDATE | '            conn.Execute "UPDATE ml_configuracion SET fecha… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)