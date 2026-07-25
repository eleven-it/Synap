# Tabla `reporte_usuario`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_reporte_usuario | DOUBLE | No | ✓ |  |  |
| id_reporte | INT | No |  |  |  |
| perfil_reporte | VARCHAR | Sí |  |  |  |
| nombre_reporte | VARCHAR | Sí |  |  |  |
| activo_reporte | INT | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |

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
| Info_Stock.frm | 11554 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Estadistica.frm | 5921 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Impositivo.frm | 2282 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Logi_Info.frm | 1294 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Banco.frm | 3074 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Venta_respaldo_bruno.frm | 9967 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Venta.frm | 10054 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Conta_Info.frm | 1663 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| CargaPuesto.frm | 943 | INSERT | conn.Execute "INSERT INTO `reporte_usuario` (`id_reporte`,`p… |
| CargaPuesto.frm | 997 | INSERT | conn.Execute "INSERT INTO `reporte_usuario` (`id_reporte`,`p… |
| CargaPuesto.frm | 1003 | SELECT | " FROM `reporte_usuario` WHERE id_puesto = " & Puesto_Base.B… |
| CargaPermiso_Sistema_Puesto.frm | 3552 | SELECT | DataPerfil.RecordSource = "SELECT DISTINCT(perfil_reporte) F… |
| CargaPermiso_Sistema_Puesto.frm | 3561 | SELECT | DataReporte.RecordSource = "SELECT * FROM reporte_usuario WH… |
| CargaPermiso_Sistema_Puesto.frm | 3904 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '-… |
| CargaPermiso_Sistema_Puesto.frm | 3906 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '0… |
| CargaPermiso_Sistema_Puesto.frm | 3934 | SELECT | DataReporte.RecordSource = "SELECT * FROM reporte_usuario WH… |
| CargaPermiso_Sistema_Puesto.frm | 3941 | SELECT | DataReporte.RecordSource = "SELECT * FROM reporte_usuario WH… |
| CargaPermiso_Sistema_Puesto.frm | 3964 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '-… |
| CargaPermiso_Sistema_Puesto.frm | 3966 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '0… |
| Info_Comercial.frm | 8191 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| En_Info.frm | 3691 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Caja.frm | 1919 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Pago.frm | 2489 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Crm_Info.frm | 1388 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_RepRapidos.frm | 896 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario "… |
| Info_RepRapidos.frm | 908 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario "… |
| Info_RepRapidos.frm | 1247 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario "… |
| Info_RepRapidos.frm | 1260 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario "… |
| Info_RepRapidos.frm | 1273 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario "… |
| Info_Cobranza.frm | 5540 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Erp_Info.frm | 3475 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Info_Compra.frm | 3183 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| Programa_Descuentos_Info.frm | 817 | SELECT | data_informe.RecordSource = "SELECT * FROM reporte_usuario W… |
| CargaPermiso_Sistema.frm | 4670 | SELECT | DataPerfil.RecordSource = "SELECT DISTINCT(perfil_reporte) F… |
| CargaPermiso_Sistema.frm | 4675 | SELECT | "From reporte_usuario " & _ |
| CargaPermiso_Sistema.frm | 4685 | SELECT | DataReporte.RecordSource = "SELECT * FROM reporte_usuario WH… |
| CargaPermiso_Sistema.frm | 4781 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '-… |
| CargaPermiso_Sistema.frm | 4783 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '0… |
| CargaPermiso_Sistema.frm | 4792 | SELECT | '    DataPerfil.RecordSource = "SELECT DISTINCT(perfil_repor… |
| CargaPermiso_Sistema.frm | 4797 | SELECT | '                            "From reporte_usuario " & _ |
| CargaPermiso_Sistema.frm | 4825 | SELECT | DataReporte.RecordSource = "SELECT * FROM reporte_usuario WH… |
| CargaPermiso_Sistema.frm | 4832 | SELECT | DataReporte.RecordSource = "SELECT * FROM reporte_usuario WH… |
| CargaPermiso_Sistema.frm | 4855 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '-… |
| CargaPermiso_Sistema.frm | 4857 | UPDATE | conn.Execute "UPDATE reporte_usuario SET activo_reporte = '0… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)