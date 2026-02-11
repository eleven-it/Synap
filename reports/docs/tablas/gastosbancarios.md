# Tabla `gastosbancarios`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| CodGasto | INT | No | ✓ |  |  |
| NombreGasto | VARCHAR | No |  |  |  |
| Alicuota | INT | No |  |  |  |
| computa_libro_compras | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| id_pc | DOUBLE | Sí |  |  |  |

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
| Info_Banco.frm | 3174 | SELECT | data_gasto.RecordSource = "select * from gastosbancarios ord… |
| ABMGastoBancario.frm | 339 | SELECT | DataGasto.RecordSource = "SELECT * FROM gastosbancarios WHER… |
| ABMGastoBancario.frm | 361 | SELECT | DataGasto.RecordSource = "select * from gastosbancarios orde… |
| CargaGastoBancario.frm | 1373 | SELECT | DataGastosB.RecordSource = "select * from gastosbancarios" |
| CargaGastoBancario.frm | 1636 | SELECT | rs_GastoBanc.Open "SELECT * from gastosbancarios where CodGa… |
| CargaGastoBcario.frm | 387 | SELECT | rs_Gasto.Open "SELECT * FROM gastosbancarios WHERE CodGasto … |
| CargaGastoBcario.frm | 411 | SELECT | ABMGastoBancario.DataGasto.RecordSource = "select * from Gas… |
| CargaGastoBcario.frm | 425 | SELECT | rs_Gasto.Open "SELECT * FROM gastosbancarios WHERE CodGasto … |
| CargaGastoBcario.frm | 451 | SELECT | ABMGastoBancario.DataGasto.RecordSource = "SELECT * FROM gas… |
| CargaDeudaBancaria.frm | 1192 | SELECT | DataGastosB.RecordSource = "select * from gastosbancarios" |
| CargaDeudaBancaria.frm | 1541 | SELECT | rs_GastoBanc.Open "SELECT * from gastosbancarios where CodGa… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)