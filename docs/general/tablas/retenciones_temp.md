# Tabla `retenciones_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodRetencion | INT | No |  |  |  |
| NroCertificado | DECIMAL | No |  |  |  |
| CodCliente | INT | No |  |  |  |
| Fecha | DATE | No |  |  |  |
| Porcentaje | DECIMAL | No |  |  |  |
| Importe | DECIMAL | No |  |  |  |
| CodUsuario | INT | No |  |  |  |
| CodAgentRet | INT | Sí |  |  |  |
| NroREC | VARCHAR | No |  |  |  |
| id_retenciones_temp | INT | No | ✓ |  |  |
| CodBanco | DOUBLE | Sí |  |  |  |
| tipo_retencion | VARCHAR | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| codigo_movimiento_fact | DOUBLE | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 7538 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| Visualiza_ReciboCobro.frm | 7538 | DELETE | conn.Execute "delete from retenciones_temp where Codusuario … |
| Visualiza_ReciboCobro.frm | 8161 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| Visualiza_ReciboCobro.frm | 8161 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| Visualiza_ReciboCobro.frm | 8872 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| Visualiza_ReciboCobro.frm | 8884 | SELECT | DataRetencionTemp.RecordSource = "select retenciones_temp.*,… |
| Visualiza_ReciboCobro.frm | 8918 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| Visualiza_ReciboCobro.frm | 8929 | SELECT | DataRetencionTemp.RecordSource = "select Retenciones_Temp.*,… |
| Visualiza_ReciboCobro.frm | 10745 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| Visualiza_ReciboCobro.frm | 10745 | DELETE | conn.Execute "delete from retenciones_temp where Codusuario … |
| CuentaCliente.frm | 2191 | SELECT | '        conn.Execute "delete from retenciones_temp where Co… |
| CuentaCliente.frm | 2191 | DELETE | '        conn.Execute "delete from retenciones_temp where Co… |
| CuentaCliente.frm | 2335 | SELECT | '                Visualiza_ReciboCobro.DataRetencionTemp.Rec… |
| CuentaCliente.frm | 2356 | SELECT | '                    Visualiza_ReciboCobro.DataRetencionTemp… |
| Logi_Gestion2.frm | 5116 | SELECT | '                conn.Execute "DELETE FROM retenciones_temp … |
| Logi_Gestion2.frm | 5116 | DELETE | '                conn.Execute "DELETE FROM retenciones_temp … |
| Logi_Gestion2.frm | 5119 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| Logi_Gestion2.frm | 5119 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| Logi_Gestion2.frm | 5931 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE codUsuario … |
| Logi_Gestion2.frm | 5931 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE codUsuario … |
| Logi_Gestion2.frm | 9775 | JOIN | '                "LEFT JOIN retenciones_temp ON (retenciones… |
| Logi_Gestion2.frm | 9824 | SELECT | "FROM retenciones_temp " & _ |
| Logi_Gestion2.frm | 9908 | SELECT | "FROM retenciones_temp where Codusuario = " & Principal.idUs… |
| Logi_Gestion2.frm | 9922 | SELECT | '    DataRetencionTemp.RecordSource = "select retenciones_te… |
| Logi_Gestion.frm | 6359 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| Logi_Gestion.frm | 6359 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| Logi_Gestion.frm | 6362 | SELECT | '                 conn.Execute "DELETE FROM retenciones_temp… |
| Logi_Gestion.frm | 6362 | DELETE | '                 conn.Execute "DELETE FROM retenciones_temp… |
| Logi_Gestion.frm | 7255 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE codUsuario … |
| Logi_Gestion.frm | 7255 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE codUsuario … |
| Logi_Gestion.frm | 11440 | JOIN | '                "LEFT JOIN retenciones_temp ON (retenciones… |
| Logi_Gestion.frm | 11489 | SELECT | "FROM retenciones_temp " & _ |
| Logi_Gestion.frm | 11573 | SELECT | "FROM retenciones_temp where Codusuario = " & Principal.idUs… |
| Logi_Gestion.frm | 11587 | SELECT | '    DataRetencionTemp.RecordSource = "select retenciones_te… |
| trz_trazabilidad.frm | 7248 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| trz_trazabilidad.frm | 7248 | DELETE | conn.Execute "delete from retenciones_temp where Codusuario … |
| trz_trazabilidad.frm | 7437 | SELECT | Visualiza_ReciboCobro.DataRetencionTemp.RecordSource = "SELE… |
| trz_trazabilidad.frm | 7458 | SELECT | Visualiza_ReciboCobro.DataRetencionTemp.RecordSource = "SELE… |
| CargaLiquidacionTC.frm | 1896 | SELECT | DataRetencionTemp.RecordSource = "select * from Retenciones_… |
| CargaLiquidacionTC.frm | 2245 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| CargaLiquidacionTC.frm | 2260 | SELECT | '    DataRetencionTemp.RecordSource = "select * from Retenci… |
| CargaLiquidacionTC.frm | 2263 | SELECT | DataRetencionTemp.RecordSource = "select Retenciones_Temp.*,… |
| CargaLiquidacionTC.frm | 2291 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| CargaLiquidacionTC.frm | 2291 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| ReciboCobro.frm | 8054 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| ReciboCobro.frm | 8054 | DELETE | conn.Execute "delete from retenciones_temp where Codusuario … |
| ReciboCobro.frm | 8583 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| ReciboCobro.frm | 8583 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| ReciboCobro.frm | 9439 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| ReciboCobro.frm | 9451 | SELECT | DataRetencionTemp.RecordSource = "select retenciones_temp.*,… |
| ReciboCobro.frm | 9485 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| ReciboCobro.frm | 9496 | SELECT | DataRetencionTemp.RecordSource = "select Retenciones_Temp.*,… |
| ReciboCobro.frm | 11740 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| ReciboCobro.frm | 11740 | DELETE | conn.Execute "delete from retenciones_temp where Codusuario … |
| Visualiza_ReciboCobroC.frm | 7304 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| Visualiza_ReciboCobroC.frm | 7304 | DELETE | conn.Execute "delete from retenciones_temp where Codusuario … |
| Visualiza_ReciboCobroC.frm | 7927 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| Visualiza_ReciboCobroC.frm | 7927 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| Visualiza_ReciboCobroC.frm | 8531 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| Visualiza_ReciboCobroC.frm | 8543 | SELECT | DataRetencionTemp.RecordSource = "select retenciones_temp.*,… |
| Visualiza_ReciboCobroC.frm | 8577 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| Visualiza_ReciboCobroC.frm | 8588 | SELECT | DataRetencionTemp.RecordSource = "select Retenciones_Temp.*,… |
| Visualiza_ReciboCobroC.frm | 10402 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| Visualiza_ReciboCobroC.frm | 10402 | DELETE | conn.Execute "delete from retenciones_temp where Codusuario … |
| Principal.frm | 6098 | SELECT | conn.Execute "delete from retenciones_temp where CodUsuario … |
| Principal.frm | 6098 | DELETE | conn.Execute "delete from retenciones_temp where CodUsuario … |
| Principal.frm | 6164 | SELECT | conn.Execute "delete from retenciones_temp where CodUsuario … |
| Principal.frm | 6164 | DELETE | conn.Execute "delete from retenciones_temp where CodUsuario … |
| CargaRetencion.frm | 573 | SELECT | DataRetencionTemp.RecordSource = "SELECT * FROM retenciones_… |
| CargaRetencion.frm | 624 | SELECT | DataRetencionTemp.RecordSource = "SELECT * FROM retenciones_… |
| CargaRetencion.frm | 676 | SELECT | Logi_GestionRec.DataRetencionTemp.RecordSource = "SELECT * F… |
| Logi_GestionRec.frm | 1991 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| Logi_GestionRec.frm | 1991 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE id_retencio… |
| Logi_GestionRec.frm | 2038 | SELECT | rs_retenciones_temp.Open "SELECT SUM(importe) as TotalRet FR… |
| Logi_GestionRec.frm | 2049 | SELECT | DataRetencionTemp.RecordSource = "select Retenciones_Temp.*,… |
| Logi_GestionRec.frm | 2177 | SELECT | "FROM retenciones_temp " & _ |
| Logi_GestionRec.frm | 2194 | SELECT | "FROM retenciones_temp,tipo_retencion_cli " & _ |
| Logi_GestionRec.frm | 2318 | SELECT | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| Logi_GestionRec.frm | 2318 | DELETE | conn.Execute "DELETE FROM retenciones_temp WHERE CodUsuario … |
| Visualiza.bas | 6144 | SELECT | conn.Execute "delete from retenciones_temp where Codusuario … |
| … | … | … | *(3 referencias más)* |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)