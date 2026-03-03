# Tabla `en_configuracion_bascula`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_configuracion | BIGINT | No | ✓ |  |  |
| puerto_com | INT | Sí |  |  |  |
| baudio_rate | INT | Sí |  |  |  |
| paridad_datos | VARCHAR | Sí |  |  |  |
| bits_datos | INT | Sí |  |  |  |
| bit_stop | INT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| nombre | VARCHAR | Sí |  |  |  |
| posicion_caracter_control | INT | Sí |  |  |  |
| longitud_caracter_control | INT | Sí |  |  |  |
| codigo_caracter_control | INT | Sí |  |  |  |
| posicion_inicio_dato | INT | Sí |  |  |  |
| longitud_dato_bascula | INT | Sí |  |  |  |
| dispositivo_predeterminado | VARCHAR | Sí |  |  |  |

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
| En_ABM_Configuracion_Bascula.frm | 618 | SELECT | consulta = "SELECT * FROM  en_configuracion_bascula WHERE  n… |
| En_Carga_Configuracion_Bascula.frm | 446 | SELECT | rs_EnArt.Open "SELECT * FROM en_configuracion_bascula WHERE … |
| En_Carga_Configuracion_Bascula.frm | 494 | SELECT | rs_EnArt.Open "SELECT * FROM en_configuracion_bascula WHERE … |
| En_Carga_Configuracion_Bascula.frm | 519 | UPDATE | conn.Execute "UPDATE en_configuracion_bascula AS bascula SET… |
| En_Carga_Configuracion_Bascula.frm | 707 | SELECT | cargo_data_abm = "select * from en_configuracion_bascula WHE… |
| En_Carga_Tara_Temporada.frm | 975 | SELECT | "FROM en_configuracion_bascula WHERE dispositivo_predetermin… |
| En_Carga_Pesaje.frm | 6419 | SELECT | "FROM en_configuracion_bascula WHERE dispositivo_predetermin… |
| En_Carga_Vale.frm | 5348 | SELECT | '                    "FROM en_configuracion_bascula WHERE di… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)