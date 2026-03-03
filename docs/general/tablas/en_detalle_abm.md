# Tabla `en_detalle_abm`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_detalle_abm | DOUBLE | No | ✓ |  |  |
| nombre_en_detalle_abm | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| gasto_externo | VARCHAR | Sí |  |  |  |
| desc_stock_form | VARCHAR | Sí |  |  |  |
| orden_etapa | INT | Sí |  |  |  |

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
| En_abmRef.frm | 455 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE N… |
| En_abmRef.frm | 624 | SELECT | rs_validacion.Open "SELECT * FROM en_detalle_abm WHERE anula… |
| En_abmRef.frm | 643 | SELECT | rs_validacion.Open "SELECT * FROM en_detalle_abm WHERE anula… |
| En_OrdenRef.frm | 498 | UPDATE | conn.Execute "UPDATE en_detalle_abm " & _ |
| En_OrdenRef.frm | 551 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE A… |
| En_Carga_UsuRef.frm | 840 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE a… |
| En_GeneraOE.frm | 2871 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraOE.frm | 2875 | SELECT | "FROM en_detalle_abm WHERE en_detalle_abm.id_en_detalle_abm … |
| En_GeneraOE.frm | 3365 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraOE.frm | 3450 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraOE.frm | 4758 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GestionOE.frm | 792 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GestionOE.frm | 818 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GestionOE.frm | 829 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GestionOE.frm | 853 | JOIN | '                            "LEFT JOIN en_detalle_abm ON (e… |
| En_GestionOE.frm | 905 | SELECT | rs_orden.Open "SELECT orden_etapa FROM en_detalle_abm WHERE … |
| En_GestionOE.frm | 915 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_GestionOE.frm | 920 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_GestionOE.frm | 932 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_GestionOE.frm | 938 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_GestionOE.frm | 1157 | SELECT | rs_taller.Open "SELECT * FROM en_detalle_abm WHERE gasto_ext… |
| En_GestionOE.frm | 1735 | JOIN | "RIGHT OUTER JOIN en_detalle_abm ON (en_detalle_abm.id_en_de… |
| En_GestionOE.frm | 1800 | SELECT | rs_orden.Open "SELECT orden_etapa FROM en_detalle_abm WHERE … |
| En_GestionOE.frm | 1808 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| ConsultaComprobante.frm | 3307 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| ConsultaComprobante.frm | 3325 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| Visualiza_En_GeneraOE.frm | 3004 | SELECT | rs_gastoExt.Open "SELECT id_en_detalle_abm FROM en_detalle_a… |
| Visualiza_En_GeneraOE.frm | 3062 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| Visualiza_En_GeneraOE.frm | 3066 | SELECT | "FROM en_detalle_abm WHERE en_detalle_abm.id_en_detalle_abm … |
| Visualiza_En_GeneraOE.frm | 3144 | SELECT | rs_orden.Open "SELECT orden_etapa FROM en_detalle_abm WHERE … |
| Visualiza_En_GeneraOE.frm | 3150 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| Visualiza_En_GeneraOE.frm | 4496 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| Visualiza_En_GeneraOE.frm | 4604 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| Visualiza_En_GeneraOE.frm | 5773 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraPOE.frm | 1350 | SELECT | "FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 1538 | SELECT | '                            "FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 1764 | SELECT | "FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 1882 | SELECT | "FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 2462 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraPOE.frm | 2484 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraPOE.frm | 2495 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraPOE.frm | 2555 | SELECT | VarRef = "SELECT * FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 2560 | SELECT | VarRef = "SELECT * FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 2572 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 2576 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 2677 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_GeneraPOE.frm | 3543 | SELECT | rs_orden.Open "SELECT orden_etapa FROM en_detalle_abm " & _ |
| En_GeneraPOE.frm | 3549 | SELECT | "From en_detalle_abm " & _ |
| En_Carga_EtapaRef.frm | 592 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE a… |
| En_CargaOE_Ref.frm | 1048 | SELECT | rs_orden.Open "SELECT orden_etapa FROM en_detalle_abm WHERE … |
| En_CargaOE_Ref.frm | 1056 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_CargaOE_Ref.frm | 1062 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_CargaOE_Ref.frm | 1072 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_CargaOE_Ref.frm | 1078 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm " & _ |
| En_CargaOE_Ref.frm | 1090 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE g… |
| En_CargaOE_Ref.frm | 1092 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE g… |
| En_CargaOE_Ref.frm | 1098 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE g… |
| En_CargaOE_Ref.frm | 1100 | SELECT | DataRef.RecordSource = "SELECT * FROM en_detalle_abm WHERE g… |
| En_CargaOE_Ref.frm | 2033 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_CargaOE_Ref.frm | 2036 | SELECT | "FROM en_detalle_abm WHERE en_detalle_abm.id_en_detalle_abm … |
| En_CargaOE_Ref.frm | 2090 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |
| En_CargaOE_Ref.frm | 2093 | SELECT | "FROM en_detalle_abm WHERE en_detalle_abm.id_en_detalle_abm … |
| En_CargaOE_Ref.frm | 2315 | SELECT | rs_orden.Open "SELECT orden_etapa FROM en_detalle_abm " & _ |
| En_CargaOE_Ref.frm | 2324 | SELECT | "From en_detalle_abm " & _ |
| En_CargaOE_Ref.frm | 2339 | SELECT | "From en_detalle_abm " & _ |
| En_CargaRef.frm | 1224 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle_abm WHERE Nombre_en_de… |
| En_CargaRef.frm | 1240 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle_abm WHERE id_en_detall… |
| En_CargaRef.frm | 1251 | SELECT | rs_orden.Open "SELECT MAX(orden_etapa) AS MaxOrden FROM en_d… |
| En_CargaRef.frm | 1287 | SELECT | En_abmRef.DataRef.RecordSource = "SELECT * FROM en_detalle_a… |
| En_CargaRef.frm | 1307 | SELECT | rs_Ref.Open "SELECT * FROM en_detalle_abm WHERE id_en_detall… |
| En_CargaRef.frm | 1321 | SELECT | '                    rs_orden.Open "SELECT MAX(orden_etapa) … |
| En_CargaRef.frm | 1357 | SELECT | En_abmRef.DataRef.RecordSource = "SELECT * FROM en_detalle_a… |
| Visualiza.bas | 8312 | JOIN | "RIGHT OUTER JOIN en_detalle_abm ON (en_detalle_abm.id_en_de… |
| Visualiza.bas | 8376 | SELECT | rs_orden.Open "SELECT orden_etapa FROM en_detalle_abm WHERE … |
| Visualiza.bas | 8384 | JOIN | "LEFT JOIN en_detalle_abm ON (en_detalle_abm.id_en_detalle_a… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)