# Tabla `ped_pd`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ped_pd | DOUBLE | No | ✓ |  |  |
| codigo_movimiento_ped | DECIMAL | Sí |  |  |  |
| codigo_movimiento_pd | DECIMAL | Sí |  |  |  |
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
| Visualiza_Pedido.frm | 14609 | SELECT | '                    rs_ped_pd.Open "SELECT * FROM ped_pd WH… |
| trz_trazabilidad.frm | 5833 | SELECT | rs_pd.Open "SELECT * FROM ped_pd WHERE ped_pd.codigo_movimie… |
| Pedido.frm | 4666 | SELECT | rs_ped_pd.Open "SELECT * FROM ped_pd WHERE id_ped_pd = 0", c… |
| ConsultaComprobante.frm | 10307 | SELECT | rs_ped_pd.Open "SELECT * FROM ped_pd WHERE codigo_movimiento… |
| ConsultaComprobante.frm | 10336 | JOIN | '                             "LEFT JOIN  ped_pd ON pd.Codig… |
| Principal.frm | 9024 | SELECT | rs_pd.Open "SELECT * FROM ped_pd WHERE ped_pd.codigo_movimie… |
| Principal.frm | 9533 | SELECT | rs_pd.Open "SELECT * FROM ped_pd WHERE ped_pd.codigo_movimie… |
| Visualiza.bas | 993 | SELECT | rs_pd.Open "SELECT * FROM ped_pd WHERE ped_pd.codigo_movimie… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)