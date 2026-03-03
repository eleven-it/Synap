# Tabla `en_vale_factura`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_en_vale_factura | BIGINT | No | ✓ |  |  |
| CodMovVale | BIGINT | Sí |  |  |  |
| CodMovFactura | BIGINT | Sí |  |  |  |
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
| PFactura.frm | 4170 | INSERT | conn.Execute "INSERT INTO en_vale_factura(CodMovVale,CodMovF… |
| ConsultaComprobante.frm | 30023 | JOIN | conn.Execute "UPDATE en_vale_viaje LEFT JOIN en_vale_factura… |
| En_Liquidacion_Vales.frm | 2691 | SELECT | " FROM en_vale_factura as f" & _ |
| Visualiza.bas | 4673 | SELECT | rs_vales.Open "SELECT * FROM en_vale_factura WHERE en_vale_f… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)