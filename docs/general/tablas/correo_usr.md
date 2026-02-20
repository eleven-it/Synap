# Tabla `correo_usr`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_correo_usr | DOUBLE | No | ✓ |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| nombre_servidor_smtp | VARCHAR | Sí |  |  |  |
| nombre_servidor_pop3 | VARCHAR | Sí |  |  |  |
| puerto_servidor_smtp | INT | Sí |  |  |  |
| puerto_servidor_pop | INT | Sí |  |  |  |
| nombre_usuario | VARCHAR | Sí |  |  |  |
| pass_usuario | VARCHAR | Sí |  |  |  |
| firma_mensaje | VARCHAR | Sí |  |  |  |
| Foto1 | LONGBLOB | Sí |  |  |  |
| ssl | VARCHAR | Sí |  |  |  |
| cuenta_correo | VARCHAR | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

| Origen | Destino | Archivo | Línea | Fragmento |
|--------|---------|---------|-------|------------|
| correo_usr | usuarios | Crm_CargaLlamada.frm | 2569 | '        rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FR… |
| correo_usr | viajantes | Crm_CargaLlamada.frm | 2569 | '        rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FR… |
| correo_usr | usuarios | Funciones.bas | 13143 | rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FROM correo… |
| correo_usr | viajantes | Funciones.bas | 13143 | rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id_usuario FROM correo… |

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

| Archivo | Línea | Operación | Fragmento |
|---------|-------|-----------|-----------|
| CorreoEnvio2.frm | 1888 | SELECT | "FROM correo_usr " & _ |
| CorreoEnvio2.frm | 2484 | SELECT | rs.Open "SELECT * FROM correo_usr " & _ |
| CorreoEnvio2.frm | 2776 | SELECT | "FROM correo_usr " & _ |
| CorreoEnvio2.frm | 3096 | SELECT | "FROM correo_usr " & _ |
| CorreoEnvio.frm | 978 | SELECT | "FROM correo_usr " & _ |
| Info2.frm | 903 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info2.frm | 1126 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Crm_CargaLlamada.frm | 2569 | SELECT | '        rs_correo.Open "SELECT correo_usr.nombre_usuario,us… |
| Info3.frm | 903 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info3.frm | 1126 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info7.frm | 904 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info7.frm | 1127 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info6.frm | 904 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info6.frm | 1127 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info4.frm | 906 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info4.frm | 1129 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info5.frm | 904 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info5.frm | 1127 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info8.frm | 904 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info8.frm | 1127 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info9.frm | 904 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info9.frm | 1127 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info10.frm | 904 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info10.frm | 1127 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Correo_Configuracion.frm | 503 | INSERT | conn.Execute "INSERT INTO correo_usr " & _ |
| Correo_Configuracion.frm | 515 | UPDATE | conn.Execute "UPDATE correo_usr " & _ |
| Correo_Configuracion.frm | 572 | SELECT | rs.Open "SELECT * FROM correo_usr " & _ |
| Correo_Configuracion.frm | 851 | SELECT | rs_foto.Open "SELECT * FROM correo_usr WHERE id_usuario = " … |
| Correo_Configuracion.frm | 900 | UPDATE | conn.Execute "UPDATE correo_usr SET Foto1 = NULL WHERE id_us… |
| Correo_Configuracion.frm | 944 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & id_… |
| Info.frm | 903 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info.frm | 1126 | SELECT | rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " & Pri… |
| Info.frm | 797 | SELECT | '            rs_datos.Open "SELECT firma_mensaje, foto1 FROM… |
| Info.frm | 1009 | SELECT | '    rs.Open "SELECT * FROM correo_usr WHERE id_usuario = " … |
| Funciones.bas | 13143 | SELECT | rs_correo.Open "SELECT correo_usr.nombre_usuario,usuarios.id… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)