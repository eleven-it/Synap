# Tabla `viajantes_liq`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_viajantes_liq | DOUBLE | No | ✓ |  |  |
| periodo_desde | DATE | Sí |  |  |  |
| periodo_hasta | DATE | Sí |  |  |  |
| fecha_control | TIMESTAMP | No |  |  |  |
| fecha_liq | DATE | Sí |  |  |  |
| porcentaje_liq | DECIMAL | Sí |  |  |  |
| tipo_liq | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| cancelado | VARCHAR | Sí |  |  |  |
| id_viajante | DOUBLE | Sí |  |  |  |
| id_chofer | DOUBLE | Sí |  |  |  |
| tipo_calculo | VARCHAR | Sí |  |  |  |

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
| Liq_ABM_Viajante.frm | 1027 | SELECT | data_viajantes_liq.RecordSource = "SELECT * FROM viajantes_l… |
| Liq_ABM_Viajante.frm | 1039 | SELECT | data_viajantes_liq.RecordSource = "SELECT * FROM viajantes_l… |
| Liq_ABM_Viajante.frm | 1051 | SELECT | data_viajantes_liq.RecordSource = "SELECT * FROM viajantes_l… |
| Liq_Carga_Viajante.frm | 668 | SELECT | rs_liq.Open "SELECT * FROM viajantes_liq WHERE  id_viajantes… |
| Liq_Carga_Viajante.frm | 709 | SELECT | rs_liq.Open "SELECT * FROM viajantes_liq WHERE id_viajantes_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)