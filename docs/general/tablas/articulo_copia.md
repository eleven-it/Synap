# Tabla `articulo_copia`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| IDArt | INT | No | ✓ |  |  |
| id_manual | VARCHAR | Sí |  |  |  |
| CodigoRubro | INT | Sí |  |  |  |
| CodigoSubRubro | INT | No |  |  |  |
| CodigoSubRubroT | VARCHAR | No |  |  |  |
| CodigoArticulo | INT | Sí |  |  |  |
| IDSubRubro | INT | Sí |  |  |  |
| CodigoArticuloT | VARCHAR | No |  |  |  |
| CodArtProv | VARCHAR | Sí |  |  |  |
| NombreArticulo | VARCHAR | Sí |  |  |  |
| PrecioCosto | DECIMAL | Sí |  |  |  |
| Util1 | DECIMAL | Sí |  |  |  |
| Util2 | DECIMAL | Sí |  |  |  |
| Util3 | DECIMAL | Sí |  |  |  |
| Util4 | DECIMAL | Sí |  |  |  |
| Util5 | DECIMAL | Sí |  |  |  |
| Precio1V | DECIMAL | Sí |  |  |  |
| Precio2V | DECIMAL | Sí |  |  |  |
| Precio3V | DECIMAL | Sí |  |  |  |
| Precio4V | DECIMAL | Sí |  |  |  |
| Precio5V | DECIMAL | Sí |  |  |  |
| Precio1VI | DECIMAL | Sí |  |  |  |
| Precio2VI | DECIMAL | Sí |  |  |  |
| Precio3VI | DECIMAL | Sí |  |  |  |
| Precio4VI | DECIMAL | Sí |  |  |  |
| Precio5VI | DECIMAL | Sí |  |  |  |
| PNOficial | DECIMAL | Sí |  |  |  |
| PFOficial | DECIMAL | Sí |  |  |  |
| PorOficial1 | DECIMAL | Sí |  |  |  |
| PorOficial2 | DECIMAL | Sí |  |  |  |
| PorOficial3 | DECIMAL | Sí |  |  |  |
| UtilOficial | DECIMAL | Sí |  |  |  |
| Alicuota | INT | Sí |  |  |  |
| AlicuotaIB | INT | No |  |  |  |
| saldo_articulo | INT | Sí |  |  |  |
| Moneda | VARCHAR | Sí |  |  |  |
| TipoIVA | VARCHAR | Sí |  |  |  |
| TipoIB | VARCHAR | No |  |  |  |
| CodigoProveedor | INT | Sí |  |  |  |
| CodigoModelo | INT | Sí |  |  |  |
| CodigoMarca | INT | Sí |  |  |  |
| CodLaboratorio | INT | Sí |  |  |  |
| NroCodBarra | VARCHAR | Sí |  |  |  |
| NroCodBarraF | VARCHAR | Sí |  |  |  |
| Simbologia | VARCHAR | Sí |  |  |  |
| SimbologiaF | VARCHAR | Sí |  |  |  |
| Foto1 | LONGBLOB | Sí |  |  |  |
| Foto2 | LONGBLOB | Sí |  |  |  |
| Discontinuo | VARCHAR | No |  |  |  |
| Detalle | LONGTEXT | Sí |  |  |  |
| lote | VARCHAR | Sí |  |  |  |
| tipo_art | VARCHAR | Sí |  |  |  |
| cod_gasto | INT | Sí |  |  |  |
| cod_act_iibb | INT | Sí |  |  |  |
| stock_max | DECIMAL | Sí |  |  |  |
| stock_min | DECIMAL | Sí |  |  |  |
| punto_pedido | INT | Sí |  |  |  |
| promocion | VARCHAR | Sí |  |  |  |
| promocion_por | DECIMAL | Sí |  |  |  |
| promocion_cant | DECIMAL | Sí |  |  |  |
| promocion_alcance | VARCHAR | Sí |  |  |  |
| promocion_tipo | VARCHAR | Sí |  |  |  |
| promocion_listaoficial | VARCHAR | Sí |  |  |  |
| promocion_lista1 | VARCHAR | Sí |  |  |  |
| promocion_lista2 | VARCHAR | Sí |  |  |  |
| promocion_lista3 | VARCHAR | Sí |  |  |  |
| promocion_lista4 | VARCHAR | Sí |  |  |  |
| promocion_lista5 | VARCHAR | Sí |  |  |  |
| promocion_destacado_web | VARCHAR | Sí |  |  |  |
| impuesto_interno | DECIMAL | Sí |  |  |  |
| promocion_vigencia_hasta | DATE | Sí |  |  |  |
| promocion_vigencia_desde | DATE | Sí |  |  |  |
| id_unimed | DOUBLE | Sí |  |  |  |
| AlicuotaC | INT | Sí |  |  |  |
| ecommerce | VARCHAR | Sí |  |  |  |
| id_pc_vta | DOUBLE | Sí |  |  |  |
| id_pc_comp | DOUBLE | Sí |  |  |  |
| limVtaxArt | DECIMAL | Sí |  |  |  |
| detalle_web | LONGTEXT | Sí |  |  |  |
| id_proyecto | INT | Sí |  |  |  |
| recalcula_pc | VARCHAR | Sí |  |  |  |
| recalcula_pv | VARCHAR | Sí |  |  |  |
| ensamblado | VARCHAR | Sí |  |  |  |
| id_en_abm | DOUBLE | Sí |  |  |  |

### 1.2 Relaciones (FK del catálogo)

*No hay claves foráneas definidas en el catálogo para esta tabla.*

---

## 2. Relaciones inferidas desde consultas SQL

Relaciones detectadas por uso en código (JOINs en VB6 y Synap). Sirven para diseñar una DB normalizada.

*No se encontraron JOINs que involucren esta tabla en el código escaneado.*

---

## 3. Uso en AdministraNET (VB6)

Formularios y procedimientos que referencian esta tabla (lectura/escritura). Base para migración AdministraNET → Synap.

*No se encontraron referencias a esta tabla en el código VB6 escaneado.*

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)