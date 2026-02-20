# Tabla `calculo_temp`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_calculo_temp | DOUBLE | No | ✓ |  |  |
| id_usuario | INT | Sí |  |  |  |
| proceso | VARCHAR | Sí |  |  |  |
| limite_dias | DATE | Sí |  |  |  |

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
| FacturaB_COPIA.frm | 11090 | SELECT | '            conn.Execute "delete from calculo_temp where id… |
| FacturaB_COPIA.frm | 11090 | DELETE | '            conn.Execute "delete from calculo_temp where id… |
| FacturaB_COPIA.frm | 11093 | INSERT | '            conn.Execute "INSERT INTO calculo_temp (id_usua… |
| FacturaB_COPIA.frm | 11110 | SELECT | '             rs_limitescli.Open "SELECT limite_dias as ulti… |
| TPV.frm | 26131 | SELECT | '                conn.Execute "delete from calculo_temp wher… |
| TPV.frm | 26131 | DELETE | '                conn.Execute "delete from calculo_temp wher… |
| TPV.frm | 26134 | INSERT | '                conn.Execute "INSERT INTO calculo_temp (id_… |
| TPV.frm | 26151 | SELECT | '                 rs_limitescli.Open "SELECT limite_dias as … |
| TPV.frm | 33557 | SELECT | '                            conn.Execute "delete from calcu… |
| TPV.frm | 33557 | DELETE | '                            conn.Execute "delete from calcu… |
| TPV.frm | 33560 | INSERT | '                            conn.Execute "INSERT INTO calcu… |
| TPV.frm | 33577 | SELECT | '                             rs_limitescli.Open "SELECT lim… |
| Facturacion_Ciclica.frm | 4647 | SELECT | '                conn.Execute "delete from calculo_temp wher… |
| Facturacion_Ciclica.frm | 4647 | DELETE | '                conn.Execute "delete from calculo_temp wher… |
| Facturacion_Ciclica.frm | 4650 | INSERT | '                conn.Execute "INSERT INTO calculo_temp (id_… |
| Facturacion_Ciclica.frm | 4667 | SELECT | '                 rs_limitescli.Open "SELECT limite_dias as … |
| FacturaB.frm | 16898 | SELECT | '            conn.Execute "delete from calculo_temp where id… |
| FacturaB.frm | 16898 | DELETE | '            conn.Execute "delete from calculo_temp where id… |
| FacturaB.frm | 16901 | INSERT | '            conn.Execute "INSERT INTO calculo_temp (id_usua… |
| FacturaB.frm | 16918 | SELECT | '             rs_limitescli.Open "SELECT limite_dias as ulti… |
| FacturaA.frm | 12980 | SELECT | '            conn.Execute "delete from calculo_temp where id… |
| FacturaA.frm | 12980 | DELETE | '            conn.Execute "delete from calculo_temp where id… |
| FacturaA.frm | 12983 | INSERT | '            conn.Execute "INSERT INTO calculo_temp (id_usua… |
| FacturaA.frm | 13000 | SELECT | '             rs_limitescli.Open "SELECT limite_dias as ulti… |
| Facturacion.frm | 3361 | SELECT | '                conn.Execute "delete from calculo_temp wher… |
| Facturacion.frm | 3361 | DELETE | '                conn.Execute "delete from calculo_temp wher… |
| Facturacion.frm | 3364 | INSERT | '                conn.Execute "INSERT INTO calculo_temp (id_… |
| Facturacion.frm | 3381 | SELECT | '                 rs_limitescli.Open "SELECT limite_dias as … |
| Pedido.frm | 3929 | SELECT | conn.Execute "delete from calculo_temp where id_usuario = " … |
| Pedido.frm | 3929 | DELETE | conn.Execute "delete from calculo_temp where id_usuario = " … |
| Pedido.frm | 3932 | INSERT | conn.Execute "INSERT INTO calculo_temp (id_usuario,proceso,l… |
| Pedido.frm | 3949 | SELECT | rs_limitescli.Open "SELECT limite_dias as ultimaf from calcu… |
| Pedido.frm | 10563 | SELECT | '            conn.Execute "delete from calculo_temp where id… |
| Pedido.frm | 10563 | DELETE | '            conn.Execute "delete from calculo_temp where id… |
| Pedido.frm | 10566 | INSERT | '            conn.Execute "INSERT INTO calculo_temp (id_usua… |
| Pedido.frm | 10583 | SELECT | '             rs_limitescli.Open "SELECT limite_dias as ulti… |
| Carga_Cliente.frm | 6589 | SELECT | '                   conn.Execute "delete from calculo_temp w… |
| Carga_Cliente.frm | 6589 | DELETE | '                   conn.Execute "delete from calculo_temp w… |
| Carga_Cliente.frm | 6592 | INSERT | '                   conn.Execute "INSERT INTO calculo_temp (… |
| Carga_Cliente.frm | 6609 | SELECT | '                    rs_limitescli.Open "SELECT limite_dias … |
| TPV_2.frm | 24164 | SELECT | '                conn.Execute "delete from calculo_temp wher… |
| TPV_2.frm | 24164 | DELETE | '                conn.Execute "delete from calculo_temp wher… |
| TPV_2.frm | 24167 | INSERT | '                conn.Execute "INSERT INTO calculo_temp (id_… |
| TPV_2.frm | 24184 | SELECT | '                 rs_limitescli.Open "SELECT limite_dias as … |
| TPV_2.frm | 31588 | SELECT | '                            conn.Execute "delete from calcu… |
| TPV_2.frm | 31588 | DELETE | '                            conn.Execute "delete from calcu… |
| TPV_2.frm | 31591 | INSERT | '                            conn.Execute "INSERT INTO calcu… |
| TPV_2.frm | 31608 | SELECT | '                             rs_limitescli.Open "SELECT lim… |
| Principal.frm | 6105 | SELECT | conn.Execute "delete from calculo_temp where id_usuario = " … |
| Principal.frm | 6105 | DELETE | conn.Execute "delete from calculo_temp where id_usuario = " … |
| Principal.frm | 6171 | SELECT | conn.Execute "delete from calculo_temp where id_usuario = " … |
| Principal.frm | 6171 | DELETE | conn.Execute "delete from calculo_temp where id_usuario = " … |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)