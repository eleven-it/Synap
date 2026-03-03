# Tabla `comisiones_historial_detalle`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id | INT | No | ✓ |  |  |
| id_historial | INT | No |  |  |  |
| id_stock | BIGINT | No |  |  |  |
| porcentaje | DECIMAL | Sí |  |  |  |
| monto_base | DECIMAL | Sí |  |  |  |
| monto_comision | DECIMAL | Sí |  |  |  |

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
| Liq_Impresion_Comisiones_Avanzadas.frm | 728 | SELECT | sql = sql & "WHERE s.id_stock IN (SELECT id_stock FROM comis… |
| Liq_Impresion_ComisionesAvanzadas.frm | 736 | SELECT | sql = sql & "WHERE s.id_stock IN (SELECT id_stock FROM comis… |
| Liq_ABM_Comision_avanzada.frm | 1190 | SELECT | sql = sql & "WHERE s.id_stock IN (SELECT id_stock FROM comis… |
| Liq_ABM_Comision_avanzada.frm | 1323 | INSERT | 'sqlInsertDetalle = "INSERT INTO comisiones_historial_detall… |
| Liq_ABM_Comision_avanzada.frm | 1349 | INSERT | sqlInsertDetalleLote = "INSERT INTO comisiones_historial_det… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)