# Tabla `activ_iibb`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| ID | INT | No | ✓ |  |  |
| nombre_iibb | VARCHAR | Sí |  |  |  |
| alicuota | DECIMAL | Sí |  |  |  |
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
| Visualiza_TPV.frm | 6999 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| TPV.frm | 15047 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| TPV.frm | 21087 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| CargaIngBrutos.frm | 242 | SELECT | rs_ingBruto.Open "SELECT * FROM activ_iibb WHERE ID = 0", co… |
| CargaIngBrutos.frm | 257 | SELECT | ABMIngBrutos.DataIngBruto.RecordSource = "SELECT * FROM acti… |
| CargaIngBrutos.frm | 268 | SELECT | rs_ingBruto.Open "SELECT * FROM activ_iibb WHERE ID =" & ABM… |
| CargaIngBrutos.frm | 286 | SELECT | ABMIngBrutos.DataIngBruto.RecordSource = "SELECT * FROM acti… |
| CargaArticulo_Original.frm | 8707 | SELECT | rs_alicuota_iibb.Open "SELECT * FROM activ_iibb", conn_datac… |
| Articulo.frm | 3392 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 3787 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 4181 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 4580 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 4938 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 5307 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 5642 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 5962 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 8761 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 9162 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 9462 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 9823 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAr… |
| Articulo.frm | 10274 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| Articulo.frm | 11535 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| Articulo.frm | 12123 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| Articulo.frm | 13129 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| Articulo.frm | 14130 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| Articulo.frm | 15133 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| Articulo.frm | 16128 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| ABMIngBrutos.frm | 298 | SELECT | DataIngBruto.RecordSource = "SELECT * FROM activ_iibb  ORDER… |
| Sup_importacion_tablas.frm | 6167 | SELECT | DataAlicuotaIB.RecordSource = "SELECT  * FROM activ_iibb ORD… |
| CargaArticulo2.frm | 8604 | SELECT | rs_alicuota_iibb.Open "SELECT * FROM activ_iibb", conn_datac… |
| TPV_Modifica_Renglon.frm | 3994 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| TPV_Seleccion_Articulo_Simple.frm | 985 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & DataAB… |
| ActDatos_Articulo.frm | 3926 | JOIN | " LEFT JOIN activ_iibb ON (activ_iibb.id = articulo.Alicuota… |
| ActDatos_Articulo.frm | 4089 | SELECT | data_alicuota_iibb.RecordSource = "SELECT * FROM activ_iibb" |
| CargaArticulo.frm | 9644 | SELECT | rs_alicuota_iibb.Open "SELECT * FROM activ_iibb", conn_datac… |
| TPV_2.frm | 14053 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| TPV_2.frm | 19165 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| ArticuloProv.frm | 6922 | SELECT | rs_iibb.Open "SELECT * FROM activ_iibb WHERE ID = " & rs_art… |
| CargaArticulo2.frm | 8604 | SELECT | rs_alicuota_iibb.Open "SELECT * FROM activ_iibb", conn_datac… |
| Funciones.bas | 4465 | SELECT | rs_consulta.Open "SELECT activ_iibb.id,activ_iibb.alicuota F… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)