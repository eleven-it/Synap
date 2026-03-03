# Tabla `en_vale_viaje`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_vale | BIGINT | No | ✓ |  |  |
| CodigoMovimiento | BIGINT | Sí |  |  |  |
| nro_comprobante | VARCHAR | Sí |  |  |  |
| nro_comp_busq | VARCHAR | Sí |  |  |  |
| id_en_chofer | BIGINT | Sí |  |  |  |
| id_pesaje | BIGINT | Sí |  |  |  |
| id_precio_zona_origen | BIGINT | Sí |  |  |  |
| id_zona_destino | BIGINT | Sí |  |  |  |
| peso_transportado | DECIMAL | Sí |  |  |  |
| id_iva | BIGINT | Sí |  |  |  |
| precio_neto | DECIMAL | Sí |  |  |  |
| precio_final | DECIMAL | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| observaciones | TEXT | Sí |  |  |  |
| tipo_viaje | VARCHAR | Sí |  |  |  |
| id_usuario | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| nombre_zona_destino | VARCHAR | Sí |  |  |  |
| estado | VARCHAR | Sí |  |  |  |
| nombre_productor | VARCHAR | Sí |  |  |  |
| CodigoProductor | BIGINT | Sí |  |  |  |
| id_temporada | BIGINT | Sí |  |  |  |
| fecha_hora | DATETIME | Sí |  |  |  |

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
| PFactura.frm | 4182 | UPDATE | conn.Execute "UPDATE en_vale_viaje SET en_vale_viaje.estado=… |
| ConsultaComprobante.frm | 3460 | JOIN | " LEFT JOIN en_vale_viaje as v ON  (v.id_pesaje = p.id_pesaj… |
| ConsultaComprobante.frm | 3485 | JOIN | " LEFT JOIN en_vale_viaje as v ON  (v.id_pesaje = p.id_pesaj… |
| ConsultaComprobante.frm | 3613 | SELECT | " FROM en_vale_viaje  AS v" & _ |
| ConsultaComprobante.frm | 3641 | SELECT | " FROM en_vale_viaje  AS v" & _ |
| ConsultaComprobante.frm | 5165 | SELECT | rs_vale_pesaje.Open "SELECT * FROM en_vale_viaje WHERE en_va… |
| ConsultaComprobante.frm | 5439 | SELECT | rs_vale_psj.Open "SELECT * FROM en_vale_viaje WHERE en_vale_… |
| ConsultaComprobante.frm | 30023 | UPDATE | conn.Execute "UPDATE en_vale_viaje LEFT JOIN en_vale_factura… |
| En_Info.frm | 3724 | JOIN | "LEFT JOIN en_vale_viaje ON en_vale_viaje.CodigoProductor = … |
| En_Info.frm | 3801 | SELECT | "FROM en_vale_viaje AS vv " & _ |
| En_Pesajes_Pendientes.frm | 644 | JOIN | " LEFT JOIN en_vale_viaje AS vv ON vv.id_pesaje=p.id_pesaje"… |
| En_Carga_Pesaje.frm | 5385 | SELECT | rs_vale.Open "SELECT * FROM en_vale_viaje WHERE en_vale_viaj… |
| En_Carga_Pesaje.frm | 5413 | SELECT | rs_vale.Open "SELECT id_vale FROM en_vale_viaje WHERE en_val… |
| En_Carga_Pesaje.frm | 5460 | JOIN | "LEFT JOIN en_vale_viaje as vale ON vale.id_vale= vv.id_vale… |
| En_Liquidacion_Vales.frm | 2425 | SELECT | " FROM en_vale_viaje  AS v" & _ |
| En_Liquidacion_Vales.frm | 2692 | JOIN | " LEFT JOIN en_vale_viaje  AS v ON v.CodigoMovimiento = f.Co… |
| En_Carga_Vale.frm | 4044 | JOIN | " LEFT JOIN en_vale_viaje AS vl On vl.id_vale = vv.id_vale" … |
| En_Carga_Vale.frm | 4466 | SELECT | rs_vale.Open "SELECT * FROM en_vale_viaje WHERE en_vale_viaj… |
| En_Carga_Vale.frm | 4506 | SELECT | rs_vale.Open "SELECT id_vale FROM en_vale_viaje WHERE en_val… |
| En_Carga_Vale.frm | 4754 | JOIN | "LEFT JOIN en_vale_viaje as vale ON vale.id_vale= vv.id_vale… |
| En_Carga_Vale.frm | 5779 | JOIN | " LEFT JOIN en_vale_viaje AS vl On vl.id_vale = vv.id_vale" … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)