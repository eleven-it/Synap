# Tabla `viajantes`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| Nombre | VARCHAR | Sí |  |  |  |
| CodViajante | INT | No | ✓ |  |  |
| ComisionVta | DECIMAL | Sí |  |  |  |
| ComisionCob | DECIMAL | No |  |  |  |
| Zona | VARCHAR | Sí |  |  |  |
| observaciones | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| web_desc_renglon | VARCHAR | Sí |  |  |  |
| web_desc_pie | VARCHAR | Sí |  |  |  |
| web_cliente_todos | VARCHAR | Sí |  |  |  |
| cobrador | VARCHAR | Sí |  |  |  |
| clave_caja | VARCHAR | Sí |  |  |  |
| logueado | VARCHAR | Sí |  |  |  |
| detalle_logueo | VARCHAR | Sí |  |  |  |
| ip_logueo | VARCHAR | Sí |  |  |  |
| comisionesAvanzadas | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| configuracion | viajantes | Info_Estadistica.frm | 3183 | "From `configuracion`, `stock` INNER JOIN viajantes ON (`viajantes`.`CodViajante… |
| correo_usr | viajantes | Crm_CargaLlamada.frm | 2569 | '        rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FR… |
| correo_usr | viajantes | Funciones.bas | 13143 | rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FROM correo… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| Cliente.frm | 1619 | JOIN | var_left = var_left & " LEFT JOIN viajantes ON (viajantes.Co… |
| Cliente.frm | 1935 | SELECT | DataViajante.RecordSource = "select * from Viajantes WHERE  … |
| Cliente.frm | 1974 | SELECT | DataViajante.RecordSource = "select * from Viajantes where C… |
| Cliente.frm | 2181 | SELECT | DataViajante.RecordSource = "select * from Viajantes where  … |
| Cliente.frm | 2258 | SELECT | DataViajante.RecordSource = "select * from Viajantes where  … |
| Cliente.frm | 3206 | SELECT | DataViajante2.RecordSource = "SELECT * FROM viajantes " & _ |
| Cliente.frm | 3212 | SELECT | DataViajante2.RecordSource = "SELECT * FROM viajantes WHERE … |
| Cliente.frm | 3250 | JOIN | " LEFT JOIN Viajantes ON Cliente.CodViajante = Viajantes.Cod… |
| Info_Stock.frm | 11563 | SELECT | 'DataViajante.RecordSource = "SELECT * FROM viajantes WHERE … |
| Info_Stock.frm | 11571 | SELECT | DataViajante.RecordSource = "SELECT * FROM viajantes " & _ |
| Info_Stock.frm | 11577 | SELECT | DataViajante.RecordSource = "SELECT * FROM viajantes WHERE v… |
| Liq_Carga_Comision_avanzada.frm | 498 | JOIN | "JOIN viajantes v ON c.codViajante = v.codViajante " & _ |
| Liq_Carga_Comision_avanzada.frm | 511 | SELECT | rs.Open "SELECT CodViajante, Nombre FROM viajantes WHERE com… |
| Liq_Carga_Comision_avanzada.frm | 777 | SELECT | rs.Open "SELECT CodViajante, Nombre FROM viajantes WHERE com… |
| Visualiza_ReciboCobro.frm | 10788 | SELECT | rs_cobrador.Open "SELECT * FROM viajantes WHERE CodViajante … |
| Visualiza_ReciboCobro.frm | 11257 | SELECT | rs_viajante.Open "select * from viajantes where CodViajante … |
| Visualiza_ReciboCobro.frm | 11629 | SELECT | rs_viajante.Open "select * from viajantes where CodViajante … |
| Visualiza_ReciboCobro.frm | 11857 | SELECT | '        rs_viajante.Open "select * from viajantes where Cod… |
| Visualiza_ReciboCobro.frm | 12006 | SELECT | '        rs_viajante.Open "select * from viajantes where Cod… |
| Visualiza_ReciboCobro.frm | 12091 | SELECT | '        rs_viajante.Open "select * from viajantes where Cod… |
| Visualiza_ReciboCobro.frm | 12514 | SELECT | rs_vendedor.Open "SELECT * FROM viajantes WHERE CodViajante … |
| Visualiza_ReciboCobro.frm | 12517 | SELECT | rs_vendedor.Open "SELECT * FROM viajantes WHERE CodViajante … |
| Visualiza_NotaCred.frm | 2528 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| Visualiza_NotaCred.frm | 2732 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| Visualiza_NotaCred.frm | 3049 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| ABMViajantes_Sesiones_Caja.frm | 399 | UPDATE | conn.Execute "UPDATE viajantes SET viajantes.logueado = 'No'… |
| ABMViajantes_Sesiones_Caja.frm | 402 | UPDATE | conn.Execute "UPDATE viajantes SET viajantes.detalle_logueo … |
| ABMViajantes_Sesiones_Caja.frm | 405 | UPDATE | conn.Execute "UPDATE viajantes SET viajantes.ip_logueo = '' … |
| ABMViajantes_Sesiones_Caja.frm | 452 | SELECT | "FROM viajantes " & _ |
| CargaUsuario.frm | 2118 | SELECT | DataViajante.RecordSource = "select * from Viajantes WHERE  … |
| Info_Estadistica.frm | 3183 | JOIN | "From `configuracion`, `stock` INNER JOIN viajantes ON (`via… |
| Info_Estadistica.frm | 5956 | SELECT | DataViajante.RecordSource = "SELECT * FROM viajantes WHERE  … |
| Visualiza_CargaMovStock.frm | 4200 | SELECT | "FROM viajantes " & _ |
| Liq_ABM_Viajante.frm | 980 | SELECT | data_viaj_cob.RecordSource = "SELECT * FROM viajantes WHERE … |
| Liq_ABM_Viajante.frm | 994 | SELECT | data_viaj_cob.RecordSource = "SELECT * FROM viajantes WHERE … |
| NotaCredCon.frm | 3600 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCredCon.frm | 3922 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCredCon.frm | 4420 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredCon.frm | 4683 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredCon.frm | 4941 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredCon.frm | 5182 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredCon.frm | 5415 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredCon.frm | 7838 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCredCon.frm | 9300 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 5591 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 5608 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 6106 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 6114 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 6445 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 6454 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 6733 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 12708 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 13533 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 13541 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 14720 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| FacturaB_COPIA.frm | 14728 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredDesc.frm | 1373 | SELECT | rs_viajante.Open "select * from viajantes where CodViajante … |
| NotaCredDesc.frm | 2965 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCredDesc.frm | 3250 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCredDesc.frm | 4883 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredDesc.frm | 5134 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredDesc.frm | 5387 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredDesc.frm | 5631 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredDesc.frm | 5874 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCredDesc.frm | 6114 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCredDesc.frm | 7627 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCred_COPIA.frm | 4523 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCred_COPIA.frm | 5089 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCred_COPIA.frm | 5341 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCred_COPIA.frm | 5713 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCred_COPIA.frm | 5949 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| NotaCred_COPIA.frm | 9409 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| NotaCred_COPIA.frm | 10025 | SELECT | rs_informe.Open "select * from Viajantes where CodViajante =… |
| Visualiza_TPV.frm | 6120 | SELECT | rs_vendedor.Open "SELECT * FROM viajantes WHERE CodViajante … |
| Visualiza_TPV.frm | 7806 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| Visualiza_TPV.frm | 7996 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| Visualiza_TPV.frm | 8281 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| Visualiza_TPV.frm | 8441 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| TPV.frm | 12803 | SELECT | rs_vendedor.Open "SELECT * FROM viajantes WHERE anulado = 'N… |
| TPV.frm | 17366 | SELECT | rs_informe.Open "select * from viajantes where CodViajante =… |
| … | … | … | *(477 referencias más)* |

---

## 4. Uso en Synap (reports)

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| services/query_runner.py | 3032 | JOIN | LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante |
| services/query_runner.py | 3560 | JOIN | LEFT JOIN viajantes v ON v.CodViajante = cp.CodViajante |

[← Índice de tablas](../DB_INDICE_TABLAS.md)