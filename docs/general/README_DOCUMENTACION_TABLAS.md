# Documentación de tablas de la base AdministraNET

Este proceso genera documentación **tabla por tabla** para:

1. **Diseño de una nueva DB normalizada**: schema actual (columnas, PK, FK) y **relaciones inferidas desde las consultas SQL** usadas en VB6 y Synap (la base actual no está normalizada; los JOINs del código son la fuente de verdad).
2. **Migración AdministraNET → Synap**: **uso de cada tabla** en formularios y procedimientos VB6, y en el módulo reports de Synap (como base para migración completa, análoga a la del TPV).

## Cómo generar la documentación

**Requisito:** Conexión a la base MySQL y `mysqlclient` instalado (`pip install mysqlclient`). La base por defecto se toma de `DEFAULT_BASE_EMPRESA` / `DB_NAME` en `.env`.

```bash
# Con la base por defecto (DB_NAME en .env)
python manage.py documentar_tablas_db

# Especificar base
python manage.py documentar_tablas_db --base-empresa administranet89

# Solo schema desde information_schema (no escanea VB6/Synap)
python manage.py documentar_tablas_db --solo-schema

# Ruta custom a VB6 y salida
python manage.py documentar_tablas_db --vb6 /ruta/administranet_vb6 --output-dir docs/general
```

## Salida

- **`DB_INDICE_TABLAS.md`**: Índice con enlace a cada tabla.
- **`tablas/<nombre_tabla>.md`**: Por cada tabla:
  - **1. Schema**: columnas, tipos, PK, FK (desde `information_schema`).
  - **2. Relaciones inferidas desde SQL**: JOINs donde participa la tabla (archivo, línea, fragmento) — fundamental para normalización.
  - **3. Uso en AdministraNET (VB6)**: archivo, línea, operación (SELECT/INSERT/UPDATE/DELETE/JOIN), fragmento.
  - **4. Uso en Synap (reports)**: referencias en código Python de reports.

## Servicios utilizados

- **`SemanticService`** (`reports/services/semantic_service.py`): `list_datasources(base_empresa)`, `get_fields()`, `get_relationships()`.
- **`documentacion_db_service`** (`reports/services/documentacion_db_service.py`): extracción de tablas y JOINs desde VB6 (`.frm`, `.bas`) y Synap (`reports/**/*.py`).

## Documentos de referencia (mismo estilo)

- `STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md` — quién escribe/lee en `stock`.
- `STOCKP_VB6_PROCEDIMIENTOS_GUARDADO.md` — quién escribe/lee en `stockp`.
- `INFO_COMPRA_TABLAS_CAMPOS.md` — tablas y campos en informes de compra.

La documentación generada por tabla puede ampliarse manualmente con el mismo nivel de detalle (por formulario, tipo de comprobante, condiciones) para la migración completa.
