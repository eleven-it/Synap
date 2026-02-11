# Tabla `percepcion_prov_convenio`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_percepcion_prov_convenio | DOUBLE | No | ✓ |  |  |
| id_provincia | INT | Sí |  |  |  |
| codigo_movimiento | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| monto_percepcion | DOUBLE | Sí |  |  |  |
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
| PNotaCred.frm | 2986 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| PNotaDebCopia.frm | 1915 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| PNotaDebCopia.frm | 1965 | SELECT | '            rs_percep_prov_conv.Open "SELECT * FROM percepc… |
| PNotaDebCopia.frm | 1977 | SELECT | '            rs_percep_prov_conv.Open "SELECT * FROM percepc… |
| Exportacion.frm | 920 | SELECT | " FROM percepcion_prov_convenio " & _ |
| PFactura.frm | 4218 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| PFactura.frm | 4269 | SELECT | '                        rs_percep_prov_conv.Open "SELECT * … |
| PFactura.frm | 4281 | SELECT | '                        rs_percep_prov_conv.Open "SELECT * … |
| ConsultaComprobante.frm | 19478 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| ConsultaComprobante.frm | 20134 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| ConsultaComprobante.frm | 20605 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| ConsultaComprobante.frm | 30494 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| PNotaCred_Importe.frm | 2086 | SELECT | '                    rs_percep_prov_conv.Open "SELECT * FROM… |
| PNotaCred_Importe.frm | 2098 | SELECT | '                    rs_percep_prov_conv.Open "SELECT * FROM… |
| PNotaCred_Importe.frm | 2125 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| PNotaDeb.frm | 2009 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| PNotaDeb.frm | 2059 | SELECT | '            rs_percep_prov_conv.Open "SELECT * FROM percepc… |
| PNotaDeb.frm | 2071 | SELECT | '            rs_percep_prov_conv.Open "SELECT * FROM percepc… |
| PNotaCredCopia.frm | 2888 | SELECT | rs_percep_prov_conv.Open "SELECT * FROM percepcion_prov_conv… |
| PNotaCredCopia.frm | 2938 | SELECT | '                        rs_percep_prov_conv.Open "SELECT * … |
| PNotaCredCopia.frm | 2950 | SELECT | '                        rs_percep_prov_conv.Open "SELECT * … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)