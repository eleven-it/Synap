# Tabla `conf_grilla`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_grilla | INT | No | ✓ |  |  |
| nombre_grilla | VARCHAR | Sí |  |  |  |
| nombre_campo | VARCHAR | Sí |  |  |  |
| index_campo | INT | Sí |  |  |  |
| activa | INT | Sí |  |  |  |
| id_puesto | INT | Sí |  |  |  |
| alineacion | INT | Sí |  |  |  |

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
| PNotaCred.frm | 4528 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Visualiza_ReciboCobro.frm | 11270 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| Visualiza_ReciboCobro.frm | 11643 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| Visualiza_ReciboCobro.frm | 11872 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| Visualiza_NotaCred.frm | 3900 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| FacturaB_COPIA.frm | 8622 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| FacturaB_COPIA.frm | 10508 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| NotaCred_COPIA.frm | 6833 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| CuentaCliente.frm | 1555 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Logi_Gestion2.frm | 8572 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Logi_Gestion2.frm | 8924 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Logi_Gestion2.frm | 9183 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Facturacion_Ciclica.frm | 3184 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Facturacion_Ciclica.frm | 3579 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Visualiza_Pedido.frm | 6433 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Logi_Gestion.frm | 10119 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Logi_Gestion.frm | 10504 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Logi_Gestion.frm | 10801 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| trz_trazabilidad.frm | 4044 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| trz_trazabilidad.frm | 4486 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| trz_trazabilidad.frm | 5490 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| trz_trazabilidad.frm | 5799 | SELECT | '            rs_grilla.Open "SELECT * FROM conf_grilla where… |
| trz_trazabilidad.frm | 6141 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| ABMArticulo_seleccion.frm | 4631 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Articulo.frm | 7295 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Visualiza_POrden_Compra.frm | 5365 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_FB_Copia.frm | 4761 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_FB_Copia.frm | 5950 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| POrden_CompraCopia.frm | 4817 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Visualiza_PNotaCredDev.frm | 3642 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| NotaCred_SinCompO.frm | 8414 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Visualiza_FA.frm | 4429 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_FA.frm | 5631 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| NotaCredCopia.frm | 7401 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| ABMArticulo_seleccion_simple.frm | 2822 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Visualiza_FB.frm | 5214 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_FB.frm | 6487 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| CargaPermiso_Sistema_Puesto.frm | 3510 | SELECT | '    Dataconf_grilla_ABMArt.RecordSource = "SELECT * FROM co… |
| CargaPermiso_Sistema_Puesto.frm | 3517 | SELECT | '    Dataconf_grilla_Art.RecordSource = "SELECT * FROM conf_… |
| CargaPermiso_Sistema_Puesto.frm | 3524 | SELECT | '    Dataconf_grilla_renglonfact.RecordSource = "SELECT * FR… |
| CargaPermiso_Sistema_Puesto.frm | 3531 | SELECT | '    Dataconf_grilla_Art_P.RecordSource = "SELECT * FROM con… |
| Presupuesto.frm | 6392 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Pedido.frm | 7673 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Visualiza_PPresupuesto.frm | 4139 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| PPresupuesto.frm | 4949 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Visualiza_PFactura_Copia.frm | 5249 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_POrden_CompraC.frm | 4675 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_NotaCredCopia.frm | 3673 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| NotaCred.frm | 7707 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Visualiza_Presupuesto.frm | 6216 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| PNotaCredCopia.frm | 4392 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| ReciboCobro.frm | 12361 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| ReciboCobro.frm | 12790 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| Visualiza_PFacturaCopia2.frm | 5388 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_PFactura.frm | 5596 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_PPresupuestoC.frm | 3969 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_PNotaCredDevC.frm | 3771 | SELECT | rs_grilla.Open "SELECT * FROM conf_grilla where nombre_grill… |
| Visualiza_ReciboCobroC.frm | 10917 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| Visualiza_ReciboCobroC.frm | 11290 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| Visualiza_ReciboCobroC.frm | 11519 | SELECT | '        rs_grilla.Open "SELECT * FROM conf_grilla where nom… |
| ArticuloProv.frm | 4930 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| Principal.frm | 8992 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Principal.frm | 9501 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| POrden_Compra.frm | 5657 | SELECT | 'rs_grilla.Open "SELECT * FROM conf_grilla where nombre_gril… |
| CargaPermiso_Sistema.frm | 4628 | SELECT | Dataconf_grilla_ABMArt.RecordSource = "SELECT * FROM conf_gr… |
| CargaPermiso_Sistema.frm | 4635 | SELECT | Dataconf_grilla_Art.RecordSource = "SELECT * FROM conf_grill… |
| CargaPermiso_Sistema.frm | 4642 | SELECT | Dataconf_grilla_renglonfact.RecordSource = "SELECT * FROM co… |
| CargaPermiso_Sistema.frm | 4649 | SELECT | Dataconf_grilla_Art_P.RecordSource = "SELECT * FROM conf_gri… |
| Visualiza.bas | 965 | SELECT | '    rs_grilla.Open "SELECT * FROM conf_grilla where nombre_… |
| Visualiza.bas | 2306 | SELECT | '     rs_grilla.Open "SELECT * FROM conf_grilla where nombre… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)