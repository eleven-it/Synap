# Tabla `pais`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_pais | INT | No | ✓ |  |  |
| nombre | VARCHAR | Sí |  |  |  |
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
| Cliente.frm | 2994 | JOIN | "LEFT JOIN pais ON (pais.id_pais = cliente_domicilio.id_pais… |
| CargaSucursal.frm | 1402 | SELECT | data_pais.RecordSource = "select * from pais order by nombre… |
| Erp_Carga_Zona.frm | 500 | SELECT | DataPais.RecordSource = "SELECT * FROM pais ORDER BY nombre" |
| CargaZona.frm | 499 | SELECT | DataPais.RecordSource = "SELECT * FROM pais ORDER BY nombre" |
| CargaProveedor.frm | 4277 | SELECT | data_pais.RecordSource = "select * from pais order by nombre… |
| Sup_importacion_tablas.frm | 6069 | SELECT | DataPais.RecordSource = "SELECT * FROM Pais ORDER BY nombre" |
| Carga_ClienteDomicilio.frm | 1680 | SELECT | data_pais.RecordSource = "select * from pais order by nombre… |
| ABMDpto.frm | 1231 | SELECT | 'data_pais.RecordSource = "select * from pais where id_pais … |
| ABMDpto.frm | 1232 | SELECT | data_pais.RecordSource = "select * from pais order by nombre… |
| ABMDpto.frm | 1729 | SELECT | data_pais.RecordSource = "SELECT * FROM pais WHERE nombre LI… |
| Carga_Cliente.frm | 6259 | SELECT | data_pais.RecordSource = "select * from pais order by nombre… |
| Empresa.frm | 1330 | SELECT | data_pais.RecordSource = "select * from pais order by nombre… |
| Visualiza.bas | 23233 | JOIN | " LEFT JOIN pais ON (pais.id_pais = cliente_domicilio.id_pai… |
| Visualiza.bas | 23246 | JOIN | " LEFT JOIN pais ON (pais.id_pais = cliente.id_pais) " & _ |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)