# Tabla `fe_datos_caea`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_fe_datos_caea | BIGINT | No | ✓ |  |  |
| fecha_solicitud | DATE | Sí |  |  |  |
| periodo | VARCHAR | Sí |  |  |  |
| orden | INT | Sí |  |  |  |
| fecha_vigencia_desde | DATE | Sí |  |  |  |
| fecha_vigencia_hasta | DATE | Sí |  |  |  |
| fecha_tope | DATE | Sí |  |  |  |
| fecha_proceso | DATE | Sí |  |  |  |
| nro_caea | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| transmitido_afip | VARCHAR | Sí |  |  |  |
| fecha_transmision | DATETIME | Sí |  |  |  |
| fecha_control | TIMESTAMP | Sí |  |  |  |
| id_pv | INT | Sí |  |  |  |

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
| adm_felectronicas_caea.frm | 633 | SELECT | consulta = "SELECT fe_datos_caea.*,punto_venta.id_punto_vent… |
| adm_felectronicas_carga_caea.frm | 811 | SELECT | rs_caea.Open "SELECT * FROM fe_datos_caea WHERE id_fe_datos_… |
| Funciones.bas | 4325 | SELECT | " FROM fe_datos_caea " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)