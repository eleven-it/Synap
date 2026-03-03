# Tabla `viajantes_intervalo_liq`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_intervalo_liq | INT | No | ✓ |  |  |
| desde_intervalo_liq | DECIMAL | Sí |  |  |  |
| hasta_intervalo_liq | DECIMAL | Sí |  |  |  |
| porcentaje_intervalo_liq | DECIMAL | Sí |  |  |  |
| id_viajante | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| alicuota | DECIMAL | Sí |  |  |  |
| tipo_intervalo_liq | VARCHAR | Sí |  |  |  |

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
| Liq_ABM_Cob_Intervalo.frm | 509 | SELECT | data_intervalo_liq.RecordSource = "SELECT * FROM viajantes_i… |
| Liq_Cob_Intervalo.frm | 334 | SELECT | rs_liq_intervalo.Open "SELECT * FROM viajantes_intervalo_liq… |
| Liq_Cob_Intervalo.frm | 339 | SELECT | rs_liq_intervalo.Open "SELECT * FROM viajantes_intervalo_liq… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)