# Tabla `puestos`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| idpuesto | INT | No | ✓ |  |  |
| puesto | VARCHAR | No |  |  |  |
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
| Erp_Carga_Parte_Diario.frm | 4283 | JOIN | " LEFT JOIN puestos ON usuarios.id_puesto=puestos.idpuesto" … |
| Erp_Carga_Parte_Diario.frm | 4418 | JOIN | " LEFT JOIN puestos ON usuarios.id_puesto=puestos.idpuesto" … |
| CargaUsuario.frm | 2078 | SELECT | DataPuesto.RecordSource = "select * from puestos order by pu… |
| IngresoUsuario.frm | 2344 | SELECT | .Source = "SELECT  * FROM puestos WHERE idpuesto = " & rs_us… |
| ABMPuesto.frm | 855 | SELECT | DataPuesto.RecordSource = "select * from Puestos where IDpue… |
| ABMPuesto.frm | 864 | SELECT | DataPuesto.RecordSource = "select * from Puestos" |
| ABMPuesto.frm | 870 | SELECT | DataPuesto.RecordSource = "SELECT * from puestos order by pu… |
| ABMPuesto.frm | 905 | SELECT | DataPuesto.RecordSource = "select * from puestos order by pu… |
| ABMPuesto.frm | 1103 | SELECT | consulta = "select * from puestos  WHERE " & _ |
| CargaPuesto.frm | 489 | SELECT | rs_puestos.Open "select * from Puestos where puesto='" & Pue… |
| CargaPuesto.frm | 495 | SELECT | rs_puestos.Open "SELECT * FROM puestos where idpuesto = 1", … |
| CargaPuesto.frm | 579 | SELECT | ABMPuesto.Datapuesto.RecordSource = "select * from puestos o… |
| CargaPuesto.frm | 618 | UPDATE | conn.Execute "UPDATE puestos SET puesto='" & Puesto.Text & "… |
| CargaPuesto.frm | 657 | SELECT | ABMPuesto.Datapuesto.RecordSource = "select * from puestos o… |
| CargaPuesto.frm | 832 | SELECT | Data_Puesto_Base.RecordSource = "SELECT * FROM puestos order… |
| CargaPuesto.frm | 1455 | SELECT | Datapuesto.RecordSource = "select * from puestos where IDpue… |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3828 | JOIN | " LEFT JOIN puestos ON usuarios.id_puesto=puestos.idpuesto" … |
| Visualiza_Erp_Carga_Parte_Diario.frm | 3961 | JOIN | " LEFT JOIN puestos ON usuarios.id_puesto=puestos.idpuesto" … |
| ABMUsuarios.frm | 676 | JOIN | " LEFT JOIN puestos ON puestos.idpuesto = usuarios.id_puesto… |
| Info_Cobranza.frm | 5718 | JOIN | " LEFT JOIN puestos ON usuarios.id_puesto=puestos.idpuesto" … |
| ABMPermiso_Sistema.frm | 368 | SELECT | DataPuesto.RecordSource = "select * from puestos order by pu… |
| ABMPermiso_Sistema.frm | 663 | SELECT | consulta = "select * from puestos  WHERE " & _ |
| Funciones.bas | 3388 | SELECT | rs_consulta.Open "SELECT * FROM puestos " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)