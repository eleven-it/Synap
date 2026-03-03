# Tabla `ecom_conf_ml`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_conf_ml | BIGINT | No | ✓ |  |  |
| promedio_porc_cm | DECIMAL | Sí |  |  |  |
| lista_precio_ml | VARCHAR | Sí |  |  |  |
| servidor_acceso_ml | VARCHAR | Sí |  |  |  |
| servidor_acceso_certificado_ml | VARCHAR | Sí |  |  |  |
| credenciales_ml | VARCHAR | Sí |  |  |  |
| token_ml | VARCHAR | Sí |  |  |  |

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
| ml_sincronizacion.frm | 1297 | SELECT | '        rslista.Open "SELECT * FROM ecom_conf_ml ", conn, a… |
| ml_sincronizacion.frm | 1876 | SELECT | rs.Open "SELECT * FROM ecom_conf_ml  ", conn, adOpenDynamic,… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)