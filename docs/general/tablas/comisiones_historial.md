# Tabla `comisiones_historial`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_historial | INT | No | ✓ |  |  |
| sesion_id | VARCHAR | No |  |  |  |
| codViajante | INT | No |  |  |  |
| tipoComision | VARCHAR | No |  |  |  |
| tipoCalculo | VARCHAR | No |  |  |  |
| cantidadVendida | INT | No |  |  |  |
| monto_base | DECIMAL | No |  |  |  |
| porcentaje_comision | DECIMAL | No |  |  |  |
| monto_comision | DECIMAL | No |  |  |  |
| fecha_registro | TIMESTAMP | Sí |  |  |  |
| fecha_inicio | DATE | No |  |  |  |
| fecha_fin | DATE | No |  |  |  |
| nombreViajante | VARCHAR | Sí |  |  |  |

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
| Liq_Impresion_Comisiones_Avanzadas.frm | 485 | SELECT | sql = "SELECT DISTINCT codViajante, nombreViajante FROM comi… |
| Liq_Impresion_Comisiones_Avanzadas.frm | 543 | SELECT | sql = "SELECT DISTINCT sesion_id, fecha_inicio, fecha_fin FR… |
| Liq_Impresion_Comisiones_Avanzadas.frm | 664 | SELECT | "SELECT * FROM comisiones_historial " & _ |
| Liq_Impresion_Comisiones_Avanzadas.frm | 729 | SELECT | "            WHERE id_historial IN (SELECT id_historial FROM… |
| Liq_Impresion_ComisionesAvanzadas.frm | 506 | SELECT | sql = "SELECT DISTINCT codViajante, nombreViajante FROM comi… |
| Liq_Impresion_ComisionesAvanzadas.frm | 566 | SELECT | sql = "SELECT DISTINCT sesion_id, fecha_inicio, fecha_fin FR… |
| Liq_Impresion_ComisionesAvanzadas.frm | 669 | SELECT | "SELECT * FROM comisiones_historial " & _ |
| Liq_Impresion_ComisionesAvanzadas.frm | 737 | SELECT | "            WHERE id_historial IN (SELECT id_historial FROM… |
| Liq_ABM_Comision_avanzada.frm | 1058 | SELECT | "FROM comisiones_historial h " & _ |
| Liq_ABM_Comision_avanzada.frm | 1191 | SELECT | "            WHERE id_historial IN (SELECT id_historial FROM… |
| Liq_ABM_Comision_avanzada.frm | 1307 | INSERT | sqlInsertHistorial = "INSERT INTO comisiones_historial " & _ |
| Liq_ABM_Comision_avanzada.frm | 1403 | SELECT | sqlEliminar = "DELETE FROM comisiones_historial " & _ |
| Liq_ABM_Comision_avanzada.frm | 1403 | DELETE | sqlEliminar = "DELETE FROM comisiones_historial " & _ |
| Liq_ABM_Comision_avanzada.frm | 1445 | SELECT | consulta = "SELECT COUNT(*) AS cantidadLiquidaciones FROM co… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)