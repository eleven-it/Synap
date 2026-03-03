# Tabla `erp_encuesta`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_encuesta | INT | No | ✓ |  |  |
| tipocomprobante | VARCHAR | Sí |  |  |  |
| codigomovimiento | INT | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| id_cliente | INT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| resultado | INT | Sí |  |  |  |
| resultado_texto | VARCHAR | Sí |  |  |  |

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
| Erp_Carga_Parte_Diario.frm | 3075 | SELECT | rs_encuesta_temp.Open "SELECT * FROM erp_encuesta WHERE erp_… |
| Erp_Carga_Parte_Diario.frm | 3078 | UPDATE | conn.Execute "UPDATE erp_encuesta " & _ |
| Erp_Carga_Parte_Diario.frm | 3085 | SELECT | rs_encuesta.Open "SELECT * FROM erp_encuesta WHERE erp_encue… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2520 | SELECT | rs_encuesta_temp.Open "SELECT * FROM erp_encuesta WHERE erp_… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2523 | UPDATE | conn.Execute "UPDATE erp_encuesta " & _ |
| Visualiza_Erp_Carga_Parte_Diario.frm | 2530 | SELECT | rs_encuesta.Open "SELECT * FROM erp_encuesta WHERE erp_encue… |
| Visualiza.bas | 8667 | SELECT | rs_encuesta.Open "SELECT * FROM erp_encuesta WHERE tipocompr… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)