# Tabla `impuesto_interno_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_impuesto_interno_abm | BIGINT | No | ✓ |  |  |
| descripcion_impuesto_interno | VARCHAR | Sí |  |  |  |
| tipo_impuesto_interno | VARCHAR | Sí |  |  |  |
| porcentaje | DOUBLE | Sí |  |  |  |
| monto_fijo | DOUBLE | Sí |  |  |  |
| peso_calculo | DOUBLE | Sí |  |  |  |
| pago_minimo | DOUBLE | Sí |  |  |  |
| id_unimed | INT | Sí |  |  |  |
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
| ABM_ImpuestoInterno.frm | 430 | SELECT | consulta = "SELECT impuesto_interno_abm.* FROM impuesto_inte… |
| CargaArticulo.frm | 9657 | SELECT | rs_impuesto_interno.Open "SELECT * FROM impuesto_interno_abm… |
| Carga_ABM_ImpuestoInterno.frm | 404 | SELECT | rs.Open "SELECT * FROM impuesto_interno_abm WHERE descripcio… |
| Carga_ABM_ImpuestoInterno.frm | 420 | SELECT | rs.Open "SELECT * FROM impuesto_interno_abm WHERE id_impuest… |
| Carga_ABM_ImpuestoInterno.frm | 451 | SELECT | rs.Open "SELECT * FROM impuesto_interno_abm WHERE id_impuest… |
| Funciones.bas | 13014 | SELECT | " FROM impuesto_interno_abm " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)