# Tabla `percep_prov`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percep_prov | BIGINT | No | ✓ |  |  |
| id_jurisdiccion | BIGINT | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| importe_percep | DOUBLE | Sí |  |  |  |
| id_proveedor | BIGINT | Sí |  |  |  |
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
| PNotaCred.frm | 2987 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| POrden_CompraCopia.frm | 3018 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| PNotaDebCopia.frm | 1916 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| PFactura.frm | 4219 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| ConsultaComprobante.frm | 19489 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percep_prov WHERE co… |
| ConsultaComprobante.frm | 20145 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percep_prov WHERE co… |
| ConsultaComprobante.frm | 20616 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percep_prov WHERE co… |
| ConsultaComprobante.frm | 30505 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percep_prov WHERE co… |
| PPresupuesto.frm | 3348 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| PNotaCred_Importe.frm | 2126 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| percep_ib_compras.frm | 710 | SELECT | rs_percep_prov_visualiza.Open "SELECT * FROM percep_prov WHE… |
| percep_ib_compras.frm | 861 | SELECT | rs_percep_prov_visualiza.Open "SELECT * FROM percep_prov WHE… |
| PNotaDeb.frm | 2010 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| PNotaCredCopia.frm | 2889 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |
| POrden_Compra.frm | 3626 | SELECT | rs_percep_prov.Open "SELECT * FROM percep_prov WHERE id_perc… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)