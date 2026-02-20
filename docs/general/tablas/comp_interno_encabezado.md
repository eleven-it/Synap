# Tabla `comp_interno_encabezado`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_comp_interno_encabezado | BIGINT | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| comprobante | VARCHAR | Sí |  |  |  |
| nro_comp | VARCHAR | Sí |  |  |  |
| nro_comp_busq | DOUBLE | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| codigo_movimiento_comp_orig | DOUBLE | Sí |  |  |  |
| id_cliente | BIGINT | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| id_sucursal | DOUBLE | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |
| fecha_control | TIMESTAMP | Sí |  |  |  |
| estado_comp | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |

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
| ConsultaComprobante.frm | 2616 | SELECT | DataConsulta.RecordSource = "SELECT comp_interno_encabezado.… |
| ConsultaComprobante.frm | 2624 | SELECT | DataConsulta.RecordSource = "SELECT comp_interno_encabezado.… |
| Funciones.bas | 7803 | SELECT | rs_mov_comp_int.Open "select * from comp_interno_encabezado … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)