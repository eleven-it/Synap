# Tabla `en_pesaje`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_pesaje | BIGINT | No | ✓ |  |  |
| fecha | DATE | Sí |  |  |  |
| tipo_comprobante | VARCHAR | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| CodigoMovimiento | BIGINT | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| nro_comp_busq | VARCHAR | Sí |  |  |  |
| id_en_chofer | BIGINT | Sí |  |  |  |
| CodigoProveedor | BIGINT | Sí |  |  |  |
| IDArt | BIGINT | Sí |  |  |  |
| total_tara_bines | DECIMAL | Sí |  |  |  |
| peso_bruto | DECIMAL | Sí |  |  |  |
| peso_neto | DECIMAL | Sí |  |  |  |
| peso_tara | DECIMAL | Sí |  |  |  |
| fecha_hora_ingreso | DATETIME | Sí |  |  |  |
| fecha_hora_salida | DATETIME | Sí |  |  |  |
| total_tara_vehiculo | DECIMAL | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| id_temporada | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| fecha_control | TIMESTAMP | No |  |  |  |
| nombre_proveedor | VARCHAR | Sí |  |  |  |
| numero_remito_prov | VARCHAR | Sí |  |  |  |
| fecha_remito_prov | DATE | Sí |  |  |  |
| nombre_materia_prima | VARCHAR | Sí |  |  |  |
| observaciones | VARCHAR | Sí |  |  |  |
| cla_primera_por | DECIMAL | Sí |  |  |  |
| cla_primera_valor | DECIMAL | Sí |  |  |  |
| cla_segunda_por | DECIMAL | Sí |  |  |  |
| cla_segunda_valor | DECIMAL | Sí |  |  |  |
| cla_moler_por | DECIMAL | Sí |  |  |  |
| cla_moler_valor | DECIMAL | Sí |  |  |  |
| cla_svalor_por | DECIMAL | Sí |  |  |  |
| cla_svalor_valor | DECIMAL | Sí |  |  |  |

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
| ConsultaComprobante.frm | 3457 | SELECT | " FROM en_pesaje  AS p" & _ |
| ConsultaComprobante.frm | 3482 | SELECT | " FROM en_pesaje  AS p" & _ |
| ConsultaComprobante.frm | 3615 | JOIN | " LEFT JOIN en_pesaje as p ON  v.id_pesaje = p.id_pesaje" & … |
| ConsultaComprobante.frm | 5142 | SELECT | rs_pesaje.Open "SELECT * FROM en_pesaje WHERE en_pesaje.id_p… |
| En_Info.frm | 3723 | JOIN | "LEFT JOIN en_pesaje ON proveedor.Codigo = en_pesaje.CodigoP… |
| En_Carga_Clasificacion_Pesaje.frm | 1140 | UPDATE | conn.Execute "UPDATE en_pesaje " & _ |
| En_Carga_Clasificacion_Pesaje.frm | 1203 | UPDATE | conn.Execute "UPDATE en_pesaje SET " & var_campos & " WHERE … |
| En_Carga_Clasificacion_Pesaje.frm | 1487 | SELECT | " FROM en_pesaje  AS p" & _ |
| En_Pesajes_Pendientes.frm | 639 | SELECT | " FROM en_pesaje  AS p" & _ |
| En_Carga_Pesaje.frm | 5089 | SELECT | rs_pesaje.Open "SELECT * FROM en_pesaje WHERE en_pesaje.id_p… |
| En_Carga_Pesaje.frm | 5220 | SELECT | rs_pesaje.Open "SELECT id_pesaje FROM en_pesaje WHERE en_pes… |
| En_Carga_Pesaje.frm | 7051 | SELECT | rs_remito.Open "SELECT id_pesaje FROM en_pesaje WHERE en_pes… |
| En_Carga_Pesaje.frm | 7052 | SELECT | Debug.Print "sqlRemito:=> " & "SELECT id_pesaje FROM en_pesa… |
| En_Liquidacion_Vales.frm | 2427 | JOIN | " LEFT JOIN en_pesaje as p ON  v.id_pesaje = p.id_pesaje" & … |
| En_Liquidacion_Vales.frm | 2589 | SELECT | "FROM en_pesaje " & _ |
| En_Liquidacion_Vales.frm | 2694 | JOIN | " LEFT JOIN en_pesaje as p ON  v.id_pesaje = p.id_pesaje" & … |
| En_Carga_Vale.frm | 4300 | SELECT | '    rs_pesaje.Open "SELECT id_pesaje FROM en_pesaje WHERE e… |
| En_Carga_Vale.frm | 4500 | UPDATE | conn.Execute "UPDATE en_pesaje SET estado='En Frigor�fico' W… |
| En_Carga_Vale.frm | 5691 | SELECT | rs_pesaje.Open "SELECT * FROM en_pesaje AS p WHERE p.id_pesa… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)