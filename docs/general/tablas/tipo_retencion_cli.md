# Tabla `tipo_retencion_cli`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodRetencion | INT | No | ✓ |  |  |
| NombreRetencion | VARCHAR | No |  |  |  |
| CodAgeRet | VARCHAR | No |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |
| id_impuesto | DOUBLE | Sí |  |  |  |
| cod_afip | INT | Sí |  |  |  |
| id_juridic_convenio | INT | Sí |  |  |  |
| tipo | VARCHAR | Sí |  |  |  |

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
| Visualiza_ReciboCobro.frm | 13574 | SELECT | rs_vect.Open "SELECT * from tipo_retencion_cli where CodRete… |
| Visualiza_ReciboCobro.frm | 14577 | SELECT | rs_vect.Open "SELECT * from tipo_retencion_cli where CodRete… |
| Info_Impositivo.frm | 2391 | SELECT | data_retencion.RecordSource = "SELECT * FROM tipo_retencion_… |
| Logi_Gestion2.frm | 9825 | JOIN | "LEFT JOIN tipo_retencion_cli ON (tipo_retencion_cli.CodRete… |
| Logi_Gestion.frm | 11490 | JOIN | "LEFT JOIN tipo_retencion_cli ON (tipo_retencion_cli.CodRete… |
| CargaRetCli.frm | 804 | SELECT | rs_tipoRet.Open "SELECT * FROM tipo_retencion_cli WHERE CodR… |
| CargaRetCli.frm | 825 | SELECT | ABMRetCli.DataTipoRet.RecordSource = "SELECT * FROM tipo_ret… |
| CargaRetCli.frm | 835 | SELECT | rs_tipoRet.Open "SELECT * FROM tipo_retencion_cli WHERE CodR… |
| Exportacion.frm | 880 | JOIN | "LEFT JOIN tipo_retencion_cli ON (tipo_retencion_cli.CodRete… |
| Exportacion.frm | 957 | JOIN | "LEFT JOIN tipo_retencion_cli ON (tipo_retencion_cli.CodRete… |
| CargaGastoBancario.frm | 1393 | SELECT | DataRetenciones.RecordSource = "select * from tipo_retencion… |
| CargaGastoBancario.frm | 1770 | SELECT | rs_ret.Open "SELECT * from tipo_retencion_cli where codReten… |
| CargaLiquidacionTC.frm | 2573 | SELECT | rs_vect.Open "SELECT * from tipo_retencion_cli where CodRete… |
| ReciboCobro.frm | 14608 | SELECT | rs_vect.Open "SELECT * from tipo_retencion_cli where CodRete… |
| ReciboCobro.frm | 15625 | SELECT | rs_vect.Open "SELECT * from tipo_retencion_cli where CodRete… |
| Visualiza_ReciboCobroC.frm | 13191 | SELECT | rs_vect.Open "SELECT * from tipo_retencion_cli where CodRete… |
| Visualiza_ReciboCobroC.frm | 14194 | SELECT | rs_vect.Open "SELECT * from tipo_retencion_cli where CodRete… |
| ABMTipoRetencion.frm | 444 | SELECT | DataTipoRet.RecordSource = "select * from Tipo_Retencion_Cli… |
| ABMTipoRetencion.frm | 556 | SELECT | consulta = "select * from Tipo_Retencion_Cli   " & _ |
| CargaRetencion.frm | 746 | SELECT | DataABMRetencion.RecordSource = "select * from tipo_retencio… |
| CargaRetencion.frm | 866 | SELECT | DataABMRetCons.RecordSource = "select * from tipo_retencion_… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)