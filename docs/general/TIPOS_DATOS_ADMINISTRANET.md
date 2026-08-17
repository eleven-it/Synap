# Tipos de datos y normalización con AdministraNET

## Regla de proyecto

En **todo el código** que lea o escriba datos en MySQL de administraNET (bases/tablas compartidas con VB6), se deben **validar y normalizar** los tipos de datos para cumplir el **mismo criterio que AdministraNET**.

Así se evitan inconsistencias (por ejemplo no ver en Synap cambios hechos en VB6, o guardar valores que VB6 no espera) y se mantiene compatibilidad con el schema y el comportamiento de los formularios VB6.

## Criterios por tipo de columna

| Tipo MySQL   | Criterio                                                                 | Uso en código |
|-------------|---------------------------------------------------------------------------|----------------|
| **INT** (nullable) | Enviar `int` o `None`. No enviar string numérico sin convertir.           | `to_int_or_none(val)` |
| **DATE** (nullable) | Enviar string `'YYYY-MM-DD'` o `None`. No enviar string vacío (evitar `0000-00-00`). | `to_date_or_none(val)` |
| **VARCHAR / MEDIUMTEXT** | Enviar string. Para campos opcionales vacíos, usar el mismo valor por defecto que VB6 (ej. `'-'`). | `str_or_default(val, default='')` o `str_or_default(val, '-')` |
| **DECIMAL** (nullable) | Enviar `Decimal` o `None`. Opcional redondear con `quantize`.             | `to_decimal_or_none(val, quantize='0.01')` |

## Módulo centralizado

Las funciones de normalización están en **`core.utils.administranet_types`**:

- `to_int_or_none(value)` → `Optional[int]`
- `to_date_or_none(value)` → `Optional[str]` (formato 'YYYY-MM-DD')
- `str_or_default(value, default='')` → `str`
- `str_codigo_manual_articulo(id_manual)` → `str` (solo `articulo.id_manual` para UI; no sustituir por código de talón; ver docstring en el módulo)
- `to_decimal_or_none(value, quantize=None)` → `Optional[Decimal]`

**Uso:** en servicios que escriban o lean tablas administraNET (empresa, sucursales, usuarios, permisos, etc.), importar y usar estas funciones antes de armar los diccionarios para `cursor.execute` o al mapear filas a diccionarios.

## Dónde aplica

- Servicios en `core/services/administranet_*.py` (empresas, sucursales, usuarios, puestos, permisos).
- Cualquier otro módulo que use `core.mysql_pool` o conexión MySQL hacia bases administraNET para leer/escribir tablas (reports, self_checkout, login, etc.).

## Referencia de schema

- Tablas y columnas: `reports/docs/tablas/*.md`, `docs/general/tablas/*.md`.
- Comportamiento de formularios VB6: `docs/general/MIGRACION_ADMINISTRANET_VB6_ANALISIS.md`.

## `articulo.tipo_art` (artículos de venta)

Columna VARCHAR en AdministraNET (valores típicos: `Articulo`, `Gasto`, `Servicio`). En reportes de **artículos de venta** y en **inventario por etapa** se excluye siempre `tipo_art = 'Gasto'` (`core.utils.articulo_tipo_sql`). No confundir con `tipo_art_fab`. Ver [FILTRO_TIPO_ART_GASTO.md](../reports/FILTRO_TIPO_ART_GASTO.md).

## Compatibilidad Empresa.frm (DatosEmpresa)

- **Tablas:** Empresa.frm puede usar `DatosEmpresa` o `datosempresa2` (según flujo, ver MIGRACION_ADMINISTRANET_VB6_ANALISIS.md § 3.1). Synap al guardar actualiza **ambas** tablas si existen, para que AdministraNET muestre los mismos datos con independencia de a cuál esté enlazado el formulario.
- **actividad / rubro_canal:** En VB6 son controles de texto; se guarda el valor tal cual. Vacío se persiste como `'-'` para compatibilidad. Synap envía el valor seleccionado o escrito sin forzar mayúsculas ni formatos adicionales.

## Regla en el flujo de desarrollo

Al agregar o modificar código que toque MySQL administraNET:

1. Usar siempre las funciones de `core.utils.administranet_types` para los tipos anteriores.
2. No asumir que el valor que llega (formulario, API, sesión) ya está en el tipo correcto; normalizar antes de usarlo en la consulta.
3. Resolver nombres de tablas con mayúsculas/minúsculas cuando corresponda (p. ej. `_nombre_tabla(cursor, "datosempresa")`) para compatibilidad con distintos servidores MySQL.
