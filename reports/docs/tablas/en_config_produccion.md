# Tabla `en_config_produccion`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_config | BIGINT | Sí |  |  |  |
| cod_sub_rubro_contenedor | BIGINT | Sí |  |  |  |
| cod_sub_rubro_produccion | BIGINT | Sí |  |  |  |
| cod_deposito_contenedor | BIGINT | Sí |  |  |  |
| cod_deposito_produccion | BIGINT | Sí |  |  |  |
| cod_referencia_mstock_frigorifico | BIGINT | Sí |  |  |  |
| cod_referencia_mstock_comodato | BIGINT | Sí |  |  |  |
| cod_deposito_salida_frigorifico | BIGINT | Sí |  |  |  |

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
| En_Carga_Config_Produccion.frm | 1136 | SELECT | rs_EnArt.Open "SELECT * FROM en_config_produccion WHERE id_e… |
| En_Carga_Config_Produccion.frm | 1206 | SELECT | rs_config.Open "SELECT * FROM en_config_produccion WHERE id_… |
| En_Carga_Config_Produccion.frm | 1343 | SELECT | cargo_data_abm = "SELECT id_en_config, cod_sub_rubro_contene… |
| En_Carga_Precio_Zona_Temporada.frm | 1239 | SELECT | " FROM en_config_produccion AS cnf" & _ |
| En_Info.frm | 3764 | SELECT | "FROM en_config_produccion AS cnf " & _ |
| En_Carga_Tipo_Clasificacion.frm | 653 | SELECT | " FROM en_config_produccion AS cnf" & _ |
| En_Carga_Pesaje.frm | 6397 | SELECT | rs_config_pesaje.Open "SELECT * FROM en_config_produccion AS… |
| En_Carga_Pesaje.frm | 6522 | SELECT | "FROM en_config_produccion AS cnf " & _ |
| En_Carga_Pesaje.frm | 6558 | SELECT | " FROM en_config_produccion AS cnf" & _ |
| En_Liquidacion_Vales.frm | 2629 | SELECT | "FROM en_config_produccion AS cnf " & _ |
| En_Carga_Vale.frm | 5322 | SELECT | rs_config_pesaje.Open "SELECT * FROM en_config_produccion AS… |
| En_Carga_Vale.frm | 5452 | SELECT | "FROM en_config_produccion AS cnf " & _ |
| En_Carga_Vale.frm | 5487 | SELECT | " FROM en_config_produccion AS cnf" & _ |
| En_ABM_Config_Produccion.frm | 329 | SELECT | consulta = "SELECT id_en_config, cod_sub_rubro_contenedor, c… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)