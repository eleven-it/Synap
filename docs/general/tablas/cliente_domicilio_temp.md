# Tabla `cliente_domicilio_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_cliente_domicilio_temp | DOUBLE | No | ✓ |  |  |
| Calle | VARCHAR | Sí |  |  |  |
| NroCalle | VARCHAR | Sí |  |  |  |
| Dpto | VARCHAR | Sí |  |  |  |
| IDDistrito | INT | Sí |  |  |  |
| CodProvincia | INT | Sí |  |  |  |
| IDDepartamento | INT | Sí |  |  |  |
| id_zona | INT | Sí |  |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| id_usuario | DOUBLE | Sí |  |  |  |
| visualiza | VARCHAR | Sí |  |  |  |
| NombreProv | VARCHAR | Sí |  |  |  |
| NombreDpto | VARCHAR | Sí |  |  |  |
| NombreDist | VARCHAR | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| diasContacto | VARCHAR | Sí |  |  |  |
| id_cliente_domicilio | DOUBLE | Sí |  |  |  |
| id_pais | INT | Sí |  |  |  |
| geo_latitud | VARCHAR | Sí |  |  |  |
| geo_longitud | VARCHAR | Sí |  |  |  |
| distancia_sucursal | DECIMAL | Sí |  |  |  |
| hora_desde | TIME | Sí |  |  |  |
| hora_hasta | TIME | Sí |  |  |  |
| periodicidad_visita_vendedor | VARCHAR | Sí |  |  |  |
| visita_vendedor_valor | VARCHAR | Sí |  |  |  |
| nro_seguimiento | VARCHAR | Sí |  |  |  |

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
| Cliente.frm | 2984 | SELECT | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Cliente.frm | 2984 | DELETE | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Cliente.frm | 2987 | INSERT | conn.Execute "INSERT INTO cliente_domicilio_temp " & _ |
| Cliente.frm | 3002 | SELECT | Carga_Cliente.DataDomicilios.RecordSource = "SELECT * FROM c… |
| Visualiza_CliDom.frm | 909 | SELECT | '    conn.Execute "delete from cliente_domicilio_temp where … |
| Visualiza_CliDom.frm | 909 | DELETE | '    conn.Execute "delete from cliente_domicilio_temp where … |
| Visualiza_CliDom.frm | 911 | INSERT | '    conn.Execute "INSERT INTO cliente_domicilio_temp " & _ |
| Visualiza_CliDom.frm | 926 | SELECT | '    DataDomicilios.RecordSource = "SELECT * FROM cliente_do… |
| Carga_ClienteDomicilio.frm | 1448 | SELECT | rs_consulta.Open "SELECT * FROM cliente_domicilio_temp WHERE… |
| Carga_ClienteDomicilio.frm | 1465 | SELECT | DataDomicilios.RecordSource = "SELECT * FROM cliente_domicil… |
| Carga_ClienteDomicilio.frm | 1525 | SELECT | Carga_Cliente.DataDomicilios.RecordSource = "SELECT * FROM c… |
| Carga_ClienteDomicilio.frm | 1643 | SELECT | Carga_Cliente.DataDomicilios.RecordSource = "SELECT * FROM c… |
| Facturacion.frm | 3486 | SELECT | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Facturacion.frm | 3486 | DELETE | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Facturacion.frm | 3488 | INSERT | conn.Execute "INSERT INTO cliente_domicilio_temp " & _ |
| Facturacion.frm | 3501 | SELECT | Carga_Cliente.DataDomicilios.RecordSource = "SELECT * FROM c… |
| Carga_Cliente.frm | 4770 | SELECT | conn.Execute "DELETE FROM cliente_domicilio_temp WHERE id_cl… |
| Carga_Cliente.frm | 4770 | DELETE | conn.Execute "DELETE FROM cliente_domicilio_temp WHERE id_cl… |
| Carga_Cliente.frm | 5598 | SELECT | "FROM cliente_domicilio_temp " & _ |
| Carga_Cliente.frm | 5943 | SELECT | "FROM cliente_domicilio_temp " & _ |
| Carga_Cliente.frm | 5952 | SELECT | "FROM cliente_domicilio_temp " & _ |
| Carga_Cliente.frm | 6055 | SELECT | '            conn.Execute "delete from cliente_domicilio_tem… |
| Carga_Cliente.frm | 6055 | DELETE | '            conn.Execute "delete from cliente_domicilio_tem… |
| Carga_Cliente.frm | 7233 | SELECT | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Carga_Cliente.frm | 7233 | DELETE | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Principal.frm | 6107 | SELECT | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Principal.frm | 6107 | DELETE | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Principal.frm | 6173 | SELECT | conn.Execute "delete from cliente_domicilio_temp where id_us… |
| Principal.frm | 6173 | DELETE | conn.Execute "delete from cliente_domicilio_temp where id_us… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)