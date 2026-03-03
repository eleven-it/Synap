# Tabla `en_temporada`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_temporada | BIGINT | No | ✓ |  |  |
| nombre_temporada | VARCHAR | Sí |  |  |  |
| fecha_inicio | DATE | Sí |  |  |  |
| fecha_hasta | DATE | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
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
| En_CargaTemporada.frm | 445 | SELECT | rs_EnArt.Open "SELECT * FROM en_temporada WHERE nombre_tempo… |
| En_CargaTemporada.frm | 461 | SELECT | rs_EnArt.Open "SELECT * FROM en_temporada WHERE  id_temporad… |
| En_CargaTemporada.frm | 483 | SELECT | En_ABMTemporada.DataTemporada.RecordSource = "SELECT * FROM … |
| En_CargaTemporada.frm | 502 | SELECT | rs_EnArt.Open "SELECT * FROM en_temporada WHERE id_temporada… |
| En_CargaTemporada.frm | 525 | SELECT | En_ABMTemporada.DataTemporada.RecordSource = "SELECT * From … |
| En_Carga_Precio_Zona_Temporada.frm | 1227 | SELECT | consulta = "SELECT id_temporada,nombre_temporada FROM en_tem… |
| ConsultaComprobante.frm | 3459 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = p.id_tempo… |
| ConsultaComprobante.frm | 3484 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = p.id_tempo… |
| ConsultaComprobante.frm | 3616 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = v.id_tempo… |
| ConsultaComprobante.frm | 3644 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = v.id_tempo… |
| En_Info.frm | 3713 | SELECT | consulta = "SELECT id_temporada,nombre_temporada FROM en_tem… |
| En_Carga_Clasificacion_Pesaje.frm | 1490 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = p.id_tempo… |
| En_Pesajes_Pendientes.frm | 642 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = p.id_tempo… |
| En_Carga_Tara_Temporada.frm | 1565 | SELECT | consulta = "SELECT id_temporada,nombre_temporada FROM en_tem… |
| En_ABMTemporada.frm | 509 | SELECT | consulta = "SELECT * FROM en_temporada WHERE anulado <> 'Si'… |
| En_Carga_Pesaje.frm | 6467 | SELECT | consulta = "SELECT id_temporada,nombre_temporada FROM en_tem… |
| En_Liquidacion_Vales.frm | 2428 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = v.id_tempo… |
| En_Liquidacion_Vales.frm | 2580 | SELECT | consulta = "SELECT id_temporada,nombre_temporada FROM en_tem… |
| En_Liquidacion_Vales.frm | 2695 | JOIN | " LEFT JOIN en_temporada As t ON t.id_temporada = v.id_tempo… |
| En_Carga_Vale.frm | 5397 | SELECT | consulta = "SELECT id_temporada,nombre_temporada FROM en_tem… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)