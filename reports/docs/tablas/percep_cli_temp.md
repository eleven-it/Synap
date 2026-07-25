# Tabla `percep_cli_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percep_cli_temp | DOUBLE | No | ✓ |  |  |
| id_percep_cli_tipo | INT | Sí |  |  |  |
| alicuota_percep_cli_temp | DECIMAL | Sí |  |  |  |
| nombre_percep_temp | VARCHAR | Sí |  |  |  |
| importe_percep_cli_temp | DECIMAL | Sí |  |  |  |
| cod_afip | INT | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |

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
| NotaCredCon.frm | 2712 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 3357 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 3774 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 4078 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 5989 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredCon.frm | 5989 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredCon.frm | 6011 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 6417 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredCon.frm | 6417 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredCon.frm | 6969 | SELECT | rs_percepCliTemp.Open "SELECT * FROM percep_cli_temp WHERE i… |
| NotaCredCon.frm | 9576 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 9827 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredCon.frm | 9827 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredCon.frm | 9847 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 10832 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredCon.frm | 11380 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| FacturaB_COPIA.frm | 4430 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| FacturaB_COPIA.frm | 5360 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| FacturaB_COPIA.frm | 5740 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| FacturaB_COPIA.frm | 7991 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| FacturaB_COPIA.frm | 7991 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| FacturaB_COPIA.frm | 9794 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| FacturaB_COPIA.frm | 9794 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| FacturaB_COPIA.frm | 9821 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| FacturaB_COPIA.frm | 11584 | SELECT | rs_percepCliTemp.Open "SELECT * FROM percep_cli_temp WHERE i… |
| FacturaB_COPIA.frm | 12997 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| FacturaB_COPIA.frm | 18489 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 1497 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredDesc.frm | 1497 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredDesc.frm | 1539 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 2548 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 2744 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 3102 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 3381 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 4079 | SELECT | rs_percepCliTemp.Open "SELECT * FROM percep_cli_temp WHERE i… |
| NotaCredDesc.frm | 7549 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredDesc.frm | 7549 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCredDesc.frm | 7847 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 8631 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCredDesc.frm | 9115 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCred_COPIA.frm | 3333 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCred_COPIA.frm | 4282 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCred_COPIA.frm | 4663 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCred_COPIA.frm | 4796 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCred_COPIA.frm | 7385 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCred_COPIA.frm | 7385 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCred_COPIA.frm | 7426 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCred_COPIA.frm | 7755 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCred_COPIA.frm | 7755 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| NotaCred_COPIA.frm | 8316 | SELECT | rs_percepCliTemp.Open "SELECT * FROM percep_cli_temp WHERE i… |
| NotaCred_COPIA.frm | 9736 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| NotaCred_COPIA.frm | 13492 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 6447 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 7793 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 9416 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 10510 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 16810 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| TPV.frm | 16810 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| TPV.frm | 16859 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 16975 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 18887 | SELECT | rs_percepCliTemp.Open "SELECT * FROM percep_cli_temp WHERE i… |
| TPV.frm | 19860 | SELECT | rs_percepCliTemp.Open "SELECT * FROM percep_cli_temp WHERE i… |
| TPV.frm | 21946 | SELECT | '        rs_percep_cli_temp.Open "SELECT * FROM percep_cli_t… |
| TPV.frm | 22105 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 22952 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 32661 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 32977 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 33404 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 37307 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 37693 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 38313 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| TPV.frm | 38706 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| Logi_Gestion2.frm | 7883 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| Visualiza_Pedido.frm | 6568 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| Visualiza_Pedido.frm | 6568 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| Visualiza_Pedido.frm | 8043 | SELECT | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| Visualiza_Pedido.frm | 8043 | DELETE | conn.Execute "delete from percep_cli_temp where id_usuario =… |
| Visualiza_Pedido.frm | 8096 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| Visualiza_Pedido.frm | 8222 | SELECT | rs_percep_cli_temp.Open "SELECT * FROM percep_cli_temp WHERE… |
| Visualiza_Pedido.frm | 8449 | SELECT | '    conn.Execute "delete from percep_cli_temp where id_usua… |
| … | … | … | *(198 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)