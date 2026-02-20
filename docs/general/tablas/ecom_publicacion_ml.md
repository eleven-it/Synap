# Tabla `ecom_publicacion_ml`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ecom_publicacion_ml | BIGINT | No | ✓ |  |  |
| id_articulo_adm | BIGINT | Sí |  |  |  |
| id_publicacion_ml | VARCHAR | Sí |  |  |  |
| titulo_publicacion_ml | VARCHAR | Sí |  |  |  |
| detalle_publicacion_ml | LONGTEXT | Sí |  |  |  |
| precio_neto_ml | DOUBLE | Sí |  |  |  |
| precio_final_ml | DOUBLE | Sí |  |  |  |
| stock_articulo_ml | DOUBLE | Sí |  |  |  |
| forma_cobro_ml | VARCHAR | Sí |  |  |  |
| forma_envio_ml | VARCHAR | Sí |  |  |  |
| costo_envio_ml | DOUBLE | Sí |  |  |  |
| forma_retiro_pesona | VARCHAR | Sí |  |  |  |
| tipo_publicacion_ml | VARCHAR | Sí |  |  |  |
| financiacion_cuotas_ml | INT | Sí |  |  |  |
| comision_ml | DOUBLE | Sí |  |  |  |
| garantia_publicacion | VARCHAR | Sí |  |  |  |
| condicion_articulo | VARCHAR | Sí |  |  |  |
| id_categoria_ml | VARCHAR | Sí |  |  |  |
| texto_categoria_ml | VARCHAR | Sí |  |  |  |
| visitas_publicacion_ml | BIGINT | Sí |  |  |  |
| cantidad_ventas_ml | BIGINT | Sí |  |  |  |
| enlace_publicacion_ml | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| fecha_sincronizacion | DATETIME | Sí |  |  |  |

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
| ml_sincronizacion.frm | 1570 | SELECT | '          "FROM ecom_publicacion_ml " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)