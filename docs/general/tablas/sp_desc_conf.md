# Tabla `sp_desc_conf`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_sp_desc_conf | BIGINT | No | ✓ |  |  |
| valor_calculo_puntaje | DECIMAL | Sí |  |  |  |
| valor_cada_puntaje | DOUBLE | Sí |  |  |  |
| vencimiento_puntaje | INT | Sí |  |  |  |
| tipo_calculo_puntaje | VARCHAR | Sí |  |  |  |
| numeracion_voucher | BIGINT | Sí |  |  |  |

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
| Programa_Descuentos_Configuracion.frm | 332 | SELECT | rs_configuracion_programa_descuentos.Open "SELECT * FROM sp_… |
| Programa_Descuentos_Configuracion.frm | 386 | SELECT | rs_configuracion_programa_descuentos.Open "SELECT * FROM sp_… |
| Programa_Descuentos_Carga.frm | 2515 | SELECT | rs_programa_descuento.Open "SELECT * FROM sp_desc_conf WHERE… |
| Programa_Descuentos_Carga.frm | 2851 | SELECT | '        rs_consulta.Open "SELECT * FROM sp_desc_conf WHERE … |
| Programa_Descuentos_Carga.frm | 3240 | SELECT | rs_consulta.Open "SELECT * FROM sp_desc_conf WHERE id_sp_des… |
| Funciones.bas | 12051 | SELECT | rs_configuracion_sp.Open "SELECT * FROM sp_desc_conf", conn,… |
| Funciones.bas | 12161 | SELECT | rs_configuracion_sp.Open "SELECT * FROM sp_desc_conf", conn,… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)