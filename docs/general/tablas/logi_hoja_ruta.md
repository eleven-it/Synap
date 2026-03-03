# Tabla `logi_hoja_ruta`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_ruta | DOUBLE | No | ✓ |  |  |
| nro_ruta | VARCHAR | Sí |  |  |  |
| nro_ruta_busq | DOUBLE | Sí |  |  |  |
| desc_ruta | VARCHAR | Sí |  |  |  |
| estado_ruta | VARCHAR | Sí |  |  |  |
| id_zona | DOUBLE | Sí |  |  |  |
| id_chofer | DOUBLE | Sí |  |  |  |
| id_unidad | DOUBLE | Sí |  |  |  |
| fecha_hora_creac | TIMESTAMP | No |  |  |  |
| fecha_hora_cierre | DATETIME | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_usuario_inicio | DOUBLE | Sí |  |  |  |
| id_usuario_cierre | DOUBLE | Sí |  |  |  |
| fecha_salida | DATETIME | Sí |  |  |  |
| rendida | VARCHAR | Sí |  |  |  |
| cancelada | VARCHAR | Sí |  |  |  |
| descripcion_zona | VARCHAR | Sí |  |  |  |
| descripcion_chofer | VARCHAR | Sí |  |  |  |
| fecha_cobranza | DATETIME | Sí |  |  |  |
| fecha_llegada | DATETIME | Sí |  |  |  |
| hora_desde | TIME | Sí |  |  |  |
| hora_hasta | TIME | Sí |  |  |  |
| diferencia_rendicion | DOUBLE | Sí |  |  |  |

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
| Logi_ABMRuta.frm | 762 | SELECT | DataRuta.RecordSource = "SELECT * FROM logi_hoja_ruta " & _ |
| Logi_ABMRuta.frm | 771 | SELECT | '    DataRuta.RecordSource = "SELECT * FROM logi_hoja_ruta "… |
| Logi_ABMRuta.frm | 782 | SELECT | DataRuta.RecordSource = "SELECT * FROM logi_hoja_ruta " & _ |
| Logi_ABMRuta.frm | 829 | SELECT | '  DataRuta.RecordSource = "SELECT * FROM logi_hoja_ruta ORD… |
| Stock_Control_Entrada.frm | 661 | SELECT | "From logi_hoja_ruta " & _ |
| Stock_Control_Entrada.frm | 767 | JOIN | " LEFT JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = clie… |
| FacturaB_COPIA.frm | 13734 | SELECT | "From logi_hoja_ruta " & _ |
| FacturaB_COPIA.frm | 14921 | SELECT | "From logi_hoja_ruta " & _ |
| Pedido_prep_consulta.frm | 1688 | JOIN | '                                    "LEFT JOIN logi_hoja_ru… |
| Pedido_prep_consulta.frm | 1753 | JOIN | "LEFT JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = prepp… |
| TPV.frm | 26640 | SELECT | "From logi_hoja_ruta " & _ |
| TPV.frm | 27788 | SELECT | "From logi_hoja_ruta " & _ |
| TPV.frm | 28878 | SELECT | "From logi_hoja_ruta " & _ |
| TPV.frm | 30022 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Gestion2.frm | 3473 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta SET rendida = 'Si', " & … |
| Logi_Gestion2.frm | 3492 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta SET cancelada = 'Si' WHE… |
| Logi_Gestion2.frm | 3535 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta " & _ |
| Logi_Gestion2.frm | 4289 | SELECT | rs_ruta.Open "SELECT logi_hoja_ruta.id_ruta,logi_hoja_ruta.e… |
| Logi_Gestion2.frm | 4828 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Gestion2.frm | 4849 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Gestion2.frm | 5395 | SELECT | "FROM logi_hoja_ruta,erp_zona,logi_abm_chofer WHERE logi_hoj… |
| Logi_Gestion2.frm | 5401 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Gestion2.frm | 6548 | JOIN | "INNER JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = clie… |
| Logi_Gestion2.frm | 6562 | JOIN | "INNER JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = clie… |
| Logi_Gestion2.frm | 7270 | SELECT | rs_ruta.Open "SELECT logi_hoja_ruta.id_ruta,logi_hoja_ruta.e… |
| Logi_Gestion2.frm | 8024 | JOIN | "LEFT JOIN logi_hoja_ruta ON (cliente_datos_adicionales.id_r… |
| Logi_Gestion2.frm | 8129 | JOIN | "LEFT JOIN logi_hoja_ruta ON (cliente_datos_adicionales.id_r… |
| Logi_Gestion2.frm | 8233 | JOIN | "LEFT JOIN  logi_hoja_ruta ON (cliente_datos_adicionales.id_… |
| Logi_Gestion2.frm | 9440 | SELECT | rs_ruta.Open "SELECT logi_hoja_ruta.id_ruta,logi_hoja_ruta.e… |
| Facturacion_Ciclica.frm | 2428 | UPDATE | '                    conn.Execute "UPDATE logi_hoja_ruta " &… |
| Logi_Info.frm | 1315 | SELECT | "FROM logi_hoja_ruta,erp_zona,logi_abm_chofer WHERE " & _ |
| Logi_Info.frm | 1321 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Info.frm | 1824 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta " & _ |
| Logi_Info.frm | 1925 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Info.frm | 1971 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta " & _ |
| Logi_Info.frm | 2063 | UPDATE | '                conn.Execute "UPDATE logi_hoja_ruta " & _ |
| Logi_Gestion.frm | 4485 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta SET rendida = 'Si', " & … |
| Logi_Gestion.frm | 4504 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta SET cancelada = 'Si' WHE… |
| Logi_Gestion.frm | 4509 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta SET diferencia_rendicion… |
| Logi_Gestion.frm | 4550 | UPDATE | conn.Execute "UPDATE logi_hoja_ruta " & _ |
| Logi_Gestion.frm | 5310 | SELECT | rs_ruta.Open "SELECT logi_hoja_ruta.id_ruta,logi_hoja_ruta.e… |
| Logi_Gestion.frm | 6055 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Gestion.frm | 6080 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Gestion.frm | 6634 | SELECT | "FROM logi_hoja_ruta,erp_zona,logi_abm_chofer WHERE logi_hoj… |
| Logi_Gestion.frm | 6640 | SELECT | "From logi_hoja_ruta " & _ |
| Logi_Gestion.frm | 6661 | SELECT | "FROM logi_hoja_ruta,erp_zona,logi_abm_chofer WHERE logi_hoj… |
| Logi_Gestion.frm | 6667 | SELECT | '                            "From logi_hoja_ruta " & _ |
| Logi_Gestion.frm | 8048 | JOIN | "INNER JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = clie… |
| Logi_Gestion.frm | 8062 | JOIN | "INNER JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = clie… |
| Logi_Gestion.frm | 8789 | SELECT | rs_ruta.Open "SELECT logi_hoja_ruta.id_ruta,logi_hoja_ruta.e… |
| Logi_Gestion.frm | 9540 | JOIN | "LEFT JOIN logi_hoja_ruta ON (cliente_datos_adicionales.id_r… |
| Logi_Gestion.frm | 9561 | JOIN | "LEFT JOIN logi_hoja_ruta ON (cliente_datos_adicionales.id_r… |
| Logi_Gestion.frm | 9669 | JOIN | "LEFT JOIN logi_hoja_ruta ON (cliente_datos_adicionales.id_r… |
| Logi_Gestion.frm | 9776 | JOIN | "LEFT JOIN  logi_hoja_ruta ON (cliente_datos_adicionales.id_… |
| Logi_Gestion.frm | 11096 | SELECT | rs_ruta.Open "SELECT logi_hoja_ruta.id_ruta,logi_hoja_ruta.e… |
| Carga_DatosAdicionales.frm | 1535 | SELECT | "FROM logi_hoja_ruta,erp_zona,logi_abm_chofer WHERE logi_hoj… |
| Carga_DatosAdicionales.frm | 1541 | SELECT | "From logi_hoja_ruta " & _ |
| Carga_DatosAdicionales.frm | 1711 | SELECT | "FROM logi_hoja_ruta " & _ |
| Carga_DatosAdicionales.frm | 1715 | SELECT | "FROM logi_hoja_ruta " & _ |
| Carga_DatosAdicionales.frm | 1903 | JOIN | '                                           "LEFT JOIN logi_… |
| Carga_DatosAdicionales.frm | 1969 | SELECT | "FROM logi_hoja_ruta " & _ |
| Carga_DatosAdicionales.frm | 1974 | SELECT | "FROM logi_hoja_ruta " & _ |
| trz_trazabilidad.frm | 7774 | JOIN | "LEFT JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = logi_… |
| Stock_Control.frm | 1647 | SELECT | "From logi_hoja_ruta " & _ |
| Stock_Control.frm | 1806 | JOIN | " LEFT JOIN logi_hoja_ruta ON (logi_hoja_ruta.id_ruta = clie… |
| Stock_Control.frm | 2918 | JOIN | "LEFT JOIN logi_hoja_ruta ON (cliente_datos_adicionales.id_r… |
| FacturaB.frm | 19669 | SELECT | "From logi_hoja_ruta " & _ |
| FacturaB.frm | 20869 | SELECT | "From logi_hoja_ruta " & _ |
| FacturaA.frm | 16244 | SELECT | "From logi_hoja_ruta " & _ |
| ListadoFacturas.frm | 911 | JOIN | "LEFT JOIN  logi_hoja_ruta ON (cliente_datos_adicionales.id_… |
| ListadoFacturas.frm | 1028 | JOIN | "LEFT JOIN  logi_hoja_ruta ON (cliente_datos_adicionales.id_… |
| Pedido_prep.frm | 4106 | SELECT | "From logi_hoja_ruta " & _ |
| Pedido_prep.frm | 5404 | SELECT | rs_ruta.Open "SELECT id_ruta,id_unidad,desc_ruta FROM logi_h… |
| Logi_CargaRuta.frm | 1693 | SELECT | '            rs_ruta.Open "SELECT desc_ruta FROM logi_hoja_r… |
| Logi_CargaRuta.frm | 1709 | SELECT | rs_ruta.Open "SELECT * FROM logi_hoja_ruta WHERE id_ruta = 0… |
| Logi_CargaRuta.frm | 1795 | SELECT | Logi_ABMRuta.DataRuta.RecordSource = "SELECT * FROM logi_hoj… |
| Logi_CargaRuta.frm | 1809 | SELECT | rs_ruta.Open "SELECT * FROM logi_hoja_ruta WHERE id_ruta = "… |
| Logi_CargaRuta.frm | 1920 | SELECT | Logi_ABMRuta.DataRuta.RecordSource = "SELECT * FROM logi_hoj… |
| Pedido_Avanzado.frm | 3463 | SELECT | "From logi_hoja_ruta " & _ |
| Pedido_Avanzado.frm | 4254 | JOIN | "LEFT JOIN logi_hoja_ruta ON (cliente_datos_adicionales.id_r… |
| … | … | … | *(110 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)