# Tabla `publicidad`

Base: **administranet**

---

## 1. Schema (information_schema)

### 1.1 Columnas

| Campo | Tipo | Nulo | PK | FK | Referencia |
|-------|------|------|----|----|------------|
| id_publicidad | BIGINT | No | ✓ |  |  |
| nombre_publicidad | VARCHAR | Sí |  |  |  |
| fecha_creacion | TIMESTAMP | Sí |  |  |  |
| vigencia_desde | DATE | Sí |  |  |  |
| vigencia_hasta | DATE | Sí |  |  |  |
| imagen | LONGBLOB | Sí |  |  |  |
| anulado | VARCHAR | Sí |  |  |  |
| tiempo_duracion_segundos | INT | Sí |  |  |  |
| id_usuario | INT | Sí |  |  |  |
| ruta_gif | VARCHAR | Sí |  |  |  |

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
| TPV.frm | 40723 | SELECT | rs.Open "SELECT * FROM publicidad WHERE id_publicidad = " & … |
| TPV.frm | 40803 | SELECT | rs.Open "SELECT id_publicidad,vigencia_desde,vigencia_hasta,… |
| ABM_Publicidad_Carga.frm | 472 | SELECT | rs_publicidad.Open "SELECT * FROM publicidad WHERE nombre_pu… |
| ABM_Publicidad_Carga.frm | 488 | SELECT | rs_publicidad.Open "SELECT * FROM publicidad WHERE id_public… |
| ABM_Publicidad_Carga.frm | 530 | SELECT | rs_publicidad.Open "SELECT * FROM publicidad WHERE id_public… |
| Consulta_Precio_Articulo_Usr.frm | 1707 | SELECT | rs.Open "SELECT * FROM publicidad WHERE id_publicidad = " & … |
| Consulta_Precio_Articulo_Usr.frm | 1784 | SELECT | rs.Open "SELECT id_publicidad,vigencia_desde,vigencia_hasta,… |
| ABM_Publicidad.frm | 624 | SELECT | consulta = "SELECT * FROM publicidad WHERE id_publicidad LIK… |
| ABM_Publicidad.frm | 870 | SELECT | rs.Open "SELECT * FROM publicidad WHERE id_publicidad = " & … |
| Funciones.bas | 8649 | SELECT | rs.Open "SELECT id_publicidad,vigencia_desde,vigencia_hasta,… |

---

## 4. Uso en Synap (reports)

*No se encontraron referencias en el módulo reports.*

[← Índice de tablas](../DB_INDICE_TABLAS.md)