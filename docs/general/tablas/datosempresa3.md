# Tabla `datosempresa3`

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
| Funciones.bas | 2920 | SELECT | rs_consulta3.Open "SELECT cuit,id_empresa FROM datosempresa3… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)