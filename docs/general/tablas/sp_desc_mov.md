# Tabla `sp_desc_mov`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sp_desc_mov | BIGINT | No | ✓ |  |  |
| id_cliente | DOUBLE | Sí |  |  |  |
| fecha | DATE | Sí |  |  |  |
| tipo_comp | VARCHAR | Sí |  |  |  |
| nro_comp | VARCHAR | Sí |  |  |  |
| monto_neto | DOUBLE | Sí |  |  |  |
| monto_final | DOUBLE | Sí |  |  |  |
| puntos_acumulados | DOUBLE | Sí |  |  |  |
| valor_cada_puntaje | DOUBLE | Sí |  |  |  |
| valor_calculo_puntaje | DOUBLE | Sí |  |  |  |
| codigo_movimiento | BIGINT | Sí |  |  |  |
| codigo_movimiento_anul | BIGINT | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| fecha_control | TIMESTAMP | Sí |  |  |  |

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
| Funciones.bas | 12065 | SELECT | rs_sp_movimiento_premios.Open "SELECT * FROM sp_desc_mov WHE… |
| Funciones.bas | 12175 | SELECT | rs_sp_movimiento_premios.Open "SELECT * FROM sp_desc_mov WHE… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)